"""Branch coverage for ``sync.run.run_sync`` org vs group listing."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from config.models import (
    AppConfig,
    AzureBoardsConfig,
    OrgMapping,
    SnykConfig,
)
from integrations.azure_devops.client import WorkItemsClient
from mapping_store.sqlite_store import SqliteMappingStore
from snyk.client import IssuesClient
from sync.run import run_sync


@pytest.fixture
def env_pat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "t")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")


def test_run_sync_uses_org_iterator_when_org_mappings(
    tmp_path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)

    iter_org = MagicMock(return_value=iter([]))
    iter_group = MagicMock(return_value=iter([]))
    monkeypatch.setattr(issues, "iter_org_issues", iter_org)
    monkeypatch.setattr(issues, "iter_group_issues", iter_group)
    monkeypatch.setattr(
        "sync.run.batch_get_work_items",
        lambda *a, **k: {},
    )

    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(
            organization="",
            project="",
            org_mappings=[
                OrgMapping(
                    organization="ado-o",
                    project="ado-p",
                    snyk_org_id="org-uuid",
                    snyk_org_slug="org-slug",
                ),
            ],
        ),
        work_item_template={},
        snyk=SnykConfig(group_id=""),
    )
    rc = run_sync(
        config=cfg,
        issues_client=issues,
        wit_client=wit,
        store=store,
    )
    assert rc == 0
    iter_org.assert_called_once()
    iter_group.assert_not_called()


def test_run_sync_uses_group_iterator_when_no_mappings(
    tmp_path,
    env_pat: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "m.sqlite"
    store = SqliteMappingStore(database_path=str(db))
    issues = IssuesClient(token="t")
    wit = MagicMock(spec=WorkItemsClient)

    iter_org = MagicMock(return_value=iter([]))
    iter_group = MagicMock(return_value=iter([]))
    monkeypatch.setattr(issues, "iter_org_issues", iter_org)
    monkeypatch.setattr(issues, "iter_group_issues", iter_group)
    monkeypatch.setattr(
        "sync.run.batch_get_work_items",
        lambda *a, **k: {},
    )

    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(
            organization="o",
            project="p",
        ),
        work_item_template={},
        snyk=SnykConfig(group_id="group-uuid"),
    )
    rc = run_sync(
        config=cfg,
        issues_client=issues,
        wit_client=wit,
        store=store,
    )
    assert rc == 0
    iter_group.assert_called_once()
    iter_org.assert_not_called()
