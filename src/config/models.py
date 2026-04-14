"""Resolved application configuration (YAML + defaults + env + CLI layers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AzureBoardsConfig:
    """Azure Boards-related settings."""

    create_new_work_items: bool = True
    organization: str = ""
    project: str = ""


@dataclass
class SnykConfig:
    """Snyk integration settings (non-secret)."""

    group_id: str = ""
    severity_threshold: str = "high"
    extra: dict[str, Any] = field(default_factory=dict)


# Default mapping persistence: local SQLite for dev/tests (see openspec design).
DEFAULT_MAPPING_STORE: str = "sqlite"
DEFAULT_SQLITE_PATH: str = "data/mapping_store.sqlite"


@dataclass
class AppConfig:
    """Full application configuration after merge."""

    azure_boards: AzureBoardsConfig
    work_item_template: dict[str, Any]
    snyk: SnykConfig
    mapping_store: str = DEFAULT_MAPPING_STORE
    sqlite_path: str = DEFAULT_SQLITE_PATH
