"""Entry point for the CLI."""

from __future__ import annotations

import sys

from commands import build_parser, run_fetch


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch subcommands."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "fetch":
        return run_fetch(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
