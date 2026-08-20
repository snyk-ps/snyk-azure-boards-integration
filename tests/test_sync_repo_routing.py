"""Integration-style tests for repo area path routing in ``run_sync``."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from config.loader import load_app_config
from integrations.azure_devops.client import WorkItemsClient
from mapping_store.sqlite_store import SqliteMappingStore
from snyk.client import IssuesClient
from sync.run import run_sync

_MINIMAL_CSV = (
    "Source,GitHub Org/ADO Project,Repo Name,Area Path,Assignee\n"
    "github,my-org,payments-api,MyProject\\Payments,csv@example.com\n"
)


def _cfg_yaml(*, area_path: str = "", repo_csv: str = "repo-mapping.csv") -> str:
    lines = [
        "azure_boards:",
        f"  repo_mapping_csv: {repo_csv!r}",
        "  defaults:",
        "    organization: ado-o",
        "    project: ado-p",
    ]
    if area_path:
        lines.append(f"    area_path: '{area_path}'")
    lines.extend(
        [
            "  org_mappings:",
            "    - organization: ado-o",
            "      project: ado-p",
            "      snyk_org_id: org-uuid",
            "      snyk_org_slug: org-slug",
            "snyk:",
            '  group_id: "group-uuid"',
        ],
    )
    return "\n".join(lines) + "\n"


@pytest.fixture
def env_pat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")


def _open_issue() -> dict:
    return {
        "org_id": "org-uuid",
        "project_id": "proj-uuid",
        "issue_id": "ISS-1",
        "snyk_project_name": "my-org/payments-api",
        "issue_attributes": {
            "status": "open",
            "ignored": False,
            "key": "ISS-1",
            "effective_severity_level": "high",
            "description": "d",
            "coordinates": [{"remedies": [{"type": "semver"}]}],
        },
    }


def test_run_sync_create_uses_csv_area_path(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(_cfg_yaml(), encoding="utf-8")
    (tmp_path / "repo-mapping.csv").write_text(_MINIMAL_CSV, encoding="utf-8")
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.create_work_item.return_value = {
        "work_item_id": "42",
        "work_item_status": "New",
    }

    monkeypatch.setattr(issues, "iter_org_issues", lambda *a, **k: iter([_open_issue()]))
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "my-org/payments-api", "origin": "github"},
    )
    monkeypatch.setattr("sync.run.batch_get_work_items", lambda *a, **k: {})

    rc = run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store)
    assert rc == 0
    patches = wit.create_work_item.call_args[0][3]
    area_ops = [o for o in patches if o.get("path") == "/fields/System.AreaPath"]
    assert area_ops and area_ops[0]["value"] == "MyProject\\Payments"
    assignee_ops = [o for o in patches if o.get("path") == "/fields/System.AssignedTo"]
    assert assignee_ops and assignee_ops[0]["value"] == "csv@example.com"


def test_run_sync_update_moves_area_path_with_comment(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(_cfg_yaml(), encoding="utf-8")
    (tmp_path / "repo-mapping.csv").write_text(_MINIMAL_CSV, encoding="utf-8")
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    store.upsert(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-1",
        snyk_status="open",
        organization="ado-o",
        project="ado-p",
        work_item_id="99",
        work_item_status="New",
        snyk_project_name="my-org/payments-api",
        snyk_project_origin="github",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.update_work_item.return_value = {
        "work_item_id": "99",
        "work_item_status": "New",
    }

    monkeypatch.setattr(issues, "iter_org_issues", lambda *a, **k: iter([_open_issue()]))
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "my-org/payments-api", "origin": "github"},
    )
    monkeypatch.setattr(
        "sync.run.batch_get_work_items",
        lambda *a, **k: {
            "99": {
                "work_item_id": "99",
                "work_item_status": "New",
                "fields": {"System.AreaPath": "Old\\Path"},
            },
        },
    )

    rc = run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store)
    assert rc == 0
    patches = wit.update_work_item.call_args[0][3]
    assert any(o.get("path") == "/fields/System.AreaPath" for o in patches)
    wit.add_work_item_comment.assert_any_call(
        "ado-o",
        "ado-p",
        "99",
        "Snyk sync moved work item area path from 'Old\\Path' to 'MyProject\\Payments'.",
    )


def test_run_sync_yaml_fallback_when_no_csv_match(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        _cfg_yaml(area_path=r"Default\Area", repo_csv=""),
        encoding="utf-8",
    )
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    issue = _open_issue()
    issue["snyk_project_name"] = "other-org/other-repo"

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.create_work_item.return_value = {"work_item_id": "1", "work_item_status": "New"}

    monkeypatch.setattr(issues, "iter_org_issues", lambda *a, **k: iter([issue]))
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "other-org/other-repo", "origin": "github"},
    )
    monkeypatch.setattr("sync.run.batch_get_work_items", lambda *a, **k: {})

    rc = run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store)
    assert rc == 0
    patches = wit.create_work_item.call_args[0][3]
    area_ops = [o for o in patches if o.get("path") == "/fields/System.AreaPath"]
    assert area_ops and area_ops[0]["value"] == "Default\\Area"
