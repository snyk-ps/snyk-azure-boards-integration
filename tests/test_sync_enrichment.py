"""Tests for optional GET issue enrichment."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from snyk.errors import SnykApiError
from sync.enrichment import (
    enrich_issue_record,
    merge_issue_attributes,
    needs_issue_detail,
)


def test_needs_issue_detail_when_both_missing() -> None:
    assert needs_issue_detail({}) is True


def test_needs_issue_detail_false_when_complete() -> None:
    attrs = {
        "description": "text",
        "coordinates": [{"remedies": [{"x": 1}]}],
    }
    assert needs_issue_detail(attrs) is False


def test_merge_issue_attributes_fills_description() -> None:
    merged = merge_issue_attributes(
        {},
        {"description": "from-get"},
    )
    assert merged["description"] == "from-get"


def test_enrich_issue_record_skips_when_complete() -> None:
    client = MagicMock()
    rec = {
        "issue_attributes": {
            "description": "d",
            "coordinates": [{"remedies": ["r"]}],
        },
    }
    out = enrich_issue_record(
        client,
        rec,
        use_org_scope=False,
        snyk_org_id=None,
        snyk_group_id="g",
        log=logging.getLogger("t"),
    )
    assert out is rec
    client.get_group_issue.assert_not_called()


def test_enrich_issue_record_calls_get_and_merges() -> None:
    client = MagicMock()
    client.get_group_issue.return_value = {
        "issue_attributes": {
            "description": "full text",
            "coordinates": [{"remedies": [{"fix": "v2"}]}],
        },
    }
    rec = {
        "rest_issue_id": "uuid-1",
        "issue_id": "SNYK-1",
        "issue_attributes": {"title": "t"},
    }
    log = logging.getLogger("t")
    out = enrich_issue_record(
        client,
        rec,
        use_org_scope=False,
        snyk_org_id=None,
        snyk_group_id="gid",
        log=log,
    )
    client.get_group_issue.assert_called_once_with("gid", "uuid-1")
    assert out["issue_attributes"]["description"] == "full text"


def test_enrich_issue_record_logs_on_api_error() -> None:
    client = MagicMock()
    client.get_group_issue.side_effect = SnykApiError("oops")
    rec = {
        "rest_issue_id": "u1",
        "issue_attributes": {},
        "issue_id": "K",
    }
    log = MagicMock(spec=logging.Logger)
    out = enrich_issue_record(
        client,
        rec,
        use_org_scope=False,
        snyk_org_id=None,
        snyk_group_id="g",
        log=log,
    )
    assert out is rec
    log.warning.assert_called()
