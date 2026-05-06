"""Derive per-mapping Azure Boards and template settings from ``AppConfig``."""

from __future__ import annotations

from typing import Any, Mapping

from config.policy_parse import (
    coerce_bool,
    normalize_reopen_policy,
    normalize_severity,
    validate_issues_sync_from,
)
from config.errors import ConfigError
from config.models import AppConfig, AzureBoardsConfig, AzureBoardsDefaults, OrgMapping
from config.template_merge import merge_work_item_templates


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
        work_item_description_appendix=appendix,
        work_item_template=dict(wit_tmpl),
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
    )
