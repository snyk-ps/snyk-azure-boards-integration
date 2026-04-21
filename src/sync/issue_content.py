"""Build work item text from Snyk issue payloads (P2-FR-5.x v1)."""

from __future__ import annotations

import re
from typing import Any, Mapping

CVE_ID_PATTERN = re.compile(r"^CVE-\d{4}-\d+$", re.IGNORECASE)
MAX_TITLE_LEN = 255


def primary_package_line(attrs: Mapping[str, Any]) -> str | None:
    """
    First ``coordinates[]`` entry with a ``representations[].dependency`` block.

    Returns:
        Human-readable ``package@version`` or ``None``.
    """
    coords = attrs.get("coordinates")
    if not isinstance(coords, list):
        return None
    for coord in coords:
        if not isinstance(coord, dict):
            continue
        reps = coord.get("representations")
        if not isinstance(reps, list):
            continue
        for rep in reps:
            if not isinstance(rep, dict):
                continue
            dep = rep.get("dependency")
            if not isinstance(dep, dict):
                continue
            name = dep.get("package_name")
            ver = dep.get("package_version")
            if name:
                if ver:
                    return f"{name}@{ver}"
                return str(name)
    return None


def title_with_package(attrs: Mapping[str, Any]) -> str:
    """``System.Title`` / heading text: title plus primary package line."""
    title = attrs.get("title")
    t = str(title).strip() if title is not None else ""
    pkg = primary_package_line(attrs)
    if pkg:
        combined = f"{t} — {pkg}" if t else pkg
    else:
        combined = t or "Snyk finding"
    if len(combined) <= MAX_TITLE_LEN:
        return combined
    suffix = "…"
    return combined[: MAX_TITLE_LEN - len(suffix)] + suffix


def finding_type_verbatim(attrs: Mapping[str, Any]) -> str:
    """``attributes.type`` verbatim."""
    t = attrs.get("type")
    return str(t) if t is not None else ""


def cwe_ids(attrs: Mapping[str, Any]) -> list[str]:
    """CWE class ids where ``source == \"CWE\"``."""
    classes = attrs.get("classes")
    if not isinstance(classes, list):
        return []
    out: list[str] = []
    for item in classes:
        if not isinstance(item, dict):
            continue
        if str(item.get("source", "")).upper() != "CWE":
            continue
        cid = item.get("id")
        if cid:
            out.append(str(cid))
    return out


def cve_entries(attrs: Mapping[str, Any]) -> list[tuple[str, str | None]]:
    """``(cve_id, url_or_none)`` from ``attributes.problems`` matching ``CVE-*``."""
    problems = attrs.get("problems")
    if not isinstance(problems, list):
        return []
    out: list[tuple[str, str | None]] = []
    for item in problems:
        if not isinstance(item, dict):
            continue
        pid = item.get("id")
        if pid is None or not CVE_ID_PATTERN.match(str(pid).strip()):
            continue
        url = item.get("url")
        u = str(url).strip() if url else None
        out.append((str(pid).strip(), u or None))
    return out


def best_effort_snyk_issue_url(*, group_id: str, rest_issue_uuid: str) -> str:
    """Best-effort HTTPS URL without org slug (UI parity deferred)."""
    gid = group_id.strip()
    rid = rest_issue_uuid.strip()
    return f"https://app.snyk.io/group/{gid}/issues/{rid}"


def fix_flag_lines(attrs: Mapping[str, Any]) -> list[str]:
    """Boolean fix signals from ``coordinates[]`` (first coordinate with flags)."""
    coords = attrs.get("coordinates")
    if not isinstance(coords, list) or not coords:
        return []
    first = coords[0]
    if not isinstance(first, dict):
        return []
    keys = (
        "is_upgradeable",
        "is_patchable",
        "is_pinnable",
        "is_fixable_manually",
        "is_fixable_snyk",
        "is_fixable_upstream",
    )
    lines: list[str] = []
    for k in keys:
        if first.get(k) is True:
            lines.append(k)
    return lines


def build_system_description(
    attrs: Mapping[str, Any],
    *,
    group_id: str,
    rest_issue_uuid: str,
) -> str:
    """Multi-line plain text for ``System.Description`` (v1 summary)."""
    title = str(attrs.get("title") or "").strip()
    pkg_line = primary_package_line(attrs)
    ftype = finding_type_verbatim(attrs)
    cwes = cwe_ids(attrs)
    cves = cve_entries(attrs)
    flags = fix_flag_lines(attrs)
    link = best_effort_snyk_issue_url(group_id=group_id, rest_issue_uuid=rest_issue_uuid)

    parts: list[str] = []
    if title:
        parts.append(title)
    if pkg_line:
        parts.append(f"Package: {pkg_line}")
    if ftype:
        parts.append(f"Finding type: {ftype}")
    if cwes:
        parts.append("CWE: " + ", ".join(cwes))
    if cves:
        cve_lines = []
        for cid, url in cves:
            cve_lines.append(f"{cid} ({url})" if url else cid)
        parts.append("CVE: " + "; ".join(cve_lines))
    if flags:
        parts.append("Fix signals: " + ", ".join(flags))
    parts.append(f"Snyk: {link}")
    parts.append(
        "(Snyk UI links that require an org slug are deferred; this URL uses group and issue id.)",
    )
    return "\n".join(parts)
