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
    ISSUES_SYNC_FROM_HISTORICAL,
    REOPEN_POLICY_NEW_WORK_ITEM,
    AppConfig,
    AzureBoardsConfig,
    AzureBoardsDefaults,
    OrgMapping,
    SnykConfig,
)
from config.policy_parse import (
    coerce_bool,
    normalize_reopen_policy,
    normalize_severity,
    validate_issues_sync_from,
)
from config.snyk_origins import parse_sync_included_snyk_origins

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

_LEGACY_AZURE_BOARDS_ROOT_KEYS: frozenset[str] = frozenset(
    {
        "create_new_work_items",
        "organization",
        "project",
    },
)

def _default_tree() -> dict[str, Any]:
    return {
        "azure_boards": {
            "defaults": {
                "organization": "",
                "project": "",
                "create_new_work_items": True,
                "severity_threshold": "high",
                "issues_sync_from": ISSUES_SYNC_FROM_HISTORICAL,
                "create_only_when_fix_available": False,
                "reopen_work_item_policy": REOPEN_POLICY_NEW_WORK_ITEM,
                "work_item_type": "Task",
                "work_item_state_active": "New",
                "work_item_state_closed": "Closed",
                "work_item_description_appendix": "",
                "work_item_template": {},
            },
            "org_mappings": [],
        },
        "work_item_template": {},
        "snyk": {"group_id": ""},
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


def _normalize_mapping_store(raw: str) -> str:
    s = raw.strip().lower()
    if s not in _ALLOWED_MAPPING_STORES:
        allowed = ", ".join(sorted(_ALLOWED_MAPPING_STORES))
        raise ConfigError(
            f"mapping_store must be one of: {allowed} (got {raw!r})",
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
        tree["azure_boards"].setdefault("defaults", {})
        if not isinstance(tree["azure_boards"]["defaults"], dict):
            tree["azure_boards"]["defaults"] = {}
        tree["azure_boards"]["defaults"]["create_new_work_items"] = coerce_bool(
            raw,
            field_name="AZURE_BOARDS_CREATE_NEW_WORK_ITEMS",
        )

    if _ENV_AZURE_BOARDS_ORGANIZATION in os.environ:
        org = os.environ[_ENV_AZURE_BOARDS_ORGANIZATION].strip()
        if org:
            tree.setdefault("azure_boards", {})
            if not isinstance(tree["azure_boards"], dict):
                tree["azure_boards"] = {}
            tree["azure_boards"].setdefault("defaults", {})
            if not isinstance(tree["azure_boards"]["defaults"], dict):
                tree["azure_boards"]["defaults"] = {}
            tree["azure_boards"]["defaults"]["organization"] = org

    if _ENV_AZURE_BOARDS_PROJECT in os.environ:
        proj = os.environ[_ENV_AZURE_BOARDS_PROJECT].strip()
        if proj:
            tree.setdefault("azure_boards", {})
            if not isinstance(tree["azure_boards"], dict):
                tree["azure_boards"] = {}
            tree["azure_boards"].setdefault("defaults", {})
            if not isinstance(tree["azure_boards"]["defaults"], dict):
                tree["azure_boards"]["defaults"] = {}
            tree["azure_boards"]["defaults"]["project"] = proj

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


def _reject_legacy_azure_boards_root_routing(ab_raw: dict[str, Any]) -> None:
    """Reject legacy flat routing / toggle keys under ``azure_boards`` root."""
    for key in _LEGACY_AZURE_BOARDS_ROOT_KEYS:
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
        slug_raw = item.get("snyk_org_slug")
        snyk_slug = str(slug_raw or "").strip()
        if not snyk_slug:
            raise ConfigError(
                f"azure_boards.org_mappings[{i}].snyk_org_slug is required "
                "(human-readable org slug for app.snyk.io links)",
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
                snyk_org_slug=snyk_slug,
                overrides=overrides,
            ),
        )
    return out


def _parse_azure_boards_defaults(ab_raw: dict[str, Any]) -> AzureBoardsDefaults:
    """Parse ``azure_boards.defaults`` into :class:`AzureBoardsDefaults`."""
    _reject_deprecated_flat_work_item_keys(ab_raw)
    _reject_legacy_azure_boards_root_routing(ab_raw)

    defaults_raw = ab_raw.get("defaults")
    if defaults_raw is None:
        defaults_raw = {}
    if not isinstance(defaults_raw, dict):
        raise ConfigError("azure_boards.defaults must be a mapping")

    org = _string_from_defaults_section(defaults_raw, "organization", hard_default="")
    proj = _string_from_defaults_section(defaults_raw, "project", hard_default="")

    create_new = coerce_bool(
        defaults_raw.get("create_new_work_items", True),
        field_name="azure_boards.defaults.create_new_work_items",
    )

    sev_raw = str(defaults_raw.get("severity_threshold", "high") or "high")
    sev = normalize_severity(sev_raw, field_prefix="azure_boards.defaults.severity_threshold")

    issues_from = validate_issues_sync_from(
        str(defaults_raw.get("issues_sync_from", ISSUES_SYNC_FROM_HISTORICAL) or ""),
    )

    fix_only = coerce_bool(
        defaults_raw.get("create_only_when_fix_available", False),
        field_name="azure_boards.defaults.create_only_when_fix_available",
    )

    reopen_raw = str(
        defaults_raw.get("reopen_work_item_policy", REOPEN_POLICY_NEW_WORK_ITEM)
        or REOPEN_POLICY_NEW_WORK_ITEM,
    )
    reopen = normalize_reopen_policy(reopen_raw)

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

    appendix_raw = defaults_raw.get("work_item_description_appendix", "")
    if appendix_raw is not None and not isinstance(appendix_raw, str):
        raise ConfigError(
            "azure_boards.defaults.work_item_description_appendix must be a string",
        )
    appendix = str(appendix_raw or "")

    allowlist = parse_sync_included_snyk_origins(
        defaults_raw.get("sync_included_snyk_origins"),
        field_prefix="azure_boards.defaults.sync_included_snyk_origins",
    )

    return AzureBoardsDefaults(
        organization=org,
        project=proj,
        create_new_work_items=create_new,
        severity_threshold=sev,
        issues_sync_from=issues_from,
        create_only_when_fix_available=fix_only,
        reopen_work_item_policy=reopen,
        work_item_type=wit_type,
        work_item_state_active=wit_active,
        work_item_state_closed=wit_closed,
        work_item_description_appendix=appendix,
        work_item_template=dict(wit_tmpl),
        sync_included_snyk_origins=allowlist,
    )


def _defaults_to_flat_config(d: AzureBoardsDefaults) -> AzureBoardsConfig:
    """Mirror ``defaults`` onto flat :class:`AzureBoardsConfig` fields."""
    return AzureBoardsConfig(
        create_new_work_items=d.create_new_work_items,
        organization=d.organization,
        project=d.project,
        severity_threshold=d.severity_threshold,
        issues_sync_from=d.issues_sync_from,
        create_only_when_fix_available=d.create_only_when_fix_available,
        reopen_work_item_policy=d.reopen_work_item_policy,
        work_item_type=d.work_item_type,
        work_item_state_active=d.work_item_state_active,
        work_item_state_closed=d.work_item_state_closed,
        defaults=d,
        org_mappings=[],
        sync_included_snyk_origins=d.sync_included_snyk_origins,
    )


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

    if "snyk_org_slug" in sn_raw:
        raise ConfigError(
            "snyk.snyk_org_slug is not supported; use "
            "azure_boards.org_mappings[].snyk_org_slug on each mapping row",
        )

    if "severity_threshold" in sn_raw:
        raise ConfigError(
            "snyk.severity_threshold is not supported; use "
            "azure_boards.defaults.severity_threshold instead",
        )

    known_snyk = {"group_id"}
    extra = {k: v for k, v in sn_raw.items() if k not in known_snyk}

    gid = str(sn_raw.get("group_id", "") or "").strip()

    if "snyk_org_slug" in ab_raw:
        raise ConfigError(
            "azure_boards.snyk_org_slug is not supported; set snyk_org_slug on each "
            "azure_boards.org_mappings[] row. Without org_mappings, group-scoped sync "
            "does not configure an org slug (Snyk UI links in work items may be incomplete).",
        )

    defaults_obj = _parse_azure_boards_defaults(ab_raw)
    org_mappings = _parse_org_mappings(ab_raw)

    flat = _defaults_to_flat_config(defaults_obj)
    flat.org_mappings = org_mappings

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
        azure_boards=flat,
        work_item_template=dict(wit),
        snyk=SnykConfig(
            group_id=gid,
            extra=extra,
        ),
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
