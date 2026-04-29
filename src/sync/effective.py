"""Derive per-mapping Azure Boards and template settings from ``AppConfig``."""

from __future__ import annotations

from typing import Any, Mapping

from config.models import AppConfig, AzureBoardsConfig, OrgMapping
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
) -> dict[str, Any]:
    """Global template → ``defaults.work_item_template`` → ``overrides.work_item_template``."""
    o = dict(overrides or {})
    raw = o.get("work_item_template")
    override_tpl = raw if isinstance(raw, dict) else {}
    return merge_work_item_templates(
        app.work_item_template,
        app.azure_boards.defaults.work_item_template,
        override_tpl,
    )


def boards_for_org_mapping(app: AppConfig, m: OrgMapping) -> AzureBoardsConfig:
    """AzureBoardsConfig scoped to one org mapping row (ADO routing + effective strings)."""
    wt, wa, wc = effective_work_item_strings(app.azure_boards, m.overrides)
    return AzureBoardsConfig(
        create_new_work_items=app.azure_boards.create_new_work_items,
        organization=m.organization,
        project=m.project,
        work_item_type=wt,
        work_item_state_active=wa,
        work_item_state_closed=wc,
        defaults=app.azure_boards.defaults,
        org_mappings=[],
    )
