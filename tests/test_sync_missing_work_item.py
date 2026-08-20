"""``run_sync`` recreates or skips when mapped Azure work item ids are missing."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from config.loader import load_app_config
from integrations.azure_devops.client import WorkItemsClient
from mapping_store.sqlite_store import SqliteMappingStore
from snyk.client import IssuesClient
from sync.lifecycle import DERIVED_OPEN, DERIVED_RESOLVED
from sync.run import run_sync


@pytest.fixture
def env_pat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")


def _base_cfg_yaml() -> str:
    return (
        "azure_boards:\n"
        "  repo_mapping_csv: \"\"\n"
        "  defaults:\n"
        "    organization: ado-o\n"
        "    project: ado-p\n"
        "  org_mappings:\n"
        "    - organization: ado-o\n"
        "      project: ado-p\n"
        "      snyk_org_id: org-uuid\n"
        "      snyk_org_slug: org-slug\n"
        "snyk:\n"
        "  group_id: group-uuid\n"
    )


def _open_issue(*, issue_id: str, key: str) -> dict:
    return {
        "org_id": "org-uuid",
        "project_id": "proj-uuid",
        "issue_id": issue_id,
        "issue_attributes": {
            "status": "open",
            "ignored": False,
            "key": key,
            "effective_severity_level": "high",
            "description": "d",
            "coordinates": [{"remedies": [{"type": "semver"}]}],
        },
    }


def _resolved_issue(*, issue_id: str, key: str) -> dict:
    return {
        "org_id": "org-uuid",
        "project_id": "proj-uuid",
        "issue_id": issue_id,
        "issue_attributes": {
            "status": "resolved",
            "ignored": False,
            "key": key,
            "effective_severity_level": "high",
            "description": "d",
        },
    }


def test_run_sync_recreates_open_issue_when_mapped_work_item_missing(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(_base_cfg_yaml(), encoding="utf-8")
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    store.upsert(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-MISSING",
        snyk_status=DERIVED_OPEN,
        organization="ado-o",
        project="ado-p",
        work_item_id="100",
        work_item_status="New",
        snyk_project_name="proj-name",
        snyk_project_origin="github",
    )
    store.upsert(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-OK",
        snyk_status=DERIVED_OPEN,
        organization="ado-o",
        project="ado-p",
        work_item_id="200",
        work_item_status="New",
        snyk_project_name="proj-name",
        snyk_project_origin="github",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.create_work_item.return_value = {
        "work_item_id": "701",
        "work_item_status": "New",
    }

    rec_missing = _open_issue(issue_id="ISS-MISSING", key="ISS-MISSING")
    rec_ok = _open_issue(issue_id="ISS-OK", key="ISS-OK")

    monkeypatch.setattr(
        issues,
        "iter_org_issues",
        lambda *a, **k: iter([rec_missing, rec_ok]),
    )
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "proj-name", "origin": "github"},
    )
    monkeypatch.setattr(
        "sync.run.batch_get_work_items",
        lambda _c, _o, _p, wids: {
            "200": {"work_item_id": "200", "work_item_status": "New", "fields": {}},
        }
        if wids
        else {},
    )

    with caplog.at_level(logging.INFO, logger="integration_audit"):
        rc = run_sync(
            config=cfg,
            issues_client=issues,
            wit_client=wit,
            store=store,
            sync_run_id="sync-missing-wi",
        )
    assert rc == 0
    wit.create_work_item.assert_called_once()
    wit.update_work_item.assert_called_once()

    row = store.get_by_natural_key(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-MISSING",
    )
    assert row is not None
    assert row.work_item_id == "701"

    wit.add_work_item_comment.assert_called_once()
    comment_text = wit.add_work_item_comment.call_args[0][3]
    assert "100" in comment_text

    missing_logs = [
        r.record
        for r in caplog.records
        if r.name == "integration_audit"
        and getattr(r, "record", None)
        and r.record.get("event") == "missing_mapped_work_item"
    ]
    assert any(
        m["prior_work_item_id"] == "100"
        and m["action"] == "recreate"
        and m["issue_key"] == "ISS-MISSING"
        for m in missing_logs
    )


def test_run_sync_skips_close_path_when_mapped_work_item_missing(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(_base_cfg_yaml(), encoding="utf-8")
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    store.upsert(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-CLOSED",
        snyk_status=DERIVED_RESOLVED,
        organization="ado-o",
        project="ado-p",
        work_item_id="300",
        work_item_status="Closed",
        snyk_project_name="proj-name",
        snyk_project_origin="github",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]

    rec = _resolved_issue(issue_id="ISS-CLOSED", key="ISS-CLOSED")
    monkeypatch.setattr(
        issues,
        "iter_org_issues",
        lambda *a, **k: iter([rec]),
    )
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "proj-name", "origin": "github"},
    )
    monkeypatch.setattr(
        "sync.run.batch_get_work_items",
        lambda *a, **k: {},
    )

    with caplog.at_level(logging.INFO, logger="integration_audit"):
        rc = run_sync(
            config=cfg,
            issues_client=issues,
            wit_client=wit,
            store=store,
        )
    assert rc == 0
    wit.create_work_item.assert_not_called()
    wit.update_work_item.assert_not_called()

    missing_logs = [
        r.record
        for r in caplog.records
        if getattr(r, "record", None)
        and r.record.get("event") == "missing_mapped_work_item"
    ]
    assert len(missing_logs) == 1
    assert missing_logs[0]["action"] == "skip"
    assert missing_logs[0]["prior_work_item_id"] == "300"


def test_run_sync_skips_recreate_when_create_new_work_items_false(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(
        _base_cfg_yaml().replace(
            "  defaults:\n",
            "  defaults:\n    create_new_work_items: false\n",
        ),
        encoding="utf-8",
    )
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    store.upsert(
        group_id="group-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-NOCREATE",
        snyk_status=DERIVED_OPEN,
        organization="ado-o",
        project="ado-p",
        work_item_id="400",
        work_item_status="New",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    rec = _open_issue(issue_id="ISS-NOCREATE", key="ISS-NOCREATE")

    monkeypatch.setattr(
        issues,
        "iter_org_issues",
        lambda *a, **k: iter([rec]),
    )
    monkeypatch.setattr(
        "sync.run.batch_get_work_items",
        lambda *a, **k: {},
    )

    with caplog.at_level(logging.INFO, logger="integration_audit"):
        rc = run_sync(
            config=cfg,
            issues_client=issues,
            wit_client=wit,
            store=store,
        )
    assert rc == 0
    wit.create_work_item.assert_not_called()
    missing_logs = [
        r.record
        for r in caplog.records
        if getattr(r, "record", None)
        and r.record.get("event") == "missing_mapped_work_item"
    ]
    assert len(missing_logs) == 1
    assert missing_logs[0]["action"] == "skip"
