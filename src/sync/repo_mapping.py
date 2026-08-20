"""Load and resolve ``repo-mapping.csv`` for area path and assignee routing."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from config.errors import ConfigError
from config.models import AppConfig, AzureBoardsConfig

DEFAULT_REPO_MAPPING_CSV = "repo-mapping.csv"

_GITHUB_FAMILY_ORIGINS: frozenset[str] = frozenset(
    {
        "github",
        "github-cloud-app",
        "github-enterprise",
        "github-server-app",
    },
)

_ALLOWED_CSV_SOURCES: frozenset[str] = frozenset({"github", "azure-repos"})

_REQUIRED_HEADERS: tuple[str, ...] = (
    "source",
    "github org/ado project",
    "repo name",
    "area path",
)

_OPTIONAL_HEADERS: frozenset[str] = frozenset({"assignee"})


def snyk_origin_to_csv_source(origin: str) -> str | None:
    """
    Map Snyk ``attributes.origin`` to CSV **Source** token.

    Returns ``github``, ``azure-repos``, or ``None`` when no CSV row can match.
    """
    o = str(origin or "").strip()
    if o in _GITHUB_FAMILY_ORIGINS:
        return "github"
    if o == "azure-repos":
        return "azure-repos"
    return None


def _normalize_repo_segment(repo: str) -> str:
    """
    Strip Snyk target suffix from a repo segment.

    Issue and scan-item display names often append ``(branch):manifest`` after the
    repository name (for example ``nodejs-goof(main):package.json``). CSV **Repo Name**
    columns use the bare repo identifier only.
    """
    s = str(repo or "").strip()
    if not s:
        return ""
    paren = s.find("(")
    if paren >= 0:
        s = s[:paren].strip()
    return s


def parse_owner_repo(project_name: str) -> tuple[str, str]:
    """
    Split Snyk project display name into ``(owner, repo)``.

    Splits on the first ``/`` only. When absent, owner is empty and repo is the
    full trimmed name (after stripping any ``(branch):manifest`` suffix). When a
    slash is present, the repo segment is normalized the same way.
    """
    name = str(project_name or "").strip()
    if not name:
        return "", ""
    if "/" not in name:
        return "", _normalize_repo_segment(name)
    owner, _, repo = name.partition("/")
    return owner.strip(), _normalize_repo_segment(repo)


@dataclass(frozen=True)
class RepoMappingMatch:
    """One matching CSV row."""

    area_path: str
    assignee: str


@dataclass(frozen=True)
class ResolvedRouting:
    """Effective area path and assignee for one issue."""

    area_path: str | None
    assignee: str | None
    area_path_source: str
    assignee_from_csv: bool


class RepoMappingIndex:
    """In-memory lookup for repo-mapping CSV rows."""

    def __init__(self, rows: Mapping[tuple[str, str, str], RepoMappingMatch]) -> None:
        self._rows = dict(rows)

    @classmethod
    def empty(cls) -> RepoMappingIndex:
        """Return an index with no CSV rows (YAML fallbacks only)."""
        return cls({})

    def lookup(self, source: str, scope: str, repo: str) -> RepoMappingMatch | None:
        """Return a row match for normalized ``(source, scope, repo)`` key parts."""
        key = (
            str(source or "").strip(),
            str(scope or "").strip(),
            str(repo or "").strip(),
        )
        return self._rows.get(key)

    @classmethod
    def load_from_path(cls, path: Path) -> RepoMappingIndex:
        """Parse CSV at ``path`` and build a lookup index."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"Cannot read repo mapping CSV {path}: {exc}") from exc

        reader = csv.reader(text.splitlines())
        try:
            header_row = next(reader)
        except StopIteration as exc:
            raise ConfigError(f"repo mapping CSV is empty: {path}") from exc

        header_map = _normalize_headers(header_row)
        _validate_required_headers(header_map, path=path)

        rows: dict[tuple[str, str, str], RepoMappingMatch] = {}
        for line_no, row in enumerate(reader, start=2):
            if not row or all(not str(cell).strip() for cell in row):
                continue
            record = _row_to_record(row, header_map, line_no=line_no, path=path)
            key = (record[0], record[1], record[2])
            if key in rows:
                raise ConfigError(
                    f"Duplicate repo mapping key {key!r} in {path} (line {line_no})",
                )
            rows[key] = RepoMappingMatch(area_path=record[3], assignee=record[4])
        return cls(rows)


def resolve_repo_mapping_csv_path(app: AppConfig) -> Path | None:
    """
    Resolve effective CSV path from merged config.

    Returns ``None`` when repo CSV routing is disabled (no config dir and no
    explicit path). When a path is returned, the file must exist before sync.
    """
    raw = app.azure_boards.repo_mapping_csv
    if raw is not None and raw == "":
        return None
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            base = app.config_file_dir
            if base:
                p = Path(base) / p
            else:
                p = Path.cwd() / p
        return p.resolve()
    if app.config_file_dir:
        return (Path(app.config_file_dir) / DEFAULT_REPO_MAPPING_CSV).resolve()
    return None


def load_repo_mapping_index(app: AppConfig) -> RepoMappingIndex:
    """Load repo mapping index or return empty when CSV routing is disabled."""
    path = resolve_repo_mapping_csv_path(app)
    if path is None:
        return RepoMappingIndex.empty()
    if not path.is_file():
        raise ConfigError(f"repo mapping CSV not found: {path}")
    return RepoMappingIndex.load_from_path(path)


def resolve_routing(
    *,
    index: RepoMappingIndex,
    snyk_project_origin: str,
    snyk_project_name: str,
    boards: AzureBoardsConfig,
    global_defaults_area_path: str | None = None,
) -> ResolvedRouting:
    """
    Resolve effective area path and assignee for one issue.

    Area path precedence: CSV row → merged ``defaults.area_path`` → unset.
    Assignee: non-empty CSV **Assignee** when row matches; else template rules.
    """
    csv_source = snyk_origin_to_csv_source(snyk_project_origin)
    owner, repo = parse_owner_repo(snyk_project_name)
    csv_match: RepoMappingMatch | None = None
    if csv_source is not None:
        csv_match = index.lookup(csv_source, owner, repo)

    if csv_match is not None:
        area_path = csv_match.area_path
        assignee = csv_match.assignee.strip() or None
        return ResolvedRouting(
            area_path=area_path,
            assignee=assignee,
            area_path_source="csv",
            assignee_from_csv=bool(assignee),
        )

    yaml_path = boards.defaults.area_path
    if yaml_path:
        if yaml_path != global_defaults_area_path:
            area_source = "org_override"
        else:
            area_source = "defaults"
        return ResolvedRouting(
            area_path=yaml_path,
            assignee=None,
            area_path_source=area_source,
            assignee_from_csv=False,
        )

    return ResolvedRouting(
        area_path=None,
        assignee=None,
        area_path_source="none",
        assignee_from_csv=False,
    )


def _normalize_headers(header_row: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, cell in enumerate(header_row):
        key = str(cell or "").strip().lower()
        if key:
            out[key] = i
    return out


def _validate_required_headers(header_map: Mapping[str, int], *, path: Path) -> None:
    missing = [h for h in _REQUIRED_HEADERS if h not in header_map]
    if missing:
        raise ConfigError(
            f"repo mapping CSV {path} missing required column(s): "
            + ", ".join(missing),
        )


def _row_to_record(
    row: list[str],
    header_map: Mapping[str, int],
    *,
    line_no: int,
    path: Path,
) -> tuple[str, str, str, str, str]:
    def cell(name: str) -> str:
        idx = header_map[name]
        if idx >= len(row):
            return ""
        return str(row[idx] or "").strip()

    source = cell("source")
    scope = cell("github org/ado project")
    repo = cell("repo name")
    area_path = cell("area path")
    assignee = cell("assignee") if "assignee" in header_map else ""

    if source not in _ALLOWED_CSV_SOURCES:
        raise ConfigError(
            f"repo mapping CSV {path} line {line_no}: Source must be "
            f"'github' or 'azure-repos' (got {source!r})",
        )
    if not repo:
        raise ConfigError(
            f"repo mapping CSV {path} line {line_no}: Repo Name is required",
        )
    if not area_path:
        raise ConfigError(
            f"repo mapping CSV {path} line {line_no}: Area Path is required",
        )
    return source, scope, repo, area_path, assignee
