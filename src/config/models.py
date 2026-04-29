"""Resolved application configuration (YAML + defaults + env + CLI layers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AzureBoardsDefaults:
    """Default work item policy under ``azure_boards.defaults`` (YAML)."""

    work_item_type: str = "Task"
    work_item_state_active: str = "New"
    work_item_state_closed: str = "Closed"
    work_item_template: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrgMapping:
    """One ADO project ↔ Snyk org pairing."""

    organization: str = ""
    project: str = ""
    snyk_org_id: str = ""
    snyk_org_slug: str = ""
    overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class AzureBoardsConfig:
    """Azure Boards-related settings."""

    create_new_work_items: bool = True
    organization: str = ""
    project: str = ""
    work_item_type: str = "Task"
    work_item_state_active: str = "New"
    work_item_state_closed: str = "Closed"
    defaults: AzureBoardsDefaults = field(default_factory=AzureBoardsDefaults)
    org_mappings: list[OrgMapping] = field(default_factory=list)


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
