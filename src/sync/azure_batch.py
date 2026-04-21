"""Batch Azure DevOps work item reads (list-by-ids, max 200 per call)."""

from __future__ import annotations

from collections.abc import Sequence

from integrations.azure_devops.client import MAX_IDS_PER_LIST, WorkItemsClient


def batch_get_work_items(
    client: WorkItemsClient,
    organization: str,
    project: str,
    work_item_ids: Sequence[str],
) -> dict[str, dict]:
    """
    Fetch normalized work item records keyed by string work item id.

    Chunks ``work_item_ids`` into batches of at most :data:`MAX_IDS_PER_LIST`.
    """
    ids = [str(w).strip() for w in work_item_ids if str(w).strip()]
    dedup: list[str] = []
    seen: set[str] = set()
    for w in ids:
        if w not in seen:
            seen.add(w)
            dedup.append(w)
    out: dict[str, dict] = {}
    for i in range(0, len(dedup), MAX_IDS_PER_LIST):
        chunk = dedup[i : i + MAX_IDS_PER_LIST]
        records = client.list_work_items_by_ids(organization, project, chunk)
        for rec in records:
            wid = rec.get("work_item_id")
            if wid is not None:
                out[str(wid)] = rec
    return out
