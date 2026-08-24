## ADDED Requirements

### Requirement: Per-issue ADO target from repo mapping CSV

When a **`repo-mapping.csv`** row matches an issue, **`sync`** SHALL use the CSV-resolved **ADO organization** and **ADO project** (first **Area Path** segment) for all Azure DevOps Work Item Tracking REST calls for that issue, including create, update, comment, batch prefetch partition, and mapping-store **`organization`** / **`project`** fields on upsert.

When no CSV row matches, **`sync`** SHALL use the merged YAML **`organization`** and **`project`** for the active **`org_mappings`** iteration or group-scoped defaults (unchanged behavior).

**`sync`** SHALL NOT require multiple **`org_mappings`** rows for the same **`snyk_org_id`** to achieve multi-project routing; CSV supplies per-repo ADO targets within one Snyk org.

#### Scenario: Matched repo routes to CSV ADO project

- **WHEN** an issue's Snyk project matches a CSV row with **`ADO Organization`** **`myado`** and **`Area Path`** **`FrontendProject\\UI`**
- **THEN** **`sync`** SHALL create or update work items using organization **`myado`** and project **`FrontendProject`**

#### Scenario: Unmatched repo uses YAML ADO target

- **WHEN** no CSV row matches and the active **`org_mappings`** row has **`organization`** **`myado`** and **`project`** **`DefaultProject`**
- **THEN** **`sync`** SHALL use **`myado`** and **`DefaultProject`** for Azure DevOps calls for that issue

---

### Requirement: Multi-project batch work item prefetch

When **`sync`** batch-prefetches mapped work items before the per-issue loop, it SHALL group work item ids by the **stored** **`organization`** and **`project`** on each mapping row (using the active config target when no row exists). It SHALL invoke Azure DevOps **List work items (by ids)** once per distinct **(organization, project)** partition with **`errorPolicy=Omit`**.

A missing id in one partition SHALL NOT cause the entire **`sync`** run to fail.

#### Scenario: Prefetch partitions by stored ADO target

- **WHEN** mapping rows reference work items in **`myado/ProjectA`** and **`myado/ProjectB`**
- **THEN** **`sync`** SHALL issue separate batch list calls for each project before processing issues

#### Scenario: Single missing id does not abort run

- **WHEN** one mapped work item id is missing from ADO in a batch partition
- **THEN** **`sync`** SHALL continue processing other issues in the run

---

### Requirement: Routing migration when CSV ADO target changes

When a mapping row exists and the stored **`organization`** or **`project`** differs from the newly resolved effective ADO target for that issue, **`sync`** SHALL apply the following rules:

- If derived Snyk status is **`open`**, **`sync`** SHALL treat the row as requiring recreation in the new ADO target (subject to **`create_new_work_items`**, origin allowlist, and **`create_only_when_fix_available`** gates). After creating the replacement work item, **`sync`** SHALL upsert the mapping row with the new **`work_item_id`**, **`organization`**, and **`project`**, and SHALL add an audit comment on the **new** work item per **P2-FR-9** documenting the prior **`work_item_id`** and old and new ADO targets.

- If derived Snyk status is **`resolved`** or **`ignored`**, **`sync`** SHALL NOT recreate. When the prior work item is reachable in the **stored** ADO target, **`sync`** SHALL add an audit comment on that work item per **P2-FR-9** documenting the mapping retarget to the new ADO target. **`sync`** SHALL then upsert the mapping row with the new **`organization`** and **`project`** while retaining the existing **`work_item_id`**.

- When the prior work item returns **404** on the close path, **`sync`** SHALL upsert the mapping row with the new ADO target without ADO mutation and SHALL emit a structured log record (no secrets).

#### Scenario: Open issue routing migration recreates with audit comment

- **WHEN** a mapping row references work item **`W`** in **`O1/P1`**, CSV now resolves **`O2/P2`**, and derived Snyk status is **`open`**
- **THEN** **`sync`** SHALL create a new work item in **`O2/P2`**, upsert the mapping to the new id, and add an audit comment on the new work item referencing **`W`**, **`O1/P1`**, and **`O2/P2`**

#### Scenario: Resolved issue routing migration comments on existing work item

- **WHEN** derived status is **`resolved`**, the mapped work item exists in the stored old target, and CSV resolves a new ADO target
- **THEN** **`sync`** SHALL add an audit comment on the existing work item documenting the mapping retarget and SHALL upsert the store with the new **`organization`** and **`project`** without recreating

#### Scenario: Resolved issue migration skips comment when work item missing

- **WHEN** derived status is **`resolved`**, the mapped work item returns **404** in the stored old target, and CSV resolves a new ADO target
- **THEN** **`sync`** SHALL upsert the store with the new ADO target and SHALL NOT fail the run

---

## MODIFIED Requirements

### Requirement: Effective area path and assignee resolution for sync

For each issue processed by **`sync`**, after **`snyk_project_name`** and **`snyk_project_origin`** are known (from persisted mapping row and/or Snyk Projects API refresh per existing rules), the run SHALL resolve:

- **Effective ADO organization and project** per **`repo-area-path-mapping`**: CSV row **ADO Organization** and first **Area Path** segment when matched; otherwise merged YAML **`organization`** and **`project`** for the active routing context.
- **Effective area path** per **`repo-area-path-mapping`** precedence: CSV row full **Area Path** → **`org_mappings[].overrides.area_path`** → **`defaults.area_path`** → unset.
- **Effective assignee** per **`repo-area-path-mapping`**: when a CSV row matches with non-empty **Assignee (Optional)** or legacy **Assignee**, that value; otherwise merged template assignee rules unchanged.

Resolution SHALL occur per issue. The implementation MAY log **`ado_target_source`** as **`csv`** or **`config`** and **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, or **`none`** at INFO without secrets.

#### Scenario: CSV match supplies ADO target area path and assignee

- **WHEN** a CSV row matches with **`ADO Organization`** **`myado`**, **`Area Path`** **`Proj\\TeamA`**, and **`Assignee (Optional)`** **`user@example.com`**
- **THEN** the effective ADO organization SHALL be **`myado`**, effective ADO project SHALL be **`Proj`**, effective area path SHALL be **`Proj\\TeamA`**, and effective assignee SHALL be **`user@example.com`**

#### Scenario: No CSV match uses org override for area path

- **WHEN** no CSV row matches and merged **`overrides.area_path`** is **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamB`** and ADO org/project SHALL come from YAML

#### Scenario: No path configured omits AreaPath patch

- **WHEN** no CSV row matches and both org override and **`defaults.area_path`** are unset or whitespace-only
- **THEN** the effective area path SHALL be unset and **`sync`** SHALL NOT include **`System.AreaPath`** in the patch

---

### Requirement: System.AreaPath on work item create and recreate

When **`sync`** creates a new Azure Boards work item or recreates a work item (including missing mapped work item replacement, **routing migration** recreation, and **`reopen_work_item_policy`** paths that create a new item), and the effective area path is non-empty after trim, the JSON Patch sent to Azure DevOps SHALL include an **`add`** operation on **`/fields/System.AreaPath`** with that value.

Create and recreate operations SHALL target the **effective ADO organization and project** resolved for that issue (CSV or YAML).

When the effective assignee from resolution is non-empty, the create patch SHALL include **`/fields/System.AssignedTo`** with that value, overriding template assignee when CSV supplied it.

When effective area path is unset, create behavior for other fields SHALL be unchanged from prior requirements.

#### Scenario: Create sets area path from CSV in CSV ADO project

- **WHEN** **`sync`** creates a work item in CSV project **`PaymentsProject`** and effective area path is **`PaymentsProject\\Payments`**
- **THEN** the create JSON Patch SHALL include **`/fields/System.AreaPath`** with that value and REST calls SHALL use project **`PaymentsProject`**

#### Scenario: Create without resolved area path

- **WHEN** **`sync`** creates a work item and effective area path is unset
- **THEN** the create JSON Patch SHALL NOT include **`/fields/System.AreaPath`**

#### Scenario: Recreate applies area path like create

- **WHEN** **`sync`** recreates a work item (including routing migration) and effective area path is non-empty
- **THEN** the create JSON Patch for the new work item SHALL include **`/fields/System.AreaPath`**

---

### Requirement: System.AreaPath update and audit comment on path change

When **`sync`** updates an existing mapped work item in the **stored** ADO target (stored **`organization`** and **`project`** match the effective resolved target), and the effective area path is non-empty and **differs** from the work item's current **`System.AreaPath`** field value (read from the normalized work item record or an explicit **`get_work_item`** fetch), **`sync`** SHALL:

1. Include **`/fields/System.AreaPath`** in the update JSON Patch with the new effective value.
2. After a successful update (or as part of the same successful mutation sequence), add a work item **audit comment** per **P2-FR-9** stating that the area path moved from the previous value to the new value.

When the previous **`System.AreaPath`** is missing or empty, the comment SHALL indicate the prior location as **`(unset)`** or equivalent non-secret placeholder documented in implementation.

When effective area path equals the current value, **`sync`** SHALL NOT patch **`System.AreaPath`** solely for this feature and SHALL NOT add an area-path move comment.

When effective assignee from CSV resolution is non-empty and differs from current **`System.AssignedTo`**, the update patch SHALL set **`/fields/System.AssignedTo`** to the CSV value.

When stored ADO target differs from effective resolved target, **`sync`** SHALL follow **Routing migration when CSV ADO target changes** instead of patching the work item in the old target.

#### Scenario: Update moves area path and comments

- **WHEN** the mapped work item has **`System.AreaPath`** **`Old\\Path`**, effective area path is **`New\\Path`**, stored and effective ADO targets match, and **`sync`** updates the work item
- **THEN** the update patch SHALL set **`System.AreaPath`** to **`New\\Path`** and an audit comment SHALL reference **`Old\\Path`** and **`New\\Path`**

#### Scenario: Unchanged area path skips move comment

- **WHEN** effective area path equals the work item's current **`System.AreaPath`**
- **THEN** **`sync`** SHALL NOT add an area-path move audit comment for this feature

#### Scenario: CSV assignee applied on update

- **WHEN** a CSV row matches with **`Assignee (Optional)`** **`user@example.com`** and the work item's assignee differs
- **THEN** the update patch SHALL set **`System.AssignedTo`** to **`user@example.com`**

#### Scenario: ADO target change triggers migration not in-place update

- **WHEN** stored mapping target is **`myado/OldProject`** and effective resolved target is **`myado/NewProject`**
- **THEN** **`sync`** SHALL NOT PATCH the work item in **`OldProject`** for routine open-issue updates and SHALL follow routing migration rules
