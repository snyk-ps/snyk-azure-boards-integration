## ADDED Requirements

### Requirement: Azure Boards defaults — optional work item description field

Under **`azure_boards.defaults`**, the configuration MAY include **`work_item_description_field`**, an optional **non-secret string** holding an Azure DevOps work item field **reference name** (for example **`System.Description`** or **`Microsoft.VSTS.TCM.ReproSteps`**). When omitted or whitespace-only after trim, the effective mode SHALL be **auto**: **`sync`** SHALL resolve the description target per routing context without operator configuration (see **`sync-lifecycle`**).

When **`work_item_description_field`** is a non-empty string after merge, **`sync`** SHALL use that reference name as the sole JSON Patch field for Snyk narrative body content in that routing context (no automatic fallback to other fields).

The loader SHALL reject a non-string value with a clear, non-secret error. The loader SHALL **not** accept **`work_item_description_field`** as a direct child of **`azure_boards`**; it belongs only under **`azure_boards.defaults`**. If the operator supplies a value beginning with **`/fields/`**, the loader SHALL normalize it to the bare reference name before merge.

#### Scenario: Omitted key enables auto mode

- **WHEN** YAML omits **`azure_boards.defaults.work_item_description_field`**
- **THEN** loading SHALL succeed and **`sync`** SHALL use auto resolution (Description, then Repro Steps)

#### Scenario: Explicit field override loads

- **WHEN** YAML sets **`work_item_description_field: Microsoft.VSTS.TCM.ReproSteps`** under **`defaults`**
- **THEN** loading SHALL succeed and merged configuration SHALL expose that reference name for sync in the default routing context

#### Scenario: Flat work_item_description_field under azure_boards rejected

- **WHEN** YAML sets **`azure_boards.work_item_description_field`** at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error directing operators to **`azure_boards.defaults`**

#### Scenario: Non-string description field rejected

- **WHEN** YAML sets **`work_item_description_field`** to a non-string type (for example a number or mapping)
- **THEN** loading SHALL fail with a clear error that does not include secrets

---

## MODIFIED Requirements

### Requirement: Azure Boards work item type and state strings for sync

Under **`azure_boards.defaults`**, the configuration SHALL include these **non-secret** string keys used by the **`sync`** command when creating or transitioning work items (see also per-mapping **`overrides`** in **`org_mappings`** when that feature is used):

- **`work_item_type`**: Boards work item type name for **`$type`** on create (default **`Task`** when omitted after merge).
- **`work_item_state_active`**: Boards **`System.State`** value representing an **active** finding in the operator’s process (default **`New`** when omitted after merge).
- **`work_item_state_closed`**: Boards **`System.State`** value used when placing a work item on the **close path** for Snyk **resolved** or **ignored** findings (default **`Closed`** when omitted after merge).

The loader SHALL **not** accept **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, or **`work_item_description_field`** as direct children of **`azure_boards`**; those fields belong only under **`azure_boards.defaults`**, and a clear, non-secret error SHALL be raised if the flat keys are present.

After merge, **`work_item_type`**, **`work_item_state_active`**, and **`work_item_state_closed`** SHALL either be omitted (and therefore defaulted as above) or be a **non-empty** string; empty strings SHALL be rejected with a clear, non-secret error **before** the per-issue sync loop begins.

The **`README.md`**, **`CONFIGURATION.md`**, and the tracked sample YAML under **`data/`** SHALL list these keys under **`azure_boards.defaults`** with their **defaults** and SHALL explain that operators **MUST** choose type and state values that exist for their **process template**. Documentation SHALL state that when **`work_item_description_field`** is omitted, **`sync`** automatically prefers **`System.Description`** and falls back to **`Microsoft.VSTS.TCM.ReproSteps`** for the effective work item type; operators MAY set **`work_item_description_field`** explicitly when their process uses a different narrative field (for example forcing Repro Steps when both fields exist on Bug).

#### Scenario: Defaults when keys omitted

- **WHEN** the three type/state keys are absent from under **`azure_boards.defaults`** in YAML and not overridden by environment or CLI layers documented for this product
- **THEN** merged configuration SHALL expose `Task`, `New`, and `Closed` as the effective defaults for sync

#### Scenario: Empty string rejected at sync startup

- **WHEN** `azure_boards.defaults.work_item_state_active` is set to an empty string and the user runs **`sync`**
- **THEN** the command SHALL exit non-zero before processing issues with an error that does not include secrets

#### Scenario: Flat work item keys under azure_boards rejected

- **WHEN** YAML sets **`azure_boards.work_item_type`** (or **`work_item_state_active`**, **`work_item_state_closed`**, or **`work_item_description_field`**) at the **`azure_boards`** root instead of under **`defaults`**
- **THEN** loading SHALL fail with a clear error that directs operators to **`azure_boards.defaults`**

---

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`**, including **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_description_appendix`**, and **`sync_included_snyk_origins`**. Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

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
- **THEN** loading SHALL succeed and **`sync`** SHALL use that field reference for issues routed through that row

#### Scenario: Overrides may set origin allowlist per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.sync_included_snyk_origins`** with a valid comma-separated allowlist string
- **THEN** loading SHALL succeed and **`sync`** SHALL use that row’s merged effective allowlist when classifying issues for that routing context
