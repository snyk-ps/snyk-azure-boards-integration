"""HTTP client for Azure DevOps Work Item Tracking (WIT)."""

from __future__ import annotations

import base64
import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from observability.integration_audit import log_integration_http
from observability.sync_context import get_sync_run_id

from integrations.azure_devops.constants import (
    AZURE_DEVOPS_COMMENT_API_VERSION,
    AZURE_DEVOPS_PAT_ENV,
    AZURE_DEVOPS_WIT_API_VERSION,
    DEFAULT_AZURE_DEVOPS_BASE_URL,
    JSON_PATCH_CONTENT_TYPE,
)
from integrations.azure_devops.errors import (
    AzureDevOpsApiError,
    AzureDevOpsAuthError,
    AzureDevOpsClientError,
    AzureDevOpsRateLimitError,
    AzureDevOpsServerError,
    AzureDevOpsTransportError,
    MissingPatError,
)
from integrations.azure_devops.normalize import (
    normalize_comment_document,
    normalize_work_item_document,
)
from integrations.azure_devops.urls import (
    normalize_devops_base_url,
    work_item_comment_url,
    work_item_create_url,
    work_item_get_url,
    work_items_list_url,
    work_item_update_url,
)

MAX_IDS_PER_LIST = 200
MAX_GET_EXTRA_RETRIES = 2
RATE_LIMIT_MAX_WAIT_SECONDS = 70.0

_Opener = Callable[..., Any]
_SleepFn = Callable[[float], None]
_MonotonicFn = Callable[[], float]


def _parse_retry_after_seconds(headers: object | None) -> float | None:
    """Parse ``Retry-After`` as delta-seconds; return ``None`` if missing or invalid."""
    if headers is None or not hasattr(headers, "get"):
        return None
    raw = headers.get("Retry-After")  # type: ignore[union-attr]
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _backoff_seconds(attempt_index: int) -> float:
    """Exponential backoff capped at 60 seconds (attempt 0 → 1s)."""
    return min(60.0, float(2**max(0, attempt_index)))


def _status_message(code: int) -> str:
    return f"Azure DevOps API HTTP error {code}"


class WorkItemsClient:
    """Create, read, update, and comment on Azure DevOps work items (WIT v1 surface)."""

    def __init__(
        self,
        base_url: str = DEFAULT_AZURE_DEVOPS_BASE_URL,
        *,
        timeout: float = 60.0,
        pat: str | None = None,
        opener: _Opener | None = None,
        sleep_fn: _SleepFn | None = None,
        monotonic_fn: _MonotonicFn | None = None,
        wit_api_version: str | None = None,
        comment_api_version: str | None = None,
        rate_limit_max_wait_seconds: float = RATE_LIMIT_MAX_WAIT_SECONDS,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: API origin, default ``https://dev.azure.com``.
            timeout: Socket timeout in seconds for each HTTP request.
            pat: Optional PAT; if omitted, ``AZURE_DEVOPS_PAT`` is read when a request runs.
            opener: Injectable ``urlopen`` for tests.
            sleep_fn: Injectable sleep (defaults to :func:`time.sleep`).
            monotonic_fn: Injectable monotonic clock (defaults to :func:`time.monotonic`).
            wit_api_version: Override WIT ``api-version`` (intended for tests).
            comment_api_version: Override comments ``api-version`` (intended for tests).
            rate_limit_max_wait_seconds: Max wall time to spend retrying HTTP 429.
        """
        self._base_url = normalize_devops_base_url(base_url)
        self._timeout = timeout
        self._pat = pat
        self._opener: _Opener = opener if opener is not None else urlopen
        self._sleep = sleep_fn if sleep_fn is not None else time.sleep
        self._monotonic = monotonic_fn if monotonic_fn is not None else time.monotonic
        self._wit_api_version = wit_api_version or AZURE_DEVOPS_WIT_API_VERSION
        self._comment_api_version = comment_api_version or AZURE_DEVOPS_COMMENT_API_VERSION
        self._rate_limit_max_wait_seconds = rate_limit_max_wait_seconds

    @property
    def base_url(self) -> str:
        """Configured API origin (normalized, no trailing slash)."""
        return self._base_url

    def _require_pat(self) -> str:
        if self._pat is not None and str(self._pat).strip():
            return str(self._pat).strip()
        t = os.environ.get(AZURE_DEVOPS_PAT_ENV, "").strip()
        if not t:
            raise MissingPatError(f"{AZURE_DEVOPS_PAT_ENV} is not set or empty")
        return t

    def _basic_auth_header(self) -> str:
        token = self._require_pat()
        raw = base64.b64encode(f":{token}".encode("utf-8")).decode("ascii")
        return f"Basic {raw}"

    def _headers_json(self, *, content_type: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "Authorization": self._basic_auth_header(),
            "Accept": "application/json",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _raise_http(self, exc: HTTPError) -> None:
        code = int(exc.code)
        if code in (401, 403):
            raise AzureDevOpsAuthError(_status_message(code), status_code=code) from exc
        if code == 429:
            raise AzureDevOpsRateLimitError(_status_message(code), status_code=code) from exc
        if 400 <= code < 500:
            raise AzureDevOpsClientError(_status_message(code), status_code=code) from exc
        if code >= 500:
            raise AzureDevOpsServerError(_status_message(code), status_code=code) from exc
        raise AzureDevOpsApiError(_status_message(code), status_code=code) from exc

    def _read_json_response(self, body: bytes) -> dict[str, Any]:
        try:
            val: Any = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AzureDevOpsClientError(
                "Response was not valid UTF-8 JSON",
                status_code=None,
            ) from exc
        if not isinstance(val, dict):
            raise AzureDevOpsClientError("Expected JSON object response", status_code=None)
        return val

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        mutating: bool,
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        deadline_429 = self._monotonic() + self._rate_limit_max_wait_seconds
        attempt_429 = 0
        attempt_get_recovery = 0
        start = self._monotonic()
        m = (method or "GET").upper()
        while True:
            req = Request(
                url,
                data=body,
                headers=self._headers_json(content_type=content_type),
                method=method,
            )
            try:
                with self._opener(req, timeout=self._timeout) as resp:
                    raw_body = resp.read()
                    raw_status = getattr(resp, "status", None)
                    if raw_status is None:
                        raw_status = getattr(resp, "code", None)
                    status = int(raw_status) if raw_status is not None else 200
            except HTTPError as exc:
                code = int(exc.code)
                elapsed_ms = (self._monotonic() - start) * 1000.0
                if code == 429:
                    ra = _parse_retry_after_seconds(getattr(exc, "headers", None))
                    wait = ra if ra is not None else _backoff_seconds(attempt_429)
                    now = self._monotonic()
                    if now + wait > deadline_429:
                        log_integration_http(
                            integration="azure_devops",
                            method=m,
                            url=url,
                            status_code=429,
                            duration_ms=elapsed_ms,
                            sync_run_id=get_sync_run_id(),
                            error="rate limit (429); retry budget exhausted",
                        )
                        raise AzureDevOpsRateLimitError(
                            "Azure DevOps API rate limit (429); retry budget exhausted",
                            status_code=429,
                        ) from exc
                    self._sleep(wait)
                    attempt_429 += 1
                    continue
                if (not mutating) and code >= 500 and attempt_get_recovery < MAX_GET_EXTRA_RETRIES:
                    self._sleep(_backoff_seconds(attempt_get_recovery))
                    attempt_get_recovery += 1
                    continue
                log_integration_http(
                    integration="azure_devops",
                    method=m,
                    url=url,
                    status_code=code,
                    duration_ms=elapsed_ms,
                    sync_run_id=get_sync_run_id(),
                )
                self._raise_http(exc)
            except URLError as exc:
                if not mutating and attempt_get_recovery < MAX_GET_EXTRA_RETRIES:
                    self._sleep(_backoff_seconds(attempt_get_recovery))
                    attempt_get_recovery += 1
                    continue
                elapsed_ms = (self._monotonic() - start) * 1000.0
                log_integration_http(
                    integration="azure_devops",
                    method=m,
                    url=url,
                    status_code=None,
                    duration_ms=elapsed_ms,
                    sync_run_id=get_sync_run_id(),
                    error=str(exc.reason or exc),
                )
                raise AzureDevOpsTransportError(str(exc.reason or exc)) from exc
            except OSError as exc:
                if not mutating and attempt_get_recovery < MAX_GET_EXTRA_RETRIES:
                    self._sleep(_backoff_seconds(attempt_get_recovery))
                    attempt_get_recovery += 1
                    continue
                elapsed_ms = (self._monotonic() - start) * 1000.0
                log_integration_http(
                    integration="azure_devops",
                    method=m,
                    url=url,
                    status_code=None,
                    duration_ms=elapsed_ms,
                    sync_run_id=get_sync_run_id(),
                    error=str(exc),
                )
                raise AzureDevOpsTransportError(str(exc)) from exc

            elapsed_ms = (self._monotonic() - start) * 1000.0
            try:
                doc = self._read_json_response(raw_body)
            except AzureDevOpsClientError as exc:
                log_integration_http(
                    integration="azure_devops",
                    method=m,
                    url=url,
                    status_code=status,
                    duration_ms=elapsed_ms,
                    sync_run_id=get_sync_run_id(),
                    error=str(exc),
                )
                raise
            log_integration_http(
                integration="azure_devops",
                method=m,
                url=url,
                status_code=status,
                duration_ms=elapsed_ms,
                sync_run_id=get_sync_run_id(),
            )
            return doc

    def create_work_item(
        self,
        organization: str,
        project: str,
        work_item_type: str,
        patch_operations: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Create a work item from JSON Patch operations; return a normalized record."""
        url = work_item_create_url(
            self._base_url,
            organization,
            project,
            work_item_type,
            api_version=self._wit_api_version,
        )
        body = json.dumps(list(patch_operations)).encode("utf-8")
        doc = self._request_json(
            "POST",
            url,
            mutating=True,
            body=body,
            content_type=JSON_PATCH_CONTENT_TYPE,
        )
        return normalize_work_item_document(doc)

    def get_work_item(
        self,
        organization: str,
        project: str,
        work_item_id: str | int,
    ) -> dict[str, Any]:
        """Fetch a single work item; return a normalized record."""
        url = work_item_get_url(
            self._base_url,
            organization,
            project,
            work_item_id,
            api_version=self._wit_api_version,
        )
        doc = self._request_json("GET", url, mutating=False)
        return normalize_work_item_document(doc)

    def list_work_items_by_ids(
        self,
        organization: str,
        project: str,
        ids: Sequence[str | int],
    ) -> list[dict[str, Any]]:
        """List work items by ids (max 200 per call); return normalized records."""
        id_list = list(ids)
        if len(id_list) > MAX_IDS_PER_LIST:
            raise AzureDevOpsClientError(
                f"list_work_items_by_ids accepts at most {MAX_IDS_PER_LIST} ids "
                f"(got {len(id_list)})",
                status_code=None,
            )
        if not id_list:
            return []
        url = work_items_list_url(
            self._base_url,
            organization,
            project,
            id_list,
            api_version=self._wit_api_version,
        )
        doc = self._request_json("GET", url, mutating=False)
        value = doc.get("value")
        if not isinstance(value, list):
            raise AzureDevOpsClientError("Unexpected list response shape", status_code=None)
        out: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                out.append(normalize_work_item_document(item))
        return out

    def update_work_item(
        self,
        organization: str,
        project: str,
        work_item_id: str | int,
        patch_operations: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Update fields via JSON Patch; return a normalized record."""
        url = work_item_update_url(
            self._base_url,
            organization,
            project,
            work_item_id,
            api_version=self._wit_api_version,
        )
        body = json.dumps(list(patch_operations)).encode("utf-8")
        doc = self._request_json(
            "PATCH",
            url,
            mutating=True,
            body=body,
            content_type=JSON_PATCH_CONTENT_TYPE,
        )
        return normalize_work_item_document(doc)

    def add_work_item_comment(
        self,
        organization: str,
        project: str,
        work_item_id: str | int,
        text: str,
    ) -> dict[str, Any]:
        """Append a discussion comment; return a normalized comment record."""
        url = work_item_comment_url(
            self._base_url,
            organization,
            project,
            work_item_id,
            api_version=self._comment_api_version,
        )
        body = json.dumps({"text": text}).encode("utf-8")
        doc = self._request_json(
            "POST",
            url,
            mutating=True,
            body=body,
            content_type="application/json",
        )
        return normalize_comment_document(doc, work_item_id=work_item_id)
