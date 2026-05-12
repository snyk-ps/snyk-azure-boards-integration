"""Azure Table ``PartitionKey`` / ``RowKey`` helpers for mapping entities."""

from __future__ import annotations

import base64

_FORBIDDEN_IN_KEYS = frozenset("/\\#?")


def _segment_needs_encoding(segment: str) -> bool:
    return any(ch in _FORBIDDEN_IN_KEYS for ch in segment)


def _b64url_utf8(segment: str) -> str:
    raw = segment.encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def table_row_key(org_id: str, project_id: str, issue_id: str) -> str:
    """
    Deterministic ``RowKey`` for issues sync persistence on Azure Table Storage.

    Uses ``org_id|project_id|issue_id`` when no component contains ``/``, ``\\``,
    ``#``, or ``?``. Otherwise encodes each component as unpadded base64url (UTF-8)
    and joins with ``_``.
    """
    segments = (org_id, project_id, issue_id)
    if any(_segment_needs_encoding(s) for s in segments):
        return "_".join(_b64url_utf8(s) for s in segments)
    return f"{org_id}|{project_id}|{issue_id}"
