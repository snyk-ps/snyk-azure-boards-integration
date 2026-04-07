"""Construct a ``MappingStore`` from resolved application configuration."""

from __future__ import annotations

from config.models import AppConfig

from mapping_store.errors import AzureTableMappingStoreUnavailableError
from mapping_store.protocol import MappingStore
from mapping_store.sqlite_store import SqliteMappingStore


def create_mapping_store(config: AppConfig) -> MappingStore:
    """
    Return the mapping persistence implementation for ``config``.

    ``azure_table`` is reserved: there is no adapter in this codebase yet, so this
    raises ``AzureTableMappingStoreUnavailableError`` (callers should exit non-zero).
    """
    if config.mapping_store == "azure_table":
        raise AzureTableMappingStoreUnavailableError(
            "mapping_store is 'azure_table' but the Azure Table Storage adapter is "
            "not available in this version. Use mapping_store 'sqlite' for local "
            "development and tests, or deploy a build that includes the Azure adapter "
            "when it exists.",
        )
    if config.mapping_store != "sqlite":
        raise AzureTableMappingStoreUnavailableError(
            f"mapping_store {config.mapping_store!r} is not supported.",
        )
    return SqliteMappingStore(config.sqlite_path)
