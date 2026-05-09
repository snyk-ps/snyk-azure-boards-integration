"""``run_sync`` origin allowlist skips Azure DevOps for excluded issues."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from config.loader import load_app_config
from integrations.azure_devops.client import WorkItemsClient
from mapping_store.sqlite_store import SqliteMappingStore
from snyk.client import IssuesClient
from sync.run import run_sync


@pytest.fixture
def env_pat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")


def test_run_sync_does_not_call_ado_when_origin_excluded(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(
        "azure_boards:\n"
        "  defaults:\n"
        "    organization: ado-o\n"
        "    project: ado-p\n"
        "    sync_included_snyk_origins: github\n"
        "  org_mappings:\n"
        "    - organization: ado-o\n"
        "      project: ado-p\n"
        "      snyk_org_id: org-uuid\n"
        "      snyk_org_slug: org-slug\n"
        "snyk:\n"
        "  group_id: \"\"\n",
        encoding="utf-8",
    )
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)

    rec = {
        "org_id": "org-uuid",
        "project_id": "proj-uuid",
        "issue_id": "ISS-1",
        "issue_attributes": {
            "status": "open",
            "ignored": False,
            "key": "ISS-1",
            "effective_severity_level": "high",
            "description": "d",
            "coordinates": [{"remedies": [{"type": "semver"}]}],
        },
    }

    monkeypatch.setattr(
        issues,
        "iter_org_issues",
        lambda *a, **k: iter([rec]),
    )
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "proj-name", "origin": "cli"},
    )
    monkeypatch.setattr(
        "sync.run.batch_get_work_items",
        lambda *a, **k: {},
    )

    rc = run_sync(
        config=cfg,
        issues_client=issues,
        wit_client=wit,
        store=store,
    )
    assert rc == 0
    wit.create_work_item.assert_not_called()
    wit.update_work_item.assert_not_called()

    row = store.get_by_natural_key(
        group_id="org-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-1",
    )
    assert row is not None
    assert row.excluded is True
    assert row.exclusion_reason == "origin_not_in_allowlist"
    assert row.snyk_project_origin == "cli"


def test_run_sync_creates_when_reincluded_row_has_empty_work_item_id(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Previously origin-excluded row with no Boards id must create when now included."""
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(
        "azure_boards:\n"
        "  defaults:\n"
        "    organization: ado-o\n"
        "    project: ado-p\n"
        "    sync_included_snyk_origins: github\n"
        "  org_mappings:\n"
        "    - organization: ado-o\n"
        "      project: ado-p\n"
        "      snyk_org_id: org-uuid\n"
        "      snyk_org_slug: org-slug\n"
        "snyk:\n"
        "  group_id: \"\"\n",
        encoding="utf-8",
    )
    cfg = load_app_config(config_path=str(cfg_path), cli_group_id=None)

    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    store.upsert(
        group_id="org-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-REINCL",
        snyk_status="open",
        organization="ado-o",
        project="ado-p",
        work_item_id="",
        work_item_status="",
        snyk_project_name="proj-name",
        snyk_project_origin="github",
        excluded=True,
        exclusion_reason="origin_not_in_allowlist",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.create_work_item.return_value = {
        "work_item_id": "701",
        "work_item_status": "New",
    }

    rec = {
        "org_id": "org-uuid",
        "project_id": "proj-uuid",
        "issue_id": "ISS-REINCL",
        "issue_attributes": {
            "status": "open",
            "ignored": False,
            "key": "ISS-REINCL",
            "effective_severity_level": "high",
            "description": "d",
            "coordinates": [{"remedies": [{"type": "semver"}]}],
        },
    }

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

    rc = run_sync(
        config=cfg,
        issues_client=issues,
        wit_client=wit,
        store=store,
    )
    assert rc == 0
    wit.create_work_item.assert_called_once()
    wit.update_work_item.assert_not_called()

    row = store.get_by_natural_key(
        group_id="org-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-REINCL",
    )
    assert row is not None
    assert row.work_item_id == "701"
    assert row.excluded is False
    assert row.exclusion_reason == ""
