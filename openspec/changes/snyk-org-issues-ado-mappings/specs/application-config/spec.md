## ADDED Requirements

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`** (**`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_template`**). Omitted override keys SHALL inherit from **`defaults`** after merge per the active change **`design.md`**.

The loader SHALL reject entries missing required keys or containing empty strings for **`organization`**, **`project`**, or **`snyk_org_id`** with a clear, non-secret error.

#### Scenario: Valid org_mappings row loads

- **WHEN** YAML contains one **`org_mappings`** row with non-empty **`organization`**, **`project`**, and **`snyk_org_id`**
- **THEN** loading SHALL succeed and expose that row for **`sync`**

#### Scenario: Invalid org_mappings row rejected

- **WHEN** a row omits **`snyk_org_id`** or supplies an empty **`organization`**
- **THEN** loading SHALL fail with a clear error that does not include secrets

---

## MODIFIED Requirements

### Requirement: YAML configuration file format

The application SHALL support an operator configuration file in **YAML** format. The file SHALL be non-secret policy only; credentials such as `SNYK_TOKEN` or Azure DevOps PATs SHALL NOT be read from this file (see `openspec/specs/azure-platform/spec.md`).

The following **top-level keys** define the configuration namespaces (after load, **defaults** apply for omitted sections or keys where this capability specifies defaults):

| Key | Purpose |
|-----|---------|
| `azure_boards` | Settings for Azure Boards behavior, including global creation enablement (**P2-FR-11**), non-secret Azure DevOps routing (**`organization`**, **`project`**), optional **`defaults`** (work item type, states, embedded **`work_item_template`**), and optional **`org_mappings`** (list of ADO **`organization`** / **`project`** + **`snyk_org_id`** + optional **`overrides`**) for multi-target sync. |
| `work_item_template` | Global template mapping (**`tags`**, **`json_patch`**) merged with **`azure_boards.defaults.work_item_template`** and per-mapping **`overrides.work_item_template`** per the active change **`design.md`**; MAY be empty. |
| `snyk` | Snyk integration settings, including **group ID** and **severity threshold**; additional keys MAY be added in later changes. |
| `mapping_store` | Backend for Snyk↔work-item mapping persistence (**P2-FR-7**): **`sqlite`** for local dev/tests, or reserved **`azure_table`** for production-style storage (see `azure-platform`). |
| `sqlite_path` | Filesystem path to the SQLite database file when `mapping_store` is **`sqlite`**. |

An operator **MAY omit** any top-level key (or inner optional key) for which this capability defines a **default**; the resolved configuration after parsing and defaulting SHALL match the documented behavior. The **README** and **`data/`** sample SHALL show a **complete** example shape for copy-paste and IaC, including **`azure_boards.defaults`** and an optional **`azure_boards.org_mappings`** example when this change is applied.

#### Scenario: Omitted sections receive defaults

- **WHEN** a valid YAML file omits optional keys or sections that have documented defaults
- **THEN** loading SHALL succeed and the resolved configuration SHALL include those defaults

#### Scenario: Full shape in documentation

- **WHEN** an operator copies the example from the README or `data/` sample
- **THEN** the file SHALL list the top-level keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` with placeholder non-secret values (omissions allowed only where defaults apply per documented rules)

#### Scenario: Documentation reflects multi-target azure_boards

- **WHEN** an operator reads the README Configuration section or `data/` sample after this change is applied
- **THEN** they SHALL find **`azure_boards.defaults`** documented with **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and **`work_item_template`**, and SHALL find **`azure_boards.org_mappings`** described as a list of **`organization`**, **`project`**, **`snyk_org_id`**, and optional **`overrides`**

---

### Requirement: Azure Boards work item type and state strings for sync

Under **`azure_boards.defaults`**, the configuration SHALL include these **non-secret** string keys used by the **`sync`** command when creating or transitioning work items (after merge of **`defaults`** with per-mapping **`overrides`**):

- **`work_item_type`**: Boards work item type name for **`$type`** on create (default **`Task`** when omitted after merge).
- **`work_item_state_active`**: Boards **`System.State`** value representing an **active** finding in the operator’s process (default **`New`** when omitted after merge).
- **`work_item_state_closed`**: Boards **`System.State`** value used when placing a work item on the **close path** for Snyk **resolved** or **ignored** findings (default **`Closed`** when omitted after merge).

Under **`azure_boards.defaults`**, the configuration MAY include **`work_item_template`**, a mapping with the same inner semantics as top-level **`work_item_template`** (**`tags`**, **`json_patch`**).

The loader SHALL **not** accept **`work_item_type`**, **`work_item_state_active`**, or **`work_item_state_closed`** as direct children of **`azure_boards`**; operators SHALL use **`azure_boards.defaults`** only. If those flat keys appear, loading SHALL fail with a clear, non-secret error.

After merge, each effective key SHALL either be omitted (and therefore defaulted as above) or be a **non-empty** string; empty strings SHALL be rejected with a clear, non-secret error **before** the per-issue sync loop begins.

The **`README.md`** and the tracked sample YAML under **`data/`** SHALL document **`azure_boards.defaults`** with the **defaults** above and SHALL explain that operators **MUST** choose values that exist for their **process template** (for example Agile **Task** vs other work item types and valid state names).

#### Scenario: Defaults when keys omitted

- **WHEN** the effective keys are absent from YAML and not overridden by environment or CLI layers documented for this product
- **THEN** merged configuration SHALL expose `Task`, `New`, and `Closed` as the effective defaults for sync

#### Scenario: Empty string rejected at sync startup

- **WHEN** the effective `work_item_state_active` is an empty string and the user runs **`sync`**
- **THEN** the command SHALL exit non-zero before processing issues with an error that does not include secrets

#### Scenario: Flat work item keys under azure_boards rejected at load

- **WHEN** YAML sets **`azure_boards.work_item_type`** (or state keys) at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error directing use of **`azure_boards.defaults`**

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

When **`org_mappings`** is non-empty, each **mapping entry** SHALL include its own **`organization`** and **`project`** strings for Azure DevOps routing for issues processed in that mapping’s iteration; the top-level **`azure_boards.organization`** and **`azure_boards.project`** MAY still be used as documented fallbacks or for commands that do not iterate **`org_mappings`** (exact precedence SHALL match the active change **`design.md`**).

These values SHALL NOT be used to transport secrets. The **`azure-devops-client`** and related commands SHALL obtain routing fields from merged configuration or explicit CLI overrides per this capability’s precedence rules; the integration package SHALL NOT read the YAML file directly.

The sample configuration file under **`data/`** and the **`README.md`** configuration documentation SHALL include **`azure_boards.organization`** and **`azure_boards.project`** with placeholder non-secret values and SHALL document **`org_mappings`** entries with per-row **`organization`** and **`project`** when this change is applied.

#### Scenario: Sample lists routing keys

- **WHEN** a developer opens the tracked sample YAML under `data/`
- **THEN** it SHALL include `azure_boards.organization` and `azure_boards.project` alongside documented `azure_boards` keys, and SHALL document **`defaults`** and optional **`org_mappings`** as specified in this change

#### Scenario: README documents routing keys

- **WHEN** an operator reads the README Configuration / parameter descriptions
- **THEN** they SHALL find `azure_boards.organization` and `azure_boards.project` described, and SHALL find **`org_mappings`** row fields described for multi-target sync

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
