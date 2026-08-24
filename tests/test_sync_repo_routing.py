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
    "Source,GitHub Org/ADO Project,Repo Name,ADO Organization,Area Path,"
    "Assignee (Optional)\n"
    "github,my-org,payments-api,ado-o,MyProject\\Payments,csv@example.com\n"
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


def test_run_sync_create_uses_csv_ado_target_and_area_path(
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
    create_args = wit.create_work_item.call_args[0]
    assert create_args[0] == "ado-o"
    assert create_args[1] == "MyProject"
    patches = create_args[3]
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
        project="MyProject",
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
    update_args = wit.update_work_item.call_args[0]
    assert update_args[0] == "ado-o"
    assert update_args[1] == "MyProject"
    patches = update_args[3]
    assert any(o.get("path") == "/fields/System.AreaPath" for o in patches)
    wit.add_work_item_comment.assert_any_call(
        "ado-o",
        "MyProject",
        "99",
        "Snyk sync moved work item area path from 'Old\\Path' to 'MyProject\\Payments'.",
    )


def test_run_sync_batch_prefetch_partitions_by_stored_ado_target(
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
        project="MyProject",
        work_item_id="99",
        work_item_status="New",
        snyk_project_name="my-org/payments-api",
        snyk_project_origin="github",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.update_work_item.return_value = {"work_item_id": "99", "work_item_status": "New"}

    batch_calls: list[tuple[str, str, list[str]]] = []

    def _batch(client, org, proj, wids):
        batch_calls.append((org, proj, list(wids)))
        return {
            "99": {
                "work_item_id": "99",
                "work_item_status": "New",
                "fields": {"System.AreaPath": "MyProject\\Payments"},
            },
        }

    monkeypatch.setattr(issues, "iter_org_issues", lambda *a, **k: iter([_open_issue()]))
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "my-org/payments-api", "origin": "github"},
    )
    monkeypatch.setattr("sync.run.batch_get_work_items", _batch)

    run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store)
    assert batch_calls == [("ado-o", "MyProject", ["99"])]


def test_run_sync_routing_migration_recreates_open_issue(
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
    wit.create_work_item.return_value = {"work_item_id": "100", "work_item_status": "New"}

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
                "fields": {"System.AreaPath": "ado-p\\Area"},
            },
        },
    )

    run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store)
    create_args = wit.create_work_item.call_args[0]
    assert create_args[0] == "ado-o"
    assert create_args[1] == "MyProject"
    wit.add_work_item_comment.assert_called()
    comment = wit.add_work_item_comment.call_args[0][3]
    assert "repo-mapping ADO target change" in comment
    assert "99" in comment


def test_run_sync_routing_migration_retargets_resolved_with_comment(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(_cfg_yaml(), encoding="utf-8")
    (tmp_path / "repo-mapping.csv").write_text(_MINIMAL_CSV, encoding="utf-8")
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    issue = _open_issue()
    issue["issue_attributes"] = {
        **issue["issue_attributes"],
        "status": "resolved",
        "ignored": False,
    }

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    store.upsert(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-1",
        snyk_status="resolved",
        organization="ado-o",
        project="ado-p",
        work_item_id="99",
        work_item_status="Done",
        snyk_project_name="my-org/payments-api",
        snyk_project_origin="github",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.get_work_item.return_value = {
        "work_item_id": "99",
        "work_item_status": "Done",
        "fields": {},
    }

    monkeypatch.setattr(issues, "iter_org_issues", lambda *a, **k: iter([issue]))
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "my-org/payments-api", "origin": "github"},
    )
    monkeypatch.setattr("sync.run.batch_get_work_items", lambda *a, **k: {"99": {}})

    run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store)
    wit.create_work_item.assert_not_called()
    wit.add_work_item_comment.assert_called_once()
    comment_args = wit.add_work_item_comment.call_args[0]
    assert comment_args[0] == "ado-o"
    assert comment_args[1] == "ado-p"
    assert "mapping target" in comment_args[3]
    row = store.get_by_natural_key(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-1",
    )
    assert row is not None
    assert row.organization == "ado-o"
    assert row.project == "MyProject"


def test_run_sync_routing_migration_resolved_skips_comment_on_404(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from integrations.azure_devops.errors import AzureDevOpsClientError

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(_cfg_yaml(), encoding="utf-8")
    (tmp_path / "repo-mapping.csv").write_text(_MINIMAL_CSV, encoding="utf-8")
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    issue = _open_issue()
    issue["issue_attributes"] = {
        **issue["issue_attributes"],
        "status": "resolved",
        "ignored": False,
    }

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    store.upsert(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-1",
        snyk_status="resolved",
        organization="ado-o",
        project="ado-p",
        work_item_id="99",
        work_item_status="Done",
        snyk_project_name="my-org/payments-api",
        snyk_project_origin="github",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]

    def _raise_404(*_a, **_k):
        raise AzureDevOpsClientError("missing", status_code=404)

    wit.get_work_item.side_effect = _raise_404

    monkeypatch.setattr(issues, "iter_org_issues", lambda *a, **k: iter([issue]))
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "my-org/payments-api", "origin": "github"},
    )
    monkeypatch.setattr("sync.run.batch_get_work_items", lambda *a, **k: {})

    run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store)
    wit.add_work_item_comment.assert_not_called()
    row = store.get_by_natural_key(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-1",
    )
    assert row is not None
    assert row.project == "MyProject"


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
    create_args = wit.create_work_item.call_args[0]
    assert create_args[0] == "ado-o"
    assert create_args[1] == "ado-p"
    patches = create_args[3]
    area_ops = [o for o in patches if o.get("path") == "/fields/System.AreaPath"]
    assert area_ops and area_ops[0]["value"] == "Default\\Area"
