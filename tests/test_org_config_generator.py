"""Unit tests for CSV → org_mappings config generator (mocked HTTP)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request

import pytest
import yaml

from org_config_generator.core import (
    CsvValidationError,
    GroupOrg,
    MappingInputRow,
    OrgResolutionError,
    SnykOrgApiError,
    fetch_group_orgs,
    parse_csv_rows,
    render_config_yaml,
    resolve_mappings,
    write_atomic,
)


class _FakeResp:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _page(orgs: list[dict], links: dict | None = None) -> bytes:
    doc: dict = {"data": orgs}
    if links is not None:
        doc["links"] = links
    return json.dumps(doc).encode("utf-8")


def _org_res(oid: str, name: str, slug: str) -> dict:
    return {
        "type": "org",
        "id": oid,
        "attributes": {"name": name, "slug": slug},
    }


def test_parse_csv_rows_valid(tmp_path: Path) -> None:
    p = tmp_path / "i.csv"
    p.write_text(
        "ado_organization,ado_project,snyk_org_name\n"
        'acme,ADO1,My Org\n'
        "acme,ADO2,Other\n",
        encoding="utf-8",
    )
    rows = parse_csv_rows(p)
    assert len(rows) == 2
    assert rows[0].snyk_org_name == "My Org"
    assert rows[0].source_row_index == 2


def test_parse_csv_rows_skips_blank_line(tmp_path: Path) -> None:
    p = tmp_path / "i.csv"
    p.write_text(
        "ado_organization,ado_project,snyk_org_name\n\n"
        "x,y,z\n",
        encoding="utf-8",
    )
    rows = parse_csv_rows(p)
    assert len(rows) == 1


def test_parse_csv_rows_rejects_missing_column(tmp_path: Path) -> None:
    p = tmp_path / "i.csv"
    p.write_text("ado_organization,ado_project\nx,y\n", encoding="utf-8")
    with pytest.raises(CsvValidationError, match="missing"):
        parse_csv_rows(p)


def test_parse_csv_rows_rejects_extra_column(tmp_path: Path) -> None:
    p = tmp_path / "i.csv"
    p.write_text(
        "ado_organization,ado_project,snyk_org_name,extra\nx,y,z,e\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvValidationError, match="unexpected"):
        parse_csv_rows(p)


def test_parse_csv_rows_rejects_empty_cell(tmp_path: Path) -> None:
    p = tmp_path / "i.csv"
    p.write_text(
        "ado_organization,ado_project,snyk_org_name\n"
        "x,,z\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvValidationError, match="row 2"):
        parse_csv_rows(p)


def test_fetch_group_orgs_paginates(tmp_path: Path) -> None:
    gid = "11111111-1111-1111-1111-111111111111"
    calls: list[str] = []

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        calls.append(req.full_url)
        if len(calls) == 1:
            assert f"/groups/{gid}/orgs" in req.full_url
            assert "limit=100" in req.full_url
            assert "version=2024-03-12" in req.full_url
            return _FakeResp(
                _page(
                    [_org_res("a", "N1", "s1")],
                    links={"next": f"rest/groups/{gid}/orgs?page=2"},
                )
            )
        return _FakeResp(_page([_org_res("b", "N2", "s2")]))

    orgs = fetch_group_orgs(
        "https://api.snyk.io/rest",
        gid,
        "2024-03-12",
        token="tok",
        opener=opener,
    )
    assert len(orgs) == 2
    assert {o.name for o in orgs} == {"N1", "N2"}


def test_fetch_group_orgs_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SNYK_TOKEN", raising=False)

    def opener(req: Request, timeout: float = 0) -> _FakeResp:  # pragma: no cover
        return _FakeResp(_page([]))

    with pytest.raises(SnykOrgApiError, match="SNYK_TOKEN"):
        fetch_group_orgs(
            "https://api.snyk.io/rest",
            "11111111-1111-1111-1111-111111111111",
            "2024-03-12",
            opener=opener,
        )


def test_resolve_mappings_success() -> None:
    rows = [
        MappingInputRow("o", "p", "Alpha", 2),
    ]
    orgs = [GroupOrg("uuid-a", "Alpha", "slug-a")]
    assert resolve_mappings(rows, orgs) == [
        {
            "organization": "o",
            "project": "p",
            "snyk_org_id": "uuid-a",
            "snyk_org_slug": "slug-a",
        }
    ]


def test_resolve_mappings_case_sensitive() -> None:
    rows = [MappingInputRow("o", "p", "alpha", 2)]
    orgs = [GroupOrg("uuid-a", "Alpha", "slug-a")]
    with pytest.raises(OrgResolutionError, match="no Snyk org"):
        resolve_mappings(rows, orgs)


def test_resolve_mappings_no_match() -> None:
    rows = [MappingInputRow("o", "p", "Missing", 3)]
    orgs = [GroupOrg("uuid-a", "Alpha", "slug-a")]
    with pytest.raises(OrgResolutionError, match="row 3"):
        resolve_mappings(rows, orgs)


def test_resolve_mappings_ambiguous() -> None:
    rows = [MappingInputRow("o", "p", "Dup", 2)]
    orgs = [
        GroupOrg("uuid-1", "Dup", "s1"),
        GroupOrg("uuid-2", "Dup", "s2"),
    ]
    with pytest.raises(OrgResolutionError, match="multiple"):
        resolve_mappings(rows, orgs)


def test_render_config_yaml_round_trip() -> None:
    text = render_config_yaml(
        "00000000-0000-0000-0000-000000000099",
        [
            {
                "organization": "ado",
                "project": "proj",
                "snyk_org_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "snyk_org_slug": "slug",
            }
        ],
    )
    data = yaml.safe_load(text)
    assert data["snyk"]["group_id"] == "00000000-0000-0000-0000-000000000099"
    assert data["azure_boards"]["org_mappings"][0]["snyk_org_slug"] == "slug"
    # ``defaults`` has only comments — PyYAML loads that as ``None``.
    assert data["azure_boards"]["defaults"] is None
    assert "  defaults:\n" in text
    assert "defaults: {}" not in text
    assert "    # organization:" in text
    assert "# mapping_store: azure_table" in text


def test_write_atomic_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "sub" / "out.yaml"
    write_atomic(out, "k: v\n")
    assert out.read_text(encoding="utf-8") == "k: v\n"


def test_script_csv_error_exits_2(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "generate_org_mapping_config.py"
    bad = tmp_path / "b.csv"
    bad.write_text("ado_organization\nx\n", encoding="utf-8")
    cmd = [
        sys.executable,
        str(script),
        "--input",
        str(bad),
        "--group-id",
        "11111111-1111-1111-1111-111111111111",
        "--output",
        str(tmp_path / "o.yaml"),
    ]
    env = {**os.environ, "PYTHONPATH": str(repo / "src")}
    env.pop("SNYK_TOKEN", None)
    r = subprocess.run(cmd, cwd=str(repo), env=env, capture_output=True, text=True)
    assert r.returncode == 2
