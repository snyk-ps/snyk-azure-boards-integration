"""Azure DevOps read-only smoke subcommand (argparse wiring)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from config import ConfigError, load_app_config
from integrations.azure_devops.client import WorkItemsClient
from integrations.azure_devops.constants import AZURE_DEVOPS_PAT_ENV
from integrations.azure_devops.errors import AzureDevOpsApiError


def register_azure_devops_smoke_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``azure-devops-smoke`` subcommand on ``subparsers``."""
    p = subparsers.add_parser(
        "azure-devops-smoke",
        help=(
            "Read-only Azure DevOps connectivity check: calls get_work_item once. "
            f"PAT must be supplied via {AZURE_DEVOPS_PAT_ENV} (never as a CLI flag)."
        ),
    )
    p.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help=(
            "Path to YAML configuration (non-secret). "
            "Overrides SNYK_APP_CONFIG when both are set."
        ),
    )
    p.add_argument(
        "--mapping-store-sqlite-path",
        dest="mapping_store_sqlite_path",
        metavar="PATH",
        default=None,
        help=(
            "Override sqlite_path for mapping persistence (CLI wins over env/YAML). "
            "See README; local dev/test only."
        ),
    )
    p.add_argument(
        "--work-item-id",
        dest="work_item_id",
        metavar="ID",
        required=True,
        help="Work item id to fetch (read-only smoke).",
    )


def run_azure_devops_smoke(args: argparse.Namespace) -> int:
    """Execute the Azure DevOps smoke subcommand; return process exit code."""
    try:
        config = load_app_config(
            config_path=args.config,
            cli_sqlite_path=args.mapping_store_sqlite_path,
        )
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    org = config.azure_boards.organization.strip()
    proj = config.azure_boards.project.strip()
    if not org or not proj:
        print(
            "azure_boards.organization and azure_boards.project must be non-empty "
            "after loading configuration (YAML and/or AZURE_BOARDS_ORGANIZATION / "
            "AZURE_BOARDS_PROJECT); see README",
            file=sys.stderr,
        )
        return 2

    if not os.environ.get(AZURE_DEVOPS_PAT_ENV, "").strip():
        print(f"{AZURE_DEVOPS_PAT_ENV} is not set or empty", file=sys.stderr)
        return 1

    client = WorkItemsClient()
    try:
        rec: dict[str, Any] = client.get_work_item(org, proj, args.work_item_id)
    except AzureDevOpsApiError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    print(json.dumps(rec, sort_keys=True))
    return 0
