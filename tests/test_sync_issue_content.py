"""Tests for Snyk → work item text builders."""

from sync.issue_content import (
    best_effort_snyk_issue_url,
    cve_entries,
    cwe_ids,
    primary_package_line,
    title_with_package,
)


def test_primary_package_line() -> None:
    attrs = {
        "coordinates": [
            {
                "representations": [
                    {"dependency": {"package_name": "lodash", "package_version": "4.0.0"}},
                ],
            },
        ],
    }
    assert primary_package_line(attrs) == "lodash@4.0.0"


def test_title_with_package() -> None:
    attrs = {"title": "X", "coordinates": []}
    assert title_with_package(attrs) == "X"


def test_cwe_ids_filters_source() -> None:
    attrs = {
        "classes": [
            {"id": "CWE-79", "source": "CWE"},
            {"id": "OTHER", "source": "OTHER"},
        ],
    }
    assert cwe_ids(attrs) == ["CWE-79"]


def test_cve_entries_matches_cve_id() -> None:
    attrs = {
        "problems": [
            {"id": "CVE-2023-12345", "url": "https://example/cve"},
            {"id": "SNYK-1", "source": "SNYK"},
        ],
    }
    assert cve_entries(attrs) == [("CVE-2023-12345", "https://example/cve")]


def test_best_effort_snyk_issue_url() -> None:
    u = best_effort_snyk_issue_url(group_id="g1", rest_issue_uuid="u1")
    assert u == "https://app.snyk.io/group/g1/issues/u1"
