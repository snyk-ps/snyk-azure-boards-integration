"""Startup validation for ``sync`` (non-secret config only)."""

from __future__ import annotations

import os

from config.errors import ConfigError
from config.models import AppConfig
from integrations.azure_devops.constants import AZURE_DEVOPS_PAT_ENV


def validate_sync_environment() -> None:
    """Require secrets from the environment (same rules as HTTP clients)."""
    if not os.environ.get("SNYK_TOKEN", "").strip():
        raise ConfigError("SNYK_TOKEN is not set or empty")
    if not os.environ.get(AZURE_DEVOPS_PAT_ENV, "").strip():
        raise ConfigError(f"{AZURE_DEVOPS_PAT_ENV} is not set or empty")


def validate_sync_config(config: AppConfig) -> None:
    """
    Validate merged configuration before a sync run.

    Raises:
        ConfigError: When required routing or work item strings are missing or empty.
    """
    ab = config.azure_boards
    if not ab.organization.strip():
        raise ConfigError(
            "azure_boards.organization is required for sync (non-empty after merge)",
        )
    if not ab.project.strip():
        raise ConfigError(
            "azure_boards.project is required for sync (non-empty after merge)",
        )
    if not config.snyk.group_id.strip():
        raise ConfigError(
            "snyk.group_id is required for sync (non-empty after merge); "
            "see README for SNYK_GROUP_ID / YAML / CLI",
        )
    for label, val in (
        ("azure_boards.work_item_type", ab.work_item_type),
        ("azure_boards.work_item_state_active", ab.work_item_state_active),
        ("azure_boards.work_item_state_closed", ab.work_item_state_closed),
    ):
        if not val.strip():
            raise ConfigError(f"{label} must be non-empty for sync (after merge)")
