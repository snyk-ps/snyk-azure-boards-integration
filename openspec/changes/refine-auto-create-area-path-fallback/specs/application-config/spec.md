## ADDED Requirements

### Requirement: Azure Boards defaults — optional auto_create_fallback_area_path

Under **`azure_boards.defaults`**, when **`auto_create_area_path`** is **`true`**, the configuration MAY include **`auto_create_fallback_area_path`**, a **string** template for the fallback area path. When omitted and **`auto_create_area_path`** is **`true`**, the effective template SHALL be **`{project}\Snyk`**.

The template SHALL support **`{project}`** substitution with the effective ADO project at sync time. After substitution with a placeholder project name at load time, the rendered path MUST satisfy **`Project\Area`** format (at least two segments; first segment equals the substituted project).

The loader SHALL reject empty values and values that cannot render to valid area-path shape. The loader SHALL **not** accept **`auto_create_fallback_area_path`** as a direct child of **`azure_boards`**.

The loader SHALL recognize environment variable **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH`** overriding **`azure_boards.defaults.auto_create_fallback_area_path`**, participating in **defaults → YAML → environment → CLI** precedence per existing **`application-config`** rules.

When **`auto_create_area_path`** is **`false`**, **`sync`** SHALL ignore **`auto_create_fallback_area_path`** (the loader MAY still accept the key in YAML).

**`CONFIGURATION.md`**, **`README.md`**, and the tracked sample YAML under **`data/`** SHALL document **`auto_create_fallback_area_path`**, the env var, runtime precedence (**`ado_targets`** → **`org_mappings[].overrides`** → **`defaults`**), and the default **`{project}\Snyk`** template.

#### Scenario: Omitted fallback template uses Snyk default

- **WHEN** **`auto_create_area_path: true`** and **`auto_create_fallback_area_path`** is omitted
- **THEN** the effective fallback template SHALL be **`{project}\Snyk`**

#### Scenario: Custom fallback template loads

- **WHEN** YAML sets **`auto_create_fallback_area_path: "{project}\\Security"`** under **`defaults`**
- **THEN** loading SHALL succeed and merged configuration SHALL expose that template

#### Scenario: Invalid template rejected

- **WHEN** YAML sets **`auto_create_fallback_area_path: "Snyk"`** (cannot render to **`Project\Area`** with **`{project}`**)
- **THEN** loading SHALL fail with a clear error that does not include secrets

#### Scenario: Environment variable overrides YAML defaults

- **WHEN** YAML sets **`defaults.auto_create_fallback_area_path: "{project}\\TeamA"`** and **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH="{project}\\TeamB"`** is set
- **THEN** merged **`defaults.auto_create_fallback_area_path`** SHALL be **`{project}\TeamB`**

## MODIFIED Requirements

### Requirement: Azure Boards ado_targets entry schema

Under **`azure_boards`**, the configuration SHALL support an optional **`ado_targets`** list of mappings that define work-item taxonomy for a specific Azure DevOps **(organization, project)** destination.

Each **`ado_targets[]`** element SHALL be a mapping containing:

- **`organization`**: required non-empty string after trim — Azure DevOps organization name.
- **`project`**: required non-empty string after trim — Azure DevOps project name or id.
- Optional work-item taxonomy keys (subset of **`azure_boards.defaults`**): **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`** (**`tags`**, **`json_patch`**).
- Optional **`auto_create_fallback_area_path`**: string template with **`{project}`** placeholder (same validation rules as **`defaults.auto_create_fallback_area_path`**).

The loader SHALL reject:

- Entries missing **`organization`** or **`project`**, or with empty strings after trim for those keys.
- Duplicate **`(organization, project)`** pairs after trim (case-sensitive comparison on trimmed values).
- Non-string values for taxonomy keys or invalid **`work_item_template`** shape (same rules as **`defaults.work_item_template`**).
- Invalid **`auto_create_fallback_area_path`** values (same rules as under **`defaults`**).
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

#### Scenario: ado_targets row with fallback template loads

- **WHEN** an **`ado_targets`** row includes **`auto_create_fallback_area_path: "{project}\\Security"`**
- **THEN** loading SHALL succeed and expose that template for the matching **`(organization, project)`**

---

### Requirement: ado_targets operator documentation

**`CONFIGURATION.md`** and **`README.md`** SHALL document **`azure_boards.ado_targets`**: purpose (per ADO destination work-item profiles for multi-project CSV routing), allowed keys (including **`auto_create_fallback_area_path`**), duplicate-key rejection, and precedence relative to **`defaults`**, **`org_mappings[].overrides`**, and optional CSV taxonomy columns.

Documentation SHALL recommend defining one **`ado_targets`** entry for each distinct ADO **`(organization, project)`** referenced in **`repo-mapping.csv`** **Area Path** first segments and in the active **`org_mappings`** baseline target.

Documentation SHALL state that per-issue fallback template precedence is **`ado_targets`** → **`org_mappings[].overrides`** → **`defaults`**.

#### Scenario: CONFIGURATION documents ado_targets

- **WHEN** an operator reads **`CONFIGURATION.md`**
- **THEN** they SHALL find **`ado_targets`** schema, precedence, and multi-project routing guidance without reading source code

---

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`**, including **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_description_appendix`**, **`sync_included_snyk_origins`**, **`area_path`**, **`auto_create_area_path`**, and **`auto_create_fallback_area_path`**. Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

For **work-item taxonomy** fields only, when an explicit **`ado_targets`** entry exists for the same **`(organization, project)`** as an **`org_mappings`** row, **`sync`** SHALL prefer the **`ado_targets`** profile over **`org_mappings[].overrides`** for those fields at runtime. **`org_mappings[].overrides`** work-item fields SHALL still apply when no matching **`ado_targets`** entry exists for that **`(organization, project)`**.

For **`auto_create_fallback_area_path`** at runtime, precedence SHALL be matching **`ado_targets`** entry → **`org_mappings[].overrides`** (when org-mapping target matches effective ADO target) → merged **`defaults`**.

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
- **THEN** loading SHALL succeed and merged configuration for that row SHALL expose **`auto_create_area_path: true`**

#### Scenario: Overrides may set fallback template per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.auto_create_fallback_area_path: "{project}\\Triage"`**
- **THEN** loading SHALL succeed and merged configuration SHALL expose that template for issues routed through that row when no matching **`ado_targets`** entry overrides it

---

### Requirement: Azure Boards defaults — optional auto_create_area_path

Under **`azure_boards.defaults`**, the configuration MAY include **`auto_create_area_path`**, a **boolean** that controls whether **`sync`** SHALL synthesize and ensure a **fallback** area path when none is configured or when a configured path is missing in Azure DevOps. When omitted, the effective value SHALL be **`false`**.

The loader SHALL reject a non-boolean value for **`auto_create_area_path`**. The loader SHALL **not** accept **`auto_create_area_path`** as a direct child of **`azure_boards`**; it belongs only under **`azure_boards.defaults`**.

When **`auto_create_area_path`** is **`true`** for the active merged routing context:

- If area-path precedence yields unset, **`sync`** SHALL synthesize the effective fallback path from **`auto_create_fallback_area_path`** (default template **`{project}\Snyk`**) and set **`area_path_source=auto_default`**.
- If a configured path (CSV row, **`org_mappings[].overrides.area_path`**, or **`defaults.area_path`**) is resolved but **does not exist** in the effective ADO target (strict full-path Classification Nodes GET), **`sync`** SHALL substitute the rendered fallback template and set **`area_path_source=auto_fallback`**.
- **`sync`** SHALL ensure (create if missing) **only** the effective fallback path via Classification Nodes REST — **not** configured paths that exist or configured paths that were substituted away.

When **`auto_create_area_path`** is **`false`**, behavior SHALL remain unchanged from prior requirements (unset area path → omit **`System.AreaPath`**; configured but missing path → ADO error on patch).

**`CONFIGURATION.md`**, **`README.md`**, and the tracked sample YAML under **`data/`** SHALL document **`auto_create_area_path`**, fallback/default semantics, **`auto_create_fallback_area_path`**, env var **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH`**, and that **`org_mappings[].overrides.auto_create_area_path`** may override the global default per mapping row.

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
