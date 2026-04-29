"""Tests for sync lifecycle derivation and severity helpers."""

import pytest

from config.errors import ConfigError
from config.models import (
    AppConfig,
    AzureBoardsConfig,
    AzureBoardsDefaults,
    OrgMapping,
    SnykConfig,
)
from sync.lifecycle import (
    DERIVED_IGNORED,
    DERIVED_OPEN,
    DERIVED_RESOLVED,
    coerce_ignored,
    derive_snyk_status,
    effective_severity_levels_from_threshold,
)
from sync.run import _format_audit_comment
from sync.validate import validate_sync_config, validate_sync_environment


def test_derive_ignored_precedence() -> None:
    out = derive_snyk_status(status="open", ignored=True)
    assert out is not None
    assert out.status == DERIVED_IGNORED


def test_derive_resolved() -> None:
    out = derive_snyk_status(status="resolved", ignored=False)
    assert out is not None
    assert out.status == DERIVED_RESOLVED


def test_derive_open() -> None:
    out = derive_snyk_status(status="open", ignored=False)
    assert out is not None
    assert out.status == DERIVED_OPEN


def test_derive_unexpected_status() -> None:
    assert derive_snyk_status(status="weird", ignored=False) is None


def test_coerce_ignored() -> None:
    assert coerce_ignored("true") is True
    assert coerce_ignored("0") is False


def test_effective_severity_levels_from_threshold() -> None:
    assert effective_severity_levels_from_threshold("high") == ("high", "critical")
    assert effective_severity_levels_from_threshold("low") == (
        "low",
        "medium",
        "high",
        "critical",
    )


def test_validate_sync_config_org_mappings_allows_missing_group_id() -> None:
    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(
            organization="",
            project="",
            org_mappings=[
                OrgMapping(
                    organization="ado-o",
                    project="ado-p",
                    snyk_org_id="org-id",
                    snyk_org_slug="acme",
                ),
            ],
            defaults=AzureBoardsDefaults(),
        ),
        work_item_template={},
        snyk=SnykConfig(group_id=""),
    )
    validate_sync_config(cfg)


def test_validate_sync_config_requires_org_project_group() -> None:
    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(organization="", project="x"),
        work_item_template={},
        snyk=SnykConfig(group_id="g"),
    )
    with pytest.raises(ConfigError, match="organization"):
        validate_sync_config(cfg)


def test_validate_sync_config_rejects_empty_work_item_type() -> None:
    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(
            organization="o",
            project="p",
            work_item_type="",
        ),
        work_item_template={},
        snyk=SnykConfig(group_id="g"),
    )
    with pytest.raises(ConfigError, match="work_item_type"):
        validate_sync_config(cfg)


def test_validate_sync_config_group_mode_allows_missing_org_slug() -> None:
    """Group-scoped sync does not configure a slug; links may be incomplete."""
    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(
            organization="o",
            project="p",
        ),
        work_item_template={},
        snyk=SnykConfig(group_id="g"),
    )
    validate_sync_config(cfg)


def test_validate_sync_config_requires_slug_each_org_mapping_row() -> None:
    """Empty row slug is rejected at YAML load; validation covers in-memory edge cases."""
    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(
            organization="",
            project="",
            org_mappings=[
                OrgMapping(
                    organization="ado-o",
                    project="ado-p",
                    snyk_org_id="org-id",
                    snyk_org_slug="ok",
                ),
            ],
            defaults=AzureBoardsDefaults(),
        ),
        work_item_template={},
        snyk=SnykConfig(group_id=""),
    )
    validate_sync_config(cfg)


def test_validate_sync_environment_requires_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SNYK_TOKEN", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
    with pytest.raises(ConfigError, match="SNYK_TOKEN"):
        validate_sync_environment()


def test_audit_comment_truncation() -> None:
    long_key = "K" * 5000
    text = _format_audit_comment(
        old_status="open",
        new_status="resolved",
        issue_key=long_key,
        prior_work_item_id=None,
    )
    assert len(text) <= 4000
    assert text.endswith("[truncated]")


def test_validate_sync_environment_requires_pat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "token-for-test")
    monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
    with pytest.raises(ConfigError, match="AZURE_DEVOPS_PAT"):
        validate_sync_environment()
