"""Resolved application configuration (YAML + defaults + env + CLI layers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from snyk.constants import DEFAULT_API_ORIGIN, DEFAULT_APP_ORIGIN


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
    work_item_description_field: str | None = None
    work_item_description_appendix: str = ""
    work_item_template: dict[str, Any] = field(default_factory=dict)
    #: Inclusive allowlist of Snyk ``attributes.origin`` values; ``None`` = no filter.
    sync_included_snyk_origins: tuple[str, ...] | None = None
    #: Default Azure DevOps area path when no ``repo-mapping.csv`` row matches.
    area_path: str | None = None


@dataclass
class OrgMapping:
    """One ADO project ↔ Snyk org pairing."""

    organization: str = ""
    project: str = ""
    snyk_org_id: str = ""
    snyk_org_slug: str = ""
    overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdoTargetProfile:
    """Work-item taxonomy profile for one Azure DevOps ``(organization, project)``."""

    organization: str
    project: str
    work_item_type: str | None = None
    work_item_state_active: str | None = None
    work_item_state_closed: str | None = None
    work_item_description_field: str | None = None
    work_item_template: dict[str, Any] = field(default_factory=dict)


class AdoTargetIndex:
    """Lookup ``ado_targets`` profiles by ``(organization, project)``."""

    def __init__(self, profiles: dict[tuple[str, str], AdoTargetProfile]) -> None:
        self._profiles = dict(profiles)

    @classmethod
    def empty(cls) -> AdoTargetIndex:
        """Return an index with no profiles."""
        return cls({})

    @classmethod
    def from_profiles(cls, profiles: list[AdoTargetProfile]) -> AdoTargetIndex:
        """Build an index from parsed ``ado_targets`` list entries."""
        out: dict[tuple[str, str], AdoTargetProfile] = {}
        for profile in profiles:
            key = (profile.organization.strip(), profile.project.strip())
            out[key] = profile
        return cls(out)

    def lookup(self, organization: str, project: str) -> AdoTargetProfile | None:
        """Return the profile for ``(organization, project)`` when configured."""
        key = (str(organization or "").strip(), str(project or "").strip())
        return self._profiles.get(key)


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
    sync_included_snyk_origins: tuple[str, ...] | None = None
    #: Path to ``repo-mapping.csv`` (relative to config dir or absolute); see loader.
    repo_mapping_csv: str | None = None
    ado_targets: list[AdoTargetProfile] = field(default_factory=list)
    ado_target_index: AdoTargetIndex = field(default_factory=AdoTargetIndex.empty)


@dataclass
class SnykConfig:
    """Snyk integration settings (non-secret)."""

    group_id: str = ""
    api_base_url: str = DEFAULT_API_ORIGIN
    app_base_url: str = DEFAULT_APP_ORIGIN
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
    #: HTTPS Table service endpoint when ``mapping_store`` is ``azure_table`` (non-secret).
    mapping_store_azure_table_endpoint: str = ""
    #: Table name when ``mapping_store`` is ``azure_table`` (non-secret).
    mapping_store_azure_table_name: str = ""
    #: Directory containing the loaded YAML config file, when loaded from disk.
    config_file_dir: str | None = None
