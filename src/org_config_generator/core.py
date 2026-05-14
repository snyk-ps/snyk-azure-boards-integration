"""CSV-driven starter config: resolve Snyk org id/slug via group org list API.

Matching rule (``snyk_org_name`` → Snyk org): compare the CSV value after stripping
ASCII leading/trailing whitespace to the JSON:API org resource **display name**
(``attributes.name``) using a **case-sensitive** string equality. The CSV value is
not normalized for internal spaces.

Authentication uses ``SNYK_TOKEN`` from the process environment only (``token``
scheme in the ``Authorization`` header, same as the Issues client).

The org list uses Snyk REST **version** ``2024-03-12`` by default (see
https://apidocs.snyk.io/?version=2024-03-12#get-/groups/-group_id-/orgs).
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml

from snyk.urls import normalize_base_url, resolve_next_url

_Opener = Callable[..., Any]

REQUIRED_COLUMNS: tuple[str, str, str] = (
    "ado_organization",
    "ado_project",
    "snyk_org_name",
)

DEFAULT_ORG_LIST_VERSION = "2024-03-12"
DEFAULT_BASE_URL = "https://api.snyk.io/rest"
ORG_LIST_LIMIT = 100


class OrgConfigGeneratorError(Exception):
    """Base error for org config generation."""


class CsvValidationError(OrgConfigGeneratorError):
    """Invalid CSV headers or row values."""


class OrgResolutionError(OrgConfigGeneratorError):
    """No unique Snyk org for a CSV row."""


class SnykOrgApiError(OrgConfigGeneratorError):
    """Snyk org list HTTP or JSON failure."""


@dataclass(frozen=True)
class MappingInputRow:
    """One row from operator CSV (1-based ``source_row_index`` is file line)."""

    ado_organization: str
    ado_project: str
    snyk_org_name: str
    source_row_index: int


@dataclass(frozen=True)
class GroupOrg:
    """Org resource from ``GET /groups/{group_id}/orgs``."""

    id: str
    name: str
    slug: str


DEFAULTS_COMMENT_BLOCK = """
    # organization: "your-azure-devops-org"
    # project: "your-azure-devops-project"
    # create_new_work_items: true
    # severity_threshold: high
    # issues_sync_from: historical
    # create_only_when_fix_available: false
    # reopen_work_item_policy: new_work_item
    # work_item_type: Task
    # work_item_state_active: New
    # work_item_state_closed: Closed
    # sync_included_snyk_origins: "github,azure-repos,gitlab"
    # work_item_description_appendix: |
    #   Internal: request Snyk access at https://example.internal/access
    # work_item_template:
    #   tags:
    #     - Snyk
    #   json_patch: []
""".strip(
    "\n"
)


MAPPING_STORE_COMMENT_BLOCK = """
# Production-style persistence (uncomment and set values when using Azure Table):
# mapping_store: azure_table
# mapping_store_azure_table_endpoint: "https://<account>.table.core.windows.net/"
# mapping_store_azure_table_name: issuesSyncMappingTable
#
# Local dev / tests (non-secret paths only):
# mapping_store: sqlite
# sqlite_path: data/mapping_store.sqlite
""".strip(
    "\n"
)


def parse_csv_rows(path: Path) -> list[MappingInputRow]:
    """Parse and validate CSV with headers ``ado_organization``, ``ado_project``, ``snyk_org_name``.

    The header row must contain **exactly** those columns (no extras, no duplicates).
    Data rows with all empty cells are skipped. Any other row with an empty
    required cell raises ``CsvValidationError``.

    Args:
        path: UTF-8 file; a BOM is accepted.

    Returns:
        Parsed rows in file order.
    """
    required_set = set(REQUIRED_COLUMNS)
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise CsvValidationError("CSV is empty") from exc
        fields = [h.strip() for h in header]
        if len(fields) != len(set(fields)):
            raise CsvValidationError("CSV header has duplicate column names")
        if set(fields) != required_set:
            missing = required_set - set(fields)
            extra = set(fields) - required_set
            parts: list[str] = []
            if missing:
                parts.append(f"missing columns: {', '.join(sorted(missing))}")
            if extra:
                parts.append(f"unexpected columns: {', '.join(sorted(extra))}")
            raise CsvValidationError("; ".join(parts) if parts else "invalid header")

        out: list[MappingInputRow] = []
        for line_no, row in enumerate(reader, start=2):
            cells = [c.strip() for c in row]
            if not cells or all(c == "" for c in cells):
                continue
            if len(cells) != len(fields):
                raise CsvValidationError(
                    f"row {line_no}: expected {len(fields)} columns, got {len(cells)}"
                )
            record = dict(zip(fields, cells, strict=True))
            if any(record[k] == "" for k in REQUIRED_COLUMNS):
                raise CsvValidationError(f"row {line_no}: empty value in a required column")
            out.append(
                MappingInputRow(
                    ado_organization=record["ado_organization"],
                    ado_project=record["ado_project"],
                    snyk_org_name=record["snyk_org_name"],
                    source_row_index=line_no,
                )
            )
    if not out:
        raise CsvValidationError("CSV contains no data rows")
    return out


def _orgs_from_document(doc: dict[str, Any]) -> list[GroupOrg]:
    """Extract orgs from one JSON:API page."""
    raw = doc.get("data")
    if not isinstance(raw, list):
        return []
    out: list[GroupOrg] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        oid = str(item.get("id", "") or "").strip()
        attrs = item.get("attributes")
        if not isinstance(attrs, dict):
            attrs = {}
        name = str(attrs.get("name", "") or "").strip()
        slug = str(attrs.get("slug", "") or "").strip()
        if oid and name and slug:
            out.append(GroupOrg(id=oid, name=name, slug=slug))
    return out


def _require_token(explicit: str | None) -> str:
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()
    t = os.environ.get("SNYK_TOKEN", "").strip()
    if not t:
        raise SnykOrgApiError("SNYK_TOKEN is not set or empty")
    return t


def _request_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


def fetch_group_orgs(
    base_url: str,
    group_id: str,
    api_version: str,
    *,
    token: str | None = None,
    opener: _Opener | None = None,
    timeout: float = 60.0,
) -> list[GroupOrg]:
    """GET all orgs under ``group_id``, following ``links.next`` with ``limit=100``."""
    base = normalize_base_url(base_url)
    tok = _require_token(token)
    op: _Opener = opener if opener is not None else urlopen

    q = urlencode({"version": api_version, "limit": str(ORG_LIST_LIMIT)})
    url = f"{base}/groups/{group_id}/orgs?{q}"
    aggregated: list[GroupOrg] = []
    seen_urls: set[str] = set()

    while url:
        if url in seen_urls:
            raise SnykOrgApiError("pagination loop detected (repeated next URL)")
        seen_urls.add(url)
        req = Request(url, headers=_request_headers(tok), method="GET")
        try:
            with op(req, timeout=timeout) as resp:
                body = resp.read()
                raw_status = getattr(resp, "status", None)
                if raw_status is None:
                    raw_status = getattr(resp, "code", None)
                status = int(raw_status) if raw_status is not None else 200
        except HTTPError as exc:
            raise SnykOrgApiError(
                f"Snyk org list HTTP {exc.code}: {exc.reason or 'error'}",
            ) from exc
        except URLError as exc:
            raise SnykOrgApiError(f"Snyk org list transport error: {exc}") from exc
        except OSError as exc:
            raise SnykOrgApiError(f"Snyk org list I/O error: {exc}") from exc

        if status >= 400:
            raise SnykOrgApiError(f"Snyk org list HTTP {status}")

        try:
            doc = json.loads(body.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise SnykOrgApiError("Snyk org list response is not valid UTF-8") from exc
        except json.JSONDecodeError as exc:
            raise SnykOrgApiError("Snyk org list response is not valid JSON") from exc

        if not isinstance(doc, dict):
            raise SnykOrgApiError("Snyk org list response must be a JSON object")

        aggregated.extend(_orgs_from_document(doc))
        links = doc.get("links")
        next_raw: str | None
        if isinstance(links, dict):
            nxt = links.get("next")
            next_raw = str(nxt).strip() if nxt is not None else None
        else:
            next_raw = None
        url = resolve_next_url(base, next_raw) if next_raw else None

    return aggregated


def resolve_mappings(
    rows: list[MappingInputRow],
    orgs: list[GroupOrg],
) -> list[dict[str, str]]:
    """Map each CSV row to ``organization`` / ``project`` / ``snyk_org_id`` / ``snyk_org_slug``.

    Raises:
        OrgResolutionError: no match or ambiguous display name.
    """
    by_name: dict[str, list[GroupOrg]] = defaultdict(list)
    for org in orgs:
        by_name[org.name].append(org)

    out: list[dict[str, str]] = []
    for row in rows:
        name_key = row.snyk_org_name
        candidates = by_name.get(name_key, [])
        if not candidates:
            raise OrgResolutionError(
                f"data row {row.source_row_index}: no Snyk org with name {name_key!r}",
            )
        if len(candidates) > 1:
            raise OrgResolutionError(
                f"data row {row.source_row_index}: multiple Snyk orgs named {name_key!r} "
                f"({len(candidates)} matches); names must be unique within the group",
            )
        c = candidates[0]
        out.append(
            {
                "organization": row.ado_organization,
                "project": row.ado_project,
                "snyk_org_id": c.id,
                "snyk_org_slug": c.slug,
            }
        )
    return out


def render_config_yaml(group_id: str, mappings: list[dict[str, str]]) -> str:
    """Build UTF-8 YAML text: commented defaults, ``org_mappings``, ``snyk.group_id``, comments."""
    header = (
        "# Generated starter config — uncomment azure_boards.defaults and mapping_store "
        "before production use.\n"
        "# Secrets (SNYK_TOKEN, Azure DevOps PAT) stay in the environment or Key Vault.\n\n"
    )
    inner = yaml.dump(
        mappings,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    indented = "".join(f"    {line}\n" for line in inner.splitlines())
    tail = f"{MAPPING_STORE_COMMENT_BLOCK}\n"
    return (
        f"{header}"
        f"azure_boards:\n"
        f"  defaults:\n"
        f"{DEFAULTS_COMMENT_BLOCK}\n"
        f"  org_mappings:\n"
        f"{indented}"
        f"snyk:\n"
        f"  group_id: \"{group_id}\"\n\n"
        f"{tail}"
    )


def write_atomic(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` using a temp file and ``os.replace`` (atomic on POSIX)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".org-config-",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
