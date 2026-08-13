"""Tests for missing mapped work item audit logging."""

from __future__ import annotations

import logging

import pytest

from observability.cli_logging import NdjsonFormatter
from observability.integration_audit import log_missing_mapped_work_item


def test_log_missing_mapped_work_item_emits_structured_record(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="integration_audit"):
        log_missing_mapped_work_item(
            prior_work_item_id="123",
            issue_key="ISS-1",
            action="recreate",
            sync_run_id="run-abc",
        )
    rows = [r.record for r in caplog.records if r.name == "integration_audit"]
    assert len(rows) == 1
    row = rows[0]
    assert row["event"] == "missing_mapped_work_item"
    assert row["prior_work_item_id"] == "123"
    assert row["issue_key"] == "ISS-1"
    assert row["action"] == "recreate"
    assert row["sync_run_id"] == "run-abc"


def test_log_missing_mapped_work_item_ndjson_record_shape(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="integration_audit"):
        log_missing_mapped_work_item(
            prior_work_item_id="99",
            issue_key="ISS-2",
            action="skip",
        )
    fmt = NdjsonFormatter()
    line = fmt.format(caplog.records[0])
    assert '"event": "missing_mapped_work_item"' in line or '"event":"missing_mapped_work_item"' in line
    assert '"action": "skip"' in line or '"action":"skip"' in line
