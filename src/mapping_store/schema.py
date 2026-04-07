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
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (group_id, org_id, project_id, issue_id)
);
""".strip()


def apply_mapping_schema(conn: sqlite3.Connection) -> None:
    """Apply idempotent DDL for the mapping table (UNIQUE implies an index in SQLite)."""
    conn.executescript(CREATE_ISSUE_WORK_ITEM_MAP_SQL)
    conn.commit()
