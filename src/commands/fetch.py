"""Fetch subcommand: argparse wiring for Snyk group issues list/get."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from snyk.client import GroupIssueListParams, IssuesClient
from snyk.errors import SnykApiError


def build_parser() -> argparse.ArgumentParser:
    """Build the root argument parser."""
    parser = argparse.ArgumentParser(
        description="Snyk — Azure Boards integration.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser(
        "fetch",
        help="Fetch issues from the Snyk REST API (smoke test; uses SNYK_TOKEN).",
    )
    fetch.add_argument(
        "action",
        choices=["list", "get"],
        help="List issues in a group or retrieve a single issue by id.",
    )
    fetch.add_argument(
        "group_id",
        help="Group ID (UUID).",
    )
    fetch.add_argument(
        "issue_id",
        nargs="?",
        help="Issue id (required when action is get).",
    )
    fetch.add_argument(
        "--severity",
        action="append",
        dest="severities",
        metavar="LEVEL",
        help=(
            "Effective severity filter (repeatable). "
            "Default when omitted: high and critical."
        ),
    )
    fetch.add_argument(
        "--type",
        dest="issue_type",
        metavar="TYPE",
        default=None,
        help="Optional issue type filter (Snyk API).",
    )
    fetch.add_argument(
        "--status",
        dest="status",
        metavar="STATUS",
        default=None,
        help="Optional status filter (Snyk API).",
    )
    return parser


def _list_params_from_args(args: argparse.Namespace) -> GroupIssueListParams:
    """Build list parameters from CLI args."""
    sev: tuple[str, ...] | None
    if args.severities is None:
        sev = None
    else:
        sev = tuple(str(s).strip() for s in args.severities if str(s).strip())
    return GroupIssueListParams(
        effective_severity_levels=sev,
        issue_type=args.issue_type,
        status=args.status,
    )


def run_fetch(args: argparse.Namespace) -> int:
    """Execute the fetch subcommand; return process exit code."""
    if not os.environ.get("SNYK_TOKEN", "").strip():
        print("SNYK_TOKEN is not set or empty", file=sys.stderr)
        return 1
    if args.action == "get" and not args.issue_id:
        print("fetch get requires issue_id", file=sys.stderr)
        return 2

    client = IssuesClient()
    try:
        if args.action == "list":
            params = _list_params_from_args(args)
            for rec in client.iter_group_issues(args.group_id, list_params=params):
                print(json.dumps(rec, sort_keys=True))
        else:
            rec: dict[str, Any] = client.get_group_issue(
                args.group_id,
                args.issue_id or "",
            )
            print(json.dumps(rec, sort_keys=True))
    except SnykApiError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 0
