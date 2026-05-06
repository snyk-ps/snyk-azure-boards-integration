"""JSON Patch assembly for Azure DevOps work items (sync v1)."""

from __future__ import annotations

import html
from typing import Any, Mapping


def _ado_system_description_html(plain: str) -> str:
    """
    Azure Boards ``System.Description`` is HTML; plain ``\\n`` / ``\\n\\n`` often
    collapse in the web UI. Split on blank lines into paragraphs and use
    ``<br />`` for single line breaks.

    A block that starts with ``Open in Snyk`` and a second line with
    ``https://app.snyk.io/...`` renders the URL as a clickable link.
    """
    if not plain.strip():
        return ""
    blocks = [b.strip() for b in plain.split("\n\n") if b.strip()]
    parts: list[str] = []
    for block in blocks:
        lines = block.split("\n")
        if (
            len(lines) >= 2
            and lines[0].strip() == "Open in Snyk"
            and lines[1].strip().startswith("https://app.snyk.io/")
        ):
            url = lines[1].strip()
            rest = "\n".join(lines[2:]).strip()
            href_esc = html.escape(url, quote=True)
            inner = f'Open in Snyk: <a href="{href_esc}">view in Snyk</a>'
            if rest:
                inner += "<br />" + html.escape(rest, quote=False).replace("\n", "<br />")
            parts.append(f"<p>{inner}</p>")
        else:
            inner = html.escape(block, quote=False).replace("\n", "<br />")
            parts.append(f"<p>{inner}</p>")
    return "".join(parts)


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
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": _ado_system_description_html(description),
        },
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
        {
            "op": "replace",
            "path": "/fields/System.Description",
            "value": _ado_system_description_html(description),
        },
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
