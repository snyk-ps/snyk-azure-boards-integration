"""Sync subcommand: argparse wiring and dependency construction."""

from __future__ import annotations

import argparse
import logging
import sys

from config import ConfigError, load_app_config
from integrations.azure_devops.constants import AZURE_DEVOPS_PAT_ENV
from integrations.azure_devops.client import WorkItemsClient
from mapping_store import create_mapping_store
from snyk.client import IssuesClient
from sync.run import run_sync


def register_sync_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the ``sync`` subcommand on ``subparsers``."""
    sync = subparsers.add_parser(
        "sync",
        help=(
            "Synchronize Snyk group issues with Azure Boards (uses SNYK_TOKEN and "
            f"{AZURE_DEVOPS_PAT_ENV})."
        ),
    )
    sync.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to YAML configuration (non-secret). Overrides SNYK_APP_CONFIG when set.",
    )
    sync.add_argument(
        "--mapping-store-sqlite-path",
        dest="mapping_store_sqlite_path",
        metavar="PATH",
        default=None,
        help="Override sqlite_path for mapping persistence (CLI wins over env/YAML).",
    )
    sync.add_argument(
        "--group-id",
        dest="group_id_flag",
        metavar="UUID",
        default=None,
        help="Override snyk.group_id for this run (CLI highest precedence for group id).",
    )


def run_sync_command(args: argparse.Namespace) -> int:
    """Execute the sync subcommand; return process exit code."""
    try:
        config = load_app_config(
            config_path=args.config,
            cli_group_id=args.group_id_flag,
            cli_sqlite_path=args.mapping_store_sqlite_path,
        )
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        store = create_mapping_store(config)
        issues_client = IssuesClient()
        wit_client = WorkItemsClient()
        run_sync(
            config=config,
            issues_client=issues_client,
            wit_client=wit_client,
            store=store,
        )
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    return 0
