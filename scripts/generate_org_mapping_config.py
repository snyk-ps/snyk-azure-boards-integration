#!/usr/bin/env python3
"""CLI: CSV + Snyk group org list → starter YAML with ``org_mappings`` resolved.

Run from the repository root, for example::

    SNYK_TOKEN=... uv run python scripts/generate_org_mapping_config.py \\
      --input data/orgs.csv --group-id <uuid>

See ``org_config_generator.core`` module docstring for API version and matching rules.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _repo_src() -> Path:
    return Path(__file__).resolve().parent.parent / "src"


def _bootstrap_path() -> None:
    src = _repo_src()
    if src.is_dir():
        sys.path.insert(0, str(src))


def main(argv: list[str] | None = None) -> int:
    """Parse CLI, resolve orgs, write YAML; return process exit code."""
    _bootstrap_path()

    from org_config_generator.core import (
        DEFAULT_ORG_LIST_VERSION,
        CsvValidationError,
        OrgResolutionError,
        OrgConfigGeneratorError,
        SnykOrgApiError,
        fetch_group_orgs,
        parse_csv_rows,
        render_config_yaml,
        resolve_mappings,
        write_atomic,
    )
    from snyk.constants import DEFAULT_BASE_URL
    from snyk.urls import resolve_snyk_rest_base

    parser = argparse.ArgumentParser(
        description=(
            "Build a starter config YAML with azure_boards.org_mappings from a CSV "
            "(ado_organization, ado_project, snyk_org_name) and the Snyk group org list API."
        ),
        epilog=(
            "Authentication: set SNYK_TOKEN in the environment (never pass tokens on the CLI).\n"
            "Default --output is data/config.yaml in the current working directory; "
            "that path is overwritten if it already exists.\n"
            "API reference: https://apidocs.snyk.io/?version=2024-03-12#get-/groups/-group_id-/orgs"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--input",
        metavar="PATH",
        required=True,
        help="CSV path with headers ado_organization, ado_project, snyk_org_name.",
    )
    parser.add_argument(
        "--group-id",
        metavar="UUID",
        required=True,
        help="Snyk Group UUID (also written to snyk.group_id in the output YAML).",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default="data/config.yaml",
        help="Output YAML path (default: data/config.yaml).",
    )
    parser.add_argument(
        "--base-url",
        metavar="URL",
        default=None,
        help=(
            f"Snyk REST base URL or API origin (default: SNYK_API_BASE_URL if set, "
            f"else {DEFAULT_BASE_URL})."
        ),
    )
    parser.add_argument(
        "--api-version",
        metavar="DATE",
        default=DEFAULT_ORG_LIST_VERSION,
        help=f"Snyk REST version query param for org list (default: {DEFAULT_ORG_LIST_VERSION}).",
    )
    args = parser.parse_args(argv)

    in_path = Path(args.input)
    out_path = Path(args.output)

    if args.base_url is not None and str(args.base_url).strip():
        rest_base = resolve_snyk_rest_base(str(args.base_url).strip())
    else:
        env_base = os.environ.get("SNYK_API_BASE_URL", "").strip()
        rest_base = resolve_snyk_rest_base(env_base) if env_base else DEFAULT_BASE_URL

    try:
        rows = parse_csv_rows(in_path)
        orgs = fetch_group_orgs(
            rest_base,
            args.group_id.strip(),
            args.api_version.strip(),
        )
        mappings = resolve_mappings(rows, orgs)
        yaml_text = render_config_yaml(args.group_id.strip(), mappings)
        write_atomic(out_path, yaml_text)
    except CsvValidationError as exc:
        print(f"generate-org-mapping-config: {exc}", file=sys.stderr)
        return 2
    except (OrgResolutionError, SnykOrgApiError) as exc:
        print(f"generate-org-mapping-config: {exc}", file=sys.stderr)
        return 1
    except OrgConfigGeneratorError as exc:
        print(f"generate-org-mapping-config: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
