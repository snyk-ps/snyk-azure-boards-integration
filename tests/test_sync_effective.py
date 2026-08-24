"""Tests for ``sync.effective`` helpers."""

import pytest

from config import ConfigError
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
    resolve_effective_work_item_config,
)
from config.models import AdoTargetIndex, AdoTargetProfile
from sync.repo_mapping import RepoMappingMatch


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


def test_boards_for_org_mapping_description_field_override() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(
                work_item_type="Task",
                work_item_description_field=None,
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
        overrides={"work_item_description_field": "Microsoft.VSTS.TCM.ReproSteps"},
    )
    b = boards_for_org_mapping(app, m)
    assert (
        b.defaults.work_item_description_field == "Microsoft.VSTS.TCM.ReproSteps"
    )


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


def test_boards_for_org_mapping_appendix_override() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(
                work_item_description_appendix="default appendix",
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
        overrides={"work_item_description_appendix": "row appendix"},
    )
    b = boards_for_org_mapping(app, m)
    assert b.defaults.work_item_description_appendix == "row appendix"


def test_boards_for_org_mapping_rejects_non_string_appendix_override() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(),
        ),
        work_item_template={},
        snyk=SnykConfig(),
    )
    m = OrgMapping(
        organization="o",
        project="p",
        snyk_org_id="s",
        snyk_org_slug="slug",
        overrides={"work_item_description_appendix": 99},
    )
    with pytest.raises(ConfigError, match="work_item_description_appendix must be a string"):
        boards_for_org_mapping(app, m)


def _app_with_defaults() -> AppConfig:
    return AppConfig(
        azure_boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(
                work_item_type="Task",
                work_item_state_active="To Do",
                work_item_state_closed="Done",
                work_item_template={"tags": ["Snyk"]},
            ),
        ),
        work_item_template={},
        snyk=SnykConfig(),
    )


def test_resolve_effective_work_item_config_ado_target_for_csv_project() -> None:
    app = _app_with_defaults()
    index = AdoTargetIndex.from_profiles(
        [
            AdoTargetProfile(
                organization="myado",
                project="PaymentsProject",
                work_item_type="Bug",
                work_item_state_active="New",
                work_item_state_closed="Closed",
            ),
        ],
    )
    mapping = OrgMapping(
        organization="myado",
        project="DefaultProject",
        snyk_org_id="s",
        snyk_org_slug="slug",
        overrides={"work_item_type": "Task", "work_item_state_active": "To Do"},
    )
    boards = boards_for_org_mapping(app, mapping)
    csv_match = RepoMappingMatch(
        organization="myado",
        project="PaymentsProject",
        area_path=r"PaymentsProject\Pay",
        assignee="",
    )
    effective = resolve_effective_work_item_config(
        app=app,
        boards=boards,
        org_mapping=mapping,
        ado_target_index=index,
        effective_organization="myado",
        effective_project="PaymentsProject",
        csv_match=csv_match,
    )
    assert effective.work_item_type == "Bug"
    assert effective.work_item_state_active == "New"
    assert effective.work_item_config_source == "ado_target"


def test_resolve_effective_work_item_config_csv_overrides_single_field() -> None:
    app = _app_with_defaults()
    index = AdoTargetIndex.from_profiles(
        [
            AdoTargetProfile(
                organization="myado",
                project="PaymentsProject",
                work_item_type="Bug",
                work_item_state_active="New",
            ),
        ],
    )
    mapping = OrgMapping(
        organization="myado",
        project="DefaultProject",
        snyk_org_id="s",
        snyk_org_slug="slug",
    )
    boards = boards_for_org_mapping(app, mapping)
    csv_match = RepoMappingMatch(
        organization="myado",
        project="PaymentsProject",
        area_path=r"PaymentsProject\Pay",
        assignee="",
        work_item_state_active="Active",
    )
    effective = resolve_effective_work_item_config(
        app=app,
        boards=boards,
        org_mapping=mapping,
        ado_target_index=index,
        effective_organization="myado",
        effective_project="PaymentsProject",
        csv_match=csv_match,
    )
    assert effective.work_item_state_active == "Active"
    assert effective.work_item_type == "Bug"
    assert effective.work_item_config_source == "csv"


def test_resolve_effective_work_item_config_org_override_same_target() -> None:
    app = _app_with_defaults()
    mapping = OrgMapping(
        organization="myado",
        project="DefaultProject",
        snyk_org_id="s",
        snyk_org_slug="slug",
        overrides={"work_item_type": "Bug", "work_item_state_active": "New"},
    )
    boards = boards_for_org_mapping(app, mapping)
    effective = resolve_effective_work_item_config(
        app=app,
        boards=boards,
        org_mapping=mapping,
        ado_target_index=AdoTargetIndex.empty(),
        effective_organization="myado",
        effective_project="DefaultProject",
        csv_match=None,
    )
    assert effective.work_item_type == "Bug"
    assert effective.work_item_config_source == "org_override"


def test_resolve_effective_work_item_config_csv_tags_merge() -> None:
    app = _app_with_defaults()
    index = AdoTargetIndex.from_profiles(
        [
            AdoTargetProfile(
                organization="myado",
                project="PaymentsProject",
                work_item_template={"tags": ["Security"]},
            ),
        ],
    )
    boards = boards_for_org_mapping(
        app,
        OrgMapping(
            organization="myado",
            project="DefaultProject",
            snyk_org_id="s",
            snyk_org_slug="slug",
        ),
    )
    csv_match = RepoMappingMatch(
        organization="myado",
        project="PaymentsProject",
        area_path=r"PaymentsProject\Pay",
        assignee="",
        csv_tags=("TeamA",),
    )
    effective = resolve_effective_work_item_config(
        app=app,
        boards=boards,
        org_mapping=OrgMapping(
            organization="myado",
            project="DefaultProject",
            snyk_org_id="s",
            snyk_org_slug="slug",
        ),
        ado_target_index=index,
        effective_organization="myado",
        effective_project="PaymentsProject",
        csv_match=csv_match,
    )
    assert effective.template.get("tags") == ["Snyk", "Security", "TeamA"]

