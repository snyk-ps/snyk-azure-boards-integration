"""Tests for Snyk → work item text builders."""

from sync.issue_content import (
    build_system_description,
    cve_entries,
    cwe_ids,
    primary_package_line,
    snyk_ui_issue_url,
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


def test_snyk_ui_issue_url() -> None:
    u = snyk_ui_issue_url(
        snyk_org_slug="my-org",
        project_id="e63ef815-f29a-4f25-a42d-acdf3b736058",
        issue_key="SNYK-PYTHON-H11-10293728",
    )
    assert (
        u == "https://app.snyk.io/org/my-org/project/"
        "e63ef815-f29a-4f25-a42d-acdf3b736058"
        "#issue-SNYK-PYTHON-H11-10293728"
    )


def test_snyk_ui_issue_url_encodes_slug() -> None:
    u = snyk_ui_issue_url(
        snyk_org_slug="org with spaces",
        project_id="pid",
        issue_key="SNYK-1",
    )
    assert "org%20with%20spaces" in u


def test_build_system_description_includes_narrative_and_link() -> None:
    attrs = {
        "title": "Sandbox Escape",
        "key": "SNYK-JS-VM2-5415299",
        "description": "Prototype pollution allows …",
        "coordinates": [
            {
                "representations": [
                    {"dependency": {"package_name": "vm2", "package_version": "3.9.3"}},
                ],
                "remedies": [{"type": "upgrade", "desc": "Upgrade to 3.9.16"}],
                "is_upgradeable": True,
            },
        ],
        "type": "package_vulnerability",
        "classes": [{"id": "CWE-265", "source": "CWE"}],
        "problems": [{"id": "CVE-2023-29017", "url": "https://nvd.example/cve"}],
    }
    text = build_system_description(
        attrs,
        snyk_org_slug="acme",
        project_id="proj-uuid",
        issue_key="SNYK-JS-VM2-5415299",
    )
    assert "Sandbox Escape" in text
    assert "Prototype pollution" in text
    assert "Remediation:" in text
    assert "upgrade" in text
    assert "CVE-2023-29017" in text
    assert text.endswith(
        "Snyk: https://app.snyk.io/org/acme/project/proj-uuid"
        "#issue-SNYK-JS-VM2-5415299",
    )
