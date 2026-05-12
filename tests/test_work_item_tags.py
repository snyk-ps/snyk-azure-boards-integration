"""Unit tests for Snyk-derived Azure Boards tag helpers."""

from __future__ import annotations

import pytest

from sync.patch_build import build_create_patch, build_update_patch
from sync.work_item_tags import (
    combine_tags_for_work_item,
    managed_severity_tag_from_level,
    managed_type_tag_from_issue_type,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("high", "Snyk-Severity-high"),
        ("HIGH", "Snyk-Severity-high"),
        ("critical", "Snyk-Severity-critical"),
        ("medium", "Snyk-Severity-medium"),
        ("low", "Snyk-Severity-low"),
    ],
)
def test_managed_severity_tag_known_levels(raw: str, expected: str) -> None:
    assert managed_severity_tag_from_level(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "  ", "nope", "unknown"])
def test_managed_severity_tag_missing_or_unknown(raw: str | None) -> None:
    assert managed_severity_tag_from_level(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("package_vulnerability", "Snyk-Type-open_source"),
        ("license", "Snyk-Type-license"),
        ("cloud", "Snyk-Type-iac"),
        ("code", "Snyk-Type-code"),
        ("custom", "Snyk-Type-custom"),
        ("config", "Snyk-Type-iac"),
        ("package", "Snyk-Type-open_source"),
        ("PACKAGE", "Snyk-Type-open_source"),
        ("container", "Snyk-Type-container"),
        ("terraform", "Snyk-Type-iac"),
    ],
)
def test_managed_type_tag_mappings(raw: str, expected: str) -> None:
    assert managed_type_tag_from_issue_type(raw) == expected


def test_managed_type_tag_license_synonym_to_license_suffix() -> None:
    """``licensing`` token maps like license findings (explicit ``Snyk-Type-license``)."""
    assert managed_type_tag_from_issue_type("licensing") == "Snyk-Type-license"


def test_managed_type_tag_hyphen_and_spaces() -> None:
    """Hyphens and spaces normalize like ``issue_snyk_type`` design."""
    assert managed_type_tag_from_issue_type("open-source") == "Snyk-Type-open_source"
    assert managed_type_tag_from_issue_type("cloud formation") == "Snyk-Type-iac"


def test_managed_type_tag_unknown_returns_none() -> None:
    assert managed_type_tag_from_issue_type(None) is None
    assert managed_type_tag_from_issue_type("") is None
    assert managed_type_tag_from_issue_type("unknown_custom") is None


def test_combine_operator_only_preserves_order() -> None:
    out = combine_tags_for_work_item(
        ["Alpha", "Beta"],
        managed_severity_tag=None,
        managed_type_tag=None,
    )
    assert out == ["Alpha", "Beta"]


def test_combine_managed_only() -> None:
    assert combine_tags_for_work_item(
        [],
        managed_severity_tag="Snyk-Severity-high",
        managed_type_tag="Snyk-Type-code",
    ) == ["Snyk-Severity-high", "Snyk-Type-code"]


def test_combine_union_order() -> None:
    out = combine_tags_for_work_item(
        ["Snyk", "Security"],
        managed_severity_tag="Snyk-Severity-critical",
        managed_type_tag="Snyk-Type-open_source",
    )
    assert out == ["Snyk", "Security", "Snyk-Severity-critical", "Snyk-Type-open_source"]


def test_combine_strips_reserved_prefixes_then_uses_managed() -> None:
    out = combine_tags_for_work_item(
        ["Roadmap", "Snyk-Severity-critical", "Snyk-Type-code"],
        managed_severity_tag="Snyk-Severity-high",
        managed_type_tag="Snyk-Type-open_source",
    )
    assert out == ["Roadmap", "Snyk-Severity-high", "Snyk-Type-open_source"]


def test_combine_consecutive_duplicate_collapse() -> None:
    out = combine_tags_for_work_item(
        ["Dup", "Dup"],
        managed_severity_tag="Snyk-Severity-low",
        managed_type_tag=None,
    )
    assert out == ["Dup", "Snyk-Severity-low"]


def test_build_create_patch_tags_with_managed_and_operator() -> None:
    tpl = {"tags": ["Snyk", "product"]}
    ops = build_create_patch(
        title="T",
        description="D",
        active_state="New",
        template=tpl,
        issue_effective_severity_level="high",
        issue_snyk_type="package",
    )
    tag_op = next(o for o in ops if o.get("path") == "/fields/System.Tags")
    assert tag_op["value"] == (
        "Snyk; product; Snyk-Severity-high; Snyk-Type-open_source"
    )


def test_build_create_patch_omits_system_tags_when_no_tags() -> None:
    ops = build_create_patch(
        title="T",
        description="D",
        active_state="New",
        template={},
        issue_effective_severity_level=None,
        issue_snyk_type=None,
    )
    paths = [o["path"] for o in ops]
    assert "/fields/System.Tags" not in paths


def test_build_update_patch_managed_only_tags() -> None:
    ops = build_update_patch(
        title="T",
        description="D",
        state="Done",
        template={},
        issue_effective_severity_level="Medium",
        issue_snyk_type="Code",
    )
    tag_op = next(o for o in ops if o.get("path") == "/fields/System.Tags")
    assert tag_op["op"] == "replace"
    assert tag_op["value"] == "Snyk-Severity-medium; Snyk-Type-code"
