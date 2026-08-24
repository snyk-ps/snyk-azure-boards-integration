## MODIFIED Requirements

### Requirement: Work item type and Boards state names from configuration

Work item **create** SHALL use the **per-issue effective **`work_item_type`** resolved per **`repo-area-path-mapping`** **Work item taxonomy precedence** as the WIT **`$type`** segment (default **`Task`** when omitted after full precedence). **Create** includes new work items for unmapped issues, reopen replacement paths, routing-migration recreation, and replacement creates when a mapped work item id is missing and derived status is **`open`** per **Recreate Azure Boards work item when mapped id is missing and finding is open**. **Update** paths (**`PATCH`** on an existing id) SHALL **not** change the Boards work item type; configuration changes to **`work_item_type`** apply to **new** work items only, not re-typing of existing mapped items. When a work item shall represent an **active** finding, the sync SHALL transition or set Boards **`System.State`** to the per-issue effective **`work_item_state_active`**. When a finding is on the **close path** (**derived `snyk_status`** is **`resolved`** or **`ignored`**), the sync SHALL set the Boards closed disposition using the per-issue effective **`work_item_state_closed`**. Operators MUST configure values that exist for their process; the application SHALL treat these as opaque strings after non-empty validation.

Per-issue effective work item config SHALL be resolved **after** effective ADO **`(organization, project)`** is known, so CSV-routed issues in a different ADO project than the **`org_mappings`** baseline use the correct type and states for that destination.

#### Scenario: Defaults apply when keys omitted

- **WHEN** the three keys are omitted from YAML and not overridden by higher-precedence layers
- **THEN** the effective values SHALL be **`Task`**, **`New`**, and **`Closed`** respectively for sync

#### Scenario: ado_targets type used for CSV-routed project

- **WHEN** CSV routes an issue to **`myado`/`PaymentsProject`**, **`ado_targets`** defines **`work_item_type`** **`Bug`**, and **`defaults.work_item_type`** is **`Task`**
- **THEN** create for that issue SHALL use WIT **`$Bug`**

#### Scenario: Config type change does not re-type existing mapped work items

- **WHEN** a mapping row references an existing Azure DevOps work item id and the operator changes effective **`work_item_type`** from **`Bug`** to **`Task`**
- **THEN** **`sync`** SHALL continue to **`PATCH`** that existing work item by id and SHALL NOT recreate it solely because the configured type changed

---

### Requirement: Effective work item description field resolution

For each **per-issue** ADO routing context (**organization**, **project**, effective **`work_item_type`**, and effective **`work_item_description_field`** configuration per **Work item taxonomy precedence**), **`sync`** SHALL determine an **effective description field reference name** used for all Snyk narrative JSON Patch operations (create and update) for that issue.

When **`work_item_description_field`** is **not** configured (auto mode) after precedence, **`sync`** SHALL query Azure DevOps for fields defined on the effective work item type and SHALL select the first available reference name in this order:

1. **`System.Description`**
2. **`Microsoft.VSTS.TCM.ReproSteps`**

If neither reference name is present, **`sync`** SHALL exit non-zero **before** the per-issue loop with a clear, non-secret error identifying the organization, project, work item type, and attempted reference names.

When **`work_item_description_field`** **is** configured to a non-empty string after precedence, **`sync`** SHALL use that reference name directly without fallback. When ADO is reachable at startup, **`sync`** SHALL validate that the explicit reference name appears on the effective work item type’s field list and SHALL exit non-zero before the per-issue loop if validation fails.

Resolution SHALL occur at **`sync`** startup for each distinct **(organization, project, work_item_type, description_field_config)** tuple from **`ado_targets`**, **`org_mappings`**, and **`defaults`**, and MAY be cached for the duration of that run. Per-issue contexts not warmed at startup SHALL be resolved on first use and cached.

#### Scenario: Auto mode selects Description for Task

- **WHEN** auto mode is active, the effective work item type is **`Task`**, and **`System.Description`** exists on that type
- **THEN** the effective description field SHALL be **`System.Description`**

#### Scenario: Auto mode selects Repro Steps for Bug without Description

- **WHEN** auto mode is active, the effective work item type is **`Bug`**, **`System.Description`** is not defined on that type, and **`Microsoft.VSTS.TCM.ReproSteps`** is defined
- **THEN** the effective description field SHALL be **`Microsoft.VSTS.TCM.ReproSteps`**

#### Scenario: Explicit override bypasses fallback

- **WHEN** effective configuration sets **`work_item_description_field`** to **`Microsoft.VSTS.TCM.ReproSteps`** and **`System.Description`** also exists on the type
- **THEN** the effective description field SHALL be **`Microsoft.VSTS.TCM.ReproSteps`** only

#### Scenario: Auto mode fails when no supported field exists

- **WHEN** auto mode is active and neither **`System.Description`** nor **`Microsoft.VSTS.TCM.ReproSteps`** is defined on the effective work item type
- **THEN** **`sync`** SHALL fail before processing issues

#### Scenario: ado_targets warmed at startup

- **WHEN** **`ado_targets`** defines a profile for **`myado`/`PaymentsProject`** with **`work_item_type`** **`Bug`**
- **THEN** **`sync`** SHALL warm description-field resolution for that context before the per-issue loop

---

### Requirement: Effective area path and assignee resolution for sync

For each issue processed by **`sync`**, after **`snyk_project_name`** and **`snyk_project_origin`** are known (from persisted mapping row and/or Snyk Projects API refresh per existing rules), the run SHALL resolve:

- **Effective ADO organization and project** per **`repo-area-path-mapping`**: CSV row **ADO Organization** and first **Area Path** segment when matched; otherwise merged YAML **`organization`** and **`project`** for the active routing context.
- **Effective area path** per **`repo-area-path-mapping`** precedence: CSV row full **Area Path** → **`org_mappings[].overrides.area_path`** → **`defaults.area_path`** → unset.
- **Effective assignee** per **`repo-area-path-mapping`**: when a CSV row matches with non-empty **Assignee (Optional)** or legacy **Assignee**, that value; otherwise merged template assignee rules unchanged.
- **Effective work item taxonomy** per **`repo-area-path-mapping`** **Work item taxonomy precedence**: type, states, description field config, and template/tags.

Resolution SHALL occur per issue. The implementation MAY log **`ado_target_source`** as **`csv`** or **`config`**, **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, or **`none`**, and **`work_item_config_source`** as **`csv`**, **`ado_target`**, **`org_override`**, or **`defaults`** at INFO without secrets. The implementation SHOULD log effective **`work_item_type`** and **`work_item_state_active`** at INFO on create/update paths without secrets.

#### Scenario: CSV match supplies ADO target area path and assignee

- **WHEN** a CSV row matches with **`ADO Organization`** **`myado`**, **`Area Path`** **`Proj\\TeamA`**, and **`Assignee (Optional)`** **`user@example.com`**
- **THEN** the effective ADO organization SHALL be **`myado`**, effective ADO project SHALL be **`Proj`**, effective area path SHALL be **`Proj\\TeamA`**, and effective assignee SHALL be **`user@example.com`**

#### Scenario: CSV-routed issue uses ado_targets taxonomy

- **WHEN** CSV routes to **`myado`/`PaymentsProject`**, **`ado_targets`** defines **`work_item_state_active`** **`New`**, and **`defaults.work_item_state_active`** is **`To Do`**
- **THEN** effective active state SHALL be **`New`** and **`work_item_config_source`** SHALL be **`ado_target`**

#### Scenario: No CSV match uses org override for area path

- **WHEN** no CSV row matches and merged **`overrides.area_path`** is **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamB`** and ADO org/project SHALL come from YAML

#### Scenario: No path configured omits AreaPath patch

- **WHEN** no CSV row matches and both org override and **`defaults.area_path`** are unset or whitespace-only
- **THEN** the effective area path SHALL be unset and **`sync`** SHALL NOT include **`System.AreaPath`** in the patch

---

### Requirement: System.AreaPath on work item create and recreate

When **`sync`** creates a new Azure Boards work item or recreates a work item (including missing mapped work item replacement, **routing migration** recreation, and **`reopen_work_item_policy`** paths that create a new item), and the effective area path is non-empty after trim, the JSON Patch sent to Azure DevOps SHALL include an **`add`** operation on **`/fields/System.AreaPath`** with that value.

Create and recreate operations SHALL target the **effective ADO organization and project** resolved for that issue (CSV or YAML) and SHALL use the **per-issue effective **`work_item_type`**, states, description field, and template** from **Work item taxonomy precedence**.

When the effective assignee from resolution is non-empty, the create patch SHALL include **`/fields/System.AssignedTo`** with that value, overriding template assignee when CSV supplied it.

When effective area path is unset, create behavior for other fields SHALL be unchanged from prior requirements.

#### Scenario: Create sets area path from CSV in CSV ADO project

- **WHEN** **`sync`** creates a work item in CSV project **`PaymentsProject`** and effective area path is **`PaymentsProject\\Payments`**
- **THEN** the create JSON Patch SHALL include **`/fields/System.AreaPath`** with that value, REST calls SHALL use project **`PaymentsProject`**, and WIT **`$type`** SHALL match per-issue effective work item type

#### Scenario: Create without resolved area path

- **WHEN** **`sync`** creates a work item and effective area path is unset
- **THEN** the create JSON Patch SHALL NOT include **`/fields/System.AreaPath`**

#### Scenario: Recreate applies area path like create

- **WHEN** **`sync`** recreates a work item (including routing migration) and effective area path is non-empty
- **THEN** the create JSON Patch for the new work item SHALL include **`/fields/System.AreaPath`** and use per-issue effective taxonomy
