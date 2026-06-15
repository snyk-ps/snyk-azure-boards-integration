## ADDED Requirements

### Requirement: Snyk API origin (regional base URL)

Under **`snyk`**, the configuration SHALL support **`api_base_url`**: a non-secret **HTTPS API origin** string (scheme + host, optional port; **no** trailing slash after normalization) used to reach the Snyk platform API for the operator's region. The default when omitted at all layers SHALL be **`https://api.snyk.io`** (**Snyk region SNYK-US-01**). The application SHALL derive the REST API base as **`{api_base_url}/rest`** and the legacy V1 API base as **`{api_base_url}/v1`** for all Snyk HTTP clients in this repository.

The implementation SHALL recognize environment variable **`SNYK_API_BASE_URL`** with the same semantics as **`snyk.api_base_url`**, participating in **defaults → YAML → environment → CLI** precedence. CLI flag **`--snyk-api-base-url`** on **`sync`** and **`fetch`** SHALL override environment for the current process when non-empty.

The loader SHALL reject empty or non-HTTPS values for **`api_base_url`** with a clear, non-secret error. Values that include a **`/rest`** suffix MAY be accepted for backward compatibility (for example org-config generator **`--base-url`**), normalizing to the origin before re-deriving REST/V1 bases.

For **Azure Container Apps Job** and similar scheduled deployments, documentation SHALL recommend setting **`SNYK_API_BASE_URL`** in the job environment (non-secret) rather than relying on CLI args alone.

#### Scenario: Default origin is SNYK-US-01

- **WHEN** no layer supplies **`api_base_url`**
- **THEN** the effective origin SHALL be **`https://api.snyk.io`** and REST calls SHALL use **`https://api.snyk.io/rest`**

#### Scenario: Environment overrides YAML for regional host

- **WHEN** YAML sets **`snyk.api_base_url: https://api.eu.snyk.io`** and **`SNYK_API_BASE_URL=https://api.us.snyk.io`**
- **THEN** the effective origin SHALL be **`https://api.us.snyk.io`**

#### Scenario: CLI overrides environment for one invocation

- **WHEN** **`SNYK_API_BASE_URL`** is set and the user passes **`--snyk-api-base-url https://api.au.snyk.io`** on **`sync`**
- **THEN** Snyk REST requests for that run SHALL use **`https://api.au.snyk.io/rest`**

#### Scenario: Invalid origin rejected at load

- **WHEN** merged **`api_base_url`** is empty or not HTTPS
- **THEN** loading or command startup SHALL fail with a clear error that does not include secrets

---

### Requirement: README troubleshooting — Snyk 401 and regional base URL

The repository **`README.md`** **Troubleshooting** section SHALL include a table row (or equivalent entry) for Snyk HTTP **401** / **`Authentication Failed`** that directs operators to verify **`SNYK_TOKEN`** **and** that **`SNYK_API_BASE_URL`** (or **`snyk.api_base_url`**) matches their Snyk **region**. The entry SHALL state the default origin **`https://api.snyk.io`** (**SNYK-US-01**) and link to [Snyk REST API — API URLs](https://docs.snyk.io/developer-tools/snyk-api/rest-api/about-the-rest-api#api-urls) for other regional hosts.

#### Scenario: Operator finds regional base URL guidance in README

- **WHEN** an operator reads the README Troubleshooting section after a Snyk **401**
- **THEN** they SHALL find guidance to check token validity and regional API host configuration without reading source code

---

## MODIFIED Requirements

### Requirement: Snyk section with group ID and severity threshold

The **`snyk`** section SHALL surface **`group_id`** for group-scoped Issues API calls and SHALL NOT accept **`severity_threshold`**; operators MUST use **`azure_boards.defaults.severity_threshold`** instead. Under **`snyk`**, the configuration defines at least:

- **`group_id`**: String identifying the Snyk **group** (UUID string as used by the Snyk REST Issues API for group-scoped operations). The **resolved** value after applying **defaults → file → environment → CLI** (see precedence requirement) MUST be **non-empty** before issuing **group-scoped** Snyk Issues API requests (list/get by group). **`fetch`** and any command that **only** performs group-scoped list/get SHALL fail with a clear, non-secret error if `group_id` is missing or empty at execution time when that mode is selected. For **`sync`**, when **`azure_boards.org_mappings`** is present with at least one valid row, org-scoped listing does not require **`group_id`** for that path (see **Sync command requires non-empty Snyk group id**). **Help-only** invocations (e.g. `--help`) SHALL NOT require `group_id`.
- **`api_base_url`**: Non-secret **HTTPS API origin** for the operator's Snyk region (default **`https://api.snyk.io`**, **SNYK-US-01**). REST and V1 bases are derived per **Snyk API origin (regional base URL)**. Override via **`SNYK_API_BASE_URL`** or **`--snyk-api-base-url`** on Snyk-calling commands.

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

The application SHALL load YAML from a **filesystem path** supplied via CLI (e.g. `--config`) and/or a documented environment variable for the path. After parsing, the implementation SHALL apply **defaults** for optional keys (including **`azure_boards.defaults.create_new_work_items`** defaulting to **`true`**, **`azure_boards.defaults.severity_threshold`** defaulting to **`high`**, **`snyk.api_base_url`** defaulting to **`https://api.snyk.io`**, **`mapping_store`** defaulting to **`sqlite`**, and **`sqlite_path`** defaulting to **`data/mapping_store.sqlite`** unless specified otherwise), then merge **environment** and **CLI** layers per the **Precedence** requirement before validating command-specific requirements (e.g. non-empty `group_id` for **`fetch`** or group-mode **`sync`** per this capability). The loader SHALL produce a clear, non-secret error when the file is missing, unreadable, or not valid YAML.

#### Scenario: Defaults applied

- **WHEN** optional keys are omitted from YAML
- **THEN** the resolved configuration object SHALL contain the documented defaults

#### Scenario: Invalid YAML

- **WHEN** the file content is not valid YAML
- **THEN** loading SHALL fail with an error that does not include secret material

---

### Requirement: CLI and entrypoint wiring

**`argparse`** definitions for configuration (including at minimum **`--config`** with a path to the YAML file) and for any **override** flags that participate in the same precedence model (e.g. group id for **`fetch`**, **`--snyk-api-base-url`** for Snyk API origin on **`sync`** and **`fetch`**, and **`--mapping-store-sqlite-path`** for **`sqlite_path`** when using SQLite) SHALL live under **`src/commands/`**. **`src/main.py`** SHALL remain the main entry point, building the parser and dispatching to subcommands, including at minimum **`fetch`** and **`sync`**. User-facing help SHALL describe how to pass the configuration file and that **CLI values override** file-based values for the current invocation where applicable.

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

The repository **`README.md`** SHALL include a completed **`Configuration`** section (including **`Parameter Descriptions`**) that documents: YAML file location and format overview; **precedence** (**defaults → file → env → CLI**, CLI wins); that **YAML is the intended IaC / deployment source** and CLI is primarily for **local overrides**; CLI flags for config; supported environment variables (including overrides and secrets policy); defaults and optional omissions; **`mapping_store`**, **`sqlite_path`**, **`MAPPING_STORE`**, **`MAPPING_STORE_SQLITE_PATH`**, **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`**, **`MAPPING_STORE_AZURE_TABLE_NAME`**, and **`--mapping-store-sqlite-path`**; **`snyk.api_base_url`**, **`SNYK_API_BASE_URL`**, and **`--snyk-api-base-url`** (default **`https://api.snyk.io`**, **SNYK-US-01**); that the SQLite database is **local non-secret persistence** and **secrets MUST NOT** be stored in that path or file; **`azure_boards.defaults`** for **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and **`work_item_template`**, with defaults where applicable, and that flat **`work_item_*`**, **`organization`**, **`project`**, **`create_new_work_items`**, and **`severity_threshold`** keys directly under **`azure_boards`** or **`snyk`** for severity are **not** supported; **`azure_boards.org_mappings`** with **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`**, and optional **`overrides`**; that assignee MAY be set via **`json_patch`** targeting **`/fields/System.AssignedTo`** under merged **`work_item_template`** semantics; **mapping store column reference** per **README documents mapping store columns**; and an **example YAML** snippet (or pointer to the **`data/`** sample) that reflects the keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` without embedding real tokens or secrets.

The **`README.md`** SHALL also include a **`Deployment`** subsection (which MAY sit after **`Configuration`** or **`Error Handling/Logging`**) that describes **Azure Container Apps** operation at a high level: non-secret operator YAML on **Azure Files** (mount path convention as implemented or documented), **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** from **Key Vault** via Container Apps secret references / environment injection, **`SNYK_API_BASE_URL`** for regional Snyk API host when not on **SNYK-US-01**, **managed identity** for Azure resource access, **`mapping_store: azure_table`** with Table endpoint and table name via environment variables, and **where to view logs**: **Log stream** under the Container App for live **stdout/stderr**, versus **Logs** / **Log Analytics** for historical queries (including tables such as **`ContainerAppConsoleLogs_CL`**, noting exact table names MAY depend on workspace configuration), cross-referencing the **Error Handling/Logging** section's guidance on **`integration_audit`** and stdout JSON.

#### Scenario: Operator can configure without reading source

- **WHEN** an operator reads only the README Configuration section
- **THEN** they SHALL be able to construct a valid YAML file and run the CLI with a config path using documented flags and variables, and SHALL understand when **`group_id`** is required for Snyk fetch and **`sync`**, including when **`org_mappings`** is used

#### Scenario: Operator can locate Container App logs

- **WHEN** an operator reads the README Deployment subsection
- **THEN** they SHALL understand how to open **Log stream** for immediate stdout/stderr and how to query workspace logs (e.g. **`ContainerAppConsoleLogs_CL`**) for **`sync_summary`** / **`integration_http`** troubleshooting as described in **Error Handling/Logging**

---

### Requirement: Sample configuration file under `data/`

The repository SHALL include at least one **sample** YAML configuration file under the **`data/`** directory that conforms to the documented schema (placeholder values only; no secrets). The sample SHALL include **`mapping_store`** and **`sqlite_path`** with placeholder non-secret values. The sample SHALL document **`azure_boards.defaults`** with **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, optional **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and optional **`work_item_template`**, with defaults or comments consistent with this capability. The sample SHALL include under **`snyk`** a commented example of **`api_base_url`** (default **`https://api.snyk.io`**, **SNYK-US-01**) with a pointer to regional hosts in documentation. The sample SHALL include a commented example of **`azure_boards.org_mappings`** (optional list) with placeholder **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`**, and example **`overrides`**. The sample SHALL be **tracked in version control** and SHALL **not** be excluded by **`.gitignore`** (or equivalent ignore rules), so it remains available in every clone for documentation and local testing (e.g. `--config` pointing at that path).

#### Scenario: Sample present and tracked

- **WHEN** a developer clones the repository
- **THEN** they SHALL find a sample YAML file under `data/` that validates against the loader and is not gitignored by default

#### Scenario: README references sample path

- **WHEN** an operator reads the README Configuration section
- **THEN** it SHALL mention the `data/` sample file path (or glob) so users can run the CLI against it without authoring YAML from scratch

#### Scenario: Sample shows sync-related azure_boards defaults

- **WHEN** a developer opens the tracked sample YAML
- **THEN** it SHALL include documented **`azure_boards.defaults`** for routing, creation toggle, severity, and sync-related work item strings with defaults or placeholders consistent with this capability
