"""Load and merge YAML configuration with defaults, environment, and CLI."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Mapping

from urllib.parse import urlsplit

import yaml

from config.errors import ConfigError
from config.field_refs import normalize_work_item_description_field
from config.models import (
    DEFAULT_MAPPING_STORE,
    DEFAULT_SQLITE_PATH,
    ISSUES_SYNC_FROM_HISTORICAL,
    REOPEN_POLICY_NEW_WORK_ITEM,
    AdoTargetIndex,
    AdoTargetProfile,
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
from snyk.constants import DEFAULT_API_ORIGIN, DEFAULT_APP_ORIGIN
from snyk.urls import normalize_api_origin, normalize_app_origin, resolve_api_origin

_ALLOWED_MAPPING_STORES: frozenset[str] = frozenset({"sqlite", "azure_table"})
_AZURE_TABLE_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9]{2,62}")

_ENV_CONFIG_PATH = "SNYK_APP_CONFIG"
_ENV_GROUP_ID = "SNYK_GROUP_ID"
_ENV_API_BASE_URL = "SNYK_API_BASE_URL"
_ENV_APP_BASE_URL = "SNYK_APP_BASE_URL"
_ENV_CREATE_NEW = "AZURE_BOARDS_CREATE_NEW_WORK_ITEMS"
_ENV_AZURE_BOARDS_ORGANIZATION = "AZURE_BOARDS_ORGANIZATION"
_ENV_AZURE_BOARDS_PROJECT = "AZURE_BOARDS_PROJECT"
_ENV_MAPPING_STORE = "MAPPING_STORE"
_ENV_SQLITE_PATH = "MAPPING_STORE_SQLITE_PATH"
_ENV_AZURE_TABLE_ENDPOINT = "MAPPING_STORE_AZURE_TABLE_ENDPOINT"
_ENV_AZURE_TABLE_NAME = "MAPPING_STORE_AZURE_TABLE_NAME"
_ENV_REPO_MAPPING_CSV_PATH = "REPO_MAPPING_CSV_PATH"


_DEPRECATED_AZURE_BOARDS_WORK_ITEM_KEYS: frozenset[str] = frozenset(
    {
        "work_item_type",
        "work_item_state_active",
        "work_item_state_closed",
        "work_item_description_field",
        "area_path",
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
        "snyk": {
            "group_id": "",
            "api_base_url": DEFAULT_API_ORIGIN,
            "app_base_url": DEFAULT_APP_ORIGIN,
        },
        "mapping_store": DEFAULT_MAPPING_STORE,
        "sqlite_path": DEFAULT_SQLITE_PATH,
        "mapping_store_azure_table_endpoint": "",
        "mapping_store_azure_table_name": "",
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


def _validate_azure_table_mapping_store_settings(
    *,
    mapping_store: str,
    endpoint: str,
    table_name: str,
) -> None:
    """Require Table endpoint and table name when ``mapping_store`` is ``azure_table``."""
    if mapping_store != "azure_table":
        return
    ep = endpoint.strip()
    if not ep:
        raise ConfigError(
            "mapping_store is 'azure_table' but MAPPING_STORE_AZURE_TABLE_ENDPOINT "
            "is missing or empty after configuration merge",
        )
    if not ep.lower().startswith("https://"):
        raise ConfigError(
            "MAPPING_STORE_AZURE_TABLE_ENDPOINT must be an https:// URL "
            "(non-secret Table service endpoint)",
        )
    tn = table_name.strip()
    if not tn:
        raise ConfigError(
            "mapping_store is 'azure_table' but MAPPING_STORE_AZURE_TABLE_NAME "
            "is missing or empty after configuration merge",
        )
    if _AZURE_TABLE_NAME_RE.fullmatch(tn) is None:
        raise ConfigError(
            "MAPPING_STORE_AZURE_TABLE_NAME must be 3–63 characters, alphanumeric, "
            "starting with a letter (Azure Table naming rules)",
        )


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


def _validate_api_base_url(raw: object, *, field_name: str = "snyk.api_base_url") -> str:
    """Return normalized HTTPS API origin or raise :class:`ConfigError`."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise ConfigError(f"{field_name} must be a non-empty HTTPS URL")
    if not isinstance(raw, str):
        raise ConfigError(f"{field_name} must be a string")
    origin = resolve_api_origin(raw)
    parts = urlsplit(origin)
    if parts.scheme != "https":
        raise ConfigError(f"{field_name} must use HTTPS")
    if not parts.netloc:
        raise ConfigError(f"{field_name} must be a valid HTTPS URL")
    return normalize_api_origin(origin)


def _validate_app_base_url(raw: object, *, field_name: str = "snyk.app_base_url") -> str:
    """Return normalized HTTPS web app origin or raise :class:`ConfigError`."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise ConfigError(f"{field_name} must be a non-empty HTTPS URL")
    if not isinstance(raw, str):
        raise ConfigError(f"{field_name} must be a string")
    origin = normalize_app_origin(raw)
    parts = urlsplit(origin)
    if parts.scheme != "https":
        raise ConfigError(f"{field_name} must use HTTPS")
    if not parts.netloc:
        raise ConfigError(f"{field_name} must be a valid HTTPS URL")
    path = parts.path.rstrip("/")
    if path:
        raise ConfigError(f"{field_name} must be an origin (scheme + host only)")
    return origin


def _apply_env_overrides(tree: dict[str, Any]) -> None:
    """Apply environment layer (between file and CLI)."""
    if _ENV_GROUP_ID in os.environ:
        gid = os.environ[_ENV_GROUP_ID].strip()
        tree.setdefault("snyk", {})
        if not isinstance(tree["snyk"], dict):
            tree["snyk"] = {"group_id": gid}
        else:
            tree["snyk"]["group_id"] = gid

    if _ENV_API_BASE_URL in os.environ:
        api_base = _validate_api_base_url(
            os.environ[_ENV_API_BASE_URL],
            field_name="SNYK_API_BASE_URL",
        )
        tree.setdefault("snyk", {})
        if not isinstance(tree["snyk"], dict):
            tree["snyk"] = {"api_base_url": api_base}
        else:
            tree["snyk"]["api_base_url"] = api_base

    if _ENV_APP_BASE_URL in os.environ:
        app_base = _validate_app_base_url(
            os.environ[_ENV_APP_BASE_URL],
            field_name="SNYK_APP_BASE_URL",
        )
        tree.setdefault("snyk", {})
        if not isinstance(tree["snyk"], dict):
            tree["snyk"] = {"app_base_url": app_base}
        else:
            tree["snyk"]["app_base_url"] = app_base

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

    if _ENV_AZURE_TABLE_ENDPOINT in os.environ:
        ep = os.environ[_ENV_AZURE_TABLE_ENDPOINT].strip()
        if ep:
            tree["mapping_store_azure_table_endpoint"] = ep

    if _ENV_AZURE_TABLE_NAME in os.environ:
        tn = os.environ[_ENV_AZURE_TABLE_NAME].strip()
        if tn:
            tree["mapping_store_azure_table_name"] = tn

    if _ENV_REPO_MAPPING_CSV_PATH in os.environ:
        csv_path = os.environ[_ENV_REPO_MAPPING_CSV_PATH].strip()
        tree.setdefault("azure_boards", {})
        if not isinstance(tree["azure_boards"], dict):
            tree["azure_boards"] = {}
        tree["azure_boards"]["repo_mapping_csv"] = csv_path


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


_ADO_TARGET_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "organization",
        "project",
        "work_item_type",
        "work_item_state_active",
        "work_item_state_closed",
        "work_item_description_field",
        "work_item_template",
    },
)


def _optional_trimmed_string(raw: object) -> str | None:
    """Return stripped string or ``None`` when absent or whitespace-only."""
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def _parse_work_item_template(raw: object, *, field_prefix: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{field_prefix} must be a mapping")
    return dict(raw)


def _parse_ado_targets(ab_raw: dict[str, Any]) -> tuple[list[AdoTargetProfile], AdoTargetIndex]:
    """Parse ``azure_boards.ado_targets`` and build a lookup index."""
    raw = ab_raw.get("ado_targets")
    if raw is None:
        return [], AdoTargetIndex.empty()
    if not isinstance(raw, list):
        raise ConfigError("azure_boards.ado_targets must be a list")

    profiles: list[AdoTargetProfile] = []
    seen: set[tuple[str, str]] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ConfigError(f"azure_boards.ado_targets[{i}] must be a mapping")
        unknown = set(item.keys()) - _ADO_TARGET_ALLOWED_KEYS
        if unknown:
            allowed = ", ".join(sorted(_ADO_TARGET_ALLOWED_KEYS))
            raise ConfigError(
                f"azure_boards.ado_targets[{i}] has unknown key(s): "
                f"{', '.join(sorted(unknown))}; allowed: {allowed}",
            )
        org = str(item.get("organization", "") or "").strip()
        proj = str(item.get("project", "") or "").strip()
        if not org:
            raise ConfigError(
                f"azure_boards.ado_targets[{i}].organization is required",
            )
        if not proj:
            raise ConfigError(
                f"azure_boards.ado_targets[{i}].project is required",
            )
        key = (org, proj)
        if key in seen:
            raise ConfigError(
                f"azure_boards.ado_targets has duplicate (organization, project) "
                f"({org!r}, {proj!r})",
            )
        seen.add(key)

        desc_field = normalize_work_item_description_field(
            item.get("work_item_description_field"),
            field_prefix=f"azure_boards.ado_targets[{i}].work_item_description_field",
        )
        template = _parse_work_item_template(
            item.get("work_item_template"),
            field_prefix=f"azure_boards.ado_targets[{i}].work_item_template",
        )
        profiles.append(
            AdoTargetProfile(
                organization=org,
                project=proj,
                work_item_type=_optional_trimmed_string(item.get("work_item_type")),
                work_item_state_active=_optional_trimmed_string(
                    item.get("work_item_state_active"),
                ),
                work_item_state_closed=_optional_trimmed_string(
                    item.get("work_item_state_closed"),
                ),
                work_item_description_field=desc_field,
                work_item_template=template,
            ),
        )
    index = AdoTargetIndex.from_profiles(profiles)
    return profiles, index


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

    wit_desc_field = normalize_work_item_description_field(
        defaults_raw.get("work_item_description_field"),
        field_prefix="azure_boards.defaults.work_item_description_field",
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

    area_path_raw = defaults_raw.get("area_path")
    area_path: str | None = None
    if area_path_raw is not None:
        if not isinstance(area_path_raw, str):
            raise ConfigError("azure_boards.defaults.area_path must be a string")
        stripped = area_path_raw.strip()
        area_path = stripped if stripped else None

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
        work_item_description_field=wit_desc_field,
        work_item_description_appendix=appendix,
        work_item_template=dict(wit_tmpl),
        sync_included_snyk_origins=allowlist,
        area_path=area_path,
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

    known_snyk = {"group_id", "api_base_url", "app_base_url"}
    extra = {k: v for k, v in sn_raw.items() if k not in known_snyk}

    gid = str(sn_raw.get("group_id", "") or "").strip()
    api_base_url = _validate_api_base_url(
        sn_raw.get("api_base_url", DEFAULT_API_ORIGIN),
    )
    app_base_url = _validate_app_base_url(
        sn_raw.get("app_base_url", DEFAULT_APP_ORIGIN),
    )

    if "snyk_org_slug" in ab_raw:
        raise ConfigError(
            "azure_boards.snyk_org_slug is not supported; set snyk_org_slug on each "
            "azure_boards.org_mappings[] row. Without org_mappings, group-scoped sync "
            "does not configure an org slug (Snyk UI links in work items may be incomplete).",
        )

    defaults_obj = _parse_azure_boards_defaults(ab_raw)
    org_mappings = _parse_org_mappings(ab_raw)
    ado_targets, ado_target_index = _parse_ado_targets(ab_raw)

    flat = _defaults_to_flat_config(defaults_obj)
    flat.org_mappings = org_mappings
    flat.ado_targets = ado_targets
    flat.ado_target_index = ado_target_index

    repo_csv_raw = ab_raw.get("repo_mapping_csv")
    if repo_csv_raw is not None:
        if not isinstance(repo_csv_raw, str):
            raise ConfigError("azure_boards.repo_mapping_csv must be a string")
        flat.repo_mapping_csv = repo_csv_raw.strip()

    ms_raw = tree.get("mapping_store", DEFAULT_MAPPING_STORE)
    if ms_raw is None or (isinstance(ms_raw, str) and not ms_raw.strip()):
        ms_raw = DEFAULT_MAPPING_STORE
    mapping_store = _normalize_mapping_store(str(ms_raw))

    sp_raw = tree.get("sqlite_path", DEFAULT_SQLITE_PATH)
    if sp_raw is None or (isinstance(sp_raw, str) and not str(sp_raw).strip()):
        sqlite_path = DEFAULT_SQLITE_PATH
    else:
        sqlite_path = str(sp_raw).strip()

    at_ep_raw = tree.get("mapping_store_azure_table_endpoint", "") or ""
    at_name_raw = tree.get("mapping_store_azure_table_name", "") or ""
    azure_ep = str(at_ep_raw).strip()
    azure_name = str(at_name_raw).strip()

    _validate_azure_table_mapping_store_settings(
        mapping_store=mapping_store,
        endpoint=azure_ep,
        table_name=azure_name,
    )

    return AppConfig(
        azure_boards=flat,
        work_item_template=dict(wit),
        snyk=SnykConfig(
            group_id=gid,
            api_base_url=api_base_url,
            app_base_url=app_base_url,
            extra=extra,
        ),
        mapping_store=mapping_store,
        sqlite_path=sqlite_path,
        mapping_store_azure_table_endpoint=azure_ep,
        mapping_store_azure_table_name=azure_name,
    )


def load_app_config(
    *,
    config_path: str | None,
    cli_group_id: str | None = None,
    cli_sqlite_path: str | None = None,
    cli_snyk_api_base_url: str | None = None,
    cli_snyk_app_base_url: str | None = None,
    cli_repo_mapping_csv_path: str | None = None,
) -> AppConfig:
    """
    Load merged configuration: defaults → YAML file (if path) → env → CLI overrides.

    ``cli_group_id`` is the top layer for ``snyk.group_id`` when non-empty.
    ``cli_sqlite_path`` is the top layer for ``sqlite_path`` when non-empty.
    ``cli_snyk_api_base_url`` is the top layer for ``snyk.api_base_url`` when non-empty.
    ``cli_snyk_app_base_url`` is the top layer for ``snyk.app_base_url`` when non-empty.
    ``cli_repo_mapping_csv_path`` is the top layer for ``azure_boards.repo_mapping_csv``
    when non-empty.
    """
    tree = _default_tree()
    path = resolve_config_path(config_path)
    config_file_dir: str | None = None
    if path:
        config_file_dir = str(_canonical_config_path(path).parent)
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
    if cli_snyk_api_base_url is not None and cli_snyk_api_base_url.strip():
        tree.setdefault("snyk", {})
        if not isinstance(tree["snyk"], dict):
            tree["snyk"] = {}
        tree["snyk"]["api_base_url"] = _validate_api_base_url(
            cli_snyk_api_base_url.strip(),
            field_name="--snyk-api-base-url",
        )
    if cli_snyk_app_base_url is not None and cli_snyk_app_base_url.strip():
        tree.setdefault("snyk", {})
        if not isinstance(tree["snyk"], dict):
            tree["snyk"] = {}
        tree["snyk"]["app_base_url"] = _validate_app_base_url(
            cli_snyk_app_base_url.strip(),
            field_name="--snyk-app-base-url",
        )
    if cli_repo_mapping_csv_path is not None and cli_repo_mapping_csv_path.strip():
        tree.setdefault("azure_boards", {})
        if not isinstance(tree["azure_boards"], dict):
            tree["azure_boards"] = {}
        tree["azure_boards"]["repo_mapping_csv"] = cli_repo_mapping_csv_path.strip()
    app = _tree_to_app_config(tree)
    app.config_file_dir = config_file_dir
    return app
