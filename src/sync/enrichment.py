"""Merge GET issue responses when list payloads omit description or remedies."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from snyk.client import IssuesClient
from snyk.errors import SnykApiError


def _coordinates_have_remedies(coords: Any) -> bool:
    if not isinstance(coords, list):
        return False
    for c in coords:
        if isinstance(c, dict) and c.get("remedies"):
            return True
    return False


def needs_issue_detail(attrs: Mapping[str, Any]) -> bool:
    """
    True when a GET-by-id call may supply ``description`` or ``coordinates[].remedies``.

    If both a non-empty description and coordinates with remedies exist, returns False.
    """
    has_desc = bool(str(attrs.get("description") or "").strip())
    has_rem = _coordinates_have_remedies(attrs.get("coordinates"))
    return not (has_desc and has_rem)


def merge_issue_attributes(
    list_attrs: dict[str, Any],
    get_attrs: dict[str, Any],
) -> dict[str, Any]:
    """Overlay GET attributes onto list attributes for missing description/remedies."""
    out = dict(list_attrs)
    if not str(out.get("description") or "").strip() and get_attrs.get("description"):
        out["description"] = get_attrs["description"]
    if not _coordinates_have_remedies(out.get("coordinates")):
        if _coordinates_have_remedies(get_attrs.get("coordinates")):
            out["coordinates"] = get_attrs["coordinates"]
        elif isinstance(get_attrs.get("coordinates"), list):
            out["coordinates"] = get_attrs["coordinates"]
    return out


def _issue_attrs(rec: Mapping[str, Any]) -> dict[str, Any]:
    raw = rec.get("issue_attributes")
    return dict(raw) if isinstance(raw, dict) else {}


def enrich_issue_record(
    client: IssuesClient,
    rec: dict[str, Any],
    *,
    use_org_scope: bool,
    snyk_org_id: str | None,
    snyk_group_id: str,
    log: logging.Logger,
) -> dict[str, Any]:
    """
    Optionally GET a single issue and merge attributes into ``rec``.

    On API failure, returns ``rec`` unchanged and logs a warning (per-issue soft failure).
    """
    attrs = _issue_attrs(rec)
    if not needs_issue_detail(attrs):
        return rec
    rest_id = str(rec.get("rest_issue_id") or "").strip()
    if not rest_id:
        return rec
    try:
        if use_org_scope and snyk_org_id and snyk_org_id.strip():
            detail = client.get_org_issue(snyk_org_id.strip(), rest_id)
        else:
            detail = client.get_group_issue(snyk_group_id.strip(), rest_id)
    except SnykApiError as exc:
        log.warning(
            "issue detail GET failed issue_id=%s: %s",
            rec.get("issue_id"),
            exc,
        )
        return rec
    merged = merge_issue_attributes(attrs, _issue_attrs(detail))
    out = dict(rec)
    out["issue_attributes"] = merged
    return out
