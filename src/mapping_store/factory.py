"""Construct a ``MappingStore`` from resolved application configuration."""

from __future__ import annotations

from config.models import AppConfig

from mapping_store.azure_table_store import AzureTableMappingStore
from mapping_store.errors import AzureTableMappingStoreUnavailableError
from mapping_store.protocol import MappingStore
from mapping_store.sqlite_store import SqliteMappingStore


def create_mapping_store(config: AppConfig) -> MappingStore:
    """
    Return the mapping persistence implementation for ``config``.

    When ``mapping_store`` is ``azure_table``, builds :class:`AzureTableMappingStore`
    using ``config.mapping_store_azure_table_endpoint`` and
    ``config.mapping_store_azure_table_name``. Raises
    ``AzureTableMappingStoreUnavailableError`` if the Table client cannot be
    initialized (callers should exit non-zero). There is no fallback to SQLite.
    """
    if config.mapping_store == "azure_table":
        return AzureTableMappingStore(
            endpoint=config.mapping_store_azure_table_endpoint,
            table_name=config.mapping_store_azure_table_name,
        )
    if config.mapping_store != "sqlite":
        raise AzureTableMappingStoreUnavailableError(
            f"mapping_store {config.mapping_store!r} is not supported.",
        )
    return SqliteMappingStore(config.sqlite_path)
