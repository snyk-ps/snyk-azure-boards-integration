"""CLI command wiring (argparse) for the application."""

from __future__ import annotations

import argparse

from .azure_devops_smoke import (
    register_azure_devops_smoke_parser,
    run_azure_devops_smoke,
)
from .fetch import register_fetch_parser, run_fetch
from .sync import register_sync_parser, run_sync_command


def build_parser() -> argparse.ArgumentParser:
    """Build the root argument parser."""
    parser = argparse.ArgumentParser(
        description="Snyk — Azure Boards integration.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    register_fetch_parser(sub)
    register_sync_parser(sub)
    register_azure_devops_smoke_parser(sub)
    return parser


def run_command(args: argparse.Namespace) -> int:
    """Dispatch a parsed subcommand."""
    if args.command == "fetch":
        return run_fetch(args)
    if args.command == "sync":
        return run_sync_command(args)
    if args.command == "azure-devops-smoke":
        return run_azure_devops_smoke(args)
    raise RuntimeError(f"unknown command: {args.command!r}")


__all__ = [
    "build_parser",
    "register_sync_parser",
    "run_command",
    "run_fetch",
    "run_sync_command",
]
