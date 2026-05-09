"""HTTP client for Snyk REST Issues endpoints (group and org scope)."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from snyk.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_EFFECTIVE_SEVERITY_LEVELS,
    ISSUES_LIST_LIMIT,
    SNYK_JSON_API_CONTENT_TYPE,
    SNYK_REST_API_VERSION,
)
from snyk.errors import (
    MissingTokenError,
    SnykApiError,
    SnykAuthError,
    SnykClientError,
    SnykRateLimitError,
    SnykServerError,
    SnykTransportError,
)
from observability.integration_audit import log_integration_http
from observability.sync_context import get_sync_run_id
from snyk.parser import (
    IssuesListPage,
    build_included_index,
    included_index_from_document,
    normalized_issue_record,
    parse_issues_list_document,
    parse_single_issue_document,
)
from snyk.urls import normalize_base_url, resolve_next_url

_Opener = Callable[..., Any]
_SleepFn = Callable[[float], None]
_MonotonicFn = Callable[[], float]


@dataclass(frozen=True)
class GroupIssueListParams:
    """Optional filters for ``GET /groups/{group_id}/issues`` first page.

    ``effective_severity_levels``:
        ``None`` — use :data:`DEFAULT_EFFECTIVE_SEVERITY_LEVELS` (high, critical).
        Empty tuple — omit severity query parameters (no filter).
        Non-empty — comma-separated ``effective_severity_level`` query value
        (e.g. ``high,critical``), matching Snyk list ``links`` pagination.
    """

    effective_severity_levels: tuple[str, ...] | None = None
    issue_type: str | None = None
    status: str | None = None


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


class IssuesClient:
    """Fetch issues from Snyk REST API (group and org scope)."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 60.0,
        token: str | None = None,
        opener: _Opener | None = None,
        sleep_fn: _SleepFn | None = None,
        monotonic_fn: _MonotonicFn | None = None,
        rate_limit_max_wait_seconds: float = 70.0,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: REST API base, default ``https://api.snyk.io/rest`` (no
                trailing slash recommended).
            timeout: Socket timeout in seconds for each HTTP request.
            token: Optional token; if omitted, ``SNYK_TOKEN`` is read from the
                environment when a request is made.
            opener: Injectable ``urlopen`` for tests.
            sleep_fn: Injectable sleep (defaults to :func:`time.sleep`).
            monotonic_fn: Injectable monotonic clock (defaults to
                :func:`time.monotonic`).
            rate_limit_max_wait_seconds: Max wall time to spend retrying HTTP 429.
        """
        self._base_url = normalize_base_url(base_url)
        self._timeout = timeout
        self._token = token
        self._opener: _Opener = opener if opener is not None else urlopen
        self._sleep = sleep_fn if sleep_fn is not None else time.sleep
        self._monotonic = monotonic_fn if monotonic_fn is not None else time.monotonic
        self._rate_limit_max_wait_seconds = rate_limit_max_wait_seconds

    @property
    def base_url(self) -> str:
        """Configured REST base URL (normalized, no trailing slash)."""
        return self._base_url

    def _require_token(self) -> str:
        if self._token is not None and str(self._token).strip():
            return str(self._token).strip()
        t = os.environ.get("SNYK_TOKEN", "").strip()
        if not t:
            raise MissingTokenError("SNYK_TOKEN is not set or empty")
        return t

    def _request_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"token {self._require_token()}",
            "Accept": SNYK_JSON_API_CONTENT_TYPE,
            "Content-Type": SNYK_JSON_API_CONTENT_TYPE,
        }

    def _get_json(self, url: str) -> dict[str, Any]:
        """GET JSON document; retry on HTTP 429 with bounded backoff."""
        deadline = self._monotonic() + self._rate_limit_max_wait_seconds
        attempt_429 = 0
        start = self._monotonic()
        method = "GET"
        while True:
            req = Request(url, headers=self._request_headers(), method=method)
            try:
                with self._opener(req, timeout=self._timeout) as resp:
                    body = resp.read()
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
                    if now + wait > deadline:
                        log_integration_http(
                            integration="snyk",
                            method=method,
                            url=url,
                            status_code=429,
                            duration_ms=elapsed_ms,
                            sync_run_id=get_sync_run_id(),
                            error="rate limit (429); retry budget exhausted",
                        )
                        raise SnykRateLimitError(
                            "Snyk API rate limit (429); retry budget exhausted",
                            status_code=429,
                        ) from exc
                    self._sleep(wait)
                    attempt_429 += 1
                    continue
                log_integration_http(
                    integration="snyk",
                    method=method,
                    url=url,
                    status_code=code,
                    duration_ms=elapsed_ms,
                    sync_run_id=get_sync_run_id(),
                )
                self._raise_http_error(exc)
            except URLError as exc:
                elapsed_ms = (self._monotonic() - start) * 1000.0
                log_integration_http(
                    integration="snyk",
                    method=method,
                    url=url,
                    status_code=None,
                    duration_ms=elapsed_ms,
                    sync_run_id=get_sync_run_id(),
                    error=str(exc.reason or exc),
                )
                raise SnykTransportError(str(exc.reason or exc)) from exc
            except OSError as exc:
                elapsed_ms = (self._monotonic() - start) * 1000.0
                log_integration_http(
                    integration="snyk",
                    method=method,
                    url=url,
                    status_code=None,
                    duration_ms=elapsed_ms,
                    sync_run_id=get_sync_run_id(),
                    error=str(exc),
                )
                raise SnykTransportError(str(exc)) from exc

            elapsed_ms = (self._monotonic() - start) * 1000.0
            try:
                parsed: dict[str, Any] = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                log_integration_http(
                    integration="snyk",
                    method=method,
                    url=url,
                    status_code=status,
                    duration_ms=elapsed_ms,
                    sync_run_id=get_sync_run_id(),
                    error="Response was not valid JSON",
                )
                raise SnykClientError("Response was not valid JSON", status_code=None) from exc
            log_integration_http(
                integration="snyk",
                method=method,
                url=url,
                status_code=status,
                duration_ms=elapsed_ms,
                sync_run_id=get_sync_run_id(),
            )
            return parsed

    def _raise_http_error(self, exc: HTTPError) -> None:
        code = exc.code
        if code in (401, 403):
            raise SnykAuthError(_status_message(code), status_code=code) from exc
        if code == 429:
            raise SnykRateLimitError(_status_message(code), status_code=code) from exc
        if 400 <= code < 500:
            raise SnykClientError(_status_message(code), status_code=code) from exc
        if code >= 500:
            raise SnykServerError(_status_message(code), status_code=code) from exc
        raise SnykApiError(_status_message(code), status_code=code) from exc

    def _first_list_url_group(
        self,
        group_id: str,
        list_params: GroupIssueListParams | None = None,
    ) -> str:
        return self._first_list_url_path(
            f"groups/{group_id}/issues",
            list_params,
        )

    def _first_list_url_org(
        self,
        org_id: str,
        list_params: GroupIssueListParams | None = None,
    ) -> str:
        return self._first_list_url_path(
            f"orgs/{org_id}/issues",
            list_params,
        )

    def _first_list_url_path(
        self,
        path_segment: str,
        list_params: GroupIssueListParams | None = None,
    ) -> str:
        p = list_params or GroupIssueListParams()
        q: list[tuple[str, str]] = [
            ("version", SNYK_REST_API_VERSION),
            ("limit", str(ISSUES_LIST_LIMIT)),
        ]
        levels: tuple[str, ...]
        if p.effective_severity_levels is None:
            levels = DEFAULT_EFFECTIVE_SEVERITY_LEVELS
        else:
            levels = p.effective_severity_levels
        if levels:
            q.append(("effective_severity_level", ",".join(levels)))
        if p.issue_type is not None:
            q.append(("type", p.issue_type))
        if p.status is not None:
            q.append(("status", p.status))
        query = urlencode(q)
        return f"{self._base_url}/{path_segment}?{query}"

    def _get_issue_url_group(self, group_id: str, issue_id: str) -> str:
        q = urlencode([("version", SNYK_REST_API_VERSION)])
        return f"{self._base_url}/groups/{group_id}/issues/{issue_id}?{q}"

    def _get_issue_url_org(self, org_id: str, issue_id: str) -> str:
        q = urlencode([("version", SNYK_REST_API_VERSION)])
        return f"{self._base_url}/orgs/{org_id}/issues/{issue_id}?{q}"

    def iter_group_issues(
        self,
        group_id: str,
        *,
        list_params: GroupIssueListParams | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield normalized issue records for a group, following ``links.next``."""
        url: str | None = self._first_list_url_group(group_id, list_params)
        while url:
            doc = self._get_json(url)
            page = parse_issues_list_document(doc)
            yield from _yield_normalized_issues(page)
            url = resolve_next_url(self._base_url, page.links.get("next"))

    def get_group_issue(self, group_id: str, issue_id: str) -> dict[str, Any]:
        """Fetch a single issue in group scope; return a normalized record."""
        doc = self._get_json(self._get_issue_url_group(group_id, issue_id))
        raw = parse_single_issue_document(doc)
        idx = included_index_from_document(doc)
        return normalized_issue_record(raw, included_index=idx)

    def iter_org_issues(
        self,
        org_id: str,
        *,
        list_params: GroupIssueListParams | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield normalized issue records for an org, following ``links.next``."""
        url: str | None = self._first_list_url_org(org_id, list_params)
        while url:
            doc = self._get_json(url)
            page = parse_issues_list_document(doc)
            yield from _yield_normalized_issues(page)
            url = resolve_next_url(self._base_url, page.links.get("next"))

    def get_org_issue(self, org_id: str, issue_id: str) -> dict[str, Any]:
        """Fetch a single issue in org scope; return a normalized record."""
        doc = self._get_json(self._get_issue_url_org(org_id, issue_id))
        raw = parse_single_issue_document(doc)
        idx = included_index_from_document(doc)
        return normalized_issue_record(raw, included_index=idx)

    def get_org_project(self, org_id: str, project_id: str) -> dict[str, Any]:
        """Fetch Snyk project metadata (``GET /orgs/{org_id}/projects/{project_id}``)."""
        q = urlencode([("version", SNYK_REST_API_VERSION)])
        url = f"{self._base_url}/orgs/{org_id}/projects/{project_id}?{q}"
        doc = self._get_json(url)
        data = doc.get("data")
        if not isinstance(data, dict):
            return {"name": "", "origin": ""}
        attrs = data.get("attributes")
        if not isinstance(attrs, dict):
            return {"name": "", "origin": ""}
        name = str(attrs.get("name") or "").strip()
        origin = str(attrs.get("origin") or "").strip()
        return {"name": name, "origin": origin}


def _yield_normalized_issues(page: IssuesListPage) -> Iterator[dict[str, Any]]:
    idx = build_included_index(page.included)
    for issue in page.issues:
        yield normalized_issue_record(issue, included_index=idx)


def _status_message(code: int) -> str:
    return f"Snyk API HTTP error {code}"
