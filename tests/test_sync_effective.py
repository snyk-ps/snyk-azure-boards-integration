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
        snyk_org_slug="slug",
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


def test_org_mapping_override_template_not_baked_into_defaults() -> None:
    """Row work_item_template must merge once in effective_work_item_template only."""
    app = AppConfig(
        azure_boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(
                work_item_template={"tags": ["Snyk"], "json_patch": []},
            ),
        ),
        work_item_template={},
        snyk=SnykConfig(),
    )
    patch_op = {
        "op": "add",
        "path": "/fields/System.AssignedTo",
        "value": "user@example.com",
    }
    m = OrgMapping(
        organization="o",
        project="p",
        snyk_org_id="oid",
        snyk_org_slug="slug",
        overrides={"work_item_template": {"json_patch": [patch_op]}},
    )
    boards = boards_for_org_mapping(app, m)
    assert boards.defaults.work_item_template == app.azure_boards.defaults.work_item_template

    merged = effective_work_item_template(app, m.overrides, boards=boards)
    assert merged["json_patch"] == [patch_op]


def test_effective_work_item_template_merge() -> None:
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(
            work_item_template={"tags": ["default-tag"]},
        ),
    )
    app = AppConfig(
        azure_boards=boards,
        work_item_template={"tags": ["global"]},
        snyk=SnykConfig(),
    )
    out = effective_work_item_template(
        app,
        {"work_item_template": {"tags": ["row"]}},
        boards=boards,
    )
    assert out["tags"] == ["global", "default-tag", "row"]
