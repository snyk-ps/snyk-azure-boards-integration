"""Fetch subcommand: argparse wiring for Snyk group issues list/get."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from config import ConfigError, load_app_config
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
        help=(
            "Fetch issues from the Snyk REST API (smoke test; uses SNYK_TOKEN). "
            "Group id: YAML/env (see README), --group-id, or positional (see below)."
        ),
    )
    fetch.add_argument(
        "action",
        choices=["list", "get"],
        help="List issues in a group or retrieve a single issue by id.",
    )
    fetch.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help=(
            "Path to YAML configuration (non-secret). "
            "Overrides SNYK_APP_CONFIG when both are set."
        ),
    )
    fetch.add_argument(
        "--group-id",
        dest="group_id_flag",
        metavar="UUID",
        default=None,
        help=(
            "Snyk group id (CLI override). For list, optional if set in config/env. "
            "For get with one argument, supplies group when not using two-arg form."
        ),
    )
    fetch.add_argument(
        "tail",
        nargs="*",
        metavar="ARG",
        help=(
            "list: optional group id (overrides --group-id). "
            "get: issue_id OR group_id issue_id (two-arg form overrides --group-id)."
        ),
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


def _parse_fetch_tail(action: str, tail: list[str]) -> tuple[str | None, str | None]:
    """
    Parse positional tail after action.

    Returns (positional_group_id, issue_id). issue_id is only for get.
    """
    if action == "list":
        if len(tail) > 1:
            raise ValueError("fetch list takes at most one optional group id")
        if len(tail) == 1:
            return tail[0].strip(), None
        return None, None
    if action == "get":
        if len(tail) == 1:
            return None, tail[0].strip()
        if len(tail) == 2:
            return tail[0].strip(), tail[1].strip()
        raise ValueError(
            "fetch get requires one argument (issue_id) or two (group_id issue_id)",
        )
    raise ValueError(f"unknown action {action!r}")


def _cli_group_id_for_merge(
    action: str,
    pos_group: str | None,
    issue_id: str | None,
    group_id_flag: str | None,
) -> str | None:
    """Effective CLI layer value for snyk.group_id (None = do not override from CLI)."""
    if action == "list":
        if pos_group:
            return pos_group
        if group_id_flag and group_id_flag.strip():
            return group_id_flag.strip()
        return None
    # get
    if pos_group:
        return pos_group
    if issue_id and group_id_flag and group_id_flag.strip():
        return group_id_flag.strip()
    return None


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
    try:
        pos_group, issue_id = _parse_fetch_tail(args.action, list(args.tail))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    cli_gid = _cli_group_id_for_merge(
        args.action,
        pos_group,
        issue_id,
        args.group_id_flag,
    )

    try:
        config = load_app_config(
            config_path=args.config,
            cli_group_id=cli_gid,
        )
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    group_id = config.snyk.group_id.strip()
    if not group_id:
        print(
            "group id is required: set snyk.group_id in config, SNYK_GROUP_ID, "
            "or pass --group-id / positional (see README)",
            file=sys.stderr,
        )
        return 2

    if not os.environ.get("SNYK_TOKEN", "").strip():
        print("SNYK_TOKEN is not set or empty", file=sys.stderr)
        return 1

    client = IssuesClient()
    try:
        if args.action == "list":
            params = _list_params_from_args(args)
            for rec in client.iter_group_issues(group_id, list_params=params):
                print(json.dumps(rec, sort_keys=True))
        else:
            assert issue_id is not None
            rec: dict[str, Any] = client.get_group_issue(group_id, issue_id)
            print(json.dumps(rec, sort_keys=True))
    except SnykApiError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 0
