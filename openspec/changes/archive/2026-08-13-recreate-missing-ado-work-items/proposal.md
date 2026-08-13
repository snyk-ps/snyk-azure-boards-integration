## Why

When the mapping store references an Azure DevOps work item id that no longer exists (deleted manually, project migration, config experiments, etc.), **`sync`** batch-prefetches all mapped ids via `GET .../wit/workitems?ids=...` with ADO's default **`errorPolicy=Fail`**. A single missing id causes HTTP **404**, aborts the entire run (container job failure), and blocks all other issues — including unmapped ones that could be synced. This was reproduced locally and matches a customer incident on v1.4.0.

The archived lifecycle design intended per-issue handling on missing work items; the current batch prefetch prevents that path from running. Operators expect the integration to **self-heal**: recreate a replacement work item when the mapped id is gone and the Snyk finding is still active, with clear logs identifying which mapping was stale.

## What Changes

- **Batch list resilience**: Pass **`errorPolicy=Omit`** on ADO **List work items (by ids)** so one missing id does not fail the whole HTTP request or sync run.
- **Recreate on missing mapped work item**: When a mapping row has a non-empty **`work_item_id`** but ADO does not return that work item in the batch cache, and the derived Snyk status is **`open`**, **`sync`** SHALL create a **new** Azure Boards work item (subject to existing gates: **`create_new_work_items`**, **`create_only_when_fix_available`**, origin allowlist), upsert the mapping to the new id, and add an audit comment referencing the prior id (and Boards URL when constructible) — same audit semantics as **P2-FR-8** **`new_work_item`** / **`reopen_existing`** fallback.
- **Close path unchanged**: When derived status is **`resolved`** or **`ignored`** and the mapped work item is missing, **`sync`** SHALL **not** recreate; it SHALL log and skip ADO mutation for that issue.
- **Structured observability**: Emit a structured audit/log record when a mapped id is missing from the batch cache, including **`prior_work_item_id`**, Snyk issue key, and **`action`** (`recreate` or `skip`) so operators can identify the stale mapping without parsing HTTP URLs (query **`ids`** are not logged in **`safe_target`** today).
- **Documentation**: **`README.md`** troubleshooting — deleted mapped work items, self-heal behavior, and that **`work_item_type`** (and related state/description field settings) apply to **new creates only**; existing mapped work items are updated in place and are **not** re-typed when configuration changes.
- **Global failure fix**: Batch prefetch errors attributable to a single missing id SHALL NOT fail the whole run; aligns with **Per-issue errors do not fail the whole sync run**.

## Capabilities

### New Capabilities

- *(None)*

### Modified Capabilities

- **`sync-lifecycle`**: Missing mapped work item handling (recreate for open; skip for close path); batch prefetch must not abort run; structured log for stale mappings.
- **`azure-devops-client`**: List-by-ids URL includes **`errorPolicy=Omit`**.
- **`integration-apis`**: Document **`errorPolicy=Omit`** on List work items (by ids).
- **`observability`**: Structured log event for missing mapped work item id (prior id, issue key, action).

## Impact

- **`src/integrations/azure_devops/urls.py`**, **`src/sync/run.py`**, **`src/observability/`** (new or extended audit helper)
- **`tests/test_azure_devops_urls.py`**, **`tests/test_azure_devops_client.py`**, **`tests/test_sync_run_branch.py`**
- **`README.md`**, **`CONFIGURATION.md`** (operator troubleshooting)
