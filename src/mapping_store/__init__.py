"""Snyk↔work-item mapping persistence (SQLite dev/test; Azure Table later)."""

from mapping_store.errors import (
    AzureTableMappingStoreUnavailableError,
    MappingDuplicateKeyError,
    MappingStoreError,
)
from mapping_store.factory import create_mapping_store
from mapping_store.protocol import MappingRow, MappingStore
from mapping_store.schema import ISSUE_WORK_ITEM_MAP_TABLE, apply_mapping_schema
from mapping_store.sqlite_store import SqliteMappingStore

__all__ = [
    "AzureTableMappingStoreUnavailableError",
    "ISSUE_WORK_ITEM_MAP_TABLE",
    "MappingDuplicateKeyError",
    "MappingRow",
    "MappingStore",
    "MappingStoreError",
    "SqliteMappingStore",
    "apply_mapping_schema",
    "create_mapping_store",
]
