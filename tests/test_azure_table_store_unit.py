"""Unit tests for ``AzureTableMappingStore`` with a mocked Table client."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import ResourceNotFoundError

from mapping_store.azure_table_store import AzureTableMappingStore


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def store_with_mock(mock_client: MagicMock) -> AzureTableMappingStore:
    st = object.__new__(AzureTableMappingStore)
    st._client = mock_client
    return st


def test_get_by_natural_key_miss(store_with_mock: AzureTableMappingStore, mock_client: MagicMock) -> None:
    mock_client.get_entity.side_effect = ResourceNotFoundError()
    assert (
        store_with_mock.get_by_natural_key(
            group_id="g",
            org_id="o",
            project_id="p",
            issue_id="i",
        )
        is None
    )


def test_get_by_natural_key_hit(store_with_mock: AzureTableMappingStore, mock_client: MagicMock) -> None:
    mock_client.get_entity.return_value = {
        "PartitionKey": "g",
        "RowKey": "o|p|i",
        "group_id": "g",
        "org_id": "o",
        "project_id": "p",
        "issue_id": "i",
        "snyk_status": "open",
        "organization": "ado",
        "project": "proj",
        "work_item_id": "99",
        "work_item_status": "New",
        "snyk_project_name": "",
        "snyk_project_origin": "",
        "excluded": "false",
        "exclusion_reason": "",
        "created_at": "2026-01-01T00:00:00.000Z",
        "updated_at": "2026-01-02T00:00:00.000Z",
    }
    row = store_with_mock.get_by_natural_key(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
    )
    assert row is not None
    assert row.work_item_id == "99"


def test_upsert_insert_then_update_preserves_created_at(
    store_with_mock: AzureTableMappingStore,
    mock_client: MagicMock,
) -> None:
    entities: dict[tuple[str, str], dict[str, object]] = {}

    def get_side_effect(pk: str, rk: str) -> dict[str, object]:
        key = (pk, rk)
        if key not in entities:
            raise ResourceNotFoundError()
        return dict(entities[key])

    def upsert_side_effect(*, entity: dict[str, object], mode: object = None) -> None:
        pk = str(entity["PartitionKey"])
        rk = str(entity["RowKey"])
        entities[(pk, rk)] = dict(entity)

    mock_client.get_entity.side_effect = get_side_effect
    mock_client.upsert_entity.side_effect = upsert_side_effect

    first = store_with_mock.upsert(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
        snyk_status="open",
        organization="ado",
        project="proj",
        work_item_id="1",
        work_item_status="New",
    )
    assert first.created_at == first.updated_at
    created_snapshot = first.created_at

    second = store_with_mock.upsert(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
        snyk_status="resolved",
        organization="ado",
        project="proj",
        work_item_id="1",
        work_item_status="Closed",
    )
    assert second.created_at == created_snapshot
    assert second.snyk_status == "resolved"


def test_delete_by_natural_key(store_with_mock: AzureTableMappingStore, mock_client: MagicMock) -> None:
    mock_client.delete_entity.return_value = None
    assert store_with_mock.delete_by_natural_key(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
    )
    mock_client.delete_entity.assert_called_once()


def test_delete_by_natural_key_missing(store_with_mock: AzureTableMappingStore, mock_client: MagicMock) -> None:
    mock_client.delete_entity.side_effect = ResourceNotFoundError()
    assert not store_with_mock.delete_by_natural_key(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
    )
