## ADDED Requirements

### Requirement: Structured audit log when mapped Azure DevOps work item id is missing

When **`sync`** detects that a mapping row has a non-empty **`work_item_id`** but that id is absent from the batch prefetch cache (after **`errorPolicy=Omit`** list-by-ids), the application SHALL emit **one** structured audit record on the **`integration_audit`** logger before skipping or recreating for that issue.

The record SHALL use **`event`:** **`missing_mapped_work_item`** and SHALL appear under the NDJSON **`record`** object per **Requirement: NDJSON structured CLI logging (P2-FR-6.x operator usability)**. Fields SHALL include at minimum:

- **`prior_work_item_id`**: the stored mapped id (string)
- **`issue_key`**: the Snyk issue key or identifier used in sync diagnostics (non-secret)
- **`action`**: **`recreate`** when a replacement work item will be created for an **open** finding; **`skip`** when Azure DevOps mutation is skipped (for example close path, **`create_new_work_items`** false, or create gates block recreation)

The record MAY include **`sync_run_id`** when a sync run is active. The record SHALL NOT include secrets, PAT material, or **`Authorization`** values.

#### Scenario: Missing mapped id on open issue logs recreate action

- **WHEN** batch prefetch omits mapped id **456**, derived status is **`open`**, and **`sync`** will create a replacement work item
- **THEN** logs SHALL contain a **`missing_mapped_work_item`** audit record with **`prior_work_item_id`** **456** and **`action`** **`recreate`**

#### Scenario: Missing mapped id on resolved issue logs skip action

- **WHEN** batch prefetch omits mapped id **456** and derived status is **`resolved`**
- **THEN** logs SHALL contain a **`missing_mapped_work_item`** audit record with **`prior_work_item_id`** **456** and **`action`** **`skip`**
