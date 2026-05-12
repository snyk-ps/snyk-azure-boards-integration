"""Azure Boards work-item tags derived from Snyk issue metadata (severity, type).

Managed tags support reporting/WIQL and are merged with ``work_item_template.tags``
without dropping operator-supplied labels (reserved prefixes stripped from YAML).
"""

from __future__ import annotations

from collections.abc import Sequence

_SEVERITY_LEVELS = frozenset({"low", "medium", "high", "critical"})


def managed_severity_tag_from_level(raw: str | None) -> str | None:
    """
    Build ``Snyk-Severity-{level}`` from Snyk ``effective_severity_level``.

    Levels are normalized to lowercase. Returns ``None`` when missing or not one of
    low / medium / high / critical (after normalization).
    """
    if raw is None:
        return None
    level = str(raw).strip().lower()
    if level not in _SEVERITY_LEVELS:
        return None
    return f"Snyk-Severity-{level}"


# Snyk Issues REST ``attributes.type`` (documented enumeration):
# ``package_vulnerability``, ``license``, ``cloud``, ``code``, ``custom``, ``config``.
#
# Managed tag form: ``Snyk-Type-{suffix}``. Most values map into **P2-FR-5.2** buckets;
# **`license`** and **`custom`** keep their REST names as the suffix (verbatim kind).
_SNYK_TYPE_TO_TAG_SUFFIX: dict[str, str] = {
    # --- Official ``type`` values ---
    "package_vulnerability": "open_source",
    "license": "license",
    "cloud": "iac",
    "code": "code",
    "custom": "custom",
    "config": "iac",
    # --- Historical / synonym tokens (backward compatibility & UI variants) ---
    "package": "open_source",
    "open_source": "open_source",
    "opensource": "open_source",
    "licensing": "license",
    "dependency": "open_source",
    "vulnerability": "open_source",
    "sast": "code",
    "container": "container",
    "image": "container",
    "iac": "iac",
    "configuration": "iac",
    "terraform": "iac",
    "cloudformation": "iac",
    "cloud_formation": "iac",
    "kubernetes": "iac",
}


def managed_type_tag_from_issue_type(raw: str | None) -> str | None:
    """
    Build ``Snyk-Type-{suffix}`` for Snyk issue ``attributes.type``.

    REST enums ``package_vulnerability``, ``license``, ``cloud``, ``code``,
    ``custom``, and ``config`` map to a stable suffix—usually a **P2-FR-5.2** bucket
    (``open_source``, ``code``, ``container``, ``iac``), except **``license``** and
    **``custom``**, which keep those literal suffixes (**``Snyk-Type-license``**,
    **``Snyk-Type-custom``**).

    Tokens are normalized: strip, lowercase, hyphens/spaces → underscores.

    Unknown values after normalization return ``None``.
    """
    if raw is None:
        return None
    token = (
        str(raw)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )
    if not token:
        return None
    suffix = _SNYK_TYPE_TO_TAG_SUFFIX.get(token)
    if suffix is None:
        return None
    return f"Snyk-Type-{suffix}"


def combine_tags_for_work_item(
    template_tags: Sequence[str],
    *,
    managed_severity_tag: str | None,
    managed_type_tag: str | None,
) -> list[str]:
    """
    Operator tags first (excluding reserved prefixes), then managed severity, then type.

    Tags matching ``Snyk-Severity-*`` or ``Snyk-Type-*`` from the operator list are
    dropped so issue-derived tags are authoritative. Consecutive duplicates are removed.
    """
    out: list[str] = []
    for raw in template_tags:
        tag = str(raw).strip()
        if not tag:
            continue
        if tag.startswith("Snyk-Severity-") or tag.startswith("Snyk-Type-"):
            continue
        out.append(tag)
    if managed_severity_tag:
        out.append(managed_severity_tag)
    if managed_type_tag:
        out.append(managed_type_tag)

    deduped: list[str] = []
    for tag in out:
        if deduped and deduped[-1] == tag:
            continue
        deduped.append(tag)
    return deduped
