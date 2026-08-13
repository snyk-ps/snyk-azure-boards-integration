## Context

**`sync`** collects mapped **`work_item_id`** values, calls **`batch_get_work_items`** once per batch, then processes each issue. Today:

1. List URL omits **`errorPolicy`** → ADO default **`Fail`** → one deleted id → HTTP **404** → whole run fails before the per-issue loop.
2. Per-issue code at **`cache.get(wid)`** would log and skip, but is never reached on batch failure.
3. **`reopen_existing`** already recreates on single-item GET **404** during reopen transitions; there is no equivalent for ordinary **open** mapped issues with stale ids.
4. **`integration_http`** audit **`safe_target`** strips query strings, so operators cannot see which **`ids`** failed in batch logs.

Customer and local reproduction: one deleted work item + mapping row → container job **`sync_outcome: failure`**.

## Goals / Non-Goals

**Goals:**

- Sync run completes (**exit 0**) when only per-issue problems occur (deleted mapped ids).
- **Open** findings with stale **`work_item_id`**: create replacement work item using **current** merged **`work_item_type`**, update mapping, audit comment with prior id.
- Batch list uses **`errorPolicy=Omit`** per [ADO List URI parameters](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/list?view=azure-devops-rest-7.1#uri-parameters).
- Structured **`integration_audit`** record (**`event`:** **`missing_mapped_work_item`**) with **`prior_work_item_id`**, Snyk issue key, and **`action`** (`recreate` | `skip`) for Log Analytics queries.
- **`README.md`**: document self-heal behavior and that **`work_item_type`** changes apply to **new creates only**.

**Non-Goals:**

- Implement **`workitemsbatch`** POST API (stay on GET list; **`azure-devops-client`** v1 constraint).
- New YAML toggle for recreate-vs-skip (always recreate for **open** when gates allow).
- Auto-delete mapping rows on missing id (mapping is updated on successful recreate).
- Recreate for **resolved**/**ignored** findings (no new closed ticket for already-closed Snyk issues).
- Re-type or bulk-recreate existing mapped work items when **`work_item_type`** changes in config (updates stay **PATCH** on the same id).

## Decisions

1. **`errorPolicy=Omit` on list URL** — Add to **`work_items_list_url`** query string. Missing ids omitted from **`value`** array; no HTTP error for not-found ids. **Alternative rejected:** catch **404** on batch and retry per-id (more round-trips).

2. **Recreate branch in `_sync_one_issue`** — After **`cache.get(wid)`** is **`None`** and **`row`** has non-empty **`work_item_id`**:
   - If **`new_status == open`**: delegate to shared create-replacement path (reuse create patch + audit comment with **`prior_work_item_id`** / URL), same gates as unmapped create. New work item uses **current** merged **`work_item_type`**.
   - If **`new_status`** is **`resolved`** or **`ignored`**: emit structured log with **`action`:** **`skip`**, skip ADO mutation (leave mapping row unchanged).

3. **Share logic with reopen fallback** — Extract or reuse the existing "create new work item + audit prior id" block from **`reopen`** **`new_work_item`** / **`reopen_existing`** fallback to avoid duplication.

4. **`create_new_work_items: false`** — When mapped id missing and status **open**, structured log with **`action`:** **`skip`**, no recreate (**P2-FR-11**).

5. **Structured observability** — Add **`log_missing_mapped_work_item(...)`** on **`integration_audit`** logger with **`event`:** **`missing_mapped_work_item`**, fields: **`prior_work_item_id`**, **`issue_key`**, **`action`**, optional **`sync_run_id`**. Do **not** log secrets or full ADO URLs with tokens.

6. **Work item type documentation** — **`README.md`** troubleshooting table: changing **`work_item_type`** / states / description field affects **creates** and **field resolution for PATCH** on existing items; it does **not** change the Boards type of already-created work items.

## Risks / Trade-offs

- **[Risk]** Operator deleted WI intentionally to stop sync → recreation creates a new ticket. **Mitigation:** document; **`create_new_work_items: false`** stops recreation.
- **[Risk]** Duplicate tickets if id missing transiently (ADO blip). **Mitigation:** accept; audit comment and structured log aid triage.
- **[Risk]** **`errorPolicy=Omit`** hides permission errors for some ids. **Mitigation:** treat cache miss like missing; recreate or skip per status; auth errors on create still surface per-issue.
- **[Risk]** Config type change + old Bug items → PATCH uses Task description field. **Mitigation:** README note; out of scope for auto re-type.

## Migration Plan

Deploy new image; no config migration. Stale mappings self-heal on next successful **open**-issue sync.

## Open Questions

- None blocking.
