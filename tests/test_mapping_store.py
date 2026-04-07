"""Tests for mapping schema, SQLite store, and factory."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from config.models import AppConfig, AzureBoardsConfig, DEFAULT_SQLITE_PATH, SnykConfig
from mapping_store import (
    AzureTableMappingStoreUnavailableError,
    SqliteMappingStore,
    apply_mapping_schema,
    create_mapping_store,
)
from mapping_store.schema import CREATE_ISSUE_WORK_ITEM_MAP_SQL, ISSUE_WORK_ITEM_MAP_TABLE


def test_apply_mapping_schema_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    conn = sqlite3.connect(str(db))
    try:
        apply_mapping_schema(conn)
        apply_mapping_schema(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (ISSUE_WORK_ITEM_MAP_TABLE,),
        )
        assert cur.fetchone() is not None
    finally:
        conn.close()


def test_sqlite_upsert_round_trip_and_preserves_created_at(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    store = SqliteMappingStore(db)
    first = store.upsert(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
        snyk_status="open",
        organization="ado-org",
        project="ado-proj",
        work_item_id="42",
        work_item_status="Active",
    )
    assert first.created_at == first.updated_at
    created = first.created_at
    second = store.upsert(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
        snyk_status="closed",
        organization="ado-org",
        project="ado-proj",
        work_item_id="42",
        work_item_status="Closed",
    )
    assert second.created_at == created
    assert second.snyk_status == "closed"
    assert second.updated_at >= second.created_at


def test_sqlite_get_and_delete(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    store = SqliteMappingStore(db)
    assert (
        store.get_by_natural_key(
            group_id="g",
            org_id="o",
            project_id="p",
            issue_id="i",
        )
        is None
    )
    store.upsert(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
        snyk_status="open",
        organization="a",
        project="b",
        work_item_id="1",
        work_item_status="New",
    )
    row = store.get_by_natural_key(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
    )
    assert row is not None
    assert row.work_item_id == "1"
    assert store.delete_by_natural_key(
        group_id="g",
        org_id="o",
        project_id="p",
        issue_id="i",
    )
    assert (
        store.get_by_natural_key(
            group_id="g",
            org_id="o",
            project_id="p",
            issue_id="i",
        )
        is None
    )


def test_plain_insert_duplicate_natural_key_raises(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    conn = sqlite3.connect(str(db))
    try:
        apply_mapping_schema(conn)
        conn.execute(
            f"INSERT INTO {ISSUE_WORK_ITEM_MAP_TABLE} "
            "(group_id, org_id, project_id, issue_id, snyk_status, organization, "
            "project, work_item_id, work_item_status, created_at, updated_at) "
            "VALUES ('g','o','p','i','open','a','b','1','New','t1','t1')",
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO {ISSUE_WORK_ITEM_MAP_TABLE} "
                "(group_id, org_id, project_id, issue_id, snyk_status, organization, "
                "project, work_item_id, work_item_status, created_at, updated_at) "
                "VALUES ('g','o','p','i','open','a','b','2','New','t2','t2')",
            )
            conn.commit()
    finally:
        conn.close()


def test_create_mapping_store_sqlite(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(),
        work_item_template={},
        snyk=SnykConfig(),
        mapping_store="sqlite",
        sqlite_path=str(db),
    )
    store = create_mapping_store(cfg)
    assert isinstance(store, SqliteMappingStore)


def test_create_mapping_store_azure_table_raises() -> None:
    cfg = AppConfig(
        azure_boards=AzureBoardsConfig(),
        work_item_template={},
        snyk=SnykConfig(),
        mapping_store="azure_table",
        sqlite_path=DEFAULT_SQLITE_PATH,
    )
    with pytest.raises(AzureTableMappingStoreUnavailableError, match="mapping_store"):
        create_mapping_store(cfg)


def test_init_script_runs_twice_zero_exit(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "init_mapping_store.py"
    db = tmp_path / "init.db"
    cmd = [
        sys.executable,
        str(script),
        "--mapping-store-sqlite-path",
        str(db),
    ]
    env = {**os.environ, "PYTHONPATH": str(repo / "src")}
    r1 = subprocess.run(cmd, cwd=str(repo), env=env, capture_output=True, text=True)
    r2 = subprocess.run(cmd, cwd=str(repo), env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr + r1.stdout
    assert r2.returncode == 0, r2.stderr + r2.stdout
    conn = sqlite3.connect(str(db))
    try:
        cur = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (ISSUE_WORK_ITEM_MAP_TABLE,),
        )
        row = cur.fetchone()
        assert row is not None
        assert "UNIQUE" in (row[0] or "").upper()
    finally:
        conn.close()


def test_ddl_source_contains_expected_columns() -> None:
    sql = CREATE_ISSUE_WORK_ITEM_MAP_SQL.upper()
    for col in (
        "GROUP_ID",
        "ORG_ID",
        "PROJECT_ID",
        "ISSUE_ID",
        "SNYK_STATUS",
        "WORK_ITEM_STATUS",
        "CREATED_AT",
        "UPDATED_AT",
    ):
        assert col in sql
