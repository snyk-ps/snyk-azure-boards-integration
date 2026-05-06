"""Resolved application configuration (YAML + defaults + env + CLI layers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ISSUES_SYNC_FROM_HISTORICAL = "historical"
REOPEN_POLICY_NEW_WORK_ITEM = "new_work_item"
REOPEN_POLICY_REOPEN_EXISTING = "reopen_existing"


@dataclass
class AzureBoardsDefaults:
    """Default policy under ``azure_boards.defaults`` (YAML)."""

    organization: str = ""
    project: str = ""
    create_new_work_items: bool = True
    severity_threshold: str = "high"
    issues_sync_from: str = ISSUES_SYNC_FROM_HISTORICAL
    create_only_when_fix_available: bool = False
    reopen_work_item_policy: str = REOPEN_POLICY_NEW_WORK_ITEM
    work_item_type: str = "Task"
    work_item_state_active: str = "New"
    work_item_state_closed: str = "Closed"
    work_item_description_appendix: str = ""
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
    """Azure Boards-related settings (merged ``defaults`` for single-target or per-row)."""

    create_new_work_items: bool = True
    organization: str = ""
    project: str = ""
    severity_threshold: str = "high"
    issues_sync_from: str = ISSUES_SYNC_FROM_HISTORICAL
    create_only_when_fix_available: bool = False
    reopen_work_item_policy: str = REOPEN_POLICY_NEW_WORK_ITEM
    work_item_type: str = "Task"
    work_item_state_active: str = "New"
    work_item_state_closed: str = "Closed"
    defaults: AzureBoardsDefaults = field(default_factory=AzureBoardsDefaults)
    org_mappings: list[OrgMapping] = field(default_factory=list)


@dataclass
class SnykConfig:
    """Snyk integration settings (non-secret)."""

    group_id: str = ""
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
