"""Tests for JSON:API issue document parsing."""

from snyk.parser import (
    normalized_issue_record,
    parse_issues_list_document,
    parse_single_issue_document,
)


def test_parse_issues_list_document_empty_data() -> None:
    page = parse_issues_list_document({})
    assert page.issues == []
    assert page.links == {}


def test_parse_issues_list_document_list() -> None:
    doc = {
        "data": [{"type": "issue", "id": "i1"}, {"type": "issue", "id": "i2"}],
        "links": {"next": "rest/orgs/x/issues?page=2"},
    }
    page = parse_issues_list_document(doc)
    assert len(page.issues) == 2
    assert page.issues[0]["id"] == "i1"
    assert page.links.get("next") == "rest/orgs/x/issues?page=2"


def test_parse_issues_list_document_single_resource_as_data() -> None:
    doc = {"data": {"type": "issue", "id": "one"}}
    page = parse_issues_list_document(doc)
    assert len(page.issues) == 1
    assert page.issues[0]["id"] == "one"


def test_parse_single_issue_document() -> None:
    doc = {"data": {"type": "issue", "id": "abc", "attributes": {}}}
    assert parse_single_issue_document(doc)["id"] == "abc"


def test_parse_single_issue_document_missing() -> None:
    assert parse_single_issue_document({}) == {}


def test_normalized_issue_record_full() -> None:
    resource = {
        "attributes": {
            "key": "issue-key",
            "created_at": "2025-04-01T12:00:00Z",
            "effective_severity_level": "critical",
        },
        "relationships": {
            "organization": {"data": {"id": "o1"}},
            "scan_item": {"data": {"id": "p1"}},
        },
    }
    rec = normalized_issue_record(resource)
    assert rec == {
        "issue_id": "issue-key",
        "created_at": "2025-04-01T12:00:00Z",
        "severity": "critical",
        "org_id": "o1",
        "project_id": "p1",
    }


def test_normalized_issue_record_minimal() -> None:
    assert normalized_issue_record({}) == {}
