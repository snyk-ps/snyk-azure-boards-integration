#!/usr/bin/env python3
"""Idempotent SQLite schema init for Snyk↔work-item mappings (dev/test).

Resolves ``sqlite_path`` the same way as the application: defaults → YAML →
environment → CLI. Run from the repository root, for example::

    uv run python scripts/init_mapping_store.py --config data/sample-config.yaml

Secrets do not belong in the database path or file; use env / Key Vault for tokens.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo_src() -> Path:
    return Path(__file__).resolve().parent.parent / "src"


def _bootstrap_path() -> None:
    src = _repo_src()
    if src.is_dir():
        sys.path.insert(0, str(src))


def main(argv: list[str] | None = None) -> int:
    _bootstrap_path()

    from config import load_app_config
    from mapping_store.schema import apply_mapping_schema

    parser = argparse.ArgumentParser(
        description="Create local SQLite mapping DB and schema (idempotent).",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="YAML configuration path (overrides SNYK_APP_CONFIG when set).",
    )
    parser.add_argument(
        "--mapping-store-sqlite-path",
        dest="sqlite_path",
        metavar="PATH",
        default=None,
        help="Override sqlite_path (highest precedence for this setting).",
    )
    args = parser.parse_args(argv)

    cfg = load_app_config(
        config_path=args.config,
        cli_sqlite_path=args.sqlite_path,
    )
    if cfg.mapping_store != "sqlite":
        print(
            f"init-mapping-store: mapping_store is {cfg.mapping_store!r}; "
            "SQLite init applies only when mapping_store is 'sqlite'.",
            file=sys.stderr,
        )
        return 2

    import sqlite3

    db_path = Path(cfg.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        apply_mapping_schema(conn)
    finally:
        conn.close()
    print(f"SQLite mapping schema ready at {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
