"""Tests for ``azure-devops-smoke`` argparse wiring."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from commands import build_parser
from commands.azure_devops_smoke import run_azure_devops_smoke


def test_smoke_parser_requires_work_item_id() -> None:
    p = build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["azure-devops-smoke", "--config", "x.yaml"])


def test_smoke_parser_accepts_work_item_id() -> None:
    p = build_parser()
    args = p.parse_args(
        ["azure-devops-smoke", "--config", "c.yaml", "--work-item-id", "42"],
    )
    assert args.command == "azure-devops-smoke"
    assert args.work_item_id == "42"


def test_run_smoke_missing_org_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "pat")
    cfg = tmp_path / "c.yaml"
    cfg.write_text("azure_boards:\n  create_new_work_items: true\n", encoding="utf-8")
    p = build_parser()
    args = p.parse_args(
        ["azure-devops-smoke", "--config", str(cfg), "--work-item-id", "1"],
    )
    code = run_azure_devops_smoke(args)
    assert code == 2


def test_run_smoke_missing_pat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AZURE_DEVOPS_PAT", raising=False)
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "azure_boards:\n  organization: org\n  project: proj\n",
        encoding="utf-8",
    )
    p = build_parser()
    args = p.parse_args(
        ["azure-devops-smoke", "--config", str(cfg), "--work-item-id", "1"],
    )
    code = run_azure_devops_smoke(args)
    assert code == 1


def test_run_smoke_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "pat")
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "azure_boards:\n  organization: org\n  project: proj\n",
        encoding="utf-8",
    )

    class _FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str]] = []

        def get_work_item(self, organization: str, project: str, work_item_id: str | int) -> dict[str, Any]:
            self.calls.append((organization, project, str(work_item_id)))
            return {"work_item_id": 1, "work_item_status": "Active", "fields": {}, "rev": 1}

    fake = _FakeClient()

    import commands.azure_devops_smoke as ads

    monkeypatch.setattr(ads, "WorkItemsClient", lambda: fake)

    p = build_parser()
    args = p.parse_args(
        ["azure-devops-smoke", "--config", str(cfg), "--work-item-id", "99"],
    )
    code = run_azure_devops_smoke(args)
    assert code == 0
    assert fake.calls == [("org", "proj", "99")]
