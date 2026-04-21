"""JSON Patch assembly for Azure DevOps work items (sync v1)."""

from __future__ import annotations

from typing import Any, Mapping


def _normalize_tags(template: Mapping[str, Any]) -> list[str]:
    raw = template.get("tags")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif item is not None:
            s = str(item).strip()
            if s:
                out.append(s)
    return out


def _normalize_json_patch(template: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = template.get("json_patch")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and "op" in item and "path" in item:
            out.append(dict(item))
    return out


def template_supplies_assigned_to(template: Mapping[str, Any]) -> bool:
    """True if ``json_patch`` includes an operation targeting ``System.AssignedTo``."""
    for op in _normalize_json_patch(template):
        path = str(op.get("path", ""))
        if "System.AssignedTo" in path:
            return True
    return False


def build_create_patch(
    *,
    title: str,
    description: str,
    active_state: str,
    template: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """
    JSON Patch for ``POST`` work item create.

    Built-in fields first, then ``tags``, then ``json_patch`` (template may override paths).
    """
    ops: list[dict[str, Any]] = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description},
        {"op": "add", "path": "/fields/System.State", "value": active_state},
    ]
    tags = _normalize_tags(template)
    if tags:
        ops.append(
            {
                "op": "add",
                "path": "/fields/System.Tags",
                "value": "; ".join(tags),
            },
        )
    ops.extend(_normalize_json_patch(template))
    return filter_assignee_from_create_patch(
        ops,
        template_supplies_assignee=template_supplies_assigned_to(template),
    )


def build_update_patch(
    *,
    title: str,
    description: str,
    state: str,
    template: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """JSON Patch for ``PATCH`` update (replace built-ins, tags, then template ops)."""
    ops: list[dict[str, Any]] = [
        {"op": "replace", "path": "/fields/System.Title", "value": title},
        {"op": "replace", "path": "/fields/System.Description", "value": description},
        {"op": "replace", "path": "/fields/System.State", "value": state},
    ]
    tags = _normalize_tags(template)
    if tags:
        ops.append(
            {
                "op": "replace",
                "path": "/fields/System.Tags",
                "value": "; ".join(tags),
            },
        )
    ops.extend(_normalize_json_patch(template))
    return ops


def filter_assignee_from_create_patch(
    ops: list[dict[str, Any]],
    *,
    template_supplies_assignee: bool,
) -> list[dict[str, Any]]:
    """Drop ``System.AssignedTo`` ops unless the operator template supplies assignee."""
    if template_supplies_assignee:
        return ops
    return [
        op
        for op in ops
        if "System.AssignedTo" not in str(op.get("path", ""))
    ]
