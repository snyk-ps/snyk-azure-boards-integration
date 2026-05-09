"""SQLite implementation of ``MappingStore``."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from mapping_store.protocol import MappingRow
from mapping_store.schema import ISSUE_WORK_ITEM_MAP_TABLE, apply_mapping_schema


def _utc_now_iso_z() -> str:
    """Current UTC time as ISO 8601 with milliseconds and ``Z`` suffix."""
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _text_to_excluded(raw: object) -> bool:
    s = str(raw or "").strip().lower()
    return s in ("true", "1", "yes")


def _excluded_to_text(flag: bool) -> str:
    return "true" if flag else "false"


def _row_from_row_tuple(t: tuple[object, ...]) -> MappingRow:
    return MappingRow(
        group_id=str(t[0]),
        org_id=str(t[1]),
        project_id=str(t[2]),
        issue_id=str(t[3]),
        snyk_status=str(t[4]),
        organization=str(t[5]),
        project=str(t[6]),
        work_item_id=str(t[7]),
        work_item_status=str(t[8]),
        snyk_project_name=str(t[9] or ""),
        snyk_project_origin=str(t[10] or ""),
        excluded=_text_to_excluded(t[11]),
        exclusion_reason=str(t[12] or ""),
        created_at=str(t[13]),
        updated_at=str(t[14]),
    )


_SELECT_COLUMNS = (
    "group_id, org_id, project_id, issue_id, snyk_status, organization, "
    "project, work_item_id, work_item_status, snyk_project_name, "
    "snyk_project_origin, excluded, exclusion_reason, created_at, updated_at"
)


class SqliteMappingStore:
    """Persist mappings in a SQLite database file using ``sqlite3`` stdlib."""

    def __init__(self, database_path: str | os.PathLike[str]) -> None:
        self._path = Path(os.fspath(database_path))

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        apply_mapping_schema(conn)
        return conn

    def get_by_natural_key(
        self,
        *,
        group_id: str,
        org_id: str,
        project_id: str,
        issue_id: str,
    ) -> MappingRow | None:
        sql = f"""
            SELECT {_SELECT_COLUMNS}
            FROM {ISSUE_WORK_ITEM_MAP_TABLE}
            WHERE group_id = ? AND org_id = ? AND project_id = ? AND issue_id = ?
        """
        with self._connect() as conn:
            cur = conn.execute(sql, (group_id, org_id, project_id, issue_id))
            row = cur.fetchone()
        if row is None:
            return None
        return _row_from_row_tuple(row)

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
        snyk_project_name: str = "",
        snyk_project_origin: str = "",
        excluded: bool = False,
        exclusion_reason: str = "",
    ) -> MappingRow:
        now = _utc_now_iso_z()
        pn = str(snyk_project_name or "")
        po = str(snyk_project_origin or "")
        ex = bool(excluded)
        reason = str(exclusion_reason or "") if ex else ""
        ex_text = _excluded_to_text(ex)
        upsert_sql = f"""
            INSERT INTO {ISSUE_WORK_ITEM_MAP_TABLE} (
                group_id, org_id, project_id, issue_id, snyk_status, organization,
                project, work_item_id, work_item_status, snyk_project_name,
                snyk_project_origin, excluded, exclusion_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(group_id, org_id, project_id, issue_id) DO UPDATE SET
                snyk_status = excluded.snyk_status,
                organization = excluded.organization,
                project = excluded.project,
                work_item_id = excluded.work_item_id,
                work_item_status = excluded.work_item_status,
                snyk_project_name = excluded.snyk_project_name,
                snyk_project_origin = excluded.snyk_project_origin,
                excluded = excluded.excluded,
                exclusion_reason = excluded.exclusion_reason,
                updated_at = excluded.updated_at
        """
        params = (
            group_id,
            org_id,
            project_id,
            issue_id,
            snyk_status,
            organization,
            project,
            work_item_id,
            work_item_status,
            pn,
            po,
            ex_text,
            reason,
            now,
            now,
        )
        with self._connect() as conn:
            conn.execute(upsert_sql, params)
            conn.commit()
        out = self.get_by_natural_key(
            group_id=group_id,
            org_id=org_id,
            project_id=project_id,
            issue_id=issue_id,
        )
        assert out is not None
        return out

    def delete_by_natural_key(
        self,
        *,
        group_id: str,
        org_id: str,
        project_id: str,
        issue_id: str,
    ) -> bool:
        sql = f"""
            DELETE FROM {ISSUE_WORK_ITEM_MAP_TABLE}
            WHERE group_id = ? AND org_id = ? AND project_id = ? AND issue_id = ?
        """
        with self._connect() as conn:
            cur = conn.execute(sql, (group_id, org_id, project_id, issue_id))
            deleted = cur.rowcount
            conn.commit()
        return deleted > 0
