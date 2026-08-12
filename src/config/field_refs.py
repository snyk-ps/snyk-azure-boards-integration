"""Azure DevOps work item field reference name helpers."""

from __future__ import annotations

from typing import Any

from config.errors import ConfigError

DESCRIPTION_FIELD_SYSTEM = "System.Description"
DESCRIPTION_FIELD_REPRO_STEPS = "Microsoft.VSTS.TCM.ReproSteps"

AUTO_DESCRIPTION_FIELD_ORDER: tuple[str, ...] = (
    DESCRIPTION_FIELD_SYSTEM,
    DESCRIPTION_FIELD_REPRO_STEPS,
)


def normalize_work_item_description_field(
    raw: Any,
    *,
    field_prefix: str = "azure_boards.defaults.work_item_description_field",
) -> str | None:
    """
    Parse optional description field config.

    Returns:
        ``None`` for auto mode (omit, null, or whitespace-only).
        Non-empty Azure DevOps field reference name otherwise.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ConfigError(f"{field_prefix} must be a string")
    s = raw.strip()
    if not s:
        return None
    if s.startswith("/fields/"):
        s = s[len("/fields/") :].strip()
    if not s:
        return None
    return s
