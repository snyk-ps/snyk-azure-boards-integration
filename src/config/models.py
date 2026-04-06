"""Resolved application configuration (YAML + defaults + env + CLI layers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AzureBoardsConfig:
    """Azure Boards-related settings."""

    create_new_work_items: bool = True


@dataclass
class SnykConfig:
    """Snyk integration settings (non-secret)."""

    group_id: str = ""
    severity_threshold: str = "high"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AppConfig:
    """Full application configuration after merge."""

    azure_boards: AzureBoardsConfig
    work_item_template: dict[str, Any]
    snyk: SnykConfig
