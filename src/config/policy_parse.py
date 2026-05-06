"""Parse and validate Azure Boards policy fields shared by loader and sync helpers."""

from __future__ import annotations

import re
from datetime import datetime

from config.errors import ConfigError
from config.models import (
    ISSUES_SYNC_FROM_HISTORICAL,
    REOPEN_POLICY_NEW_WORK_ITEM,
    REOPEN_POLICY_REOPEN_EXISTING,
)

SEVERITY_LEVELS: tuple[str, ...] = ("low", "medium", "high", "critical")

_ALLOWED_REOPEN_POLICIES: frozenset[str] = frozenset(
    {
        REOPEN_POLICY_NEW_WORK_ITEM,
        REOPEN_POLICY_REOPEN_EXISTING,
    },
)

_ISO8601_Z_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$",
)


def coerce_bool(value: object, *, field_name: str) -> bool:
    """Parse YAML/env boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1", "yes", "on"):
            return True
        if v in ("false", "0", "no", "off", ""):
            return False
    raise ConfigError(
        f"{field_name} must be a boolean (got {type(value).__name__})",
    )


def normalize_severity(raw: str, *, field_prefix: str) -> str:
    """Validate severity threshold string."""
    s = raw.strip().lower()
    if s not in SEVERITY_LEVELS:
        allowed = ", ".join(SEVERITY_LEVELS)
        raise ConfigError(
            f"{field_prefix} must be one of: {allowed} (got {raw!r})",
        )
    return s


def validate_issues_sync_from(raw: str) -> str:
    """Return ``historical`` or a validated UTC ISO 8601 ``Z`` timestamp string."""
    s = str(raw or "").strip()
    if not s:
        return ISSUES_SYNC_FROM_HISTORICAL
    if s.lower() == ISSUES_SYNC_FROM_HISTORICAL:
        return ISSUES_SYNC_FROM_HISTORICAL
    if _ISO8601_Z_RE.match(s):
        try:
            datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ConfigError(
                "azure_boards.defaults.issues_sync_from must be "
                f"'{ISSUES_SYNC_FROM_HISTORICAL}' or UTC ISO 8601 ending in Z "
                f"(got {raw!r})",
            ) from exc
        return s
    raise ConfigError(
        "azure_boards.defaults.issues_sync_from must be "
        f"'{ISSUES_SYNC_FROM_HISTORICAL}' or UTC ISO 8601 ending in Z "
        f"(got {raw!r})",
    )


def normalize_reopen_policy(raw: str) -> str:
    """Validate reopen policy enum."""
    s = str(raw or "").strip()
    if s not in _ALLOWED_REOPEN_POLICIES:
        allowed = ", ".join(sorted(_ALLOWED_REOPEN_POLICIES))
        raise ConfigError(
            "azure_boards.defaults.reopen_work_item_policy must be one of: "
            f"{allowed} (got {raw!r})",
        )
    return s
