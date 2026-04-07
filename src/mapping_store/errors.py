"""Errors for mapping persistence."""


class MappingStoreError(Exception):
    """Base class for mapping store failures."""


class MappingDuplicateKeyError(MappingStoreError):
    """Raised when inserting a row that violates the natural-key uniqueness."""


class AzureTableMappingStoreUnavailableError(MappingStoreError):
    """Raised when ``mapping_store`` is ``azure_table`` but no adapter is available."""
