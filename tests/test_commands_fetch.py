"""Tests for ``commands.fetch`` wiring."""

from commands import build_parser


def test_fetch_parser_list_positional() -> None:
    p = build_parser()
    args = p.parse_args(["fetch", "list", "11111111-1111-1111-1111-111111111111"])
    assert args.command == "fetch"
    assert args.action == "list"
    assert args.tail == ["11111111-1111-1111-1111-111111111111"]


def test_fetch_parser_accepts_org_id() -> None:
    p = build_parser()
    args = p.parse_args(
        [
            "fetch",
            "list",
            "--org-id",
            "22222222-2222-2222-2222-222222222222",
        ]
    )
    assert args.command == "fetch"
    assert args.org_id_flag == "22222222-2222-2222-2222-222222222222"


def test_fetch_parser_optional_filters() -> None:
    p = build_parser()
    args = p.parse_args(
        [
            "fetch",
            "list",
            "g1",
            "--severity",
            "medium",
            "--type",
            "package_vulnerability",
            "--status",
            "open",
        ]
    )
    assert args.severities == ["medium"]
    assert args.issue_type == "package_vulnerability"
    assert args.status == "open"
