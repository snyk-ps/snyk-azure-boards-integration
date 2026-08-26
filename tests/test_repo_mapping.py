"""Tests for repo-mapping CSV load and routing resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from unittest.mock import MagicMock

from config.errors import ConfigError
from config.models import AppConfig, AzureBoardsConfig, AzureBoardsDefaults, SnykConfig
from sync.area_path import AUTO_DEFAULT_AREA_SEGMENT
from sync.repo_mapping import (
    FinalizedAreaPath,
    RepoMappingIndex,
    RepoMappingMatch,
    finalize_area_path_for_auto_create,
    load_repo_mapping_index,
    parse_area_path_for_project,
    parse_owner_repo,
    resolve_repo_mapping_csv_path,
    resolve_routing,
    snyk_origin_to_csv_source,
)

_MINIMAL_CSV = (
    "Source,GitHub Org/ADO Project,Repo Name,ADO Organization,Area Path,"
    "Assignee (Optional)\n"
    "github,my-org,payments-api,ado-o,MyProject\\Payments,user@example.com\n"
    "azure-repos,MyAdoProject,frontend,ado-o,OtherProject\\Frontend,\n"
)

_LEGACY_ASSIGNEE_CSV = (
    "Source,GitHub Org/ADO Project,Repo Name,ADO Organization,Area Path,Assignee\n"
    "github,my-org,payments-api,ado-o,MyProject\\Payments,user@example.com\n"
)


def test_snyk_origin_to_csv_source_github_family() -> None:
    assert snyk_origin_to_csv_source("github") == "github"
    assert snyk_origin_to_csv_source("github-cloud-app") == "github"
    assert snyk_origin_to_csv_source("github-enterprise") == "github"
    assert snyk_origin_to_csv_source("github-server-app") == "github"


def test_snyk_origin_to_csv_source_azure_repos() -> None:
    assert snyk_origin_to_csv_source("azure-repos") == "azure-repos"


def test_snyk_origin_to_csv_source_unmapped() -> None:
    assert snyk_origin_to_csv_source("cli") is None


def test_parse_owner_repo_standard() -> None:
    assert parse_owner_repo("my-org/payments-api") == ("my-org", "payments-api")


def test_parse_owner_repo_no_slash() -> None:
    assert parse_owner_repo("standalone") == ("", "standalone")


def test_parse_owner_repo_strips_branch_and_manifest_suffix() -> None:
    assert parse_owner_repo("Torsten1014/nodejs-goof(main):package.json") == (
        "Torsten1014",
        "nodejs-goof",
    )
    assert parse_owner_repo("testProjectBug/nodejs-goof.git(main):package.json") == (
        "testProjectBug",
        "nodejs-goof.git",
    )


def test_parse_area_path_for_project_requires_two_segments() -> None:
    project, full = parse_area_path_for_project(r"MyProject\Payments")
    assert project == "MyProject"
    assert full == r"MyProject\Payments"
    with pytest.raises(ConfigError, match="two segments"):
        parse_area_path_for_project("TeamOnly")


def test_resolve_routing_matches_csv_with_branch_manifest_display_name() -> None:
    index = RepoMappingIndex(
        {
            ("azure-repos", "testProjectBug", "nodejs-goof.git"): RepoMappingMatch(
                organization="ado-o",
                project="testProjectBug",
                area_path="testProjectBug\\test-area",
                assignee="user@example.com",
            ),
        },
    )
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(organization="cfg-o", project="cfg-p"),
    )
    routing = resolve_routing(
        index=index,
        snyk_project_origin="azure-repos",
        snyk_project_name="testProjectBug/nodejs-goof.git(main):package.json",
        boards=boards,
        global_defaults_area_path=None,
    )
    assert routing.organization == "ado-o"
    assert routing.project == "testProjectBug"
    assert routing.area_path == "testProjectBug\\test-area"
    assert routing.ado_target_source == "csv"
    assert routing.area_path_source == "csv"
    assert routing.assignee == "user@example.com"


def test_repo_mapping_index_load_and_lookup(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(_MINIMAL_CSV, encoding="utf-8")
    index = RepoMappingIndex.load_from_path(p)
    match = index.lookup("github", "my-org", "payments-api")
    assert match is not None
    assert match.organization == "ado-o"
    assert match.project == "MyProject"
    assert match.area_path == "MyProject\\Payments"
    assert match.assignee == "user@example.com"


def test_repo_mapping_index_accepts_legacy_assignee_header(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(_LEGACY_ASSIGNEE_CSV, encoding="utf-8")
    index = RepoMappingIndex.load_from_path(p)
    match = index.lookup("github", "my-org", "payments-api")
    assert match is not None
    assert match.assignee == "user@example.com"


def test_repo_mapping_index_rejects_missing_ado_organization_header(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(
        "Source,GitHub Org/ADO Project,Repo Name,Area Path\n"
        "github,my-org,repo,ado-o,MyProject\\Area\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="ado organization"):
        RepoMappingIndex.load_from_path(p)


def test_repo_mapping_index_rejects_empty_ado_organization(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(
        "Source,GitHub Org/ADO Project,Repo Name,ADO Organization,Area Path\n"
        "github,my-org,repo,,MyProject\\Area\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="ADO Organization"):
        RepoMappingIndex.load_from_path(p)


def test_repo_mapping_index_rejects_single_segment_area_path(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(
        "Source,GitHub Org/ADO Project,Repo Name,ADO Organization,Area Path\n"
        "github,my-org,repo,ado-o,TeamOnly\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="two segments"):
        RepoMappingIndex.load_from_path(p)


def test_repo_mapping_index_rejects_invalid_source(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(
        "Source,GitHub Org/ADO Project,Repo Name,ADO Organization,Area Path\n"
        "gitlab,my-org,repo,ado-o,MyProject\\Area\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="github.*azure-repos"):
        RepoMappingIndex.load_from_path(p)


def test_repo_mapping_index_rejects_duplicate_keys(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(
        "Source,GitHub Org/ADO Project,Repo Name,ADO Organization,Area Path\n"
        "github,my-org,repo,ado-o,MyProject\\Area1\n"
        "github,my-org,repo,ado-o,MyProject\\Area2\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="Duplicate"):
        RepoMappingIndex.load_from_path(p)


def test_resolve_repo_mapping_csv_path_default_beside_config() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(),
        work_item_template={},
        snyk=SnykConfig(),
        config_file_dir="/config",
    )
    assert resolve_repo_mapping_csv_path(app) == Path("/config/repo-mapping.csv")


def test_resolve_repo_mapping_csv_path_empty_disables() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(repo_mapping_csv=""),
        work_item_template={},
        snyk=SnykConfig(),
        config_file_dir="/config",
    )
    assert resolve_repo_mapping_csv_path(app) is None


def test_load_repo_mapping_index_missing_file_raises() -> None:
    app = AppConfig(
        azure_boards=AzureBoardsConfig(),
        work_item_template={},
        snyk=SnykConfig(),
        config_file_dir="/does/not/exist",
    )
    with pytest.raises(ConfigError, match="not found"):
        load_repo_mapping_index(app)


def test_resolve_routing_csv_beats_defaults() -> None:
    index = RepoMappingIndex(
        {
            ("github", "my-org", "payments-api"): RepoMappingMatch(
                organization="csv-o",
                project="CsvProject",
                area_path="CSV\\Path",
                assignee="csv@example.com",
            ),
        },
    )
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(
            organization="cfg-o",
            project="cfg-p",
            area_path="Default\\Path",
        ),
    )
    routing = resolve_routing(
        index=index,
        snyk_project_origin="github-cloud-app",
        snyk_project_name="my-org/payments-api",
        boards=boards,
        global_defaults_area_path="Default\\Path",
    )
    assert routing.organization == "csv-o"
    assert routing.project == "CsvProject"
    assert routing.area_path == "CSV\\Path"
    assert routing.ado_target_source == "csv"
    assert routing.area_path_source == "csv"
    assert routing.assignee == "csv@example.com"
    assert routing.assignee_from_csv is True


def test_resolve_routing_org_override_beats_global_default() -> None:
    index = RepoMappingIndex.empty()
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(
            organization="cfg-o",
            project="cfg-p",
            area_path="Org\\Path",
        ),
    )
    routing = resolve_routing(
        index=index,
        snyk_project_origin="cli",
        snyk_project_name="org/repo",
        boards=boards,
        global_defaults_area_path="Global\\Path",
    )
    assert routing.organization == "cfg-o"
    assert routing.project == "cfg-p"
    assert routing.ado_target_source == "config"
    assert routing.area_path == "Org\\Path"
    assert routing.area_path_source == "org_override"


def test_resolve_routing_none_when_unset() -> None:
    index = RepoMappingIndex.empty()
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(organization="cfg-o", project="cfg-p"),
    )
    routing = resolve_routing(
        index=index,
        snyk_project_origin="cli",
        snyk_project_name="org/repo",
        boards=boards,
        global_defaults_area_path=None,
    )
    assert routing.organization == "cfg-o"
    assert routing.project == "cfg-p"
    assert routing.area_path is None
    assert routing.area_path_source == "none"


def test_resolve_routing_auto_default_when_enabled() -> None:
    index = RepoMappingIndex.empty()
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(
            organization="cfg-o",
            project="AppTeam",
            auto_create_area_path=True,
        ),
    )
    routing = resolve_routing(
        index=index,
        snyk_project_origin="cli",
        snyk_project_name="org/repo",
        boards=boards,
        global_defaults_area_path=None,
    )
    assert routing.area_path == f"AppTeam\\{AUTO_DEFAULT_AREA_SEGMENT}"
    assert routing.area_path_source == "auto_default"


def test_resolve_routing_auto_default_disabled_when_false() -> None:
    index = RepoMappingIndex.empty()
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(
            organization="cfg-o",
            project="AppTeam",
            auto_create_area_path=False,
        ),
    )
    routing = resolve_routing(
        index=index,
        snyk_project_origin="cli",
        snyk_project_name="org/repo",
        boards=boards,
        global_defaults_area_path=None,
    )
    assert routing.area_path is None
    assert routing.area_path_source == "none"


_TAXONOMY_CSV = (
    "Source,GitHub Org/ADO Project,Repo Name,ADO Organization,Area Path,"
    "Assignee (Optional),Work Item Type (Optional),Active State (Optional),"
    "Tags (Optional)\n"
    "github,my-org,payments-api,ado-o,MyProject\\Payments,user@example.com,"
    "Bug,Active,TeamA\n"
)


def test_repo_mapping_csv_optional_taxonomy_columns(tmp_path: Path) -> None:
    path = tmp_path / "repo-mapping.csv"
    path.write_text(_TAXONOMY_CSV, encoding="utf-8")
    index = RepoMappingIndex.load_from_path(path)
    match = index.lookup("github", "my-org", "payments-api")
    assert match is not None
    assert match.work_item_type == "Bug"
    assert match.work_item_state_active == "Active"
    assert match.csv_tags == ("TeamA",)


def test_finalize_area_path_substitutes_when_configured_missing() -> None:
    client = MagicMock()
    client.get_classification_node.return_value = None
    routing = resolve_routing(
        index=RepoMappingIndex(
            {
                ("github", "my-org", "payments-api"): RepoMappingMatch(
                    organization="ado-o",
                    project="Proj",
                    area_path="Proj\\Missing",
                    assignee="",
                ),
            },
        ),
        snyk_project_origin="github",
        snyk_project_name="my-org/payments-api",
        boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(auto_create_area_path=True),
        ),
    )
    finalized = finalize_area_path_for_auto_create(
        client=client,
        routing=routing,
        auto_create_area_path=True,
        fallback_template="{project}\\Snyk",
        existence_cache={},
    )
    assert isinstance(finalized, FinalizedAreaPath)
    assert finalized.routing.area_path == "Proj\\Snyk"
    assert finalized.routing.area_path_source == "auto_fallback"
    assert finalized.missing_configured_path == "Proj\\Missing"


def test_finalize_area_path_keeps_existing_configured_path() -> None:
    client = MagicMock()
    client.get_classification_node.return_value = {"name": "TeamA"}
    routing = resolve_routing(
        index=RepoMappingIndex(
            {
                ("github", "my-org", "payments-api"): RepoMappingMatch(
                    organization="ado-o",
                    project="Proj",
                    area_path="Proj\\TeamA",
                    assignee="",
                ),
            },
        ),
        snyk_project_origin="github",
        snyk_project_name="my-org/payments-api",
        boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(auto_create_area_path=True),
        ),
    )
    finalized = finalize_area_path_for_auto_create(
        client=client,
        routing=routing,
        auto_create_area_path=True,
        fallback_template="{project}\\Snyk",
        existence_cache={},
    )
    assert finalized.routing.area_path == "Proj\\TeamA"
    assert finalized.routing.area_path_source == "csv"
    client.create_classification_node.assert_not_called()
