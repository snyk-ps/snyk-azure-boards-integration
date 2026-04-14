"""Normalize Azure DevOps WIT JSON into stable records for callers."""

from __future__ import annotations

from typing import Any


def normalize_work_item_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Map a WIT JSON document to a normalized work item record."""
    fields = doc.get("fields")
    if not isinstance(fields, dict):
        fields = {}
    state = fields.get("System.State")
    rec: dict[str, Any] = {
        "work_item_id": doc.get("id"),
        "work_item_status": state,
        "fields": fields,
    }
    if "rev" in doc:
        rec["rev"] = doc["rev"]
    return rec


def normalize_comment_document(
    doc: dict[str, Any],
    *,
    work_item_id: str | int | None = None,
) -> dict[str, Any]:
    """Map a comment JSON document to a normalized comment record."""
    wid = doc.get("workItemId")
    if wid is None:
        wid = doc.get("work_item_id")
    if wid is None:
        wid = work_item_id
    rec: dict[str, Any] = {
        "id": doc.get("id"),
        "work_item_id": wid,
    }
    return rec
