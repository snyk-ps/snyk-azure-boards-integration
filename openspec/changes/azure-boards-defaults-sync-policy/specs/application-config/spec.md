## ADDED Requirements

### Requirement: Azure Boards defaults — severity threshold and optional sync policy keys

Under **`azure_boards.defaults`**, after merge with **`org_mappings[].overrides`**, the configuration SHALL support:

- **`severity_threshold`**: One of **`low`**, **`medium`**, **`high`**, **`critical`** as the **minimum** severity included in Snyk Issues list filtering and qualifying-create policy (ordering: `low` < `medium` < `high` < `critical`). The default when omitted SHALL be **`high`**, consistent with **P2-FR-1** when interpreted as High/Critical baseline.
- **`issues_sync_from`**: Either the literal string **`historical`** (default) or an **ISO 8601 / RFC 3339 timestamp in UTC** denoting the lower bound for Issues list filtering per **`sync-lifecycle`** and **`snyk-issues-client`**. When **`historical`**, the application SHALL NOT apply an Issues API time lower-bound filter solely from this key.
- **`create_only_when_fix_available`**: Boolean; default **`false`**. When **`true`**, the sync run SHALL NOT create new work items for issues that do not satisfy “fix available” policy defined in **`sync-lifecycle`** (aligned with issue payload fix signals).
- **`reopen_work_item_policy`**: One of **`new_work_item`** or **`reopen_existing`** (exact strings). It SHALL control behavior when a finding transitions from a closed-path derived status back to **`open`** per **`sync-lifecycle`**.

The loader SHALL reject **`snyk.severity_threshold`** or legacy flat **`azure_boards.severity_threshold`** with a clear, non-secret error pointing operators to **`azure_boards.defaults.severity_threshold`**.

#### Scenario: Severity default is high

- **WHEN** `azure_boards.defaults.severity_threshold` is omitted everywhere and not overridden by env/CLI
- **THEN** the merged effective value SHALL be **`high`**

#### Scenario: Legacy snyk.severity_threshold rejected

- **WHEN** YAML contains **`snyk.severity_threshold`**
- **THEN** loading SHALL fail with a clear error naming **`azure_boards.defaults.severity_threshold`**

#### Scenario: issues_sync_from accepts historical or timestamp

- **WHEN** `issues_sync_from` is **`historical`** or a valid UTC ISO 8601 timestamp string under **`azure_boards.defaults`**
- **THEN** loading SHALL succeed and expose the value for sync list filtering

---

### Requirement: README documents mapping store columns

The **`README.md`** SHALL include a subsection under **Configuration** (or **Mapping store**) that lists **every column** (field name and purpose) of the logical mapping row persisted by **`mapping_store`**, including at minimum those defined in **`azure-platform`** for **`issue_work_item_map`** / Azure Table parity, including **`snyk_project_name`** and **`snyk_project_origin`** when specified by **`sync-lifecycle`**.

#### Scenario: Operators see mapping schema in README

- **WHEN** an operator reads the README for deployment or troubleshooting
- **THEN** they SHALL find a table or list describing mapping columns and their roles without reading source code

---

## MODIFIED Requirements

### Requirement: YAML configuration file format

The application SHALL support an operator configuration file in **YAML** format. The file SHALL be non-secret policy only; credentials such as `SNYK_TOKEN` or Azure DevOps PATs SHALL NOT be read from this file (see `openspec/specs/azure-platform/spec.md`).

The following **top-level keys** define the configuration namespaces (after load, **defaults** apply for omitted sections or keys where this capability specifies defaults):

| Key | Purpose |
|-----|---------|
| `azure_boards` | Settings for Azure Boards behavior, optional **`org_mappings`**, and **`defaults`**: ADO routing (**`organization`**, **`project`**), **`create_new_work_items`** (**P2-FR-11**), **`severity_threshold`**, optional sync bounds (**`issues_sync_from`**), **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, work item type/state/template keys, and related options. |
| `work_item_template` | Global template mapping (**`tags`**, **`json_patch`**) merged with **`azure_boards.defaults.work_item_template`** and per-mapping **`overrides.work_item_template`**; MAY be empty. |
| `snyk` | Snyk integration settings, including **group ID** for group-scoped Issues API calls; **severity threshold is not configured here**. |
| `mapping_store` | Backend for Snyk↔work-item mapping persistence (**P2-FR-7**): **`sqlite`** for local dev/tests, or reserved **`azure_table`** for production-style storage (see `azure-platform`). |
| `sqlite_path` | Filesystem path to the SQLite database file when `mapping_store` is **`sqlite`**. |

An operator **MAY omit** any top-level key (or inner optional key) for which this capability defines a **default**; the resolved configuration after parsing and defaulting SHALL match the documented behavior. The **README** and **`data/`** sample SHALL show a **complete** example shape for copy-paste and IaC.

#### Scenario: Omitted sections receive defaults

- **WHEN** a valid YAML file omits optional keys or sections that have documented defaults
- **THEN** loading SHALL succeed and the resolved configuration SHALL include those defaults

#### Scenario: Full shape in documentation

- **WHEN** an operator copies the example from the README or `data/` sample
- **THEN** the file SHALL list the top-level keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` with placeholder non-secret values (omissions allowed only where defaults apply per documented rules)

---

### Requirement: Azure Boards global creation toggle

Under **`azure_boards.defaults`**, the configuration SHALL include **`create_new_work_items`**, a boolean that **globally enables or disables creation of new Azure Boards work items** (satisfies **P2-FR-11**). When set to `false`, the application MUST NOT create new work items for qualifying findings. When set to `false`, the **`sync`** command SHALL additionally **never insert** a new mapping row for issues that do not already have a mapping; it SHALL still **update** and **close** mapped work items per **`sync-lifecycle`**. When set to `true`, downstream sync logic MAY create new work items subject to other requirements (e.g. **P2-FR-1**).

The loader SHALL **not** accept **`create_new_work_items`** as a direct child of **`azure_boards`**; it belongs only under **`azure_boards.defaults`**. A clear, non-secret error SHALL be raised if the legacy flat key is present.

#### Scenario: Creation disabled

- **WHEN** `azure_boards.defaults.create_new_work_items` is `false`
- **THEN** downstream sync logic SHALL treat new work item creation as disabled for policy decisions that read this setting and SHALL not insert new mapping rows for unmapped issues

#### Scenario: Creation enabled

- **WHEN** `azure_boards.defaults.create_new_work_items` is `true`
- **THEN** downstream sync logic MAY create new work items subject to other requirements (e.g. **P2-FR-1**)

#### Scenario: Legacy flat create_new_work_items rejected

- **WHEN** YAML sets **`azure_boards.create_new_work_items`** at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error directing operators to **`azure_boards.defaults.create_new_work_items`**

---

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`**, including **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_template`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, and **`reopen_work_item_policy`**. Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

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

---

### Requirement: Azure DevOps routing under azure_boards

Under **`azure_boards.defaults`**, the configuration SHALL include **`organization`** and **`project`**, each a **non-secret** string used as Azure DevOps routing inputs when **`org_mappings`** is absent or empty (single-target mode), as documented for REST path templates in `openspec/specs/integration-apis/spec.md`.

Human-readable Snyk organization slugs for **`app.snyk.io`** links SHALL appear **only** on **`azure_boards.org_mappings[]`** rows (**`snyk_org_slug`** per row). The loader SHALL reject **`azure_boards.snyk_org_slug`** at the **`azure_boards`** root with a clear, non-secret error. Group-scoped **`sync`** without **`org_mappings`** does not configure an org slug; composed Snyk UI links MAY be incomplete until a future configuration path exists.

The loader SHALL **not** accept **`organization`** or **`project`** as direct children of **`azure_boards`**; those fields belong only under **`azure_boards.defaults`**, and a clear, non-secret error SHALL be raised if the legacy flat keys are present.

When **`org_mappings`** is non-empty, each **mapping entry** SHALL include its own **`organization`** and **`project`** strings for Azure DevOps routing for issues processed in that mapping’s iteration; merged **`defaults`** and row **`overrides`** SHALL supply effective routing per **`application-config`** merge rules (see **`org_mappings`** schema).

These values SHALL NOT be used to transport secrets. The **`azure-devops-client`** and related commands SHALL obtain routing fields from merged configuration or explicit CLI overrides per this capability’s precedence rules; the integration package SHALL NOT read the YAML file directly.

The sample configuration file under **`data/`** and the **`README.md`** configuration documentation SHALL document **`azure_boards.defaults.organization`** and **`azure_boards.defaults.project`** with placeholder non-secret values and SHALL document **`org_mappings`** entries with per-row **`organization`** and **`project`**.

#### Scenario: Sample lists routing keys under defaults

- **WHEN** a developer opens the tracked sample YAML under `data/`
- **THEN** it SHALL include **`azure_boards.defaults.organization`** and **`azure_boards.defaults.project`** alongside documented `azure_boards` keys, and SHALL document **`defaults`** and optional **`org_mappings`** as specified in this capability

#### Scenario: README documents routing keys under defaults

- **WHEN** an operator reads the README Configuration / parameter descriptions
- **THEN** they SHALL find **`azure_boards.defaults.organization`** and **`azure_boards.defaults.project`** described, and SHALL find **`org_mappings`** row fields described for multi-target sync

---

### Requirement: Snyk section with group ID and severity threshold

Under **`snyk`**, the configuration defines at least:

- **`group_id`**: String identifying the Snyk **group** (UUID string as used by the Snyk REST Issues API for group-scoped operations). The **resolved** value after applying **defaults → file → environment → CLI** (see precedence requirement) MUST be **non-empty** before issuing **group-scoped** Snyk Issues API requests (list/get by group). **`fetch`** and any command that **only** performs group-scoped list/get SHALL fail with a clear, non-secret error if `group_id` is missing or empty at execution time when that mode is selected. For **`sync`**, when **`azure_boards.org_mappings`** is present with at least one valid row, org-scoped listing does not require **`group_id`** for that path (see **Sync command requires non-empty Snyk group id**). **Help-only** invocations (e.g. `--help`) SHALL NOT require `group_id`.

The key **`snyk_org_slug`** SHALL NOT appear under **`snyk`**. Human-readable org slugs for **`app.snyk.io`** links belong **only** under **`azure_boards.org_mappings[].snyk_org_slug`**. If YAML contains **`snyk.snyk_org_slug`**, the loader SHALL fail with a clear, non-secret error that names the supported location.

Additional keys under **`snyk`** MAY be introduced in future changes; the loader SHALL allow forward-compatible preservation or ignore rules as documented for unknown keys (at minimum, documented behavior for known keys).

#### Scenario: Group ID present after merge

- **WHEN** the merged `snyk.group_id` is a non-empty string
- **THEN** group-scoped Snyk Issues API calls MAY use that value

#### Scenario: Fetch or group sync without group ID

- **WHEN** the user runs **`fetch`** or **`sync`** in group-only mode (no effective **`org_mappings`**) and the resolved `group_id` is missing or empty
- **THEN** the command SHALL exit without issuing group-scoped Snyk Issues API calls, with a clear error that does not include secrets

#### Scenario: snyk.snyk_org_slug rejected

- **WHEN** YAML sets **`snyk.snyk_org_slug`**
- **THEN** loading SHALL fail with a clear error directing operators to **`azure_boards.org_mappings[].snyk_org_slug`**

#### Scenario: azure_boards.snyk_org_slug rejected

- **WHEN** YAML sets **`azure_boards.snyk_org_slug`** at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error explaining that slugs belong on **`org_mappings`** rows only

---

### Requirement: Configuration loading and defaults

The application SHALL load YAML from a **filesystem path** supplied via CLI (e.g. `--config`) and/or a documented environment variable for the path. After parsing, the implementation SHALL apply **defaults** for optional keys (including **`azure_boards.defaults.create_new_work_items`** defaulting to **`true`**, **`azure_boards.defaults.severity_threshold`** defaulting to **`high`**, **`mapping_store`** defaulting to **`sqlite`**, and **`sqlite_path`** defaulting to **`data/mapping_store.sqlite`** unless specified otherwise), then merge **environment** and **CLI** layers per the **Precedence** requirement before validating command-specific requirements (e.g. non-empty `group_id` for **`fetch`** or group-mode **`sync`** per this capability). The loader SHALL produce a clear, non-secret error when the file is missing, unreadable, or not valid YAML.

#### Scenario: Defaults applied

- **WHEN** optional keys are omitted from YAML
- **THEN** the resolved configuration object SHALL contain the documented defaults

#### Scenario: Invalid YAML

- **WHEN** the file content is not valid YAML
- **THEN** loading SHALL fail with an error that does not include secret material

---

### Requirement: README configuration documentation

The repository **`README.md`** SHALL include a completed **`Configuration`** section (including **`Parameter Descriptions`**) that documents: YAML file location and format overview; **precedence** (**defaults → file → env → CLI**, CLI wins); that **YAML is the intended IaC / deployment source** and CLI is primarily for **local overrides**; CLI flags for config; supported environment variables (including overrides and secrets policy); defaults and optional omissions; **`mapping_store`**, **`sqlite_path`**, **`MAPPING_STORE`**, **`MAPPING_STORE_SQLITE_PATH`**, and **`--mapping-store-sqlite-path`**; that the SQLite database is **local non-secret persistence** and **secrets MUST NOT** be stored in that path or file; **`azure_boards.defaults`** for **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and **`work_item_template`**, with defaults where applicable, and that flat **`work_item_*`**, **`organization`**, **`project`**, **`create_new_work_items`**, and **`severity_threshold`** keys directly under **`azure_boards`** or **`snyk`** for severity are **not** supported; **`azure_boards.org_mappings`** with **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`**, and optional **`overrides`**; that assignee MAY be set via **`json_patch`** targeting **`/fields/System.AssignedTo`** under merged **`work_item_template`** semantics; **mapping store column reference** per **README documents mapping store columns**; and an **example YAML** snippet (or pointer to the **`data/`** sample) that reflects the keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` without embedding real tokens or secrets.

#### Scenario: Operator can configure without reading source

- **WHEN** an operator reads only the README Configuration section
- **THEN** they SHALL be able to construct a valid YAML file and run the CLI with a config path using documented flags and variables, and SHALL understand when **`group_id`** is required for Snyk fetch and **`sync`**, including when **`org_mappings`** is used

---

### Requirement: Sample configuration file under `data/`

The repository SHALL include at least one **sample** YAML configuration file under the **`data/`** directory that conforms to the documented schema (placeholder values only; no secrets). The sample SHALL include **`mapping_store`** and **`sqlite_path`** with placeholder non-secret values. The sample SHALL document **`azure_boards.defaults`** with **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, optional **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and optional **`work_item_template`**, with defaults or comments consistent with this capability. The sample SHALL include a commented example of **`azure_boards.org_mappings`** (optional list) with placeholder **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`**, and example **`overrides`**. The sample SHALL be **tracked in version control** and SHALL **not** be excluded by **`.gitignore`** (or equivalent ignore rules), so it remains available in every clone for documentation and local testing (e.g. `--config` pointing at that path).

#### Scenario: Sample present and tracked

- **WHEN** a developer clones the repository
- **THEN** they SHALL find a sample YAML file under `data/` that validates against the loader and is not gitignored by default

#### Scenario: README references sample path

- **WHEN** an operator reads the README Configuration section
- **THEN** it SHALL mention the `data/` sample file path (or glob) so users can run the CLI against it without authoring YAML from scratch

#### Scenario: Sample shows sync-related azure_boards defaults

- **WHEN** a developer opens the tracked sample YAML
- **THEN** it SHALL include documented **`azure_boards.defaults`** for routing, creation toggle, severity, and sync-related work item strings with defaults or placeholders consistent with this capability
