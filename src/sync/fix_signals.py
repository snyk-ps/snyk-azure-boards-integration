"""Fix-availability signals read from Snyk issue ``coordinates[]`` (P2-FR-5.5)."""

from __future__ import annotations

from typing import Any, Mapping

# Boolean fix signals defined by P2-FR-5.5, in display order. ``is_pinnable`` is
# deliberately absent: pin semantics do not imply an actionable upgrade path.
FIX_SIGNAL_LABELS: dict[str, str] = {
    "is_upgradeable": "Upgrade available",
    "is_patchable": "Patch available",
    "is_fixable_manually": "Manual remediation possible",
    "is_fixable_snyk": "Automated fix available via Snyk",
    "is_fixable_upstream": "Upstream fix published",
}

FIX_SIGNAL_KEYS: tuple[str, ...] = tuple(FIX_SIGNAL_LABELS)


def true_fix_signal_keys(attrs: Mapping[str, Any]) -> list[str]:
    """Fix-signal keys set to ``True`` on any ``coordinates[]`` entry.

    Every coordinate is inspected rather than only the first: a Snyk issue
    reachable by several introduction paths may carry the actionable signal on
    any one of them, and API ordering does not guarantee it comes first.

    Args:
        attrs: Issue attributes holding an optional ``coordinates`` list.

    Returns:
        Unique keys from :data:`FIX_SIGNAL_KEYS` that are ``True`` on at least
        one coordinate, in :data:`FIX_SIGNAL_LABELS` declaration order. Empty
        when ``coordinates`` is absent, is not a list, is empty, or carries no
        true signal. Entries that are not objects are skipped.
    """
    coords = attrs.get("coordinates")
    if not isinstance(coords, list):
        return []
    found = {
        key
        for coord in coords
        if isinstance(coord, dict)
        for key in FIX_SIGNAL_KEYS
        if coord.get(key) is True
    }
    return [key for key in FIX_SIGNAL_KEYS if key in found]
