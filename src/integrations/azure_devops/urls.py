"""URL helpers for Azure DevOps REST."""

from __future__ import annotations

from urllib.parse import quote, urlencode


def normalize_devops_base_url(base_url: str) -> str:
    """Return the API origin without a trailing slash."""
    return base_url.rstrip("/")


def _segment(s: str) -> str:
    """Encode a single path segment (organization / project)."""
    return quote(s.strip(), safe="")


def work_item_create_url(
    base_url: str,
    organization: str,
    project: str,
    work_item_type: str,
    *,
    api_version: str,
) -> str:
    """Build URL for ``POST .../wit/workitems/${type}``."""
    root = normalize_devops_base_url(base_url)
    org = _segment(organization)
    proj = _segment(project)
    t = work_item_type.strip().lstrip("$")
    type_path = "$" + quote(t, safe="")
    q = urlencode({"api-version": api_version})
    return f"{root}/{org}/{proj}/_apis/wit/workitems/{type_path}?{q}"


def work_item_get_url(
    base_url: str,
    organization: str,
    project: str,
    work_item_id: str | int,
    *,
    api_version: str,
) -> str:
    """Build URL for ``GET .../wit/workitems/{id}``."""
    root = normalize_devops_base_url(base_url)
    org = _segment(organization)
    proj = _segment(project)
    wid = quote(str(work_item_id).strip(), safe="")
    q = urlencode({"api-version": api_version})
    return f"{root}/{org}/{proj}/_apis/wit/workitems/{wid}?{q}"


def work_items_list_url(
    base_url: str,
    organization: str,
    project: str,
    ids: list[str | int],
    *,
    api_version: str,
) -> str:
    """Build URL for ``GET .../wit/workitems?ids=...``."""
    root = normalize_devops_base_url(base_url)
    org = _segment(organization)
    proj = _segment(project)
    id_list = ",".join(str(i).strip() for i in ids)
    q = urlencode(
        {"ids": id_list, "errorPolicy": "Omit", "api-version": api_version},
    )
    return f"{root}/{org}/{proj}/_apis/wit/workitems?{q}"


def work_item_update_url(
    base_url: str,
    organization: str,
    project: str,
    work_item_id: str | int,
    *,
    api_version: str,
) -> str:
    """Build URL for ``PATCH .../wit/workitems/{id}``."""
    root = normalize_devops_base_url(base_url)
    org = _segment(organization)
    proj = _segment(project)
    wid = quote(str(work_item_id).strip(), safe="")
    q = urlencode({"api-version": api_version})
    return f"{root}/{org}/{proj}/_apis/wit/workitems/{wid}?{q}"


def work_item_type_fields_url(
    base_url: str,
    organization: str,
    project: str,
    work_item_type: str,
    *,
    api_version: str,
) -> str:
    """Build URL for ``GET .../wit/workitemtypes/{type}/fields``."""
    root = normalize_devops_base_url(base_url)
    org = _segment(organization)
    proj = _segment(project)
    wit = quote(work_item_type.strip(), safe="")
    q = urlencode({"api-version": api_version})
    return f"{root}/{org}/{proj}/_apis/wit/workitemtypes/{wit}/fields?{q}"


def work_item_comment_url(
    base_url: str,
    organization: str,
    project: str,
    work_item_id: str | int,
    *,
    api_version: str,
) -> str:
    """Build URL for ``POST .../wit/workItems/{id}/comments`` (note ``workItems`` casing)."""
    root = normalize_devops_base_url(base_url)
    org = _segment(organization)
    proj = _segment(project)
    wid = quote(str(work_item_id).strip(), safe="")
    q = urlencode({"api-version": api_version})
    return f"{root}/{org}/{proj}/_apis/wit/workItems/{wid}/comments?{q}"


def _classification_path_segment(path: str) -> str:
    """Encode an ADO classification path for URL segments (``\\`` → ``/``)."""
    normalized = str(path or "").strip().replace("\\", "/")
    parts = [p.strip() for p in normalized.split("/") if p.strip()]
    return "/".join(quote(part, safe="") for part in parts)


def classification_node_url(
    base_url: str,
    organization: str,
    project: str,
    structure_group: str,
    path: str | None,
    *,
    api_version: str,
) -> str:
    """Build URL for Classification Nodes GET/POST under ``Areas`` or ``Iterations``."""
    root = normalize_devops_base_url(base_url)
    org = _segment(organization)
    proj = _segment(project)
    group = quote(structure_group.strip(), safe="")
    q = urlencode({"api-version": api_version})
    base = f"{root}/{org}/{proj}/_apis/wit/classificationnodes/{group}"
    if path and str(path).strip():
        return f"{base}/{_classification_path_segment(path)}?{q}"
    return f"{base}?{q}"
