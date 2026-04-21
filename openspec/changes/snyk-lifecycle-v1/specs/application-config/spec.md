## ADDED Requirements

### Requirement: Azure Boards work item type and state strings for sync

Under **`azure_boards`**, the configuration SHALL include these additional **non-secret** string keys used by the **`sync`** command when creating or transitioning work items:

- **`work_item_type`**: Boards work item type name for **`$type`** on create (default **`Task`** when omitted after merge).
- **`work_item_state_active`**: Boards **`System.State`** value representing an **active** finding in the operator’s process (default **`New`** when omitted after merge).
- **`work_item_state_closed`**: Boards **`System.State`** value used when placing a work item on the **close path** for Snyk **resolved** or **ignored** findings (default **`Closed`** when omitted after merge).

After merge, each key SHALL either be omitted (and therefore defaulted as above) or be a **non-empty** string; empty strings SHALL be rejected with a clear, non-secret error **before** the per-issue sync loop begins.

The **`README.md`** and the tracked sample YAML under **`data/`** SHALL list these keys under **`azure_boards`** with their **defaults** and SHALL explain that operators **MUST** choose values that exist for their **process template** (for example Agile **Task** vs other work item types and valid state names).

#### Scenario: Defaults when keys omitted

- **WHEN** the three keys are absent from YAML and not overridden by environment or CLI layers documented for this product
- **THEN** merged configuration SHALL expose `Task`, `New`, and `Closed` as the effective defaults for sync

#### Scenario: Empty string rejected at sync startup

- **WHEN** `azure_boards.work_item_state_active` is set to an empty string and the user runs **`sync`**
- **THEN** the command SHALL exit non-zero before processing issues with an error that does not include secrets

### Requirement: Sync command requires non-empty Snyk group id

The **`sync`** command SHALL follow the same **`snyk.group_id`** non-empty validation rules as group-scoped **`fetch`**: when merged **`snyk.group_id`** is missing or empty, the process SHALL exit with a clear, non-secret error **before** issuing group-scoped Snyk Issues API calls. Help-only invocations SHALL NOT require `group_id`.

#### Scenario: Sync without group id

- **WHEN** the user runs **`sync`** and merged `snyk.group_id` is missing or empty
- **THEN** the command SHALL exit non-zero without calling Snyk Issues list for the group

---

## MODIFIED Requirements

### Requirement: Azure Boards global creation toggle

Under `azure_boards`, the configuration SHALL include **`create_new_work_items`**, a boolean that **globally enables or disables creation of new Azure Boards work items** (satisfies **P2-FR-11**). When set to `false`, the application MUST NOT create new work items for qualifying findings. When set to `false`, the **`sync`** command SHALL additionally **never insert** a new mapping row for issues that do not already have a mapping; it SHALL still **update** and **close** mapped work items per **`sync-lifecycle`**. When set to `true`, downstream sync logic MAY create new work items subject to other requirements (e.g. **P2-FR-1**).

#### Scenario: Creation disabled

- **WHEN** `azure_boards.create_new_work_items` is `false`
- **THEN** downstream sync logic SHALL treat new work item creation as disabled for policy decisions that read this setting and SHALL not insert new mapping rows for unmapped issues

#### Scenario: Creation enabled

- **WHEN** `azure_boards.create_new_work_items` is `true`
- **THEN** downstream sync logic MAY create new work items subject to other requirements (e.g. **P2-FR-1**)

---

### Requirement: Work item template section

The **`work_item_template`** value SHALL be a **mapping** (YAML dictionary). It MAY be empty. The loader SHALL accept an empty mapping and preserve unknown keys for forward compatibility where the YAML library permits.

For **`sync`**, the following inner keys, when present, SHALL be interpreted by the application:

- **`tags`**: A YAML list of strings representing work item tags to apply on create and update (**P2-FR-10**).
- **`json_patch`**: A YAML list of JSON Patch operation objects (`op`, `path`, optional `value`) appended or merged into work item create/update patch lists as documented in the active change **`design.md`** (superseded by archived spec after merge), without transporting secrets.

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

The repository **`README.md`** SHALL include a completed **`Configuration`** section (including **`Parameter Descriptions`**) that documents: YAML file location and format overview; **precedence** (**defaults → file → env → CLI**, CLI wins); that **YAML is the intended IaC / deployment source** and CLI is primarily for **local overrides**; CLI flags for config; supported environment variables (including overrides and secrets policy); defaults and optional omissions; **`mapping_store`**, **`sqlite_path`**, **`MAPPING_STORE`**, **`MAPPING_STORE_SQLITE_PATH`**, and **`--mapping-store-sqlite-path`**; that the SQLite database is **local non-secret persistence** and **secrets MUST NOT** be stored in that path or file; **`azure_boards.work_item_type`**, **`azure_boards.work_item_state_active`**, and **`azure_boards.work_item_state_closed`** with defaults (**`Task`**, **`New`**, **`Closed`**) and the requirement that operators set valid values for their process; and an **example YAML** snippet (or pointer to the **`data/`** sample) that reflects the keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` without embedding real tokens or secrets.

#### Scenario: Operator can configure without reading source

- **WHEN** an operator reads only the README Configuration section
- **THEN** they SHALL be able to construct a valid YAML file and run the CLI with a config path using documented flags and variables, and SHALL understand when **`group_id`** is required for Snyk fetch and **`sync`**

---

### Requirement: Sample configuration file under `data/`

The repository SHALL include at least one **sample** YAML configuration file under the **`data/`** directory that conforms to the documented schema (placeholder values only; no secrets). The sample SHALL include **`mapping_store`** and **`sqlite_path`** with placeholder non-secret values. The sample SHALL list **`azure_boards.work_item_type`**, **`azure_boards.work_item_state_active`**, and **`azure_boards.work_item_state_closed`** with their documented defaults and comments stating that values MUST exist for the target process. The sample SHALL be **tracked in version control** and SHALL **not** be excluded by **`.gitignore`** (or equivalent ignore rules), so it remains available in every clone for documentation and local testing (e.g. `--config` pointing at that path).

#### Scenario: Sample present and tracked

- **WHEN** a developer clones the repository
- **THEN** they SHALL find a sample YAML file under `data/` that validates against the loader and is not gitignored by default

#### Scenario: README references sample path

- **WHEN** an operator reads the README Configuration section
- **THEN** it SHALL mention the `data/` sample file path (or glob) so users can run the CLI against it without authoring YAML from scratch

#### Scenario: Sample shows sync-related azure_boards keys

- **WHEN** a developer opens the tracked sample YAML
- **THEN** it SHALL include the three `azure_boards` keys introduced for sync with defaults or placeholders consistent with this capability
