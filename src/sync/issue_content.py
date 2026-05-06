"""Build work item text from Snyk issue payloads (P2-FR-5.x)."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping
from urllib.parse import quote

CVE_ID_PATTERN = re.compile(r"^CVE-\d{4}-\d+$", re.IGNORECASE)
MAX_TITLE_LEN = 255
# Azure DevOps rich-text field practical limit; tail is truncated with notice.
_MAX_DESCRIPTION_CHARS = 32_000


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


def effective_target_label_for_title(
    *,
    snyk_project_name: str = "",
    ado_organization: str = "",
    ado_project: str = "",
) -> str | None:
    """
    Target prefix for ``System.Title``, aligned with the description header block.

    Prefers the **Snyk target** name when present; otherwise the **Azure Boards**
    ``organization / project`` string (same order as the description context).
    """
    s = str(snyk_project_name or "").strip()
    if s:
        return s
    ao = str(ado_organization or "").strip()
    ap = str(ado_project or "").strip()
    if ao and ap:
        return f"{ao} / {ap}"
    if ap:
        return ap
    if ao:
        return ao
    return None


def title_with_package(attrs: Mapping[str, Any]) -> str:
    """Deprecated path: title plus primary package. Prefer :func:`work_item_title`."""
    return work_item_title(attrs, target_name=None)


def work_item_title(
    attrs: Mapping[str, Any],
    *,
    target_name: str | None = None,
) -> str:
    """
    ``System.Title``: ``<target> - <issue>`` when a target label is known.

    ``target_name`` should match :func:`effective_target_label_for_title` so the
    title aligns with **Snyk target** context in the description when present.

    ``issue`` is the Snyk ``attributes.title``; if missing, falls back to the
    primary ``package@version`` line. Without ``target_name``, only the issue part
    is used (no `` - `` prefix).
    """
    target = str(target_name or "").strip()
    title_raw = attrs.get("title")
    issue_part = str(title_raw).strip() if title_raw is not None else ""
    if not issue_part:
        issue_part = primary_package_line(attrs) or ""
    if not issue_part:
        issue_part = "Snyk finding"

    if target:
        combined = f"{target} - {issue_part}"
    else:
        combined = issue_part

    if len(combined) <= MAX_TITLE_LEN:
        return combined
    suffix = "…"
    if target and len(target) + 3 < MAX_TITLE_LEN:
        budget = MAX_TITLE_LEN - len(target) - len(" - ") - len(suffix)
        if budget > 0:
            return f"{target} - {issue_part[:budget]}{suffix}"
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


def snyk_ui_issue_url(
    *,
    snyk_org_slug: str,
    project_id: str,
    issue_key: str,
) -> str:
    """
    Canonical Snyk web app URL: org / project / fragment issue key.

    Path segments are percent-encoded as required; issue key is used verbatim in the
    fragment (``#issue-<key>``).
    """
    slug = snyk_org_slug.strip()
    pid = project_id.strip()
    key = issue_key.strip()
    org_seg = quote(slug, safe="")
    base = f"https://app.snyk.io/org/{org_seg}/project/{pid}"
    return f"{base}#issue-{key}"


def _format_remedy_dict(item: dict[str, Any]) -> str:
    """Prefer human-readable upgrade/patch lines over raw JSON."""
    t = item.get("type")
    desc = item.get("desc") or item.get("description") or item.get("message")
    if isinstance(desc, str) and desc.strip():
        if t is not None and str(t).strip():
            return f"{str(t).strip()}: {desc.strip()}"
        return desc.strip()
    return json.dumps(item, sort_keys=True)


def _upgrade_version_strings_from_remedy(rem: dict[str, Any]) -> list[str]:
    """Extract recommended / target versions from a single remedy object."""
    out: list[str] = []
    for key in (
        "upgradeTo",
        "upgrade_to",
        "targetVersion",
        "target_version",
        "fixedIn",
        "fixed_in",
    ):
        v = rem.get(key)
        if v is not None and str(v).strip():
            s = str(v).strip()
            if s and s not in out:
                out.append(s)
    changes = rem.get("changes")
    if isinstance(changes, list):
        for ch in changes:
            if not isinstance(ch, dict):
                continue
            for key in ("upgradeTo", "upgrade_to", "to"):
                v = ch.get(key)
                if v is not None and str(v).strip():
                    s = str(v).strip()
                    if s and s not in out:
                        out.append(s)
    return out


def _dependency_version_hints(coord: dict[str, Any]) -> list[str]:
    """``representations[].dependency`` fields that name a non-vulnerable version."""
    out: list[str] = []
    reps = coord.get("representations")
    if not isinstance(reps, list):
        return out
    for rep in reps:
        if not isinstance(rep, dict):
            continue
        dep = rep.get("dependency")
        if not isinstance(dep, dict):
            continue
        for key in (
            "upgrade_package_version",
            "latest_upgrade",
            "patch_package_version",
            "fixed_version",
            "latest_version",
        ):
            v = dep.get(key)
            if v is not None and str(v).strip():
                out.append(str(v).strip())
                break
    return out


def recommended_upgrade_lines(attrs: Mapping[str, Any]) -> list[str]:
    """
    Short, de-duplicated lines suggesting a fix version (``upgradeTo``-style data).

    Used for a **How to fix** section in addition to free-text remedy lines.
    """
    coords = attrs.get("coordinates")
    if not isinstance(coords, list):
        return []
    seen: set[str] = set()
    lines: list[str] = []
    for coord in coords:
        if not isinstance(coord, dict):
            continue
        for dv in _dependency_version_hints(coord):
            k0 = dv.lower()
            if k0 in seen:
                continue
            seen.add(k0)
            lines.append(f"Upgrade to: {dv}")
        rem = coord.get("remedies")
        if isinstance(rem, list):
            for item in rem:
                if not isinstance(item, dict):
                    continue
                for ver in _upgrade_version_strings_from_remedy(item):
                    key = ver.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    lines.append(f"Upgrade to: {ver}")
        fixes = coord.get("fixes")
        if isinstance(fixes, list):
            for fx in fixes:
                if not isinstance(fx, dict):
                    continue
                for ver in _upgrade_version_strings_from_remedy(fx):
                    k2 = ver.lower()
                    if k2 in seen:
                        continue
                    seen.add(k2)
                    lines.append(f"Upgrade to: {ver}")
    return lines


def _remedy_lines_from_coordinate(coord: dict[str, Any]) -> list[str]:
    rem = coord.get("remedies")
    if rem is None or rem == []:
        return []
    if isinstance(rem, str) and rem.strip():
        return [rem.strip()]
    if isinstance(rem, list):
        out: list[str] = []
        for item in rem:
            if isinstance(item, dict):
                out.append(_format_remedy_dict(item))
            elif item is not None:
                out.append(str(item).strip())
        return [x for x in out if x]
    if isinstance(rem, dict):
        return [_format_remedy_dict(rem)]
    return [str(rem)]


def remedy_section_lines(attrs: Mapping[str, Any]) -> list[str]:
    """Human-readable lines for ``coordinates[].remedies``."""
    coords = attrs.get("coordinates")
    if not isinstance(coords, list):
        return []
    lines: list[str] = []
    for coord in coords:
        if isinstance(coord, dict):
            lines.extend(_remedy_lines_from_coordinate(coord))
    return lines


def code_location_lines(attrs: Mapping[str, Any]) -> list[str]:
    """
    File path and line range from Snyk Code ``coordinates[].representations[]``.

    Uses ``sourceLocation.file`` and ``region.start`` / ``region.end`` line numbers
    when present (see ``data/sample_coord.local.json``).
    """
    coords = attrs.get("coordinates")
    if not isinstance(coords, list):
        return []
    out: list[str] = []
    for coord in coords:
        if not isinstance(coord, dict):
            continue
        reps = coord.get("representations")
        if not isinstance(reps, list):
            continue
        for rep in reps:
            if not isinstance(rep, dict):
                continue
            sl = rep.get("sourceLocation")
            if not isinstance(sl, dict):
                continue
            fp = sl.get("file")
            if not isinstance(fp, str) or not fp.strip():
                continue
            region = sl.get("region")
            if isinstance(region, dict):
                start = region.get("start")
                end = region.get("end")
                sln = (
                    start.get("line")
                    if isinstance(start, dict)
                    else None
                )
                eln = (
                    end.get("line")
                    if isinstance(end, dict)
                    else None
                )
                if sln is not None and eln is not None:
                    out.append(f"{fp.strip()} (lines {sln}-{eln})")
                    continue
            out.append(fp.strip())
    return out


def coordinate_path_hints(attrs: Mapping[str, Any]) -> list[str]:
    """Best-effort lockfile / manifest paths from ``coordinates[]`` (developer context)."""
    coords = attrs.get("coordinates")
    if not isinstance(coords, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for coord in coords:
        if not isinstance(coord, dict):
            continue
        for key in ("path", "target_path", "file"):
            v = coord.get(key)
            if isinstance(v, str) and v.strip() and v.strip() not in seen:
                seen.add(v.strip())
                out.append(v.strip())
                break
        files = coord.get("files")
        if isinstance(files, list):
            for f in files:
                if isinstance(f, dict):
                    p = f.get("path") or f.get("filePath")
                    if isinstance(p, str) and p.strip() and p.strip() not in seen:
                        seen.add(p.strip())
                        out.append(p.strip())
                elif isinstance(f, str) and f.strip() and f.strip() not in seen:
                    seen.add(f.strip())
                    out.append(f.strip())
    return out


_FIX_SIGNAL_LABELS: dict[str, str] = {
    "is_upgradeable": "Upgrade available",
    "is_patchable": "Patch available",
    "is_fixable_manually": "Manual remediation possible",
    "is_fixable_snyk": "Automated fix available via Snyk",
    "is_fixable_upstream": "Upstream fix published",
}


def fix_signal_labels(attrs: Mapping[str, Any]) -> list[str]:
    """Human-readable fix signals from ``coordinates[]`` (first coordinate with flags).

    Omits ``is_pinnable`` (low signal for most workflows).
    """
    coords = attrs.get("coordinates")
    if not isinstance(coords, list) or not coords:
        return []
    first = coords[0]
    if not isinstance(first, dict):
        return []
    lines: list[str] = []
    for key, label in _FIX_SIGNAL_LABELS.items():
        if first.get(key) is True:
            lines.append(label)
    return lines


def _join_description_sections(section_blocks: list[list[str]]) -> str:
    """Join blocks with a blank line between each; keep blank lines inside a block."""
    sections: list[str] = []
    for block in section_blocks:
        trimmed = list(block)
        while trimmed and not str(trimmed[0]).strip():
            trimmed.pop(0)
        while trimmed and not str(trimmed[-1]).strip():
            trimmed.pop()
        if not trimmed:
            continue
        sections.append("\n".join(trimmed))
    return "\n\n".join(sections)


def build_system_description(
    attrs: Mapping[str, Any],
    *,
    snyk_org_slug: str,
    project_id: str,
    issue_key: str,
    snyk_project_name: str | None = None,
    snyk_project_origin: str | None = None,
    severity: str | None = None,
) -> str:
    """Multi-line plain text for ``System.Description``."""
    pkg_line = primary_package_line(attrs)
    narrative = str(attrs.get("description") or "").strip()
    remedies = remedy_section_lines(attrs)
    upgrade_hints = recommended_upgrade_lines(attrs)
    ftype = finding_type_verbatim(attrs)
    cwes = cwe_ids(attrs)
    cves = cve_entries(attrs)
    flags = fix_signal_labels(attrs)
    path_hints = coordinate_path_hints(attrs)
    code_locs = code_location_lines(attrs)
    link = snyk_ui_issue_url(
        snyk_org_slug=snyk_org_slug,
        project_id=project_id,
        issue_key=issue_key,
    )

    sev = str(severity or "").strip()
    target_name = str(snyk_project_name or "").strip()
    origin = str(snyk_project_origin or "").strip()

    context_blocks: list[list[str]] = []
    if target_name:
        context_blocks.append([f"Snyk target: {target_name}"])
    if origin:
        context_blocks.append([f"Snyk project origin: {origin}"])
    meta_lines: list[str] = []
    if sev:
        meta_lines.append(f"Severity: {sev}")
    meta_lines.append(f"Snyk issue key: {issue_key}")
    context_blocks.append(meta_lines)

    finding_lines: list[str] = []
    if pkg_line:
        finding_lines.append(f"Affected package: {pkg_line}")
    if path_hints:
        finding_lines.append("Detected in:")
        finding_lines.extend(f"  • {p}" for p in path_hints[:20])
        if len(path_hints) > 20:
            finding_lines.append("  • …")
    if code_locs:
        finding_lines.append("Code location:")
        finding_lines.extend(f"  • {p}" for p in code_locs[:20])
        if len(code_locs) > 20:
            finding_lines.append("  • …")

    how_to_fix_lines: list[str] = []
    if upgrade_hints:
        how_to_fix_lines.append("Recommended versions:")
        how_to_fix_lines.extend(f"  • {line}" for line in upgrade_hints)
    if remedies:
        if how_to_fix_lines:
            how_to_fix_lines.append("")
        how_to_fix_lines.append("Remediation steps (from Snyk):")
        how_to_fix_lines.extend(f"  • {line}" for line in remedies)

    details_lines: list[str] = []
    if narrative:
        details_lines.append("Details")
        details_lines.append(narrative)

    classification_lines: list[str] = []
    class_parts: list[str] = []
    if ftype:
        class_parts.append(f"Finding type: {ftype}")
    if cwes:
        class_parts.append("CWE: " + ", ".join(cwes))
    if cves:
        cve_lines = []
        for cid, url in cves:
            cve_lines.append(f"{cid} ({url})" if url else cid)
        class_parts.append("CVE: " + "; ".join(cve_lines))
    if flags:
        class_parts.append("Fix availability: " + "; ".join(flags))
    if class_parts:
        classification_lines.append("Classification")
        classification_lines.extend(class_parts)

    link_lines = [
        "Open in Snyk",
        link,
        "",
        "Use the link above for PR/MR fixes, precise upgrade paths, and ignore "
        "controls when your policy allows.",
    ]

    body = _join_description_sections(
        context_blocks
        + [
            finding_lines,
            how_to_fix_lines,
            details_lines,
            classification_lines,
            link_lines,
        ],
    )
    if len(body) <= _MAX_DESCRIPTION_CHARS:
        return body
    trunc = "[description truncated for Azure Boards field size]\n"
    keep = _MAX_DESCRIPTION_CHARS - len(trunc)
    return body[:keep] + trunc

