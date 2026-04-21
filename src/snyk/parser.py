"""Parse Snyk JSON:API issue documents into simple structures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast


@dataclass(frozen=True)
class IssuesListPage:
    """One page of a list-issues response."""

    issues: list[dict[str, Any]]
    links: dict[str, str | None]


def parse_issues_list_document(doc: Mapping[str, Any]) -> IssuesListPage:
    """Parse a JSON:API document for list issues (``data`` may be a list)."""
    raw_data = doc.get("data")
    issues: list[dict[str, Any]]
    if raw_data is None:
        issues = []
    elif isinstance(raw_data, list):
        issues = [cast(dict[str, Any], x) for x in raw_data if isinstance(x, dict)]
    elif isinstance(raw_data, dict):
        issues = [cast(dict[str, Any], raw_data)]
    else:
        issues = []

    raw_links = doc.get("links")
    links: dict[str, str | None]
    if isinstance(raw_links, dict):
        links = {
            str(k): (None if v is None else str(v))
            for k, v in raw_links.items()
            if isinstance(k, str)
        }
    else:
        links = {}

    return IssuesListPage(issues=issues, links=links)


def parse_single_issue_document(doc: Mapping[str, Any]) -> dict[str, Any]:
    """Parse a JSON:API document for get issue (``data`` is a single resource)."""
    data = doc.get("data")
    if isinstance(data, dict):
        return cast(dict[str, Any], data)
    return {}


def _coerce_ignored_for_record(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "1", "yes", "on")
    return bool(raw)


def normalized_issue_record(resource: Mapping[str, Any]) -> dict[str, Any]:
    """Map a JSON:API issue resource to a flat record for sync and CLI output.

    Keys are included only when present in the resource: ``org_id``,
    ``project_id``, ``issue_id``, ``created_at``, ``severity``, ``status``,
    ``ignored``, and ``issue_attributes`` (copy of ``attributes``) when present.
    Optional relationships (``organization``, ``scan_item``) or attributes may
    be absent in partial payloads; omitted keys mean unknown/missing in that response.
    """
    out: dict[str, Any] = {}
    rid = resource.get("id")
    if rid is not None:
        out["rest_issue_id"] = str(rid)
    attrs = resource.get("attributes")
    if isinstance(attrs, dict):
        out["issue_attributes"] = dict(attrs)
        if "key" in attrs:
            out["issue_id"] = attrs["key"]
        if "created_at" in attrs:
            out["created_at"] = attrs["created_at"]
        if "effective_severity_level" in attrs:
            out["severity"] = attrs["effective_severity_level"]
        if "status" in attrs:
            out["status"] = attrs["status"]
        if "ignored" in attrs:
            out["ignored"] = _coerce_ignored_for_record(attrs.get("ignored"))
    rel = resource.get("relationships")
    if isinstance(rel, dict):
        org = rel.get("organization")
        if isinstance(org, dict):
            data = org.get("data")
            if isinstance(data, dict) and "id" in data:
                out["org_id"] = data["id"]
        scan = rel.get("scan_item")
        if isinstance(scan, dict):
            data = scan.get("data")
            if isinstance(data, dict) and "id" in data:
                out["project_id"] = data["id"]
    return out
