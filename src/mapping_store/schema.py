"""DDL for the local SQLite mapping table (idempotent)."""

from __future__ import annotations

import sqlite3

ISSUE_WORK_ITEM_MAP_TABLE = "issue_work_item_map"

# Single source of truth for CREATE TABLE / indexes (script and runtime share this).
CREATE_ISSUE_WORK_ITEM_MAP_SQL = f"""
CREATE TABLE IF NOT EXISTS {ISSUE_WORK_ITEM_MAP_TABLE} (
    group_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    snyk_status TEXT,
    organization TEXT,
    project TEXT,
    work_item_id TEXT,
    work_item_status TEXT,
    snyk_project_name TEXT,
    snyk_project_origin TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (group_id, org_id, project_id, issue_id)
);
""".strip()

_ALTER_STATEMENTS: tuple[str, ...] = (
    f"ALTER TABLE {ISSUE_WORK_ITEM_MAP_TABLE} ADD COLUMN snyk_project_name TEXT",
    f"ALTER TABLE {ISSUE_WORK_ITEM_MAP_TABLE} ADD COLUMN snyk_project_origin TEXT",
)


def apply_mapping_schema(conn: sqlite3.Connection) -> None:
    """Apply idempotent DDL for the mapping table (UNIQUE implies an index in SQLite)."""
    conn.executescript(CREATE_ISSUE_WORK_ITEM_MAP_SQL)
    for stmt in _ALTER_STATEMENTS:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass
    conn.commit()
