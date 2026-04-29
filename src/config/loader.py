"""Load and merge YAML configuration with defaults, environment, and CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from config.errors import ConfigError
from config.models import (
    DEFAULT_MAPPING_STORE,
    DEFAULT_SQLITE_PATH,
    AppConfig,
    AzureBoardsConfig,
    AzureBoardsDefaults,
    OrgMapping,
    SnykConfig,
)

SEVERITY_LEVELS: tuple[str, ...] = ("low", "medium", "high", "critical")

_ALLOWED_MAPPING_STORES: frozenset[str] = frozenset({"sqlite", "azure_table"})

_ENV_CONFIG_PATH = "SNYK_APP_CONFIG"
_ENV_GROUP_ID = "SNYK_GROUP_ID"
_ENV_CREATE_NEW = "AZURE_BOARDS_CREATE_NEW_WORK_ITEMS"
_ENV_AZURE_BOARDS_ORGANIZATION = "AZURE_BOARDS_ORGANIZATION"
_ENV_AZURE_BOARDS_PROJECT = "AZURE_BOARDS_PROJECT"
_ENV_MAPPING_STORE = "MAPPING_STORE"
_ENV_SQLITE_PATH = "MAPPING_STORE_SQLITE_PATH"


_DEPRECATED_AZURE_BOARDS_WORK_ITEM_KEYS: frozenset[str] = frozenset(
    {
        "work_item_type",
        "work_item_state_active",
        "work_item_state_closed",
    },
)


def _default_tree() -> dict[str, Any]:
    return {
        "azure_boards": {
            "create_new_work_items": True,
            "organization": "",
            "project": "",
            "defaults": {
                "work_item_type": "Task",
                "work_item_state_active": "New",
                "work_item_state_closed": "Closed",
                "work_item_template": {},
            },
            "org_mappings": [],
        },
        "work_item_template": {},
        "snyk": {"group_id": "", "severity_threshold": "high"},
        "mapping_store": DEFAULT_MAPPING_STORE,
        "sqlite_path": DEFAULT_SQLITE_PATH,
    }


def _deep_merge_dict(base: dict[str, Any], overlay: Mapping[str, Any]) -> None:
    """Merge overlay into base in place (dict values recurse)."""
    for key, val in overlay.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(val, Mapping)
        ):
            _deep_merge_dict(base[key], val)
        else:
            base[key] = val


def _coerce_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1", "yes", "on"):
            return True
        if v in ("false", "0", "no", "off", ""):
            return False
    raise ConfigError(
        f"{field_name} must be a boolean (got {type(value).__name__})",
    )


def _normalize_mapping_store(raw: str) -> str:
    s = raw.strip().lower()
    if s not in _ALLOWED_MAPPING_STORES:
        allowed = ", ".join(sorted(_ALLOWED_MAPPING_STORES))
        raise ConfigError(
            f"mapping_store must be one of: {allowed} (got {raw!r})",
        )
    return s


def _normalize_severity(raw: str) -> str:
    s = raw.strip().lower()
    if s not in SEVERITY_LEVELS:
        allowed = ", ".join(SEVERITY_LEVELS)
        raise ConfigError(
            f"snyk.severity_threshold must be one of: {allowed} (got {raw!r})",
        )
    return s


def parse_yaml_bytes(data: bytes, *, source: str = "YAML") -> dict[str, Any]:
    """Parse YAML bytes into a dict; raise ConfigError on invalid input."""
    try:
        raw = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid {source}: {exc}") from exc
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{source} root must be a mapping, not {type(raw).__name__}")
    return raw


def _canonical_config_path(path: str | os.PathLike[str]) -> Path:
    """Expand user home and resolve to a canonical path (no ``..`` segments)."""
    pstr = os.fspath(path)
    if "\x00" in pstr:
        raise ConfigError("Invalid configuration path")
    return Path(pstr).expanduser().resolve(strict=False)


def load_yaml_file(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read and parse a YAML file from disk."""
    p = _canonical_config_path(path)
    try:
        data = p.read_bytes()
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file not found: {p}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read configuration file {p}: {exc}") from exc
    return parse_yaml_bytes(data, source=str(p))


def resolve_config_path(cli_config: str | None) -> str | None:
    """Resolve path to YAML: CLI wins, then SNYK_APP_CONFIG."""
    if cli_config and cli_config.strip():
        return cli_config.strip()
    env_path = os.environ.get(_ENV_CONFIG_PATH, "").strip()
    return env_path or None


def _apply_env_overrides(tree: dict[str, Any]) -> None:
    """Apply environment layer (between file and CLI)."""
    if _ENV_GROUP_ID in os.environ:
        gid = os.environ[_ENV_GROUP_ID].strip()
        tree.setdefault("snyk", {})
        if not isinstance(tree["snyk"], dict):
            tree["snyk"] = {"group_id": gid}
        else:
            tree["snyk"]["group_id"] = gid

    if _ENV_CREATE_NEW in os.environ:
        raw = os.environ[_ENV_CREATE_NEW]
        tree.setdefault("azure_boards", {})
        if not isinstance(tree["azure_boards"], dict):
            tree["azure_boards"] = {}
        tree["azure_boards"]["create_new_work_items"] = _coerce_bool(
            raw,
            field_name="AZURE_BOARDS_CREATE_NEW_WORK_ITEMS",
        )

    if _ENV_AZURE_BOARDS_ORGANIZATION in os.environ:
        org = os.environ[_ENV_AZURE_BOARDS_ORGANIZATION].strip()
        if org:
            tree.setdefault("azure_boards", {})
            if not isinstance(tree["azure_boards"], dict):
                tree["azure_boards"] = {}
            tree["azure_boards"]["organization"] = org

    if _ENV_AZURE_BOARDS_PROJECT in os.environ:
        proj = os.environ[_ENV_AZURE_BOARDS_PROJECT].strip()
        if proj:
            tree.setdefault("azure_boards", {})
            if not isinstance(tree["azure_boards"], dict):
                tree["azure_boards"] = {}
            tree["azure_boards"]["project"] = proj

    if _ENV_MAPPING_STORE in os.environ:
        ms = os.environ[_ENV_MAPPING_STORE].strip()
        if ms:
            tree["mapping_store"] = ms

    if _ENV_SQLITE_PATH in os.environ:
        sp = os.environ[_ENV_SQLITE_PATH].strip()
        if sp:
            tree["sqlite_path"] = sp


def _reject_deprecated_flat_work_item_keys(ab_raw: dict[str, Any]) -> None:
    """Reject unsupported flat ``work_item_*`` keys under ``azure_boards`` root."""
    for key in _DEPRECATED_AZURE_BOARDS_WORK_ITEM_KEYS:
        if key in ab_raw:
            raise ConfigError(
                f"azure_boards.{key} is not supported; "
                f"use azure_boards.defaults.{key} instead",
            )


def _string_from_defaults_section(
    defaults_raw: dict[str, Any],
    key: str,
    *,
    hard_default: str,
) -> str:
    """Read a string field from ``defaults`` with built-in fallback."""
    if key not in defaults_raw:
        return hard_default
    raw = defaults_raw[key]
    if raw is None:
        return hard_default
    s = str(raw).strip()
    return s if s else hard_default


def _parse_org_mappings(ab_raw: dict[str, Any]) -> list[OrgMapping]:
    raw = ab_raw.get("org_mappings")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError("azure_boards.org_mappings must be a list")
    out: list[OrgMapping] = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ConfigError(
                f"azure_boards.org_mappings[{i}] must be a mapping",
            )
        org = str(item.get("organization", "") or "").strip()
        proj = str(item.get("project", "") or "").strip()
        snyk_org = str(item.get("snyk_org_id", "") or "").strip()
        if not org:
            raise ConfigError(
                f"azure_boards.org_mappings[{i}].organization is required",
            )
        if not proj:
            raise ConfigError(
                f"azure_boards.org_mappings[{i}].project is required",
            )
        if not snyk_org:
            raise ConfigError(
                f"azure_boards.org_mappings[{i}].snyk_org_id is required",
            )
        ov = item.get("overrides")
        overrides: dict[str, Any] = {}
        if ov is not None:
            if not isinstance(ov, Mapping):
                raise ConfigError(
                    f"azure_boards.org_mappings[{i}].overrides must be a mapping",
                )
            overrides = dict(ov)
        out.append(
            OrgMapping(
                organization=org,
                project=proj,
                snyk_org_id=snyk_org,
                overrides=overrides,
            ),
        )
    return out


def _parse_azure_boards_defaults(
    ab_raw: dict[str, Any],
) -> tuple[AzureBoardsDefaults, str, str, str]:
    """Build ``AzureBoardsDefaults`` and duplicate flat fields on ``AzureBoardsConfig``."""
    _reject_deprecated_flat_work_item_keys(ab_raw)

    defaults_raw = ab_raw.get("defaults")
    if defaults_raw is None:
        defaults_raw = {}
    if not isinstance(defaults_raw, dict):
        raise ConfigError("azure_boards.defaults must be a mapping")

    wit_type = _string_from_defaults_section(
        defaults_raw,
        "work_item_type",
        hard_default="Task",
    )
    wit_active = _string_from_defaults_section(
        defaults_raw,
        "work_item_state_active",
        hard_default="New",
    )
    wit_closed = _string_from_defaults_section(
        defaults_raw,
        "work_item_state_closed",
        hard_default="Closed",
    )

    wit_tmpl = defaults_raw.get("work_item_template")
    if wit_tmpl is None:
        wit_tmpl = {}
    if not isinstance(wit_tmpl, dict):
        raise ConfigError("azure_boards.defaults.work_item_template must be a mapping")

    defaults = AzureBoardsDefaults(
        work_item_type=wit_type,
        work_item_state_active=wit_active,
        work_item_state_closed=wit_closed,
        work_item_template=dict(wit_tmpl),
    )
    return defaults, wit_type, wit_active, wit_closed


def _tree_to_app_config(tree: dict[str, Any]) -> AppConfig:
    """Build AppConfig from a merged tree."""
    ab_raw = tree.get("azure_boards") or {}
    if not isinstance(ab_raw, dict):
        raise ConfigError("azure_boards must be a mapping")

    wit = tree.get("work_item_template")
    if wit is None:
        wit = {}
    if not isinstance(wit, dict):
        raise ConfigError("work_item_template must be a mapping")

    sn_raw = tree.get("snyk") or {}
    if not isinstance(sn_raw, dict):
        raise ConfigError("snyk must be a mapping")

    known_snyk = {"group_id", "severity_threshold"}
    extra = {k: v for k, v in sn_raw.items() if k not in known_snyk}

    gid = str(sn_raw.get("group_id", "") or "").strip()
    sev_raw = str(sn_raw.get("severity_threshold", "high") or "high")
    sev = _normalize_severity(sev_raw)

    create_new = _coerce_bool(
        ab_raw.get("create_new_work_items", True),
        field_name="azure_boards.create_new_work_items",
    )

    org = str(ab_raw.get("organization", "") or "").strip()
    proj = str(ab_raw.get("project", "") or "").strip()

    defaults_obj, wit_type, wit_active, wit_closed = _parse_azure_boards_defaults(ab_raw)
    org_mappings = _parse_org_mappings(ab_raw)

    ms_raw = tree.get("mapping_store", DEFAULT_MAPPING_STORE)
    if ms_raw is None or (isinstance(ms_raw, str) and not ms_raw.strip()):
        ms_raw = DEFAULT_MAPPING_STORE
    mapping_store = _normalize_mapping_store(str(ms_raw))

    sp_raw = tree.get("sqlite_path", DEFAULT_SQLITE_PATH)
    if sp_raw is None or (isinstance(sp_raw, str) and not str(sp_raw).strip()):
        sqlite_path = DEFAULT_SQLITE_PATH
    else:
        sqlite_path = str(sp_raw).strip()

    return AppConfig(
        azure_boards=AzureBoardsConfig(
            create_new_work_items=create_new,
            organization=org,
            project=proj,
            work_item_type=wit_type,
            work_item_state_active=wit_active,
            work_item_state_closed=wit_closed,
            defaults=defaults_obj,
            org_mappings=org_mappings,
        ),
        work_item_template=dict(wit),
        snyk=SnykConfig(group_id=gid, severity_threshold=sev, extra=extra),
        mapping_store=mapping_store,
        sqlite_path=sqlite_path,
    )


def load_app_config(
    *,
    config_path: str | None,
    cli_group_id: str | None = None,
    cli_sqlite_path: str | None = None,
) -> AppConfig:
    """
    Load merged configuration: defaults → YAML file (if path) → env → CLI overrides.

    ``cli_group_id`` is the top layer for ``snyk.group_id`` when non-empty.
    ``cli_sqlite_path`` is the top layer for ``sqlite_path`` when non-empty.
    """
    tree = _default_tree()
    path = resolve_config_path(config_path)
    if path:
        overlay = load_yaml_file(path)
        _deep_merge_dict(tree, overlay)
    _apply_env_overrides(tree)
    if cli_group_id is not None and cli_group_id.strip():
        tree.setdefault("snyk", {})
        if not isinstance(tree["snyk"], dict):
            tree["snyk"] = {}
        tree["snyk"]["group_id"] = cli_group_id.strip()
    if cli_sqlite_path is not None and cli_sqlite_path.strip():
        tree["sqlite_path"] = cli_sqlite_path.strip()
    return _tree_to_app_config(tree)
