"""Tests that sync/fetch wire merged Snyk API base URL into IssuesClient."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from commands.fetch import run_fetch
from commands.sync import run_sync_command


@pytest.fixture
def minimal_config_yaml(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "snyk:\n"
        "  group_id: 00000000-0000-0000-0000-000000000001\n"
        "  api_base_url: https://api.us.snyk.io\n"
        "azure_boards:\n"
        '  repo_mapping_csv: ""\n'
        "  defaults:\n"
        "    organization: ado\n"
        "    project: proj\n",
        encoding="utf-8",
    )
    return str(p)


def test_sync_passes_regional_rest_base_to_issues_client(
    minimal_config_yaml: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")

    captured: dict[str, str] = {}

    class _FakeIssuesClient:
        def __init__(self, base_url: str = "", **kwargs: object) -> None:
            captured["base_url"] = base_url

        def iter_group_issues(self, *args, **kwargs):
            return iter([])

    with patch("commands.sync.IssuesClient", _FakeIssuesClient):
        with patch("commands.sync.WorkItemsClient"):
            with patch("commands.sync.create_mapping_store", return_value=MagicMock()):
                with patch("commands.sync.run_sync"):
                    args = argparse.Namespace(
                        config=minimal_config_yaml,
                        mapping_store_sqlite_path=None,
                        group_id_flag=None,
                        snyk_api_base_url=None,
                        snyk_app_base_url=None,
                    )
                    assert run_sync_command(args) == 0

    assert captured["base_url"] == "https://api.us.snyk.io/rest"


def test_fetch_passes_regional_rest_base_to_issues_client(
    minimal_config_yaml: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")

    captured: dict[str, str] = {}

    class _FakeIssuesClient:
        def __init__(self, base_url: str = "", **kwargs: object) -> None:
            captured["base_url"] = base_url

        def iter_group_issues(self, *args, **kwargs):
            return iter([])

    with patch("commands.fetch.IssuesClient", _FakeIssuesClient):
        args = argparse.Namespace(
            action="list",
            config=minimal_config_yaml,
            mapping_store_sqlite_path=None,
            group_id_flag=None,
            org_id_flag=None,
            snyk_api_base_url=None,
            tail=[],
            severities=None,
            issue_type=None,
            status=None,
        )
        assert run_fetch(args) == 0

    assert captured["base_url"] == "https://api.us.snyk.io/rest"
