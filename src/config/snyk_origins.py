"""Snyk project ``origin`` allowlist for ``sync_included_snyk_origins``."""

from __future__ import annotations

import re
from typing import Final

from config.errors import ConfigError

# Catalog aligned with README and
# https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin
# plus REST-observed GitHub app variants.
ACCEPTABLE_SNYK_ORIGIN_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "acr",
        "api",
        "artifactory-cr",
        "aws-config",
        "aws-lambda",
        "azure-functions",
        "azure-repos",
        "bitbucket-cloud",
        "bitbucket-server",
        "cli",
        "cloud-foundry",
        "digitalocean-cr",
        "docker-hub",
        "ecr",
        "gcr",
        "github",
        "github-cloud-app",
        "github-cr",
        "github-enterprise",
        "github-server-app",
        "gitlab",
        "gitlab-cr",
        "google-artifact-cr",
        "harbor-cr",
        "heroku",
        "ibm-cloud",
        "kubernetes",
        "nexus-cr",
        "pivotal",
        "quay-cr",
        "terraform-cloud",
    },
)

_TOKEN_RE = re.compile(r"^[a-z0-9-]+$")
_README_ORIGIN_HINT = (
    "see README.md (Snyk origin allowlist) and "
    "https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin"
)


def parse_sync_included_snyk_origins(
    raw: object | None,
    *,
    field_prefix: str,
) -> tuple[str, ...] | None:
    """
    Parse and validate a comma-separated inclusive origin allowlist.

    Returns:
        ``None`` when the setting is absent, not a string, empty, or only empty
        segments after split (no origin filtering). Otherwise a tuple of tokens.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ConfigError(f"{field_prefix} must be a string")
    s_full = raw.strip()
    if not s_full:
        return None
    parts = [p.strip() for p in s_full.split(",")]
    tokens = tuple(p for p in parts if p)
    if not tokens:
        return None
    for t in tokens:
        if not _TOKEN_RE.fullmatch(t):
            raise ConfigError(
                f"{field_prefix} contains invalid origin token {t!r}; "
                f"tokens must match [a-z0-9-]+; {_README_ORIGIN_HINT}",
            )
        if t not in ACCEPTABLE_SNYK_ORIGIN_TOKENS:
            raise ConfigError(
                f"{field_prefix} contains unknown origin token {t!r}; {_README_ORIGIN_HINT}",
            )
    return tokens
