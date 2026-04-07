"""Tests for scripts/init_mapping_store.py exit codes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_init_script_exits_nonzero_when_not_sqlite_store(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "init_mapping_store.py"
    cfg = tmp_path / "c.yaml"
    cfg.write_text("mapping_store: azure_table\nsqlite_path: x.sqlite\n", encoding="utf-8")
    cmd = [sys.executable, str(script), "--config", str(cfg)]
    env = {**os.environ, "PYTHONPATH": str(repo / "src")}
    r = subprocess.run(cmd, cwd=str(repo), env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert "mapping_store" in (r.stderr + r.stdout).lower()
