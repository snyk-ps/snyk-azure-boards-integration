"""Ensure Azure DevOps area paths exist before work item create/update."""

from __future__ import annotations

from integrations.azure_devops.client import WorkItemsClient
from integrations.azure_devops.errors import AzureDevOpsClientError

AUTO_DEFAULT_AREA_SEGMENT = "Snyk"

AreaPathEnsureCache = dict[tuple[str, str, str], bool]


def _area_path_segments(full_path: str) -> list[str]:
    return [segment.strip() for segment in str(full_path or "").split("\\") if segment.strip()]


def _classification_api_segments(full_path: str, project: str) -> list[str]:
    """
    Convert a work-item ``System.AreaPath`` to Classification Nodes API segments.

    ADO area paths on work items include the project name as the first segment
    (for example ``My Project\\Team\\Snyk``). Classification Nodes REST paths are
    relative to the project root (``Team/Snyk``), so drop a leading segment when
    it matches ``project``.
    """
    segments = _area_path_segments(full_path)
    proj = str(project or "").strip()
    if segments and proj and segments[0] == proj:
        return segments[1:]
    return segments


def ensure_area_path_exists(
    client: WorkItemsClient,
    organization: str,
    project: str,
    full_path: str,
    cache: AreaPathEnsureCache,
) -> None:
    """
    Ensure ``full_path`` exists under the ADO project area hierarchy.

    Creates missing child segments via Classification Nodes REST. Uses ``cache``
    keyed by ``(organization, project, full_path)`` to skip repeat work in one sync run.
    """
    org = str(organization or "").strip()
    proj = str(project or "").strip()
    path = str(full_path or "").strip()
    if not org or not proj or not path:
        raise AzureDevOpsClientError(
            "area path ensure requires non-empty organization, project, and path",
            status_code=None,
        )

    cache_key = (org, proj, path)
    if cache.get(cache_key):
        return

    api_segments = _classification_api_segments(path, proj)
    if not api_segments:
        raise AzureDevOpsClientError(
            f"area path ensure requires at least one area segment beyond project; got {path!r}",
            status_code=None,
        )

    for index in range(len(api_segments)):
        cumulative = "\\".join(api_segments[: index + 1])
        existing = client.get_classification_node(org, proj, cumulative)
        if existing is not None:
            continue
        parent = "\\".join(api_segments[:index]) if index > 0 else None
        client.create_classification_node(org, proj, parent, api_segments[index])

    cache[cache_key] = True
