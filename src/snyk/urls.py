"""URL helpers for Snyk REST ``links.next`` pagination."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit


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
