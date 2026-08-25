## ADDED Requirements

### Requirement: Azure Boards defaults — optional auto_create_area_path

Under **`azure_boards.defaults`**, the configuration MAY include **`auto_create_area_path`**, a **boolean** that controls whether **`sync`** SHALL ensure effective area paths exist in Azure DevOps and MAY synthesize a default area path when none is configured. When omitted, the effective value SHALL be **`false`**.

The loader SHALL reject a non-boolean value for **`auto_create_area_path`**. The loader SHALL **not** accept **`auto_create_area_path`** as a direct child of **`azure_boards`**; it belongs only under **`azure_boards.defaults`**.

When **`auto_create_area_path`** is **`true`** for the active merged routing context:

- If area-path precedence yields unset, **`sync`** SHALL synthesize **`{effective_ado_project}\Snyk`** as the effective area path (fixed segment **`Snyk`** in v1).
- Before create/recreate/update paths that set **`System.AreaPath`**, **`sync`** SHALL ensure the full effective area path exists in the effective ADO target via Classification Nodes REST (see **`azure-devops-client`** and **`sync-lifecycle`**).

When **`auto_create_area_path`** is **`false`**, behavior SHALL remain unchanged from prior requirements (unset area path → omit **`System.AreaPath`**; configured but missing path → ADO error on patch).

**`CONFIGURATION.md`**, **`README.md`**, and the tracked sample YAML under **`data/`** SHALL document **`auto_create_area_path`**, the **`{project}\Snyk`** fallback when enabled, and that **`org_mappings[].overrides.auto_create_area_path`** may override the global default per mapping row.

#### Scenario: Omitted auto_create_area_path defaults to false

- **WHEN** YAML omits **`azure_boards.defaults.auto_create_area_path`**
- **THEN** loading SHALL succeed and the effective value SHALL be **`false`**

#### Scenario: Explicit true loads

- **WHEN** YAML sets **`auto_create_area_path: true`** under **`defaults`**
- **THEN** loading SHALL succeed and merged configuration SHALL expose **`true`** for sync

#### Scenario: Flat auto_create_area_path under azure_boards rejected

- **WHEN** YAML sets **`azure_boards.auto_create_area_path`** at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error directing operators to **`azure_boards.defaults.auto_create_area_path`**

#### Scenario: Non-boolean rejected

- **WHEN** YAML sets **`auto_create_area_path`** to a non-boolean value
- **THEN** loading SHALL fail with a clear error that does not include secrets

---

### Requirement: Optional area-path permissions for auto_create_area_path

**`CONFIGURATION.md`** and **`README.md`** SHALL document that when **`auto_create_area_path`** is **`false`** (default), the existing **Work Items: Read & write** PAT scope is sufficient for all features in this repository.

When **`auto_create_area_path`** is **`true`**, documentation SHALL state that, in addition to **Work Items: Read & write**, the PAT user MUST have Azure DevOps project permissions to **create child nodes** on the parent area path nodes under which new segments will be added (**Project Settings** → **Project configuration** → **Areas** → **Security** → **Create child nodes** = Allow). Documentation SHALL note that some organizations require **Project Administrators** to add areas directly under the project root node, and that these permissions are **optional** — operators who pre-create area paths manually MAY leave **`auto_create_area_path`** **`false`**.

#### Scenario: CONFIGURATION documents optional permissions

- **WHEN** an operator reads **`CONFIGURATION.md`** PAT guidance
- **THEN** they SHALL find that **Create child nodes** permissions are required only when **`auto_create_area_path`** is enabled

#### Scenario: README references optional permissions

- **WHEN** an operator reads **`README.md`** Azure DevOps PAT section
- **THEN** they SHALL find a pointer to optional area-path permissions when auto-create is enabled

## MODIFIED Requirements

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`**, including **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_description_appendix`**, **`sync_included_snyk_origins`**, **`area_path`**, and **`auto_create_area_path`**. Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

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

#### Scenario: Overrides may enable auto_create_area_path per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.auto_create_area_path: true`** and global **`defaults.auto_create_area_path`** is **`false`**
- **THEN** loading SHALL succeed and **`sync`** SHALL treat auto-create as enabled for issues routed through that row

#### Scenario: ado_targets beats org override for same ADO target

- **WHEN** **`ado_targets`** defines **`work_item_type`** **`Bug`** for **`myado`/`PaymentsProject`** and an **`org_mappings`** row for the same **`(organization, project)`** sets **`overrides.work_item_type`** **`Task`**
- **THEN** **`sync`** SHALL use **`Bug`** for work items created in **`PaymentsProject`** when no CSV taxonomy override applies
