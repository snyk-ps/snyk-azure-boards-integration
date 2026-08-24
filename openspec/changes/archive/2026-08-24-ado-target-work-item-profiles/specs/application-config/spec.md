## ADDED Requirements

### Requirement: Azure Boards ado_targets entry schema

Under **`azure_boards`**, the configuration SHALL support an optional **`ado_targets`** list of mappings that define work-item taxonomy for a specific Azure DevOps **(organization, project)** destination.

Each **`ado_targets[]`** element SHALL be a mapping containing:

- **`organization`**: required non-empty string after trim — Azure DevOps organization name.
- **`project`**: required non-empty string after trim — Azure DevOps project name or id.
- Optional work-item taxonomy keys (subset of **`azure_boards.defaults`**): **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`** (**`tags`**, **`json_patch`**).

The loader SHALL reject:

- Entries missing **`organization`** or **`project`**, or with empty strings after trim for those keys.
- Duplicate **`(organization, project)`** pairs after trim (case-sensitive comparison on trimmed values).
- Non-string values for taxonomy keys or invalid **`work_item_template`** shape (same rules as **`defaults.work_item_template`**).
- **`ado_targets`** as a direct child of any key other than **`azure_boards`**.

When **`ado_targets`** is omitted or an empty list, behavior SHALL be unchanged from configurations without this key.

#### Scenario: Valid ado_targets row loads

- **WHEN** YAML contains one **`ado_targets`** row with non-empty **`organization`** **`myado`**, **`project`** **`PaymentsProject`**, and **`work_item_type`** **`Bug`**
- **THEN** loading SHALL succeed and expose that profile for **`sync`**

#### Scenario: Duplicate ado_targets key rejected

- **WHEN** two **`ado_targets`** rows share the same **`organization`** and **`project`** after trim
- **THEN** loading SHALL fail with a clear, non-secret error identifying the duplicate pair

#### Scenario: Omitted ado_targets unchanged behavior

- **WHEN** YAML omits **`ado_targets`**
- **THEN** loading SHALL succeed and **`sync`** SHALL use existing **`defaults`** and **`org_mappings[].overrides`** merge rules only

---

### Requirement: ado_targets operator documentation

**`CONFIGURATION.md`** and **`README.md`** SHALL document **`azure_boards.ado_targets`**: purpose (per ADO destination work-item profiles for multi-project CSV routing), allowed keys, duplicate-key rejection, and precedence relative to **`defaults`**, **`org_mappings[].overrides`**, and optional CSV taxonomy columns.

Documentation SHALL recommend defining one **`ado_targets`** entry for each distinct ADO **`(organization, project)`** referenced in **`repo-mapping.csv`** **Area Path** first segments and in the active **`org_mappings`** baseline target.

#### Scenario: CONFIGURATION documents ado_targets

- **WHEN** an operator reads **`CONFIGURATION.md`**
- **THEN** they SHALL find **`ado_targets`** schema, precedence, and multi-project routing guidance without reading source code

---

## MODIFIED Requirements

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`**, including **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_description_appendix`**, **`sync_included_snyk_origins`**, and **`area_path`**. Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

For **work-item taxonomy** fields only, when an explicit **`ado_targets`** entry exists for the same **`(organization, project)`** as an **`org_mappings`** row, **`sync`** SHALL prefer the **`ado_targets`** profile over **`org_mappings[].overrides`** for those fields at runtime. **`org_mappings[].overrides`** work-item fields SHALL still apply when no matching **`ado_targets`** entry exists for that **`(organization, project)`**.

The loader SHALL reject entries missing required keys or containing empty strings for **`organization`**, **`project`**, or **`snyk_org_id`** with a clear, non-secret error.

#### Scenario: Valid org_mappings row loads

- **WHEN** YAML contains one **`org_mappings`** row with non-empty **`organization`**, **`project`**, **`snyk_org_id`**, and **`snyk_org_slug`**
- **THEN** loading SHALL succeed and expose that row for **`sync`**

#### Scenario: Invalid org_mappings row rejected

- **WHEN** a row omits **`snyk_org_id`** or supplies an empty **`organization`**
- **THEN** loading SHALL fail with a clear error that does not include secrets

#### Scenario: Org_mappings row missing snyk_org_slug rejected at load

- **WHEN** a row omits **`snyk_org_slug`** or supplies an empty string for **`snyk_org_slug`**
- **THEN** loading SHALL fail with a clear error that does not include secrets

#### Scenario: Overrides may set description appendix per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.work_item_description_appendix`** with a string value
- **THEN** loading SHALL succeed and merged configuration SHALL expose that override for **`sync`** description assembly for issues routed through that row

#### Scenario: Overrides may set description field per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.work_item_description_field`** with a non-empty string
- **THEN** loading SHALL succeed and **`sync`** SHALL use that field reference for issues routed through that row when no higher-precedence source applies

#### Scenario: Overrides may set origin allowlist per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.sync_included_snyk_origins`** with a valid comma-separated allowlist string
- **THEN** loading SHALL succeed and **`sync`** SHALL use that row’s merged effective allowlist when classifying issues for that routing context

#### Scenario: Overrides may set area path per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.area_path`** with a non-empty string
- **THEN** loading SHALL succeed and merged configuration SHALL expose that area path for YAML fallback routing when no CSV row matches

#### Scenario: ado_targets beats org override for same ADO target

- **WHEN** **`ado_targets`** defines **`work_item_type`** **`Bug`** for **`myado`/`PaymentsProject`** and an **`org_mappings`** row for the same **`(organization, project)`** sets **`overrides.work_item_type`** **`Task`**
- **THEN** **`sync`** SHALL use **`Bug`** for work items created in **`PaymentsProject`** when no CSV taxonomy override applies
