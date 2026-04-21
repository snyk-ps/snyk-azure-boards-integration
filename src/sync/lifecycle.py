"""Snyk issue lifecycle derivation for sync (attributes only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from config.loader import SEVERITY_LEVELS


DERIVED_OPEN: Final = "open"
DERIVED_RESOLVED: Final = "resolved"
DERIVED_IGNORED: Final = "ignored"


@dataclass(frozen=True, slots=True)
class DeriveOutcome:
    """Result of mapping Snyk attributes to a stored ``snyk_status``."""

    status: str


def coerce_ignored(raw: Any) -> bool:
    """Normalize API ``ignored`` to bool."""
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "1", "yes", "on")
    return bool(raw)


def derive_snyk_status(*, status: Any, ignored: Any) -> DeriveOutcome | None:
    """
    Map ``attributes.status`` and ``attributes.ignored`` to derived vocabulary.

    Returns:
        ``DeriveOutcome`` with ``status`` in ``open`` | ``resolved`` | ``ignored``,
        or ``None`` when the issue must be skipped (unexpected ``status``).
    """
    ign = coerce_ignored(ignored)
    if ign:
        return DeriveOutcome(status=DERIVED_IGNORED)

    st = status if isinstance(status, str) else ("" if status is None else str(status))
    st = st.strip()
    if st == "resolved":
        return DeriveOutcome(status=DERIVED_RESOLVED)
    if st == "open":
        return DeriveOutcome(status=DERIVED_OPEN)
    return None


def effective_severity_levels_from_threshold(threshold: str) -> tuple[str, ...]:
    """
    Build ``effective_severity_level`` query values at or above ``threshold``.

    Ordering follows :data:`config.loader.SEVERITY_LEVELS`.
    """
    t = threshold.strip().lower()
    if t not in SEVERITY_LEVELS:
        t = "high"
    idx = SEVERITY_LEVELS.index(t)
    return tuple(SEVERITY_LEVELS[idx:])
