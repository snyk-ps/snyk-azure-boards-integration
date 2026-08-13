## 1. Azure DevOps client — batch list resilience

- [x] 1.1 Add **`errorPolicy=Omit`** to **`work_items_list_url`** in **`src/integrations/azure_devops/urls.py`**.
- [x] 1.2 Update **`tests/test_azure_devops_urls.py`** to assert **`errorPolicy=Omit`** in list-by-ids URLs.

## 2. Observability — missing mapped work item audit

- [x] 2.1 Add **`log_missing_mapped_work_item(...)`** to **`src/observability/integration_audit.py`** with **`event`:** **`missing_mapped_work_item`**, **`prior_work_item_id`**, **`issue_key`**, **`action`**, optional **`sync_run_id`**.
- [x] 2.2 Unit tests for the new audit helper (NDJSON **`record`** shape, no secrets).

## 3. Sync — recreate missing mapped work items

- [x] 3.1 Refactor shared **create replacement work item + audit prior id** helper in **`src/sync/run.py`** (reuse from reopen fallback where possible).
- [x] 3.2 When **`cache.get(wid)`** is **`None`**, mapped **`work_item_id`** non-empty, and derived status is **`open`**: run recreate path subject to **`create_new_work_items`**, **`create_only_when_fix_available`**, and origin gates; upsert new **`work_item_id`** using **current** merged **`work_item_type`**; emit **`missing_mapped_work_item`** with **`action`:** **`recreate`**.
- [x] 3.3 When mapped id missing and derived status is **`resolved`** or **`ignored`**: emit **`missing_mapped_work_item`** with **`action`:** **`skip`**, skip ADO mutation (no recreate).
- [x] 3.4 When mapped id missing, derived status **`open`**, and **`create_new_work_items`** is **false**: emit **`action`:** **`skip`**, skip recreate.

## 4. Tests

- [x] 4.1 **`tests/test_azure_devops_client.py`**: list-by-ids request URL includes **`errorPolicy=Omit`**; partial **`value`** array when an id is omitted.
- [x] 4.2 **`tests/test_sync_run_branch.py`** (or new file): one deleted mapped id + one valid id → sync exit **0**; open issue gets new WI and updated mapping; audit comment mentions prior id.
- [x] 4.3 Test close-path skip when mapped id missing (**resolved**/**ignored**); structured log **`action`:** **`skip`**.
- [x] 4.4 Test **`create_new_work_items: false`** skips recreate when id missing.

## 5. Documentation

- [x] 5.1 **`README.md`** troubleshooting: deleted mapped work item → self-heal recreate for **open** findings; identify stale mappings via **`missing_mapped_work_item`** logs; **`work_item_type`** / state / description field config applies to **new creates** only (existing mapped items are **PATCH**ed in place, not re-typed).
- [x] 5.2 **`CONFIGURATION.md`**: brief note on missing mapped work item behavior and type-change semantics.

## 6. Verification

- [x] 6.1 Run **`pytest`**; Snyk Code / Open Source checks per repo guidelines.

## 7. Archive (human only)

- [ ] **[ ]** Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/recreate-missing-ado-work-items/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive recreate-missing-ado-work-items`** (or project equivalent) to fold deltas into canonical specs.
