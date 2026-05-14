"""Structured JSON audit lines for integration HTTP calls and sync summaries."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

_AUDIT = logging.getLogger("integration_audit")

_PLACEHOLDER = "-"


def _safe_target(url: str) -> str:
    """Return scheme, host, and path only (no query or fragment)."""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return parsed.path or url.split("?", maxsplit=1)[0]


def log_integration_http(
    *,
    integration: str,
    method: str,
    url: str,
    status_code: int | None,
    duration_ms: float,
    sync_run_id: str | None = None,
    error: str | None = None,
) -> None:
    """
    Emit one terminal-outcome audit line (JSON object) for an outbound HTTP call.

    Secrets MUST NOT appear in ``url`` beyond what callers already pass; prefer
    logging only the request URL string available to the client (query may be
    stripped upstream for safety).
    """
    payload: dict[str, object] = {
        "duration_ms": round(duration_ms, 3),
        "event": "integration_http",
        "http_status": status_code,
        "integration": integration,
        "method": method.upper(),
        "safe_target": _safe_target(url),
    }
    if sync_run_id:
        payload["sync_run_id"] = sync_run_id
    if status_code in (401, 403):
        payload["error"] = f"Authentication Failed (HTTP {status_code})"
    elif error:
        payload["error"] = str(error)[:500]

    if status_code is None:
        _AUDIT.log(logging.ERROR, _PLACEHOLDER, extra={"record": payload})
    elif status_code >= 400:
        _AUDIT.log(logging.WARNING, _PLACEHOLDER, extra={"record": payload})
    else:
        _AUDIT.log(logging.INFO, _PLACEHOLDER, extra={"record": payload})


def log_sync_summary(
    *,
    sync_run_id: str,
    sync_duration_seconds: float,
    sync_outcome: str,
    error: str = "",
) -> None:
    """Emit exactly one JSON summary line per sync invocation."""
    payload: dict[str, object] = {
        "event": "sync_summary",
        "sync_duration_seconds": round(sync_duration_seconds, 6),
        "sync_outcome": sync_outcome,
        "sync_run_id": sync_run_id,
    }
    if error:
        payload["error"] = error[:500]
    _AUDIT.info(_PLACEHOLDER, extra={"record": payload})
