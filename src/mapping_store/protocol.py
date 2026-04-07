"""Abstract mapping persistence (SQLite now; Azure Table later)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class MappingRow:
    """One persisted Snyk↔work-item mapping row including store timestamps."""

    group_id: str
    org_id: str
    project_id: str
    issue_id: str
    snyk_status: str
    organization: str
    project: str
    work_item_id: str
    work_item_status: str
    created_at: str
    updated_at: str


@runtime_checkable
class MappingStore(Protocol):
    """CRUD for issue↔work-item mappings (no sync orchestration)."""

    def get_by_natural_key(
        self,
        *,
        group_id: str,
        org_id: str,
        project_id: str,
        issue_id: str,
    ) -> MappingRow | None:
        """Return the row for the natural key, or ``None`` if missing."""
        ...

    def upsert(
        self,
        *,
        group_id: str,
        org_id: str,
        project_id: str,
        issue_id: str,
        snyk_status: str,
        organization: str,
        project: str,
        work_item_id: str,
        work_item_status: str,
    ) -> MappingRow:
        """Insert or update by natural key; set ``created_at`` / ``updated_at`` in UTC ISO 8601 Z."""
        ...

    def delete_by_natural_key(
        self,
        *,
        group_id: str,
        org_id: str,
        project_id: str,
        issue_id: str,
    ) -> bool:
        """Delete the row if present. Return ``True`` if a row was removed."""
        ...
