"""Tests for repo-mapping CSV load and routing resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.errors import ConfigError
from config.models import AppConfig, AzureBoardsConfig, AzureBoardsDefaults, SnykConfig
from sync.repo_mapping import (
    RepoMappingIndex,
    load_repo_mapping_index,
    parse_owner_repo,
    resolve_repo_mapping_csv_path,
    resolve_routing,
    snyk_origin_to_csv_source,
)

_MINIMAL_CSV = (
    "Source,GitHub Org/ADO Project,Repo Name,Area Path,Assignee\n"
    "github,my-org,payments-api,MyProject\\Payments,user@example.com\n"
    "azure-repos,MyAdoProject,frontend,MyProject\\Frontend,\n"
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


def test_resolve_routing_matches_csv_with_branch_manifest_display_name() -> None:
    from sync.repo_mapping import RepoMappingMatch

    index = RepoMappingIndex(
        {
            ("azure-repos", "testProjectBug", "nodejs-goof.git"): RepoMappingMatch(
                area_path="testProjectBug\\test-area",
                assignee="user@example.com",
            ),
        },
    )
    boards = AzureBoardsConfig(defaults=AzureBoardsDefaults())
    routing = resolve_routing(
        index=index,
        snyk_project_origin="azure-repos",
        snyk_project_name="testProjectBug/nodejs-goof.git(main):package.json",
        boards=boards,
        global_defaults_area_path=None,
    )
    assert routing.area_path == "testProjectBug\\test-area"
    assert routing.area_path_source == "csv"
    assert routing.assignee == "user@example.com"


def test_repo_mapping_index_load_and_lookup(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(_MINIMAL_CSV, encoding="utf-8")
    index = RepoMappingIndex.load_from_path(p)
    match = index.lookup("github", "my-org", "payments-api")
    assert match is not None
    assert match.area_path == "MyProject\\Payments"
    assert match.assignee == "user@example.com"


def test_repo_mapping_index_rejects_invalid_source(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(
        "Source,GitHub Org/ADO Project,Repo Name,Area Path\n"
        "gitlab,my-org,repo,Area\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="github.*azure-repos"):
        RepoMappingIndex.load_from_path(p)


def test_repo_mapping_index_rejects_duplicate_keys(tmp_path: Path) -> None:
    p = tmp_path / "repo-mapping.csv"
    p.write_text(
        "Source,GitHub Org/ADO Project,Repo Name,Area Path\n"
        "github,my-org,repo,Area1\n"
        "github,my-org,repo,Area2\n",
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
    from sync.repo_mapping import RepoMappingMatch

    index = RepoMappingIndex(
        {
            ("github", "my-org", "payments-api"): RepoMappingMatch(
                area_path="CSV\\Path",
                assignee="csv@example.com",
            ),
        },
    )
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(area_path="Default\\Path"),
    )
    routing = resolve_routing(
        index=index,
        snyk_project_origin="github-cloud-app",
        snyk_project_name="my-org/payments-api",
        boards=boards,
        global_defaults_area_path="Default\\Path",
    )
    assert routing.area_path == "CSV\\Path"
    assert routing.area_path_source == "csv"
    assert routing.assignee == "csv@example.com"
    assert routing.assignee_from_csv is True


def test_resolve_routing_org_override_beats_global_default() -> None:
    index = RepoMappingIndex.empty()
    boards = AzureBoardsConfig(
        defaults=AzureBoardsDefaults(area_path="Org\\Path"),
    )
    routing = resolve_routing(
        index=index,
        snyk_project_origin="cli",
        snyk_project_name="org/repo",
        boards=boards,
        global_defaults_area_path="Global\\Path",
    )
    assert routing.area_path == "Org\\Path"
    assert routing.area_path_source == "org_override"


def test_resolve_routing_none_when_unset() -> None:
    index = RepoMappingIndex.empty()
    boards = AzureBoardsConfig(defaults=AzureBoardsDefaults())
    routing = resolve_routing(
        index=index,
        snyk_project_origin="cli",
        snyk_project_name="org/repo",
        boards=boards,
        global_defaults_area_path=None,
    )
    assert routing.area_path is None
    assert routing.area_path_source == "none"
