"""Snyk project origin inclusive allowlist for sync (vs ``sync_included_snyk_origins``)."""

from __future__ import annotations

EXCLUSION_ORIGIN_UNKNOWN = "origin_unknown"
EXCLUSION_ORIGIN_NOT_IN_ALLOWLIST = "origin_not_in_allowlist"


def classify_origin_for_allowlist(
    snyk_project_origin: str,
    allowlist: tuple[str, ...] | None,
) -> tuple[bool, str]:
    """
    Return ``(included, exclusion_reason)``.

    When ``allowlist`` is ``None`` or empty tuple, every origin is **included**
    and ``exclusion_reason`` is empty.

    When allowlisted, **included** iff ``strip(snyk_project_origin)`` equals a token.
    """
    if not allowlist:
        return True, ""
    origin = str(snyk_project_origin or "").strip()
    if not origin:
        return False, EXCLUSION_ORIGIN_UNKNOWN
    if origin in allowlist:
        return True, ""
    return False, EXCLUSION_ORIGIN_NOT_IN_ALLOWLIST
