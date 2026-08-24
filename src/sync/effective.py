"""Derive per-mapping Azure Boards and template settings from ``AppConfig``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from config.field_refs import normalize_work_item_description_field
from config.policy_parse import (
    coerce_bool,
    normalize_reopen_policy,
    normalize_severity,
    validate_issues_sync_from,
)
from config.errors import ConfigError
from config.models import (
    AdoTargetIndex,
    AdoTargetProfile,
    AppConfig,
    AzureBoardsConfig,
    AzureBoardsDefaults,
    OrgMapping,
)
from config.snyk_origins import parse_sync_included_snyk_origins
from config.template_merge import merge_work_item_templates
from sync.repo_mapping import RepoMappingMatch


def effective_work_item_strings(
    ab: AzureBoardsConfig,
    overrides: Mapping[str, Any] | None,
) -> tuple[str, str, str]:
    """Merge ``azure_boards.defaults`` with optional per-mapping ``overrides``."""
    o = dict(overrides or {})
    d = ab.defaults
    wt = o.get("work_item_type", d.work_item_type)
    active = o.get("work_item_state_active", d.work_item_state_active)
    closed = o.get("work_item_state_closed", d.work_item_state_closed)
    return (
        str(wt or d.work_item_type).strip(),
        str(active or d.work_item_state_active).strip(),
        str(closed or d.work_item_state_closed).strip(),
    )


def effective_snyk_org_slug(_app: AppConfig, mapping: OrgMapping | None) -> str:
    """
    Human-readable Snyk org slug for ``app.snyk.io`` URLs.

    Only ``azure_boards.org_mappings[]`` rows carry a slug. Group-scoped sync
    (no ``org_mappings``) passes an empty slug until a dedicated configuration
    exists; links in work items may be incomplete.
    """
    if mapping is not None:
        return mapping.snyk_org_slug.strip()
    return ""


def _merged_defaults_with_overrides(
    base: AzureBoardsDefaults,
    overrides: Mapping[str, Any],
    *,
    row_organization: str,
    row_project: str,
) -> AzureBoardsDefaults:
    """
    Apply ``org_mappings[].overrides`` onto ``azure_boards.defaults`` (policy fields only).

    ``overrides.work_item_template`` is **not** merged here; it is applied only in
    :func:`effective_work_item_template` so ``json_patch`` / ``tags`` appear once.
    """
    o = dict(overrides)

    org = str(o.get("organization", row_organization) or "").strip()
    proj = str(o.get("project", row_project) or "").strip()

    create_new = base.create_new_work_items
    if "create_new_work_items" in o:
        create_new = coerce_bool(
            o["create_new_work_items"],
            field_name="org_mappings[].overrides.create_new_work_items",
        )

    sev = base.severity_threshold
    if "severity_threshold" in o:
        sev = normalize_severity(
            str(o["severity_threshold"] or "high"),
            field_prefix="org_mappings[].overrides.severity_threshold",
        )

    issues_from = base.issues_sync_from
    if "issues_sync_from" in o:
        issues_from = validate_issues_sync_from(str(o["issues_sync_from"] or ""))

    fix_only = base.create_only_when_fix_available
    if "create_only_when_fix_available" in o:
        fix_only = coerce_bool(
            o["create_only_when_fix_available"],
            field_name="org_mappings[].overrides.create_only_when_fix_available",
        )

    reopen = base.reopen_work_item_policy
    if "reopen_work_item_policy" in o:
        reopen = normalize_reopen_policy(str(o["reopen_work_item_policy"] or ""))

    wit_type = str(o.get("work_item_type", base.work_item_type) or base.work_item_type)
    wit_active = str(
        o.get("work_item_state_active", base.work_item_state_active)
        or base.work_item_state_active,
    )
    wit_closed = str(
        o.get("work_item_state_closed", base.work_item_state_closed)
        or base.work_item_state_closed,
    )

    appendix = base.work_item_description_appendix
    if "work_item_description_appendix" in o:
        raw_ap = o["work_item_description_appendix"]
        if raw_ap is not None and not isinstance(raw_ap, str):
            raise ConfigError(
                "org_mappings[].overrides.work_item_description_appendix must be a string",
            )
        appendix = str(raw_ap or "")

    desc_field = base.work_item_description_field
    if "work_item_description_field" in o:
        desc_field = normalize_work_item_description_field(
            o["work_item_description_field"],
            field_prefix="org_mappings[].overrides.work_item_description_field",
        )

    if "sync_included_snyk_origins" in o:
        allowlist = parse_sync_included_snyk_origins(
            o["sync_included_snyk_origins"],
            field_prefix="org_mappings[].overrides.sync_included_snyk_origins",
        )
    else:
        allowlist = base.sync_included_snyk_origins

    area_path = base.area_path
    if "area_path" in o:
        raw_ap = o["area_path"]
        if raw_ap is not None and not isinstance(raw_ap, str):
            raise ConfigError("org_mappings[].overrides.area_path must be a string")
        stripped = str(raw_ap or "").strip()
        area_path = stripped if stripped else None

    wit_tmpl = dict(base.work_item_template)

    return AzureBoardsDefaults(
        organization=org,
        project=proj,
        create_new_work_items=create_new,
        severity_threshold=sev,
        issues_sync_from=issues_from,
        create_only_when_fix_available=fix_only,
        reopen_work_item_policy=reopen,
        work_item_type=str(wit_type).strip() or base.work_item_type,
        work_item_state_active=str(wit_active).strip() or base.work_item_state_active,
        work_item_state_closed=str(wit_closed).strip() or base.work_item_state_closed,
        work_item_description_field=desc_field,
        work_item_description_appendix=appendix,
        work_item_template=dict(wit_tmpl),
        sync_included_snyk_origins=allowlist,
        area_path=area_path,
    )


def effective_work_item_template(
    app: AppConfig,
    overrides: Mapping[str, Any] | None,
    *,
    boards: AzureBoardsConfig | None = None,
) -> dict[str, Any]:
    """
    Merge work item template from config: global → file ``defaults.work_item_template``
    → optional ``overrides.work_item_template``.

    Per-row ``work_item_template`` is **not** folded into ``boards.defaults`` in
    :func:`boards_for_org_mapping` (avoids duplicating ``json_patch`` with this step).
    """
    o = dict(overrides or {})
    raw = o.get("work_item_template")
    override_tpl = raw if isinstance(raw, dict) else {}
    mid = (boards or app.azure_boards).defaults.work_item_template
    return merge_work_item_templates(
        app.work_item_template,
        mid,
        override_tpl,
    )


@dataclass(frozen=True)
class EffectiveWorkItemConfig:
    """Per-issue work item taxonomy after routing and precedence resolution."""

    work_item_type: str
    work_item_state_active: str
    work_item_state_closed: str
    work_item_description_field: str | None
    template: dict[str, Any]
    work_item_config_source: str


def _org_mapping_matches_target(
    org_mapping: OrgMapping | None,
    *,
    organization: str,
    project: str,
) -> bool:
    if org_mapping is None:
        return False
    return (
        org_mapping.organization.strip() == organization.strip()
        and org_mapping.project.strip() == project.strip()
    )


def _resolve_string_field(
    *,
    csv_value: str | None,
    ado_value: str | None,
    org_override_value: str | None,
    default_value: str,
    org_override_applies: bool,
) -> tuple[str, str | None]:
    """Resolve one string field; return ``(value, source)``."""
    if csv_value:
        return csv_value, "csv"
    if ado_value:
        return ado_value, "ado_target"
    if org_override_applies and org_override_value:
        return org_override_value, "org_override"
    return default_value, "defaults"


def _resolve_description_field(
    *,
    csv_value: str | None,
    ado_profile: AdoTargetProfile | None,
    org_mapping: OrgMapping | None,
    defaults: AzureBoardsDefaults,
    org_override_applies: bool,
) -> tuple[str | None, str | None]:
    if csv_value:
        return normalize_work_item_description_field(
            csv_value,
            field_prefix="repo-mapping.csv Description Field (Optional)",
        ), "csv"
    if ado_profile is not None and ado_profile.work_item_description_field is not None:
        return ado_profile.work_item_description_field, "ado_target"
    if org_override_applies and org_mapping is not None:
        raw = org_mapping.overrides.get("work_item_description_field")
        if raw is not None and str(raw).strip():
            return normalize_work_item_description_field(
                raw,
                field_prefix="org_mappings[].overrides.work_item_description_field",
            ), "org_override"
    return defaults.work_item_description_field, "defaults"


def _merge_effective_template(
    app: AppConfig,
    *,
    boards: AzureBoardsConfig,
    ado_profile: AdoTargetProfile | None,
    org_mapping: OrgMapping | None,
    org_override_applies: bool,
    csv_tags: tuple[str, ...],
) -> dict[str, Any]:
    """Build effective template: global → defaults → ado_target or org override → CSV tags."""
    base = merge_work_item_templates(
        app.work_item_template,
        boards.defaults.work_item_template,
        {},
    )
    if ado_profile is not None and ado_profile.work_item_template:
        base = merge_work_item_templates(base, {}, ado_profile.work_item_template)
    elif org_override_applies and org_mapping is not None:
        raw = org_mapping.overrides.get("work_item_template")
        override_tpl = raw if isinstance(raw, dict) else {}
        base = merge_work_item_templates(base, {}, override_tpl)
    if csv_tags:
        tag_dict = {"tags": list(csv_tags)}
        base = merge_work_item_templates(base, {}, tag_dict)
    return base


def resolve_effective_work_item_config(
    *,
    app: AppConfig,
    boards: AzureBoardsConfig,
    org_mapping: OrgMapping | None,
    ado_target_index: AdoTargetIndex,
    effective_organization: str,
    effective_project: str,
    csv_match: RepoMappingMatch | None,
) -> EffectiveWorkItemConfig:
    """
    Resolve per-issue work item taxonomy after ADO target is known.

    Precedence per field: CSV (non-empty) → ``ado_targets`` → org override (same
    target) → ``defaults``.
    """
    defaults = boards.defaults
    ado_profile = ado_target_index.lookup(effective_organization, effective_project)
    org_override_applies = _org_mapping_matches_target(
        org_mapping,
        organization=effective_organization,
        project=effective_project,
    )
    overrides = org_mapping.overrides if org_mapping is not None else {}

    csv_type = csv_match.work_item_type if csv_match else None
    csv_active = csv_match.work_item_state_active if csv_match else None
    csv_closed = csv_match.work_item_state_closed if csv_match else None
    csv_desc = csv_match.work_item_description_field if csv_match else None
    csv_tags = csv_match.csv_tags if csv_match else ()

    wit_type, type_src = _resolve_string_field(
        csv_value=csv_type,
        ado_value=ado_profile.work_item_type if ado_profile else None,
        org_override_value=str(overrides.get("work_item_type", "") or "").strip() or None,
        default_value=defaults.work_item_type,
        org_override_applies=org_override_applies,
    )
    wit_active, active_src = _resolve_string_field(
        csv_value=csv_active,
        ado_value=ado_profile.work_item_state_active if ado_profile else None,
        org_override_value=(
            str(overrides.get("work_item_state_active", "") or "").strip() or None
        ),
        default_value=defaults.work_item_state_active,
        org_override_applies=org_override_applies,
    )
    wit_closed, closed_src = _resolve_string_field(
        csv_value=csv_closed,
        ado_value=ado_profile.work_item_state_closed if ado_profile else None,
        org_override_value=(
            str(overrides.get("work_item_state_closed", "") or "").strip() or None
        ),
        default_value=defaults.work_item_state_closed,
        org_override_applies=org_override_applies,
    )
    desc_field, desc_src = _resolve_description_field(
        csv_value=csv_desc,
        ado_profile=ado_profile,
        org_mapping=org_mapping,
        defaults=defaults,
        org_override_applies=org_override_applies,
    )
    template = _merge_effective_template(
        app,
        boards=boards,
        ado_profile=ado_profile,
        org_mapping=org_mapping,
        org_override_applies=org_override_applies,
        csv_tags=csv_tags,
    )

    sources = {type_src, active_src, closed_src, desc_src}
    if csv_tags:
        sources.add("csv")
    if "csv" in sources:
        config_source = "csv"
    elif "ado_target" in sources:
        config_source = "ado_target"
    elif "org_override" in sources:
        config_source = "org_override"
    else:
        config_source = "defaults"

    return EffectiveWorkItemConfig(
        work_item_type=wit_type,
        work_item_state_active=wit_active,
        work_item_state_closed=wit_closed,
        work_item_description_field=desc_field,
        template=template,
        work_item_config_source=config_source,
    )


def boards_for_org_mapping(app: AppConfig, m: OrgMapping) -> AzureBoardsConfig:
    """Effective Azure Boards policy for one ``org_mappings`` row."""
    merged_defaults = _merged_defaults_with_overrides(
        app.azure_boards.defaults,
        m.overrides,
        row_organization=m.organization,
        row_project=m.project,
    )
    return AzureBoardsConfig(
        create_new_work_items=merged_defaults.create_new_work_items,
        organization=merged_defaults.organization,
        project=merged_defaults.project,
        severity_threshold=merged_defaults.severity_threshold,
        issues_sync_from=merged_defaults.issues_sync_from,
        create_only_when_fix_available=merged_defaults.create_only_when_fix_available,
        reopen_work_item_policy=merged_defaults.reopen_work_item_policy,
        work_item_type=merged_defaults.work_item_type,
        work_item_state_active=merged_defaults.work_item_state_active,
        work_item_state_closed=merged_defaults.work_item_state_closed,
        defaults=merged_defaults,
        org_mappings=[],
        sync_included_snyk_origins=merged_defaults.sync_included_snyk_origins,
    )
