"""``run_sync`` create gate evaluates fix signals across all coordinates."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from config.loader import load_app_config
from integrations.azure_devops.client import WorkItemsClient
from mapping_store.sqlite_store import SqliteMappingStore
from snyk.client import IssuesClient
from sync.run import run_sync

CONFIG_YAML = (
    "azure_boards:\n"
    '  repo_mapping_csv: ""\n'
    "  defaults:\n"
    "    organization: ado-o\n"
    "    project: ado-p\n"
    "    create_only_when_fix_available: true\n"
    "  org_mappings:\n"
    "    - organization: ado-o\n"
    "      project: ado-p\n"
    "      snyk_org_id: org-uuid\n"
    "      snyk_org_slug: org-slug\n"
    "snyk:\n"
    '  group_id: ""\n'
)

# Remedies on the leading coordinate keep the record complete so enrichment does
# not issue a GET; the fix signal deliberately sits on a later coordinate.
SIGNAL_ON_LATER_COORDINATE = [
    {"remedies": [{"type": "semver"}], "is_upgradeable": False},
    {"is_upgradeable": True},
]

NO_SIGNAL_ON_ANY_COORDINATE = [
    {"remedies": [{"type": "semver"}], "is_upgradeable": False},
    {"is_upgradeable": False, "is_pinnable": True},
]


@pytest.fixture
def env_pat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")


def _issue_record(issue_id: str, coordinates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "org_id": "org-uuid",
        "project_id": "proj-uuid",
        "issue_id": issue_id,
        "issue_attributes": {
            "status": "open",
            "ignored": False,
            "key": issue_id,
            "effective_severity_level": "high",
            "description": "d",
            "coordinates": coordinates,
        },
    }


def _wire(
    monkeypatch: pytest.MonkeyPatch,
    issues: IssuesClient,
    record: dict[str, Any],
    *,
    prefetch: dict[str, Any] | None = None,
) -> None:
    monkeypatch.setattr(issues, "iter_org_issues", lambda *a, **k: iter([record]))
    monkeypatch.setattr(
        issues,
        "get_org_project",
        lambda org, pid: {"name": "proj-name", "origin": "github"},
    )
    monkeypatch.setattr("sync.run.batch_get_work_items", lambda *a, **k: prefetch or {})


def _config(tmp_path: Path) -> Any:
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(CONFIG_YAML, encoding="utf-8")
    return load_app_config(config_path=str(cfg_path), cli_group_id=None)


def _row(store: SqliteMappingStore, issue_id: str) -> Any:
    return store.get_by_natural_key(
        group_id="org-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id=issue_id,
    )


def test_creates_when_fix_signal_is_on_a_later_coordinate(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _config(tmp_path)
    store = SqliteMappingStore(database_path=str(tmp_path / "m.sqlite"))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.create_work_item.return_value = {"work_item_id": "801", "work_item_status": "New"}

    _wire(monkeypatch, issues, _issue_record("ISS-LATER", SIGNAL_ON_LATER_COORDINATE))

    assert run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store) == 0
    wit.create_work_item.assert_called_once()

    row = _row(store, "ISS-LATER")
    assert row is not None
    assert row.work_item_id == "801"
    assert row.work_item_status == "New"


def test_skipped_issue_writes_no_mapping_row(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _config(tmp_path)
    store = SqliteMappingStore(database_path=str(tmp_path / "m.sqlite"))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]

    _wire(monkeypatch, issues, _issue_record("ISS-NONE", NO_SIGNAL_ON_ANY_COORDINATE))

    assert run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store) == 0
    wit.create_work_item.assert_not_called()
    assert _row(store, "ISS-NONE") is None


def test_previously_skipped_issue_is_created_on_a_later_run(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No backfill needed: the skip persists nothing, so a later run picks it up."""
    cfg = _config(tmp_path)
    store = SqliteMappingStore(database_path=str(tmp_path / "m.sqlite"))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]

    _wire(monkeypatch, issues, _issue_record("ISS-LATER-RUN", NO_SIGNAL_ON_ANY_COORDINATE))
    assert run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store) == 0
    wit.create_work_item.assert_not_called()
    assert _row(store, "ISS-LATER-RUN") is None

    wit.create_work_item.return_value = {"work_item_id": "802", "work_item_status": "New"}
    _wire(monkeypatch, issues, _issue_record("ISS-LATER-RUN", SIGNAL_ON_LATER_COORDINATE))
    assert run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store) == 0
    wit.create_work_item.assert_called_once()

    row = _row(store, "ISS-LATER-RUN")
    assert row is not None
    assert row.work_item_id == "802"


def test_recreate_path_uses_all_coordinates(
    tmp_path: Path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mapped work item that vanished is recreated on a later-coordinate signal."""
    cfg = _config(tmp_path)
    store = SqliteMappingStore(database_path=str(tmp_path / "m.sqlite"))
    store.upsert(
        group_id="org-uuid",
        org_id="org-uuid",
        project_id="proj-uuid",
        issue_id="ISS-RECREATE",
        snyk_status="open",
        organization="ado-o",
        project="ado-p",
        work_item_id="555",
        work_item_status="New",
        snyk_project_name="proj-name",
        snyk_project_origin="github",
        excluded=False,
        exclusion_reason="",
    )

    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)
    wit.list_work_item_type_field_names.return_value = ["System.Description"]
    wit.create_work_item.return_value = {"work_item_id": "803", "work_item_status": "New"}

    # Empty prefetch means the mapped id 555 is gone from Azure DevOps.
    _wire(monkeypatch, issues, _issue_record("ISS-RECREATE", SIGNAL_ON_LATER_COORDINATE))

    assert run_sync(config=cfg, issues_client=issues, wit_client=wit, store=store) == 0
    wit.create_work_item.assert_called_once()

    row = _row(store, "ISS-RECREATE")
    assert row is not None
    assert row.work_item_id == "803"
