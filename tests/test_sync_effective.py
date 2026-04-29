"""Tests for ``sync.effective`` helpers."""

from config.models import (
    AppConfig,
    AzureBoardsConfig,
    AzureBoardsDefaults,
    OrgMapping,
    SnykConfig,
)
from sync.effective import (
    boards_for_org_mapping,
    effective_snyk_org_slug,
    effective_work_item_template,
)


def test_boards_for_org_mapping_applies_overrides() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(
                work_item_type="Task",
                work_item_state_active="New",
                work_item_state_closed="Closed",
            ),
        ),
        work_item_template={},
        snyk=SnykConfig(),
    )
    m = OrgMapping(
        organization="o",
        project="p",
        snyk_org_id="s",
        overrides={"work_item_type": "Bug"},
    )
    b = boards_for_org_mapping(app, m)
    assert b.work_item_type == "Bug"
    assert b.organization == "o"


def test_effective_snyk_org_slug_from_mapping_row() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(),
        work_item_template={},
        snyk=SnykConfig(),
    )
    m = OrgMapping(
        organization="o",
        project="p",
        snyk_org_id="id",
        snyk_org_slug="row-slug",
    )
    assert effective_snyk_org_slug(app, m) == "row-slug"


def test_effective_snyk_org_slug_group_mode_empty() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(organization="o", project="p"),
        work_item_template={},
        snyk=SnykConfig(),
    )
    assert effective_snyk_org_slug(app, None) == ""


def test_effective_work_item_template_merge() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(
                work_item_template={"tags": ["default-tag"]},
            ),
        ),
        work_item_template={"tags": ["global"]},
        snyk=SnykConfig(),
    )
    out = effective_work_item_template(
        app,
        {"work_item_template": {"tags": ["row"]}},
    )
    assert out["tags"] == ["global", "default-tag", "row"]
