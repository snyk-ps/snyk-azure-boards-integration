"""URL helpers for Snyk API origins, REST bases, and ``links.next`` pagination."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit

from snyk.constants import DEFAULT_API_ORIGIN, DEFAULT_APP_ORIGIN


def normalize_api_origin(origin: str) -> str:
    """Return the Snyk API origin (scheme + host) without a trailing slash."""
    return origin.strip().rstrip("/")


def normalize_app_origin(origin: str) -> str:
    """Return the Snyk web app origin (scheme + host) without a trailing slash."""
    return normalize_api_origin(origin)


def default_app_origin() -> str:
    """Return the built-in default web app origin (SNYK-US-01)."""
    return DEFAULT_APP_ORIGIN


def resolve_api_origin(configured: str) -> str:
    """Resolve an API origin or REST base URL to the origin (no ``/rest`` suffix).

    Accepts ``https://api.eu.snyk.io`` or ``https://api.eu.snyk.io/rest``.
    """
    s = normalize_api_origin(configured)
    if s.endswith("/rest"):
        return s[: -len("/rest")]
    return s


def rest_base_from_origin(origin: str) -> str:
    """Return the REST API base URL for ``origin`` (no trailing slash)."""
    return f"{normalize_api_origin(origin)}/rest"


def v1_base_from_origin(origin: str) -> str:
    """Return the legacy V1 API base URL for ``origin`` (no trailing slash)."""
    return f"{normalize_api_origin(origin)}/v1"


def resolve_snyk_rest_base(configured: str) -> str:
    """Resolve origin or REST base input to a normalized REST base URL."""
    s = configured.strip().rstrip("/")
    if s.endswith("/rest"):
        return s
    return rest_base_from_origin(s)


def default_api_origin() -> str:
    """Return the built-in default API origin (SNYK-US-01)."""
    return DEFAULT_API_ORIGIN


def normalize_base_url(base_url: str) -> str:
    """Return the REST base URL without a trailing slash.

    A trailing slash interacts badly with ``urllib.parse.urljoin`` when the
    next link starts with ``rest/``, producing ``.../rest/rest/...``.
    """
    return base_url.rstrip("/")


def resolve_next_url(base_url: str, links_next: str | None) -> str | None:
    """Resolve ``links.next`` from a JSON:API document to a full HTTPS URL.

    Snyk may return ``links.next`` as a full URL, a path starting with
    ``/rest/``, a segment starting with ``rest/``, or a path under ``rest``
    (e.g. ``orgs/...``). Combining with a base that already ends in ``/rest``
    must not produce ``rest/rest/`` in the path.

    Args:
        base_url: Configured API base, typically ``https://api.snyk.io/rest``.
        links_next: Raw ``links["next"]`` value or None.

    Returns:
        Absolute URL for the next request, or None if there is no next page.
    """
    if links_next is None:
        return None
    s = links_next.strip()
    if not s:
        return None
    if s.startswith("http://") or s.startswith("https://"):
        return s

    base = normalize_base_url(base_url)

    if s.startswith("/"):
        return _join_absolute_path(base, s)

    if s.startswith("rest/"):
        return urljoin(base, s)

    return f"{base}/{s}"


def _join_absolute_path(base: str, absolute_path: str) -> str:
    """Join base (…/rest) with an absolute path that may start with /rest/ or /orgs/."""
    path = absolute_path.strip()
    if path.startswith("/rest/"):
        # "rest/..." relative to …/rest — use base without trailing slash
        return urljoin(base, path.lstrip("/"))
    if path.startswith("/orgs/") or path.startswith("/groups/"):
        return f"{base}{path}"
    parts = urlsplit(base)
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))
