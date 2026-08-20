## ADDED Requirements

### Requirement: Effective area path and assignee resolution for sync

For each issue processed by **`sync`**, after **`snyk_project_name`** and **`snyk_project_origin`** are known (from persisted mapping row and/or Snyk Projects API refresh per existing rules), the run SHALL resolve:

- **Effective area path** per **`repo-area-path-mapping`** precedence: CSV row → **`org_mappings[].overrides.area_path`** → **`defaults.area_path`** → unset.
- **Effective assignee** per **`repo-area-path-mapping`**: when a CSV row matches with non-empty **Assignee**, that value; otherwise merged template assignee rules unchanged.

Resolution SHALL occur per issue in the active ADO routing context. The implementation MAY log **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, or **`none`** at INFO without secrets.

#### Scenario: CSV match supplies area path and assignee

- **WHEN** a CSV row matches with **`Area Path`** **`Proj\\TeamA`** and **`Assignee`** **`user@example.com`**
- **THEN** the effective area path SHALL be **`Proj\\TeamA`** and effective assignee SHALL be **`user@example.com`**

#### Scenario: No CSV match uses org override

- **WHEN** no CSV row matches and merged **`overrides.area_path`** is **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamB`**

#### Scenario: No path configured omits AreaPath patch

- **WHEN** no CSV row matches and both org override and **`defaults.area_path`** are unset or whitespace-only
- **THEN** the effective area path SHALL be unset and **`sync`** SHALL NOT include **`System.AreaPath`** in the patch

---

### Requirement: System.AreaPath on work item create and recreate

When **`sync`** creates a new Azure Boards work item or recreates a work item (including missing mapped work item replacement and **`reopen_work_item_policy`** paths that create a new item), and the effective area path is non-empty after trim, the JSON Patch sent to Azure DevOps SHALL include an **`add`** operation on **`/fields/System.AreaPath`** with that value.

When the effective assignee from resolution is non-empty, the create patch SHALL include **`/fields/System.AssignedTo`** with that value, overriding template assignee when CSV supplied it.

When effective area path is unset, create behavior for other fields SHALL be unchanged from prior requirements.

#### Scenario: Create sets area path from CSV

- **WHEN** **`sync`** creates a work item and effective area path is **`MyProject\\Payments`**
- **THEN** the create JSON Patch SHALL include **`/fields/System.AreaPath`** with that value

#### Scenario: Create without resolved area path

- **WHEN** **`sync`** creates a work item and effective area path is unset
- **THEN** the create JSON Patch SHALL NOT include **`/fields/System.AreaPath`**

#### Scenario: Recreate applies area path like create

- **WHEN** **`sync`** recreates a missing mapped work item and effective area path is non-empty
- **THEN** the create JSON Patch for the new work item SHALL include **`/fields/System.AreaPath`**

---

### Requirement: System.AreaPath update and audit comment on path change

When **`sync`** updates an existing mapped work item (including routine open-finding updates and close-path transitions that PATCH the item), and the effective area path is non-empty and **differs** from the work item’s current **`System.AreaPath`** field value (read from the normalized work item record or an explicit **`get_work_item`** fetch), **`sync`** SHALL:

1. Include **`/fields/System.AreaPath`** in the update JSON Patch with the new effective value.
2. After a successful update (or as part of the same successful mutation sequence), add a work item **audit comment** per **P2-FR-9** stating that the area path moved from the previous value to the new value.

When the previous **`System.AreaPath`** is missing or empty, the comment SHALL indicate the prior location as **`(unset)`** or equivalent non-secret placeholder documented in implementation.

When effective area path equals the current value, **`sync`** SHALL NOT patch **`System.AreaPath`** solely for this feature and SHALL NOT add an area-path move comment.

When effective assignee from CSV resolution is non-empty and differs from current **`System.AssignedTo`**, the update patch SHALL set **`/fields/System.AssignedTo`** to the CSV value.

#### Scenario: Update moves area path and comments

- **WHEN** the mapped work item has **`System.AreaPath`** **`Old\\Path`**, effective area path is **`New\\Path`**, and **`sync`** updates the work item
- **THEN** the update patch SHALL set **`System.AreaPath`** to **`New\\Path`** and an audit comment SHALL reference **`Old\\Path`** and **`New\\Path`**

#### Scenario: Unchanged area path skips move comment

- **WHEN** effective area path equals the work item’s current **`System.AreaPath`**
- **THEN** **`sync`** SHALL NOT add an area-path move audit comment for this feature

#### Scenario: CSV assignee applied on update

- **WHEN** a CSV row matches with **`Assignee`** **`user@example.com`** and the work item’s assignee differs
- **THEN** the update patch SHALL set **`System.AssignedTo`** to **`user@example.com`**

---

### Requirement: Repo mapping CSV loaded at sync startup

**`sync`** SHALL load the effective **`repo-mapping.csv`** index once at startup after configuration merge and before the per-issue loop, per **`repo-area-path-mapping`**. CSV load failures SHALL cause **`sync`** to exit non-zero before processing issues.

Hot-reload of CSV content during a single run is out of scope; a new run after file update on Azure Files (following container restart/revision) reloads the file.

#### Scenario: Sync fails fast on invalid CSV

- **WHEN** the CSV contains duplicate lookup keys
- **THEN** **`sync`** SHALL exit non-zero before the per-issue loop

#### Scenario: Sync proceeds with valid CSV

- **WHEN** the CSV loads successfully
- **THEN** **`sync`** SHALL use the in-memory index for all issues in that run
