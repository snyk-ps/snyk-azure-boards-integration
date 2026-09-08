"""Bounded, non-secret diagnostics extracted from Azure DevOps error responses."""

from __future__ import annotations

import json
import re
from typing import Any

# Kept under the 500-character clamp applied to audit-record ``error`` values so
# the truncation marker survives into the emitted log line.
MAX_ERROR_DETAIL_CHARS = 480
TRUNCATION_MARKER = "...[truncated]"
REDACTION_PLACEHOLDER = "[redacted]"

_CREDENTIAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:Basic|Bearer)\s+[A-Za-z0-9+/=._-]{8,}", re.IGNORECASE),
    re.compile(
        r"\b(?:authorization|pat|password|passwd|secret|api[_-]?key"
        r"|access[_-]?token|token)\b\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
)


def redact_credentials(text: str) -> str:
    """Replace credential-shaped substrings with :data:`REDACTION_PLACEHOLDER`.

    Args:
        text: Arbitrary diagnostic text.

    Returns:
        ``text`` with Basic/Bearer material and ``key: value`` pairs whose key
        names a credential replaced by a placeholder.
    """
    out = text
    for pattern in _CREDENTIAL_PATTERNS:
        out = pattern.sub(REDACTION_PLACEHOLDER, out)
    return out


def truncate_detail(text: str) -> str:
    """Bound ``text`` to :data:`MAX_ERROR_DETAIL_CHARS`, marking any truncation."""
    if len(text) <= MAX_ERROR_DETAIL_CHARS:
        return text
    keep = MAX_ERROR_DETAIL_CHARS - len(TRUNCATION_MARKER)
    return text[:keep].rstrip() + TRUNCATION_MARKER


def _envelope_message(text: str) -> str | None:
    """Extract ``message`` (prefixed by ``typeKey``) from an ADO error envelope."""
    try:
        doc: Any = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(doc, dict):
        return None
    message = doc.get("message")
    if not isinstance(message, str) or not message.strip():
        return None
    message = message.strip()
    type_key = doc.get("typeKey")
    if isinstance(type_key, str) and type_key.strip() and type_key.strip() not in message:
        return f"{type_key.strip()}: {message}"
    return message


def error_detail_from_body(body: bytes | str | None) -> str | None:
    """Derive a bounded, redacted diagnostic from an Azure DevOps error body.

    Only the documented error envelope is trusted, so arbitrary response content
    is never echoed into logs. This function is total: any decoding, parsing, or
    shape problem yields ``None`` rather than raising, letting callers fall back
    to a status-only message.

    Args:
        body: Raw response body, decoded text, or ``None``.

    Returns:
        Redacted single-line diagnostic bounded by
        :data:`MAX_ERROR_DETAIL_CHARS`, or ``None`` when no envelope
        ``message`` can be derived.
    """
    if body is None:
        return None
    try:
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
    except Exception:  # noqa: BLE001 - extraction must never mask the original error
        return None
    text = text.strip()
    if not text:
        return None
    message = _envelope_message(text)
    if not message:
        return None
    cleaned = redact_credentials(" ".join(message.split())).strip()
    if not cleaned:
        return None
    return truncate_detail(cleaned)


def error_detail_from_http_error(exc: Any) -> str | None:
    """Read an ``HTTPError`` body once and derive a diagnostic from it.

    Args:
        exc: The ``urllib.error.HTTPError`` raised for a terminal response.

    Returns:
        The diagnostic from :func:`error_detail_from_body`, or ``None`` when the
        body cannot be read.
    """
    try:
        body = exc.read()
    except Exception:  # noqa: BLE001 - a consumed or absent stream is not an error here
        return None
    return error_detail_from_body(body)
