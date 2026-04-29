"""Merge ``work_item_template`` mappings from global config, defaults, and overrides."""

from __future__ import annotations

from typing import Any, Mapping


def _normalize_tags(raw: Any) -> list[str]:
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


def _normalize_json_patch(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and "op" in item and "path" in item:
            out.append(dict(item))
    return out


def merge_work_item_templates(
    global_template: Mapping[str, Any],
    defaults_template: Mapping[str, Any],
    overrides_template: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Merge template dicts: ``json_patch`` lists concatenate in order (global, defaults,
    overrides). ``tags`` concatenate then dedupe preserving order. Other keys: last wins.
    """
    tags_acc: list[str] = []
    patches: list[dict[str, Any]] = []
    other: dict[str, Any] = {}

    for part in (global_template, defaults_template, overrides_template):
        if not part:
            continue
        tags_acc.extend(_normalize_tags(part.get("tags")))
        patches.extend(_normalize_json_patch(part.get("json_patch")))
        for k, v in part.items():
            if k in ("tags", "json_patch"):
                continue
            other[k] = v

    out: dict[str, Any] = dict(other)
    if tags_acc:
        seen: set[str] = set()
        uniq: list[str] = []
        for t in tags_acc:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        out["tags"] = uniq
    if patches:
        out["json_patch"] = patches
    return out
