"""Tests for ``IssuesClient`` HTTP behavior (mocked)."""

import io
import json
from http.client import HTTPMessage

import pytest
from urllib.error import HTTPError
from urllib.request import Request

from snyk.client import GroupIssueListParams, IssuesClient
from snyk.constants import SNYK_REST_API_VERSION
from snyk.errors import (
    MissingTokenError,
    SnykAuthError,
    SnykClientError,
    SnykRateLimitError,
    SnykServerError,
)


class _FakeResp:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _page_json(links: dict | None = None, data: list | dict | None = None) -> bytes:
    doc: dict = {}
    if data is not None:
        doc["data"] = data
    if links is not None:
        doc["links"] = links
    return json.dumps(doc).encode("utf-8")


def _issue_resource(issue_key: str = "k1") -> dict:
    return {
        "type": "issue",
        "id": "res-1",
        "attributes": {
            "key": issue_key,
            "created_at": "2025-01-01T00:00:00Z",
            "effective_severity_level": "high",
        },
        "relationships": {
            "organization": {"data": {"type": "org", "id": "org-uuid"}},
            "scan_item": {"data": {"type": "project", "id": "proj-uuid"}},
        },
    }


def test_iter_org_issues_two_pages_follows_links_next() -> None:
    oid = "22222222-2222-2222-2222-222222222222"
    calls: list[str] = []

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        calls.append(req.full_url)
        if len(calls) == 1:
            assert f"/orgs/{oid}/issues" in req.full_url
            return _FakeResp(
                _page_json(
                    data=[_issue_resource("a")],
                    links={"next": f"rest/orgs/{oid}/issues?page=2"},
                )
            )
        assert "page=2" in req.full_url
        return _FakeResp(_page_json(data=[_issue_resource("b")], links={}))

    client = IssuesClient(token="t", opener=opener)
    rows = list(client.iter_org_issues(oid))
    assert [r.get("issue_id") for r in rows] == ["a", "b"]


def test_get_org_issue_success_normalized() -> None:
    oid = "o1"
    issue = "i1"

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        assert f"/orgs/{oid}/issues/{issue}" in req.full_url
        return _FakeResp(_page_json(data=_issue_resource("ik")))

    client = IssuesClient(token="t", opener=opener)
    out = client.get_org_issue(oid, issue)
    assert out["issue_id"] == "ik"


def test_iter_group_issues_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SNYK_TOKEN", raising=False)
    client = IssuesClient()
    with pytest.raises(MissingTokenError):
        next(client.iter_group_issues("group-id"))


def test_iter_group_issues_two_pages_follows_links_next() -> None:
    gid = "11111111-1111-1111-1111-111111111111"
    calls: list[str] = []

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        calls.append(req.full_url)
        if len(calls) == 1:
            assert f"/groups/{gid}/issues" in req.full_url
            assert f"version={SNYK_REST_API_VERSION}" in req.full_url
            assert "limit=100" in req.full_url
            assert "effective_severity_level=high%2Ccritical" in req.full_url
            return _FakeResp(
                _page_json(
                    data=[_issue_resource("a")],
                    links={"next": f"rest/groups/{gid}/issues?page=2"},
                )
            )
        assert "page=2" in req.full_url
        assert "rest/rest" not in req.full_url
        return _FakeResp(_page_json(data=[_issue_resource("b")], links={}))

    client = IssuesClient(token="t", opener=opener)
    rows = list(client.iter_group_issues(gid))
    assert [r.get("issue_id") for r in rows] == ["a", "b"]
    assert len(calls) == 2


def test_list_first_page_omits_severity_when_empty_tuple() -> None:
    gid = "11111111-1111-1111-1111-111111111111"
    calls: list[str] = []

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        calls.append(req.full_url)
        assert "effective_severity_level" not in req.full_url
        return _FakeResp(_page_json(data=[], links={}))

    client = IssuesClient(token="t", opener=opener)
    list(client.iter_group_issues(gid, list_params=GroupIssueListParams(effective_severity_levels=())))
    assert len(calls) == 1


def test_get_group_issue_success_normalized() -> None:
    gid = "g1"
    issue = "i1"

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        assert f"/groups/{gid}/issues/{issue}" in req.full_url
        assert f"version={SNYK_REST_API_VERSION}" in req.full_url
        return _FakeResp(_page_json(data=_issue_resource("ik")))

    client = IssuesClient(token="t", opener=opener)
    out = client.get_group_issue(gid, issue)
    assert out["issue_id"] == "ik"
    assert out["org_id"] == "org-uuid"
    assert out["project_id"] == "proj-uuid"
    assert out["severity"] == "high"


def test_http_401_raises_auth_error() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        raise HTTPError(req.full_url, 401, "Unauthorized", hdrs=None, fp=io.BytesIO(b""))

    client = IssuesClient(token="t", opener=opener)
    with pytest.raises(SnykAuthError) as ei:
        client.get_group_issue("g", "i")
    assert ei.value.status_code == 401


def test_http_403_raises_auth_error() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        raise HTTPError(req.full_url, 403, "Forbidden", hdrs=None, fp=io.BytesIO(b""))

    client = IssuesClient(token="t", opener=opener)
    with pytest.raises(SnykAuthError):
        client.get_group_issue("g", "i")


def test_http_404_raises_client_error() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        raise HTTPError(req.full_url, 404, "Nope", hdrs=None, fp=io.BytesIO(b""))

    client = IssuesClient(token="t", opener=opener)
    with pytest.raises(SnykClientError) as ei:
        client.get_group_issue("g", "i")
    assert ei.value.status_code == 404


def test_http_500_raises_server_error() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        raise HTTPError(req.full_url, 500, "Err", hdrs=None, fp=io.BytesIO(b""))

    client = IssuesClient(token="t", opener=opener)
    with pytest.raises(SnykServerError) as ei:
        client.get_group_issue("g", "i")
    assert ei.value.status_code == 500


def test_invalid_json_raises_client_error() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        return _FakeResp(b"not json")

    client = IssuesClient(token="t", opener=opener)
    with pytest.raises(SnykClientError, match="valid JSON"):
        client.get_group_issue("g", "i")


def test_request_includes_auth_header() -> None:
    captured: dict[str, str] = {}

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        items = {k.lower(): v for k, v in req.header_items()}
        captured["authorization"] = items.get("authorization", "")
        return _FakeResp(_page_json(data=_issue_resource()))

    client = IssuesClient(token="secret-token", opener=opener)
    client.get_group_issue("g", "i")
    assert captured["authorization"] == "token secret-token"


def test_429_retries_then_succeeds() -> None:
    calls = 0
    sleeps: list[float] = []

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise HTTPError(req.full_url, 429, "Too Many", hdrs=None, fp=io.BytesIO(b""))
        return _FakeResp(_page_json(data=_issue_resource()))

    client = IssuesClient(
        token="t",
        opener=opener,
        sleep_fn=lambda s: sleeps.append(s),
        monotonic_fn=lambda: 0.0,
        rate_limit_max_wait_seconds=70.0,
    )
    out = client.get_group_issue("g", "i")
    assert out["issue_id"] == "k1"
    assert calls == 2
    assert sleeps == [1.0]


def test_429_respects_retry_after_header() -> None:
    calls = 0
    sleeps: list[float] = []
    hdrs = HTTPMessage()
    hdrs.add_header("Retry-After", "3")

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise HTTPError(req.full_url, 429, "Too Many", hdrs=hdrs, fp=io.BytesIO(b""))
        return _FakeResp(_page_json(data=_issue_resource()))

    client = IssuesClient(
        token="t",
        opener=opener,
        sleep_fn=lambda s: sleeps.append(s),
        monotonic_fn=lambda: 0.0,
    )
    client.get_group_issue("g", "i")
    assert sleeps == [3.0]


def test_429_exhausted_raises_rate_limit_error() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        raise HTTPError(req.full_url, 429, "Too Many", hdrs=None, fp=io.BytesIO(b""))

    client = IssuesClient(
        token="t",
        opener=opener,
        monotonic_fn=lambda: 0.0,
        rate_limit_max_wait_seconds=0.0,
    )
    with pytest.raises(SnykRateLimitError) as ei:
        client.get_group_issue("g", "i")
    assert ei.value.status_code == 429
