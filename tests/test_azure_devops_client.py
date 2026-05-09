"""Tests for ``WorkItemsClient`` (mocked HTTP)."""

from __future__ import annotations

import io
import json
import logging
from http.client import HTTPMessage

import pytest
from urllib.error import HTTPError
from urllib.request import Request

from integrations.azure_devops.client import MAX_IDS_PER_LIST, WorkItemsClient
from integrations.azure_devops.constants import AZURE_DEVOPS_WIT_API_VERSION
from integrations.azure_devops.errors import (
    AzureDevOpsAuthError,
    AzureDevOpsClientError,
    AzureDevOpsRateLimitError,
    AzureDevOpsServerError,
    MissingPatError,
)


class _FakeResp:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _work_item_json(wid: int = 7, *, state: str | None = "Active") -> bytes:
    fields: dict = {"System.Title": "Hi"}
    if state is not None:
        fields["System.State"] = state
    doc = {"id": wid, "rev": 3, "fields": fields}
    return json.dumps(doc).encode("utf-8")


def test_get_work_item_requires_pat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
    client = WorkItemsClient()
    with pytest.raises(MissingPatError):
        client.get_work_item("o", "p", 1)


def test_list_work_items_by_ids_rejects_over_limit() -> None:
    client = WorkItemsClient(pat="x")
    ids = list(range(MAX_IDS_PER_LIST + 1))
    with pytest.raises(AzureDevOpsClientError, match="at most"):
        client.list_work_items_by_ids("o", "p", ids)


def test_list_work_items_by_ids_empty_returns_empty() -> None:
    client = WorkItemsClient(pat="x")
    assert client.list_work_items_by_ids("o", "p", []) == []


def test_get_work_item_normalizes_missing_state() -> None:
    body = _work_item_json(state=None)

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        assert req.get_header("Authorization") is not None
        assert "Basic " in (req.get_header("Authorization") or "")
        return _FakeResp(body)

    client = WorkItemsClient(pat="secret-token", opener=opener)
    rec = client.get_work_item("org", "proj", 7)
    assert rec["work_item_id"] == 7
    assert rec["work_item_status"] is None
    assert rec["rev"] == 3
    assert rec["fields"]["System.Title"] == "Hi"


def test_get_work_item_maps_state() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        return _FakeResp(_work_item_json(state="Resolved"))

    client = WorkItemsClient(pat="t", opener=opener)
    rec = client.get_work_item("o", "p", 7)
    assert rec["work_item_status"] == "Resolved"


def test_get_work_item_auth_error() -> None:
    def opener(req: Request, timeout: float = 0) -> object:
        hdrs = HTTPMessage()
        raise HTTPError(req.full_url, 401, "Unauthorized", hdrs, io.BytesIO(b"{}"))

    client = WorkItemsClient(pat="t", opener=opener)
    with pytest.raises(AzureDevOpsAuthError):
        client.get_work_item("o", "p", 1)


def test_get_work_item_forbidden_audit_no_pat_leak(caplog: pytest.LogCaptureFixture) -> None:
    secret = "my-pat-value"

    def opener(req: Request, timeout: float = 0) -> object:
        hdrs = HTTPMessage()
        raise HTTPError(req.full_url, 403, "Forbidden", hdrs, io.BytesIO(b"{}"))

    client = WorkItemsClient(pat=secret, opener=opener)
    with caplog.at_level(logging.WARNING, logger="integration_audit"):
        with pytest.raises(AzureDevOpsAuthError):
            client.get_work_item("o", "p", 1)
    joined = " ".join(r.message for r in caplog.records)
    assert secret not in joined
    rows = [json.loads(r.message) for r in caplog.records if r.name == "integration_audit"]
    assert rows[-1]["http_status"] == 403
    assert "Authentication Failed" in rows[-1].get("error", "")


def test_get_work_item_retries_429_then_succeeds() -> None:
    sleeps: list[float] = []
    calls = 0

    def sleep_fn(s: float) -> None:
        sleeps.append(s)

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        nonlocal calls
        calls += 1
        if calls == 1:
            hdrs = HTTPMessage()
            hdrs["Retry-After"] = "0"
            raise HTTPError(req.full_url, 429, "Too Many", hdrs, io.BytesIO(b"{}"))
        return _FakeResp(_work_item_json())

    client = WorkItemsClient(pat="t", opener=opener, sleep_fn=sleep_fn)
    rec = client.get_work_item("o", "p", 1)
    assert rec["work_item_id"] == 7
    assert calls == 2
    assert sleeps


def test_list_parses_value_array() -> None:
    doc = {"value": [json.loads(_work_item_json(1)), json.loads(_work_item_json(2))]}
    raw = json.dumps(doc).encode("utf-8")

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        assert "ids=" in req.full_url
        assert f"api-version={AZURE_DEVOPS_WIT_API_VERSION}" in req.full_url
        return _FakeResp(raw)

    client = WorkItemsClient(pat="t", opener=opener)
    rows = client.list_work_items_by_ids("o", "p", [1, 2])
    assert [r["work_item_id"] for r in rows] == [1, 2]


def test_create_sends_json_patch_content_type() -> None:
    captured: dict[str, str | bytes] = {}

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        captured["method"] = req.method or "GET"
        hdrs = {k.lower(): v for k, v in req.header_items()}
        captured["ct"] = hdrs.get("content-type", "")
        captured["data"] = req.data or b""
        return _FakeResp(_work_item_json(wid=99))

    client = WorkItemsClient(pat="t", opener=opener)
    rec = client.create_work_item("o", "p", "Bug", [{"op": "add", "path": "/fields/System.Title", "value": "x"}])
    assert captured["method"] == "POST"
    assert "json-patch" in str(captured["ct"]).lower()
    assert json.loads(captured["data"].decode("utf-8"))[0]["op"] == "add"
    assert rec["work_item_id"] == 99


def test_mutating_post_does_not_retry_5xx() -> None:
    attempts = 0

    def opener(req: Request, timeout: float = 0) -> object:
        nonlocal attempts
        attempts += 1
        hdrs = HTTPMessage()
        raise HTTPError(req.full_url, 500, "Error", hdrs, io.BytesIO(b"{}"))

    client = WorkItemsClient(pat="t", opener=opener, sleep_fn=lambda s: None)
    with pytest.raises(AzureDevOpsServerError):
        client.add_work_item_comment("o", "p", 1, "hi")
    assert attempts == 1


def test_get_retries_5xx_limited() -> None:
    attempts = 0

    def opener(req: Request, timeout: float = 0) -> _FakeResp | object:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            hdrs = HTTPMessage()
            raise HTTPError(req.full_url, 503, "Error", hdrs, io.BytesIO(b"{}"))
        return _FakeResp(_work_item_json())

    client = WorkItemsClient(pat="t", opener=opener, sleep_fn=lambda s: None)
    rec = client.get_work_item("o", "p", 1)
    assert rec["work_item_id"] == 7
    assert attempts == 3


def test_429_exhausted_raises() -> None:
    def opener(req: Request, timeout: float = 0) -> object:
        hdrs = HTTPMessage()
        hdrs["Retry-After"] = "1000"
        raise HTTPError(req.full_url, 429, "Too Many", hdrs, io.BytesIO(b"{}"))

    client = WorkItemsClient(
        pat="t",
        opener=opener,
        sleep_fn=lambda s: None,
        rate_limit_max_wait_seconds=0.01,
    )
    with pytest.raises(AzureDevOpsRateLimitError):
        client.get_work_item("o", "p", 1)
