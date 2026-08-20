## ADDED Requirements

### Requirement: Azure Boards defaults — optional area path

Under **`azure_boards.defaults`**, the configuration MAY include **`area_path`**, an optional **non-secret string** holding a full Azure DevOps area path (for example **`MyProject\\TeamA`** or **`MyProject\\Area\\SubArea`**). When omitted or whitespace-only after trim, no default area path is configured at this layer.

The loader SHALL reject a non-string value for **`area_path`**. The loader SHALL **not** accept **`area_path`** as a direct child of **`azure_boards`**; it belongs only under **`azure_boards.defaults`**.

**`CONFIGURATION.md`**, **`README.md`**, and the tracked sample YAML under **`data/`** SHALL document **`area_path`** as the YAML fallback when no **`repo-mapping.csv`** row matches, and SHALL document that **`org_mappings[].overrides.area_path`** overrides this default for that mapping row.

#### Scenario: Omitted area path defaults to unset at YAML layer

- **WHEN** YAML omits **`azure_boards.defaults.area_path`**
- **THEN** loading SHALL succeed and no default area path is configured unless a CSV row or org override supplies one

#### Scenario: Explicit default area path loads

- **WHEN** YAML sets **`area_path: MyProject\\TeamA`** under **`defaults`**
- **THEN** loading SHALL succeed and merged configuration SHALL expose that value for sync fallback resolution

#### Scenario: Flat area_path under azure_boards rejected

- **WHEN** YAML sets **`azure_boards.area_path`** at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error directing operators to **`azure_boards.defaults.area_path`**

---

### Requirement: Azure Boards repo_mapping_csv path

Under **`azure_boards`**, the configuration MAY include **`repo_mapping_csv`**, a non-secret string path to the operator **`repo-mapping.csv`** file. When omitted at all precedence layers, the effective default SHALL be **`repo-mapping.csv`** resolved in the directory containing the loaded YAML configuration file (see **`repo-area-path-mapping`**).

The implementation SHALL recognize environment variable **`REPO_MAPPING_CSV_PATH`** with the same semantics, participating in **defaults → YAML → environment → CLI** precedence.

The loader SHALL reject a non-string **`repo_mapping_csv`** value.

**`CONFIGURATION.md`** and **`README.md`** SHALL document **`repo_mapping_csv`**, **`REPO_MAPPING_CSV_PATH`**, the default filename **`repo-mapping.csv`**, and Azure Files co-location beside operator YAML.

#### Scenario: repo_mapping_csv relative path resolves beside config

- **WHEN** YAML is loaded from **`/config/config.yaml`** and sets **`repo_mapping_csv: custom.csv`**
- **THEN** the effective path SHALL be **`/config/custom.csv`**

#### Scenario: REPO_MAPPING_CSV_PATH overrides YAML

- **WHEN** YAML sets **`repo_mapping_csv`** and **`REPO_MAPPING_CSV_PATH`** is set in the environment
- **THEN** the effective path SHALL be the environment value

---

## MODIFIED Requirements

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`**, including **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_description_appendix`**, **`sync_included_snyk_origins`**, and **`area_path`**. Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

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

#### Scenario: Overrides may set area path per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.area_path`** with a non-empty string
- **THEN** loading SHALL succeed and **`sync`** SHALL use that value as the YAML fallback area path for issues routed through that row when no CSV row matches

---

### Requirement: Sample configuration file under `data/`

The repository SHALL include at least one **sample** YAML configuration file under the **`data/`** directory that conforms to the documented schema (placeholder values only; no secrets). The sample SHALL include **`mapping_store`** and **`sqlite_path`** with placeholder non-secret values. The sample SHALL document **`azure_boards.defaults`** with **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, optional **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, optional **`area_path`**, optional **`repo_mapping_csv`**, and optional **`work_item_template`**, with defaults or comments consistent with this capability. The sample SHALL include under **`snyk`** a commented example of **`api_base_url`** (default **`https://api.snyk.io`**, **SNYK-US-01**) with a pointer to regional hosts in documentation. The sample SHALL include under **`snyk`** a commented example of **`app_base_url`** (default **`https://app.snyk.io`**, **SNYK-US-01**) with a pointer to regional app hosts in documentation. The sample SHALL include a commented example of **`azure_boards.org_mappings`** (optional list) with placeholder **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`**, example **`overrides`** including optional **`area_path`**, and a comment pointing to **`data/sample-repo-mapping.csv`**. The sample SHALL be **tracked in version control** and SHALL **not** be excluded by **`.gitignore`** (or equivalent ignore rules), so it remains available in every clone for documentation and local testing (e.g. `--config` pointing at that path).

#### Scenario: Sample present and tracked

- **WHEN** a developer clones the repository
- **THEN** they SHALL find a sample YAML file under `data/` that validates against the loader and is not gitignored by default

#### Scenario: README references sample path

- **WHEN** an operator reads the README Configuration section
- **THEN** it SHALL mention the `data/` sample file path (or glob) so users can run the CLI against it without authoring YAML from scratch

#### Scenario: Sample shows sync-related azure_boards defaults

- **WHEN** a developer opens the tracked sample YAML
- **THEN** it SHALL include documented **`azure_boards.defaults`** for routing, creation toggle, severity, sync-related work item strings, and optional **`area_path`** / **`repo_mapping_csv`** comments consistent with this capability

---

### Requirement: README configuration documentation

The repository **`README.md`** SHALL include a completed **`Configuration`** section (including **`Parameter Descriptions`**) that documents: YAML file location and format overview; **precedence** (**defaults → file → env → CLI**, CLI wins); that **YAML is the intended IaC / deployment source** and CLI is primarily for **local overrides**; CLI flags for config; supported environment variables (including overrides and secrets policy); defaults and optional omissions; **`mapping_store`**, **`sqlite_path`**, **`MAPPING_STORE`**, **`MAPPING_STORE_SQLITE_PATH`**, **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`**, **`MAPPING_STORE_AZURE_TABLE_NAME`**, and **`--mapping-store-sqlite-path`**; **`snyk.api_base_url`**, **`SNYK_API_BASE_URL`**, and **`--snyk-api-base-url`** (default **`https://api.snyk.io`**, **SNYK-US-01**); **`snyk.app_base_url`**, **`SNYK_APP_BASE_URL`**, and **`--snyk-app-base-url`** (default **`https://app.snyk.io`**, **SNYK-US-01**); that the SQLite database is **local non-secret persistence** and **secrets MUST NOT** be stored in that path or file; **`azure_boards.defaults`** for **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`area_path`**, **`repo_mapping_csv`**, **`REPO_MAPPING_CSV_PATH`**, and **`work_item_template`**, with defaults where applicable, and that flat **`work_item_*`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, and **`area_path`** keys directly under **`azure_boards`** or **`snyk`** for severity are **not** supported; **`azure_boards.org_mappings`** with **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`**, optional **`overrides`** including **`area_path`**; **`repo-mapping.csv`** format and co-location (pointer to **`CONFIGURATION.md`** and **`data/sample-repo-mapping.csv`**); that assignee MAY be set via **`json_patch`** targeting **`/fields/System.AssignedTo`** under merged **`work_item_template`** semantics unless overridden by a matching CSV row; **mapping store column reference** per **README documents mapping store columns**; and an **example YAML** snippet (or pointer to the **`data/`** sample) that reflects the keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` without embedding real tokens or secrets.

The **`README.md`** SHALL also include a **`Deployment`** subsection (which MAY sit after **`Configuration`** or **`Error Handling/Logging`**) that describes **Azure Container Apps** operation at a high level: non-secret operator YAML on **Azure Files** (mount path convention as implemented or documented), **`repo-mapping.csv`** on the same share beside operator YAML, **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** from **Key Vault** via Container Apps secret references / environment injection, **`SNYK_API_BASE_URL`** for regional Snyk API host when not on **SNYK-US-01**, **`SNYK_APP_BASE_URL`** for regional Snyk web app host when not on **SNYK-US-01**, **managed identity** for Azure resource access, **`mapping_store: azure_table`** with Table endpoint and table name via environment variables, **where to view logs** (**Log stream** vs **Log Analytics** / **`ContainerAppConsoleLogs_CL`**, cross-referencing **Error Handling/Logging**), and **Container App Job replica timeout** guidance: operators SHALL set **`replicaTimeout`** (portal **Configuration** or CLI **`--replica-timeout`**, value in **seconds**) to at least the expected maximum **`sync`** duration plus a safety buffer; the platform default is **30 minutes**; documentation SHALL state a **rough starting estimate** of **~60 seconds per 50 work items** (creates/updates and HTTP latency), recommend **stress testing** with production-like configuration and issue volume, and recommend using observed **`sync_summary.sync_duration_seconds`** from logs to size timeout above peak runs (with margin). Documentation SHALL note **`DeadlineExceeded`** / job stopped near **30 minutes** as a symptom of insufficient replica timeout.

#### Scenario: Operator can configure without reading source

- **WHEN** an operator reads only the README Configuration section
- **THEN** they SHALL be able to construct a valid YAML file and run the CLI with a config path using documented flags and variables, and SHALL understand when **`group_id`** is required for Snyk fetch and **`sync`**, including when **`org_mappings`** is used

#### Scenario: Operator can locate Container App logs

- **WHEN** an operator reads the README Deployment subsection
- **THEN** they SHALL understand how to open **Log stream** for immediate stdout/stderr and how to query workspace logs (e.g. **`ContainerAppConsoleLogs_CL`**) for **`sync_summary`** / **`integration_http`** troubleshooting as described in **Error Handling/Logging**

#### Scenario: Operator can size Container App Job replica timeout

- **WHEN** an operator reads the README Deployment subsection
- **THEN** they SHALL understand that **`replicaTimeout`** must exceed expected **`sync`** duration, how to use **`sync_duration_seconds`** from **`sync_summary`** logs to tune it, and the documented rough **~60 seconds per 50 work items** estimate as a starting point only
