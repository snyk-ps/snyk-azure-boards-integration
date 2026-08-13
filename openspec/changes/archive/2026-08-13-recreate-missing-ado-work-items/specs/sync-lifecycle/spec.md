## ADDED Requirements

### Requirement: Recreate Azure Boards work item when mapped id is missing and finding is open

When issues sync persistence holds a row with a **non-empty** **`work_item_id`**, **`sync`** batch-prefetches Azure DevOps work items for the active routing context, and the stored id is **not** returned (for example the work item was deleted or is unreadable with **`errorPolicy=Omit`**), behavior SHALL depend on the **derived Snyk status** for that issue:

- When derived status is **`open`** and **`create_new_work_items`** is **true**, **`sync`** SHALL create a **new** Azure Boards work item using the **current** merged effective **`work_item_type`** and the same gates as unmapped creation (**`create_only_when_fix_available`**, origin allowlist, severity/list filters already applied). It SHALL upsert the mapping row so **`work_item_id`** refers to the **new** work item and SHALL add an audit comment on the new work item referencing the **prior** work item id (and SHOULD include a Boards edit URL when safely constructible), consistent with **P2-FR-8** replacement semantics.
- When derived status is **`open`** and **`create_new_work_items`** is **false**, **`sync`** SHALL log and skip Azure DevOps mutation for that issue without failing the run.
- When derived status is **`resolved`** or **`ignored`**, **`sync`** SHALL **not** create a replacement work item; it SHALL log and skip Azure DevOps mutation for that issue without failing the run.

Batch prefetch of mapped work item ids SHALL **not** cause a global sync failure when individual ids are missing from Azure DevOps.

#### Scenario: Open issue with deleted mapped work item is recreated

- **WHEN** the mapping row has **`work_item_id`** **123**, batch prefetch omits **123**, derived status is **`open`**, **`create_new_work_items`** is **true**, and other create gates pass
- **THEN** **`sync`** SHALL create a new work item using the current merged **`work_item_type`**, upsert the mapping with the new id, and add an audit comment mentioning prior id **123**

#### Scenario: Resolved issue with deleted mapped work item is not recreated

- **WHEN** the mapping row has **`work_item_id`** **123**, batch prefetch omits **123**, and derived status is **`resolved`**
- **THEN** **`sync`** SHALL skip Azure DevOps mutation for that issue and SHALL NOT create a new work item

#### Scenario: One missing id does not fail the sync run

- **WHEN** batch prefetch includes at least one missing work item id and at least one valid id
- **THEN** the sync run SHALL complete the per-issue loop and SHALL exit **0** unless a separate global failure occurs

#### Scenario: create_new_work_items false skips recreate

- **WHEN** the mapped work item id is missing, derived status is **`open`**, and **`create_new_work_items`** is **false**
- **THEN** **`sync`** SHALL skip Azure DevOps mutation for that issue

---

## MODIFIED Requirements

### Requirement: Work item type and Boards state names from configuration

Work item **create** SHALL use the merged effective **`work_item_type`** from **`azure_boards.defaults`** (and **`org_mappings[].overrides`**) as the WIT **`$type`** segment (default **`Task`** when omitted after merge). **Create** includes new work items for unmapped issues, reopen replacement paths, and replacement creates when a mapped work item id is missing and derived status is **`open`** per **Recreate Azure Boards work item when mapped id is missing and finding is open**. **Update** paths (**`PATCH`** on an existing id) SHALL **not** change the Boards work item type; configuration changes to **`work_item_type`** apply to **new** work items only, not re-typing of existing mapped items. When a work item shall represent an **active** finding, the sync SHALL transition or set Boards **`System.State`** to the merged **`work_item_state_active`**. When a finding is on the **close path** (**derived `snyk_status`** is **`resolved`** or **`ignored`**), the sync SHALL set the Boards closed disposition using the merged **`work_item_state_closed`**. Operators MUST configure values that exist for their process; the application SHALL treat these as opaque strings after non-empty validation.

#### Scenario: Defaults apply when keys omitted

- **WHEN** the three keys are omitted from YAML and not overridden by higher-precedence layers
- **THEN** the effective values SHALL be **`Task`**, **`New`**, and **`Closed`** respectively for sync

#### Scenario: Config type change does not re-type existing mapped work items

- **WHEN** a mapping row references an existing Azure DevOps work item id and the operator changes merged **`work_item_type`** from **`Bug`** to **`Task`**
- **THEN** **`sync`** SHALL continue to **`PATCH`** that existing work item by id and SHALL NOT recreate it solely because the configured type changed

---

### Requirement: Per-issue errors do not fail the whole sync run

For errors attributable to a **single** issue (for example Azure PATCH failure for one id, skip due to unexpected Snyk **`status`**, or a mapped Azure DevOps work item id that no longer exists), the application SHALL **log** a concise diagnostic without secrets, **skip** or **self-heal** that issue per the **Recreate Azure Boards work item when mapped id is missing and finding is open** requirement, and **continue** processing remaining issues. The process exit code SHALL be **`0`** when the run completes the full per-issue loop after startup succeeded, even if one or more issues were skipped or healed. **Non-zero** exit codes SHALL be reserved for failures that prevent starting the run or invalidate it globally (for example missing configuration, missing tokens, or client preflight errors before the per-issue loop).

#### Scenario: Exit zero with skips

- **WHEN** at least one issue is skipped due to a per-issue error and no global failure occurred
- **THEN** the process SHALL still exit with code **`0`**

#### Scenario: Exit zero after recreating missing mapped work items

- **WHEN** at least one issue is healed by creating a replacement work item because the prior mapped id was missing
- **THEN** the process SHALL still exit with code **`0`** when no global failure occurred

#### Scenario: Global config failure is non-zero

- **WHEN** required merged configuration or secrets for startup are missing
- **THEN** the process SHALL exit non-zero before issuing per-issue network calls
