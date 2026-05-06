"""Optional client-side filtering for sync (time bounds, fix availability)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from config.models import ISSUES_SYNC_FROM_HISTORICAL


def issue_created_at_iso(record: Mapping[str, Any]) -> str | None:
    """Return ``created_at`` from a normalized issue record when present."""
    raw = record.get("created_at")
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def issue_passes_sync_from_filter(
    record: Mapping[str, Any],
    *,
    issues_sync_from: str,
) -> bool:
    """
    When ``issues_sync_from`` is ``historical``, include all issues.

    Otherwise ``issues_sync_from`` is a UTC ISO 8601 ``Z`` string; include issues
    whose ``created_at`` is **>=** that instant (client-side bound).
    """
    if not issues_sync_from or issues_sync_from == ISSUES_SYNC_FROM_HISTORICAL:
        return True
    issue_ts = issue_created_at_iso(record)
    if not issue_ts:
        return True
    try:
        bound = datetime.fromisoformat(issues_sync_from.replace("Z", "+00:00"))
        ic = datetime.fromisoformat(issue_ts.replace("Z", "+00:00"))
    except ValueError:
        return True
    if ic.tzinfo is None:
        ic = ic.replace(tzinfo=timezone.utc)
    return ic >= bound.astimezone(timezone.utc)


def attrs_indicate_fix_available(attrs: Mapping[str, Any]) -> bool:
    """True when coordinates suggest an actionable fix (aligned with P2-FR-5.5 signals)."""
    coords = attrs.get("coordinates")
    if not isinstance(coords, list) or not coords:
        return False
    first = coords[0]
    if not isinstance(first, dict):
        return False
    keys = (
        "is_upgradeable",
        "is_patchable",
        "is_fixable_manually",
        "is_fixable_snyk",
        "is_fixable_upstream",
    )
    return any(first.get(k) is True for k in keys)
