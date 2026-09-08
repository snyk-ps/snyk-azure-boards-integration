"""Tests for bounded, redacted Azure DevOps error diagnostics (P2-FR-6.2)."""

from __future__ import annotations

import io
import json
import logging
from http.client import HTTPMessage
from typing import Any

import pytest
from urllib.error import HTTPError
from urllib.request import Request

from integrations.azure_devops.client import WorkItemsClient
from integrations.azure_devops.error_detail import (
    MAX_ERROR_DETAIL_CHARS,
    REDACTION_PLACEHOLDER,
    TRUNCATION_MARKER,
    error_detail_from_body,
    error_detail_from_http_error,
    redact_credentials,
    truncate_detail,
)
from integrations.azure_devops.errors import (
    AzureDevOpsAuthError,
    AzureDevOpsClientError,
    AzureDevOpsRateLimitError,
    AzureDevOpsServerError,
)
from observability.cli_logging import NdjsonFormatter


def _envelope(**fields: Any) -> bytes:
    doc: dict[str, Any] = {"$id": "1", "innerException": None, "errorCode": 0}
    doc.update(fields)
    return json.dumps(doc).encode("utf-8")


def _audit_rows(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    return [r.record for r in caplog.records if r.name == "integration_audit"]


# --- redact_credentials ----------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Authorization: Basic OnNlY3JldFBhdFZhbHVl",
        "sent Bearer eyJhbGciOiJIUzI1NiJ9.abcdefgh",
        "pat=super-secret-value",
        "token: super-secret-value",
        "password = hunter2hunter2",
    ],
)
def test_redact_credentials_removes_credential_shapes(text: str) -> None:
    out = redact_credentials(text)
    assert REDACTION_PLACEHOLDER in out
    for leak in ("OnNlY3JldFBhdFZhbHVl", "eyJhbGciOiJIUzI1NiJ9", "super-secret-value", "hunter2"):
        assert leak not in out


def test_redact_credentials_leaves_ordinary_text_alone() -> None:
    text = "The field System.AreaPath contains invalid value Proj\\Missing."
    assert redact_credentials(text) == text


# --- truncate_detail -------------------------------------------------------


def test_truncate_detail_passes_through_short_text() -> None:
    assert truncate_detail("short") == "short"


def test_truncate_detail_marks_and_bounds_long_text() -> None:
    out = truncate_detail("x" * (MAX_ERROR_DETAIL_CHARS + 200))
    assert out.endswith(TRUNCATION_MARKER)
    assert len(out) <= MAX_ERROR_DETAIL_CHARS


def test_detail_bound_fits_under_audit_error_clamp() -> None:
    """The audit layer clamps ``error`` at 500 chars; the marker must survive."""
    assert MAX_ERROR_DETAIL_CHARS <= 500


# --- error_detail_from_body ------------------------------------------------


def test_envelope_message_with_type_key() -> None:
    body = _envelope(message="Field 'System.Foo' does not exist.", typeKey="TF401320")
    assert error_detail_from_body(body) == "TF401320: Field 'System.Foo' does not exist."


def test_envelope_message_without_type_key() -> None:
    body = _envelope(message="Work item type Bug is not defined.")
    assert error_detail_from_body(body) == "Work item type Bug is not defined."


def test_type_key_not_repeated_when_already_in_message() -> None:
    body = _envelope(message="TF401320: already prefixed", typeKey="TF401320")
    assert error_detail_from_body(body) == "TF401320: already prefixed"


def test_message_whitespace_is_collapsed_to_one_line() -> None:
    body = _envelope(message="line one\n  line two\ttab")
    assert error_detail_from_body(body) == "line one line two tab"


def test_oversized_message_is_truncated_with_marker() -> None:
    body = _envelope(message="y" * (MAX_ERROR_DETAIL_CHARS + 500))
    out = error_detail_from_body(body)
    assert out is not None
    assert out.endswith(TRUNCATION_MARKER)
    assert len(out) <= MAX_ERROR_DETAIL_CHARS


def test_credentials_in_message_are_redacted() -> None:
    body = _envelope(message="rejected Authorization: Basic OnNlY3JldFBhdFZhbHVl here")
    out = error_detail_from_body(body)
    assert out is not None
    assert "OnNlY3JldFBhdFZhbHVl" not in out
    assert REDACTION_PLACEHOLDER in out


@pytest.mark.parametrize(
    "body",
    [
        None,
        b"",
        b"   ",
        b"<html>Server Error</html>",
        b"not json at all",
        b'["a", "b"]',
        b'{"typeKey": "TF1", "errorCode": 0}',
        b'{"message": ""}',
        b'{"message": "   "}',
        b'{"message": 42}',
        b"\xff\xfe\x00bad",
    ],
    ids=[
        "none",
        "empty",
        "blank",
        "html",
        "plain-text",
        "json-array",
        "no-message",
        "empty-message",
        "blank-message",
        "non-string-message",
        "undecodable",
    ],
)
def test_non_envelope_bodies_yield_no_detail(body: bytes | None) -> None:
    assert error_detail_from_body(body) is None


def test_extraction_never_raises_on_hostile_input() -> None:
    class Hostile:
        def __str__(self) -> str:
            raise RuntimeError("boom")

    assert error_detail_from_http_error(Hostile()) is None


def test_error_detail_from_http_error_reads_body_once() -> None:
    exc = HTTPError(
        "https://dev.azure.com/o/p",
        400,
        "Bad Request",
        HTTPMessage(),
        io.BytesIO(_envelope(message="Boom", typeKey="TF1")),
    )
    assert error_detail_from_http_error(exc) == "TF1: Boom"
    # Stream already consumed; a second read must degrade rather than raise.
    assert error_detail_from_http_error(exc) is None


def test_error_detail_from_http_error_handles_absent_body() -> None:
    exc = HTTPError("https://dev.azure.com/o/p", 404, "Not Found", HTTPMessage(), None)
    assert error_detail_from_http_error(exc) is None


# --- client wiring ---------------------------------------------------------


def test_client_error_message_and_audit_carry_ado_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    body = _envelope(message="TF401347: Invalid field value.", typeKey="TF401347")

    def opener(req: Request, timeout: float = 0) -> object:
        raise HTTPError(req.full_url, 400, "Bad Request", HTTPMessage(), io.BytesIO(body))

    client = WorkItemsClient(pat="t", opener=opener)
    with caplog.at_level(logging.WARNING, logger="integration_audit"):
        with pytest.raises(AzureDevOpsClientError) as excinfo:
            client.create_work_item("o", "p", "Bug", [{"op": "add"}])

    assert "400" in str(excinfo.value)
    assert "TF401347: Invalid field value." in str(excinfo.value)

    row = _audit_rows(caplog)[-1]
    assert row["http_status"] == 400
    assert "TF401347: Invalid field value." in row["error"]


def test_unparseable_body_degrades_to_status_only(caplog: pytest.LogCaptureFixture) -> None:
    def opener(req: Request, timeout: float = 0) -> object:
        raise HTTPError(req.full_url, 400, "Bad Request", HTTPMessage(), io.BytesIO(b"<html/>"))

    client = WorkItemsClient(pat="t", opener=opener)
    with caplog.at_level(logging.WARNING, logger="integration_audit"):
        with pytest.raises(AzureDevOpsClientError) as excinfo:
            client.create_work_item("o", "p", "Bug", [{"op": "add"}])

    assert str(excinfo.value) == "Azure DevOps API HTTP error 400"

    row = _audit_rows(caplog)[-1]
    assert row["http_status"] == 400
    assert "error" not in row


def test_server_error_carries_detail(caplog: pytest.LogCaptureFixture) -> None:
    body = _envelope(message="Internal failure in WIT.")

    def opener(req: Request, timeout: float = 0) -> object:
        raise HTTPError(req.full_url, 500, "Error", HTTPMessage(), io.BytesIO(body))

    client = WorkItemsClient(pat="t", opener=opener)
    with caplog.at_level(logging.WARNING, logger="integration_audit"):
        with pytest.raises(AzureDevOpsServerError) as excinfo:
            client.create_work_item("o", "p", "Bug", [{"op": "add"}])

    assert "Internal failure in WIT." in str(excinfo.value)
    assert "Internal failure in WIT." in _audit_rows(caplog)[-1]["error"]


def test_auth_failure_keeps_alerting_error_and_leaks_no_pat(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "my-pat-value"
    body = _envelope(message="Access denied. Authorization: Basic OnNlY3JldA==")

    def opener(req: Request, timeout: float = 0) -> object:
        raise HTTPError(req.full_url, 403, "Forbidden", HTTPMessage(), io.BytesIO(body))

    client = WorkItemsClient(pat=secret, opener=opener)
    with caplog.at_level(logging.WARNING, logger="integration_audit"):
        with pytest.raises(AzureDevOpsAuthError) as excinfo:
            client.get_work_item("o", "p", 1)

    joined = " ".join(NdjsonFormatter().format(r) for r in caplog.records)
    assert secret not in joined
    assert "OnNlY3JldA==" not in joined
    assert "OnNlY3JldA==" not in str(excinfo.value)

    # The 401/403 alerting contract is preserved.
    assert "Authentication Failed" in _audit_rows(caplog)[-1]["error"]


def test_rate_limit_exhaustion_keeps_its_own_error(caplog: pytest.LogCaptureFixture) -> None:
    def opener(req: Request, timeout: float = 0) -> object:
        hdrs = HTTPMessage()
        hdrs["Retry-After"] = "9999"
        raise HTTPError(req.full_url, 429, "Too Many", hdrs, io.BytesIO(_envelope(message="slow")))

    client = WorkItemsClient(pat="t", opener=opener, sleep_fn=lambda s: None)
    with caplog.at_level(logging.WARNING, logger="integration_audit"):
        with pytest.raises(AzureDevOpsRateLimitError):
            client.create_work_item("o", "p", "Bug", [{"op": "add"}])

    assert "retry budget exhausted" in _audit_rows(caplog)[-1]["error"]


def test_sync_skip_log_names_the_ado_cause_and_run_succeeds(
    tmp_path: Any,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rejected create must surface the Azure DevOps reason without failing the run."""
    from unittest.mock import MagicMock

    from config.loader import load_app_config
    from mapping_store.sqlite_store import SqliteMappingStore
    from snyk.client import IssuesClient
    from sync.run import run_sync

    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")

    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(
        "azure_boards:\n"
        '  repo_mapping_csv: ""\n'
        "  defaults:\n"
        "    organization: ado-o\n"
        "    project: ado-p\n"
        "  org_mappings:\n"
        "    - organization: ado-o\n"
        "      project: ado-p\n"
        "      snyk_org_id: org-uuid\n"
        "      snyk_org_slug: org-slug\n"
        "snyk:\n"
        '  group_id: ""\n',
        encoding="utf-8",
    )
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    store = SqliteMappingStore(database_path=str(tmp_path / "m.sqlite"))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.create_work_item.side_effect = AzureDevOpsClientError(
        "Azure DevOps API HTTP error 400: TF401347: Invalid field value.",
        status_code=400,
    )

    rec = {
        "org_id": "org-uuid",
        "project_id": "proj-uuid",
        "issue_id": "ISS-400",
        "issue_attributes": {
            "status": "open",
            "ignored": False,
            "key": "ISS-400",
            "effective_severity_level": "high",
            "description": "d",
            "coordinates": [{"remedies": [{"type": "semver"}]}],
        },
    }
    monkeypatch.setattr(issues, "iter_org_issues", lambda *a, **k: iter([rec]))
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "proj-name", "origin": "github"},
    )
    monkeypatch.setattr("sync.run.batch_get_work_items", lambda *a, **k: {})

    with caplog.at_level(logging.ERROR):
        rc = run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store)

    assert rc == 0
    assert "ISS-400" in caplog.text
    assert "TF401347: Invalid field value." in caplog.text


def test_get_recovery_retry_does_not_consume_body_before_terminal_attempt() -> None:
    attempts = 0

    def opener(req: Request, timeout: float = 0) -> object:
        nonlocal attempts
        attempts += 1
        body = _envelope(message=f"attempt {attempts}")
        raise HTTPError(req.full_url, 503, "Error", HTTPMessage(), io.BytesIO(body))

    client = WorkItemsClient(pat="t", opener=opener, sleep_fn=lambda s: None)
    with pytest.raises(AzureDevOpsServerError) as excinfo:
        client.get_work_item("o", "p", 1)

    # Retries happened, and the diagnostic comes from the final attempt.
    assert attempts > 1
    assert f"attempt {attempts}" in str(excinfo.value)
