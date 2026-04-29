# Application configuration — YAML, defaults, env, CLI

Normative requirements for operator YAML configuration, loading, merge precedence, CLI wiring, and README/sample documentation.

## Requirements

### Requirement: YAML configuration file format

The application SHALL support an operator configuration file in **YAML** format. The file SHALL be non-secret policy only; credentials such as `SNYK_TOKEN` or Azure DevOps PATs SHALL NOT be read from this file (see `openspec/specs/azure-platform/spec.md`).

The following **top-level keys** define the configuration namespaces (after load, **defaults** apply for omitted sections or keys where this capability specifies defaults):

| Key | Purpose |
|-----|---------|
| `azure_boards` | Settings for Azure Boards behavior, including global creation enablement (**P2-FR-11**), non-secret Azure DevOps routing (**`organization`**, **`project`**), **`defaults`** (work item type, states, template), and optional **`org_mappings`**. |
| `work_item_template` | Global template mapping (**`tags`**, **`json_patch`**) merged with **`azure_boards.defaults.work_item_template`** and per-mapping **`overrides.work_item_template`**; MAY be empty. |
| `snyk` | Snyk integration settings, including **group ID** and **severity threshold**; additional keys MAY be added in later changes. |
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

Under `azure_boards`, the configuration SHALL include **`create_new_work_items`**, a boolean that **globally enables or disables creation of new Azure Boards work items** (satisfies **P2-FR-11**). When set to `false`, the application MUST NOT create new work items for qualifying findings. When set to `false`, the **`sync`** command SHALL additionally **never insert** a new mapping row for issues that do not already have a mapping; it SHALL still **update** and **close** mapped work items per **`sync-lifecycle`**. When set to `true`, downstream sync logic MAY create new work items subject to other requirements (e.g. **P2-FR-1**).

#### Scenario: Creation disabled

- **WHEN** `azure_boards.create_new_work_items` is `false`
- **THEN** downstream sync logic SHALL treat new work item creation as disabled for policy decisions that read this setting and SHALL not insert new mapping rows for unmapped issues

#### Scenario: Creation enabled

- **WHEN** `azure_boards.create_new_work_items` is `true`
- **THEN** downstream sync logic MAY create new work items subject to other requirements (e.g. **P2-FR-1**)

---

### Requirement: Azure Boards work item type and state strings for sync

Under **`azure_boards.defaults`**, the configuration SHALL include these **non-secret** string keys used by the **`sync`** command when creating or transitioning work items (see also per-mapping **`overrides`** in **`org_mappings`** when that feature is used):

- **`work_item_type`**: Boards work item type name for **`$type`** on create (default **`Task`** when omitted after merge).
- **`work_item_state_active`**: Boards **`System.State`** value representing an **active** finding in the operator’s process (default **`New`** when omitted after merge).
- **`work_item_state_closed`**: Boards **`System.State`** value used when placing a work item on the **close path** for Snyk **resolved** or **ignored** findings (default **`Closed`** when omitted after merge).

The loader SHALL **not** accept **`work_item_type`**, **`work_item_state_active`**, or **`work_item_state_closed`** as direct children of **`azure_boards`**; those fields belong only under **`azure_boards.defaults`**, and a clear, non-secret error SHALL be raised if the flat keys are present.

After merge, each key SHALL either be omitted (and therefore defaulted as above) or be a **non-empty** string; empty strings SHALL be rejected with a clear, non-secret error **before** the per-issue sync loop begins.

The **`README.md`** and the tracked sample YAML under **`data/`** SHALL list these keys under **`azure_boards.defaults`** with their **defaults** and SHALL explain that operators **MUST** choose values that exist for their **process template** (for example Agile **Task** vs other work item types and valid state names).

#### Scenario: Defaults when keys omitted

- **WHEN** the three keys are absent from under **`azure_boards.defaults`** in YAML and not overridden by environment or CLI layers documented for this product
- **THEN** merged configuration SHALL expose `Task`, `New`, and `Closed` as the effective defaults for sync

#### Scenario: Empty string rejected at sync startup

- **WHEN** `azure_boards.defaults.work_item_state_active` is set to an empty string and the user runs **`sync`**
- **THEN** the command SHALL exit non-zero before processing issues with an error that does not include secrets

#### Scenario: Flat work item keys under azure_boards rejected

- **WHEN** YAML sets **`azure_boards.work_item_type`** (or **`work_item_state_active`** / **`work_item_state_closed`**) at the **`azure_boards`** root instead of under **`defaults`**
- **THEN** loading SHALL fail with a clear error that directs operators to **`azure_boards.defaults`**

---

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`** (**`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_template`**). Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

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

### Requirement: Sync command requires non-empty Snyk group id

When merged configuration has **no** non-empty **`azure_boards.org_mappings`** entries (omitted, empty list, or no row with a non-empty **`snyk_org_id`**), the **`sync`** command SHALL follow the same **`snyk.group_id`** non-empty validation rules as group-scoped **`fetch`**: when merged **`snyk.group_id`** is missing or empty, the process SHALL exit with a clear, non-secret error **before** issuing group-scoped Snyk Issues API calls. Help-only invocations SHALL NOT require `group_id`.

When merged configuration includes **at least one** **`org_mappings`** entry with a non-empty **`snyk_org_id`**, the **`sync`** command SHALL use org-scoped Snyk Issues list operations for those entries per **`sync-lifecycle`** and SHALL NOT require **`snyk.group_id`** solely for those org-scoped list calls; **`snyk.group_id`** MAY still be present for other commands or future use.

#### Scenario: Sync without group id when org_mappings absent

- **WHEN** the user runs **`sync`**, **`org_mappings`** is absent or empty, and merged `snyk.group_id` is missing or empty
- **THEN** the command SHALL exit non-zero without calling Snyk Issues list for the group

#### Scenario: Sync with org_mappings without group id

- **WHEN** the user runs **`sync`** with at least one valid **`org_mappings`** entry and **`snyk.group_id`** is missing or empty
- **THEN** the command SHALL proceed with org-scoped issue listing for configured mappings without requiring **`group_id`** for that purpose

---

### Requirement: Azure DevOps routing under azure_boards

Under **`azure_boards`**, the configuration SHALL include **`organization`** and **`project`**, each a **non-secret** string used as Azure DevOps routing inputs when **`org_mappings`** is absent or empty (single-target mode), as documented for REST path templates in `openspec/specs/integration-apis/spec.md`.

Human-readable Snyk organization slugs for **`app.snyk.io`** links SHALL appear **only** on **`azure_boards.org_mappings[]`** rows (**`snyk_org_slug`** per row). The loader SHALL reject **`azure_boards.snyk_org_slug`** at the **`azure_boards`** root with a clear, non-secret error. Group-scoped **`sync`** without **`org_mappings`** does not configure an org slug; work item links MAY be incomplete until a future configuration path exists.

When **`org_mappings`** is non-empty, each **mapping entry** SHALL include its own **`organization`** and **`project`** strings for Azure DevOps routing for issues processed in that mapping’s iteration; the top-level **`azure_boards.organization`** and **`azure_boards.project`** MAY still be used as documented fallbacks or for commands that do not iterate **`org_mappings`** (exact precedence SHALL match **`application-config`** and implementation documentation for **`org_mappings`**).

These values SHALL NOT be used to transport secrets. The **`azure-devops-client`** and related commands SHALL obtain routing fields from merged configuration or explicit CLI overrides per this capability’s precedence rules; the integration package SHALL NOT read the YAML file directly.

The sample configuration file under **`data/`** and the **`README.md`** configuration documentation SHALL include **`azure_boards.organization`** and **`azure_boards.project`** with placeholder non-secret values and SHALL document **`org_mappings`** entries with per-row **`organization`** and **`project`**.

#### Scenario: Sample lists routing keys

- **WHEN** a developer opens the tracked sample YAML under `data/`
- **THEN** it SHALL include `azure_boards.organization` and `azure_boards.project` alongside documented `azure_boards` keys, and SHALL document **`defaults`** and optional **`org_mappings`** as specified in this capability

#### Scenario: README documents routing keys

- **WHEN** an operator reads the README Configuration / parameter descriptions
- **THEN** they SHALL find `azure_boards.organization` and `azure_boards.project` described, and SHALL find **`org_mappings`** row fields described for multi-target sync

---

### Requirement: README documents Azure DevOps PAT acquisition and scopes

The repository **README** SHALL document how operators create an Azure DevOps **personal access token (PAT)** for this integration, including:

- Step-by-step UI navigation starting from **https://dev.azure.com** through **User settings** → **Personal access tokens** → **New Token** (or equivalent labels in the current Azure DevOps UI).
- Required **Work Items** scopes by use case:
  - **Read** (e.g. **Work Items: Read**, or the Azure DevOps UI equivalent) for **`azure-devops-smoke`** and other read-only validation.
  - **Read and write** (e.g. **Work Items: Read & write**, or the Azure DevOps UI equivalent) for work item **create**, **update**, and **comment** flows used by synchronization.
- A link to Microsoft’s **official** documentation for creating and using PATs with Azure DevOps.
- That the PAT **MUST NOT** be committed to source control or embedded in YAML configuration files, and **SHALL** be provided via the **`AZURE_DEVOPS_PAT`** environment variable for local and application use (production secret storage such as Key Vault remains documented elsewhere and **MAY** be referenced briefly without duplicating deployment steps).

#### Scenario: Operator finds PAT guidance in README

- **WHEN** an operator reads the README section that covers Azure DevOps authentication or configuration
- **THEN** they SHALL find PAT creation steps, the read vs read/write scope guidance, a link to Microsoft’s PAT documentation, and explicit instruction to use **`AZURE_DEVOPS_PAT`** and never commit the token

---

### Requirement: Work item template section

The **`work_item_template`** value SHALL be a **mapping** (YAML dictionary). It MAY be empty. The loader SHALL accept an empty mapping and preserve unknown keys for forward compatibility where the YAML library permits.

For **`sync`**, the following inner keys, when present, SHALL be interpreted by the application:

- **`tags`**: A YAML list of strings representing work item tags to apply on create and update (**P2-FR-10**).
- **`json_patch`**: A YAML list of JSON Patch operation objects (`op`, `path`, optional `value`) appended or merged into work item create/update patch lists per merge rules in this capability and the README, without transporting secrets.

This change does not require any other inner keys for a valid configuration file.

#### Scenario: Empty template

- **WHEN** `work_item_template` is `{}` or omitted per defaulting rules
- **THEN** loading SHALL succeed and expose an empty or default template mapping without error

#### Scenario: Tags list accepted

- **WHEN** `work_item_template.tags` is a YAML list of strings
- **THEN** loading SHALL succeed and the merged template SHALL expose `tags` for sync to consume

#### Scenario: Json patch list accepted

- **WHEN** `work_item_template.json_patch` is a YAML list of mappings each containing `op` and `path`
- **THEN** loading SHALL succeed and the merged template SHALL expose `json_patch` for sync to consume

---

### Requirement: Snyk section with group ID and severity threshold

Under **`snyk`**, the configuration defines at least:

- **`group_id`**: String identifying the Snyk **group** (UUID string as used by the Snyk REST Issues API for group-scoped operations). The **resolved** value after applying **defaults → file → environment → CLI** (see precedence requirement) MUST be **non-empty** before issuing **group-scoped** Snyk Issues API requests (list/get by group). **`fetch`** and any command that **only** performs group-scoped list/get SHALL fail with a clear, non-secret error if `group_id` is missing or empty at execution time when that mode is selected. For **`sync`**, when **`azure_boards.org_mappings`** is present with at least one valid row, org-scoped listing does not require **`group_id`** for that path (see **Sync command requires non-empty Snyk group id**). **Help-only** invocations (e.g. `--help`) SHALL NOT require `group_id`.
- **`severity_threshold`**: A string severity level used as the **minimum** threshold for policy (ordering: `low` < `medium` < `high` < `critical`). The default applied when the key is omitted (after defaulting rules) SHALL be **`high`**, consistent with **P2-FR-1** (High/Critical) as the baseline product behavior.

The key **`snyk_org_slug`** SHALL NOT appear under **`snyk`**. Human-readable org slugs for **`app.snyk.io`** links belong **only** under **`azure_boards.org_mappings[].snyk_org_slug`**. If YAML contains **`snyk.snyk_org_slug`**, the loader SHALL fail with a clear, non-secret error that names the supported location.

Additional keys under **`snyk`** MAY be introduced in future changes; the loader SHALL allow forward-compatible preservation or ignore rules as documented for unknown keys (at minimum, documented behavior for known keys).

#### Scenario: Group ID present after merge

- **WHEN** the merged `snyk.group_id` is a non-empty string
- **THEN** group-scoped Snyk Issues API calls MAY use that value

#### Scenario: Fetch or group sync without group ID

- **WHEN** the user runs **`fetch`** or **`sync`** in group-only mode (no effective **`org_mappings`**) and the resolved `group_id` is missing or empty
- **THEN** the command SHALL exit without issuing group-scoped Snyk Issues API calls, with a clear error that does not include secrets

#### Scenario: Severity threshold default

- **WHEN** `snyk.severity_threshold` is omitted from the file and not overridden by a higher-precedence layer
- **THEN** the effective severity threshold SHALL be **`high`**

#### Scenario: snyk.snyk_org_slug rejected

- **WHEN** YAML sets **`snyk.snyk_org_slug`**
- **THEN** loading SHALL fail with a clear error directing operators to **`azure_boards.org_mappings[].snyk_org_slug`**

#### Scenario: azure_boards.snyk_org_slug rejected

- **WHEN** YAML sets **`azure_boards.snyk_org_slug`** at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error explaining that slugs belong on **`org_mappings`** rows only

---

### Requirement: Configuration loading and defaults

The application SHALL load YAML from a **filesystem path** supplied via CLI (e.g. `--config`) and/or a documented environment variable for the path. After parsing, the implementation SHALL apply **defaults** for optional keys (including `azure_boards.create_new_work_items` defaulting to **`true`**, `snyk.severity_threshold` defaulting to **`high`**, **`mapping_store`** defaulting to **`sqlite`**, and **`sqlite_path`** defaulting to **`data/mapping_store.sqlite`** unless specified otherwise), then merge **environment** and **CLI** layers per the **Precedence** requirement before validating command-specific requirements (e.g. non-empty `group_id` for **`fetch`** or group-mode **`sync`** per this capability). The loader SHALL produce a clear, non-secret error when the file is missing, unreadable, or not valid YAML.

#### Scenario: Defaults applied

- **WHEN** optional keys are omitted from YAML
- **THEN** the resolved configuration object SHALL contain the documented defaults

#### Scenario: Invalid YAML

- **WHEN** the file content is not valid YAML
- **THEN** loading SHALL fail with an error that does not include secret material

---

### Requirement: Precedence — defaults, file, environment, CLI

For any setting that can be supplied through more than one mechanism, the implementation SHALL resolve values in this order: **built-in defaults → YAML file → environment variables → CLI arguments**. When the same logical setting is present at more than one layer, **the later layer wins** (**CLI overrides** environment overrides file overrides defaults). The **README** SHALL document this chain and SHALL state that **managed YAML** (and platform-injected environment) is the **intended source of truth** for deployments and **IaC**, while **CLI flags** are primarily for **local testing and smoke workflows**.

Secrets SHALL continue to come **only** from environment variables or secret stores, not from YAML.

#### Scenario: CLI overrides file for local testing

- **WHEN** `snyk.group_id` is set in the YAML file and the user also passes a CLI argument that sets the same logical value
- **THEN** the effective value for that process SHALL be the CLI value

#### Scenario: Path from environment

- **WHEN** the operator sets the documented environment variable for config file path
- **THEN** the application SHALL determine the file path per the precedence rules (CLI path flag overriding env when both are defined, if applicable)

---

### Requirement: CLI and entrypoint wiring

**`argparse`** definitions for configuration (including at minimum **`--config`** with a path to the YAML file) and for any **override** flags that participate in the same precedence model (e.g. group id for **`fetch`**, and **`--mapping-store-sqlite-path`** for **`sqlite_path`** when using SQLite) SHALL live under **`src/commands/`**. **`src/main.py`** SHALL remain the main entry point, building the parser and dispatching to subcommands, including at minimum **`fetch`** and **`sync`**. User-facing help SHALL describe how to pass the configuration file and that **CLI values override** file-based values for the current invocation where applicable.

#### Scenario: Help lists config flag

- **WHEN** the user runs the application entry point with standard help (e.g. `--help`)
- **THEN** the help output SHALL mention the configuration file option as implemented

#### Scenario: Help does not require group ID

- **WHEN** the user runs with **`--help`** only
- **THEN** the process SHALL succeed without loading a full config or validating `group_id`

#### Scenario: Help mentions sync

- **WHEN** the user runs with **`--help`**
- **THEN** the help output SHALL mention the **`sync`** subcommand at a high level

---

### Requirement: README configuration documentation

The repository **`README.md`** SHALL include a completed **`Configuration`** section (including **`Parameter Descriptions`**) that documents: YAML file location and format overview; **precedence** (**defaults → file → env → CLI**, CLI wins); that **YAML is the intended IaC / deployment source** and CLI is primarily for **local overrides**; CLI flags for config; supported environment variables (including overrides and secrets policy); defaults and optional omissions; **`mapping_store`**, **`sqlite_path`**, **`MAPPING_STORE`**, **`MAPPING_STORE_SQLITE_PATH`**, and **`--mapping-store-sqlite-path`**; that the SQLite database is **local non-secret persistence** and **secrets MUST NOT** be stored in that path or file; **`azure_boards.defaults`** for **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and **`work_item_template`**, with defaults (**`Task`**, **`New`**, **`Closed`**) where applicable, and that flat **`work_item_*`** keys under **`azure_boards`** are **not** supported; **`azure_boards.org_mappings`** with **`organization`**, **`project`**, **`snyk_org_id`**, and optional **`overrides`**; that assignee MAY be set via **`json_patch`** targeting **`/fields/System.AssignedTo`** under merged **`work_item_template`** semantics; and an **example YAML** snippet (or pointer to the **`data/`** sample) that reflects the keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` without embedding real tokens or secrets.

#### Scenario: Operator can configure without reading source

- **WHEN** an operator reads only the README Configuration section
- **THEN** they SHALL be able to construct a valid YAML file and run the CLI with a config path using documented flags and variables, and SHALL understand when **`group_id`** is required for Snyk fetch and **`sync`**, including when **`org_mappings`** is used

---

### Requirement: Sample configuration file under `data/`

The repository SHALL include at least one **sample** YAML configuration file under the **`data/`** directory that conforms to the documented schema (placeholder values only; no secrets). The sample SHALL include **`mapping_store`** and **`sqlite_path`** with placeholder non-secret values. The sample SHALL document **`azure_boards.defaults`** with **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and optional **`work_item_template`**, with defaults or comments consistent with this capability. The sample SHALL include a commented example of **`azure_boards.org_mappings`** (optional list) with placeholder **`organization`**, **`project`**, and **`snyk_org_id`**. The sample SHALL be **tracked in version control** and SHALL **not** be excluded by **`.gitignore`** (or equivalent ignore rules), so it remains available in every clone for documentation and local testing (e.g. `--config` pointing at that path).

#### Scenario: Sample present and tracked

- **WHEN** a developer clones the repository
- **THEN** they SHALL find a sample YAML file under `data/` that validates against the loader and is not gitignored by default

#### Scenario: README references sample path

- **WHEN** an operator reads the README Configuration section
- **THEN** it SHALL mention the `data/` sample file path (or glob) so users can run the CLI against it without authoring YAML from scratch

#### Scenario: Sample shows sync-related azure_boards keys

- **WHEN** a developer opens the tracked sample YAML
- **THEN** it SHALL include documented **`azure_boards.defaults`** for sync-related work item strings with defaults or placeholders consistent with this capability

---

### Requirement: Mapping store environment and CLI overrides

For **`mapping_store`** and **`sqlite_path`**, the implementation SHALL recognize these **environment variable** overrides: **`MAPPING_STORE`** (same semantics as YAML `mapping_store`) and **`MAPPING_STORE_SQLITE_PATH`** (same semantics as YAML `sqlite_path`). The CLI MAY expose **`--mapping-store-sqlite-path`** to override **`sqlite_path`** for the current process. These layers SHALL participate in the same **defaults → YAML → environment → CLI** precedence as all other multi-layer settings in this capability.

#### Scenario: Environment overrides YAML for mapping store

- **WHEN** `mapping_store` is set in YAML and **`MAPPING_STORE`** is set in the environment
- **THEN** the effective `mapping_store` SHALL be the environment value

#### Scenario: CLI overrides environment for SQLite path

- **WHEN** **`MAPPING_STORE_SQLITE_PATH`** is set and the user passes **`--mapping-store-sqlite-path`**
- **THEN** the effective `sqlite_path` SHALL be the CLI value

#### Scenario: Default mapping store when all layers omit it

- **WHEN** `mapping_store` and `sqlite_path` are not specified in YAML, environment, or CLI
- **THEN** after defaulting, `mapping_store` SHALL be **`sqlite`** and `sqlite_path` SHALL be **`data/mapping_store.sqlite`**
