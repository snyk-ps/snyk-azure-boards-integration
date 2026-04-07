## MODIFIED Requirements

### Requirement: YAML configuration file format

The application SHALL support an operator configuration file in **YAML** format. The file SHALL be non-secret policy only; credentials such as `SNYK_TOKEN` or Azure DevOps PATs SHALL NOT be read from this file (see `openspec/specs/azure-platform/spec.md`).

The following **top-level keys** define the configuration namespaces (after load, **defaults** apply for omitted sections or keys where this capability specifies defaults):

| Key | Purpose |
|-----|---------|
| `azure_boards` | Settings for Azure Boards behavior, including global creation enablement (**P2-FR-11**). |
| `work_item_template` | Placeholder mapping for future work item defaults (type, fields, routing); MAY be empty. |
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

### Requirement: Configuration loading and defaults

The application SHALL load YAML from a **filesystem path** supplied via CLI (e.g. `--config`) and/or a documented environment variable for the path, as implemented per `design.md`. After parsing, the implementation SHALL apply **defaults** for optional keys (including `azure_boards.create_new_work_items` defaulting to **`true`**, `snyk.severity_threshold` defaulting to **`high`**, **`mapping_store`** defaulting to **`sqlite`**, and **`sqlite_path`** defaulting to **`data/mapping_store.sqlite`** unless specified otherwise in `design.md`), then merge **environment** and **CLI** layers per the **Precedence** requirement before validating command-specific requirements (e.g. non-empty `group_id` for **`fetch`**). The loader SHALL produce a clear, non-secret error when the file is missing, unreadable, or not valid YAML.

#### Scenario: Defaults applied

- **WHEN** optional keys are omitted from YAML
- **THEN** the resolved configuration object SHALL contain the documented defaults

#### Scenario: Invalid YAML

- **WHEN** the file content is not valid YAML
- **THEN** loading SHALL fail with an error that does not include secret material

---

### Requirement: CLI and entrypoint wiring

**`argparse`** definitions for configuration (including at minimum **`--config`** with a path to the YAML file) and for any **override** flags that participate in the same precedence model (e.g. group id for **`fetch`**, and **`--mapping-store-sqlite-path`** for **`sqlite_path`** when using SQLite) SHALL live under **`src/commands/`**. **`src/main.py`** SHALL remain the main entry point, building the parser and dispatching to subcommands. User-facing help SHALL describe how to pass the configuration file and that **CLI values override** file-based values for the current invocation where applicable.

#### Scenario: Help lists config flag

- **WHEN** the user runs the application entry point with standard help (e.g. `--help`)
- **THEN** the help output SHALL mention the configuration file option as implemented

#### Scenario: Help does not require group ID

- **WHEN** the user runs with **`--help`** only
- **THEN** the process SHALL succeed without loading a full config or validating `group_id`

---

### Requirement: README configuration documentation

The repository **`README.md`** SHALL include a completed **`Configuration`** section (including **`Parameter Descriptions`**) that documents: YAML file location and format overview; **precedence** (**defaults → file → env → CLI**, CLI wins); that **YAML is the intended IaC / deployment source** and CLI is primarily for **local overrides**; CLI flags for config; supported environment variables (including overrides and secrets policy); defaults and optional omissions; **`mapping_store`**, **`sqlite_path`**, **`MAPPING_STORE`**, **`MAPPING_STORE_SQLITE_PATH`**, and **`--mapping-store-sqlite-path`**; that the SQLite database is **local non-secret persistence** and **secrets MUST NOT** be stored in that path or file; and an **example YAML** snippet (or pointer to the **`data/`** sample) that reflects the keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` without embedding real tokens or secrets.

#### Scenario: Operator can configure without reading source

- **WHEN** an operator reads only the README Configuration section
- **THEN** they SHALL be able to construct a valid YAML file and run the CLI with a config path using documented flags and variables, and SHALL understand when **`group_id`** is required for Snyk fetch

---

### Requirement: Sample configuration file under `data/`

The repository SHALL include at least one **sample** YAML configuration file under the **`data/`** directory that conforms to the documented schema (placeholder values only; no secrets). The sample SHALL include **`mapping_store`** and **`sqlite_path`** with placeholder non-secret values. The sample SHALL be **tracked in version control** and SHALL **not** be excluded by **`.gitignore`** (or equivalent ignore rules), so it remains available in every clone for documentation and local testing (e.g. `--config` pointing at that path).

#### Scenario: Sample present and tracked

- **WHEN** a developer clones the repository
- **THEN** they SHALL find a sample YAML file under `data/` that validates against the loader and is not gitignored by default

#### Scenario: README references sample path

- **WHEN** an operator reads the README Configuration section
- **THEN** it SHALL mention the `data/` sample file path (or glob) so users can run the CLI against it without authoring YAML from scratch

---

## ADDED Requirements

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
