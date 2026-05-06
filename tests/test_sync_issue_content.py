"""Tests for Snyk → work item text builders."""

import pytest

from sync import issue_content as issue_content_mod
from sync.issue_content import (
    build_system_description,
    effective_target_label_for_title,
    cve_entries,
    cwe_ids,
    primary_package_line,
    recommended_upgrade_lines,
    snyk_ui_issue_url,
    title_with_package,
    work_item_title,
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


def test_title_with_package_delegates() -> None:
    attrs = {"title": "X", "coordinates": []}
    assert title_with_package(attrs) == "X"


def test_work_item_title_with_target() -> None:
    attrs = {"title": "HTTP Smuggling", "coordinates": []}
    assert (
        work_item_title(attrs, target_name="my-target") == "my-target - HTTP Smuggling"
    )


def test_work_item_title_no_target() -> None:
    attrs = {"title": "Alone", "coordinates": []}
    assert work_item_title(attrs, target_name=None) == "Alone"


def test_effective_target_label_prefers_snyk_project_name() -> None:
    assert (
        effective_target_label_for_title(
            snyk_project_name="snyk-a",
            ado_organization="o",
            ado_project="p",
        )
        == "snyk-a"
    )


def test_effective_target_label_falls_back_to_azure_boards_path() -> None:
    assert (
        effective_target_label_for_title(
            snyk_project_name="",
            ado_organization="myorg",
            ado_project="myproj",
        )
        == "myorg / myproj"
    )


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


def test_recommended_upgrade_lines_from_remedy() -> None:
    attrs = {
        "coordinates": [
            {
                "remedies": [
                    {
                        "type": "upgrade",
                        "changes": [{"upgradeTo": "h11@0.16.0"}],
                    },
                ],
            },
        ],
    }
    assert recommended_upgrade_lines(attrs) == ["Upgrade to: h11@0.16.0"]


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
        snyk_project_name="my-snyk-repo",
        severity="critical",
    )
    assert "Snyk target: my-snyk-repo" in text
    assert "Severity: critical" in text
    assert "\n\n" in text
    assert "Prototype pollution" in text
    assert "Remediation steps (from Snyk):" in text
    assert "upgrade" in text.lower()
    assert "CVE-2023-29017" in text
    assert "Upgrade available" in text
    assert "Open in Snyk" in text
    assert (
        "https://app.snyk.io/org/acme/project/proj-uuid"
        "#issue-SNYK-JS-VM2-5415299"
    ) in text


def test_build_system_description_appendix_appended() -> None:
    attrs: dict = {"title": "X", "key": "K", "coordinates": []}
    appendix = "Internal: request access at https://example.internal/snyk"
    text = build_system_description(
        attrs,
        snyk_org_slug="o",
        project_id="p",
        issue_key="K",
        description_appendix=appendix,
    )
    assert text.endswith(appendix)
    assert "Open in Snyk" in text


def test_build_system_description_whitespace_appendix_skipped() -> None:
    attrs: dict = {"title": "X", "key": "K", "coordinates": []}
    base = build_system_description(
        attrs,
        snyk_org_slug="o",
        project_id="p",
        issue_key="K",
        description_appendix="",
    )
    assert (
        build_system_description(
            attrs,
            snyk_org_slug="o",
            project_id="p",
            issue_key="K",
            description_appendix="   \n\t  ",
        )
        == base
    )


def test_build_system_description_truncation_covers_appendix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(issue_content_mod, "_MAX_DESCRIPTION_CHARS", 260)
    attrs: dict = {"title": "X", "key": "K", "coordinates": []}
    appendix = "x" * 500
    text = build_system_description(
        attrs,
        snyk_org_slug="o",
        project_id="p",
        issue_key="K",
        description_appendix=appendix,
    )
    assert "[description truncated for Azure Boards field size]" in text
    assert len(text) <= 260


def test_build_create_patch_escapes_special_chars_in_description() -> None:
    """Appendix text uses the same description → HTML path as Snyk body text."""
    from sync.patch_build import build_create_patch

    plain = "Open\n\nRequest access: x & y <https://example.com>"
    ops = build_create_patch(
        title="T",
        description=plain,
        active_state="New",
        template={},
    )
    desc_op = next(o for o in ops if o.get("path") == "/fields/System.Description")
    val = desc_op["value"]
    assert "&amp;" in val
    assert "&lt;" in val
