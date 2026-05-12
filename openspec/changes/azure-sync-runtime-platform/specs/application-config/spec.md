## MODIFIED Requirements

### Requirement: README configuration documentation

The repository **`README.md`** SHALL include a completed **`Configuration`** section (including **`Parameter Descriptions`**) that documents: YAML file location and format overview; **precedence** (**defaults → file → env → CLI**, CLI wins); that **YAML is the intended IaC / deployment source** and CLI is primarily for **local overrides**; CLI flags for config; supported environment variables (including overrides and secrets policy); defaults and optional omissions; **`mapping_store`**, **`sqlite_path`**, **`MAPPING_STORE`**, **`MAPPING_STORE_SQLITE_PATH`**, **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`**, **`MAPPING_STORE_AZURE_TABLE_NAME`**, and **`--mapping-store-sqlite-path`**; that the SQLite database is **local non-secret persistence** and **secrets MUST NOT** be stored in that path or file; **`azure_boards.defaults`** for **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and **`work_item_template`**, with defaults where applicable, and that flat **`work_item_*`**, **`organization`**, **`project`**, **`create_new_work_items`**, and **`severity_threshold`** keys directly under **`azure_boards`** or **`snyk`** for severity are **not** supported; **`azure_boards.org_mappings`** with **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`**, and optional **`overrides`**; that assignee MAY be set via **`json_patch`** targeting **`/fields/System.AssignedTo`** under merged **`work_item_template`** semantics; **mapping store column reference** per **README documents mapping store columns**; and an **example YAML** snippet (or pointer to the **`data/`** sample) that reflects the keys `azure_boards`, `work_item_template`, `snyk`, `mapping_store`, and `sqlite_path` without embedding real tokens or secrets.

The **`README.md`** SHALL also include a **`Deployment`** subsection (which MAY sit after **`Configuration`** or **`Error Handling/Logging`**) that describes **Azure Container Apps** operation at a high level: non-secret operator YAML on **Azure Files** (mount path convention as implemented or documented), **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** from **Key Vault** via Container Apps secret references / environment injection, **managed identity** for Azure resource access, **`mapping_store: azure_table`** with Table endpoint and table name via environment variables, and **where to view logs**: **Log stream** under the Container App for live **stdout/stderr**, versus **Logs** / **Log Analytics** for historical queries (including tables such as **`ContainerAppConsoleLogs_CL`**, noting exact table names MAY depend on workspace configuration), cross-referencing the **Error Handling/Logging** section’s guidance on **`integration_audit`** and stdout JSON.

#### Scenario: Operator can configure without reading source

- **WHEN** an operator reads only the README Configuration section
- **THEN** they SHALL be able to construct a valid YAML file and run the CLI with a config path using documented flags and variables, and SHALL understand when **`group_id`** is required for Snyk fetch and **`sync`**, including when **`org_mappings`** is used

#### Scenario: Operator can locate Container App logs

- **WHEN** an operator reads the README Deployment subsection
- **THEN** they SHALL understand how to open **Log stream** for immediate stdout/stderr and how to query workspace logs (e.g. **`ContainerAppConsoleLogs_CL`**) for **`sync_summary`** / **`integration_http`** troubleshooting as described in **Error Handling/Logging**

---

### Requirement: Mapping store environment and CLI overrides

For **`mapping_store`** and **`sqlite_path`**, the implementation SHALL recognize these **environment variable** overrides: **`MAPPING_STORE`** (same semantics as YAML `mapping_store`) and **`MAPPING_STORE_SQLITE_PATH`** (same semantics as YAML `sqlite_path`). When **`mapping_store`** resolves to **`azure_table`**, the implementation SHALL additionally require non-empty **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`** (HTTPS URL of the Table service endpoint, e.g. `https://<account>.table.core.windows.net`) and **`MAPPING_STORE_AZURE_TABLE_NAME`** (Table name). These variables SHALL be **non-secret** configuration. The CLI MAY expose **`--mapping-store-sqlite-path`** to override **`sqlite_path`** for the current process. These layers SHALL participate in the same **defaults → YAML → environment → CLI** precedence as all other multi-layer settings in this capability.

#### Scenario: Environment overrides YAML for mapping store

- **WHEN** `mapping_store` is set in YAML and **`MAPPING_STORE`** is set in the environment
- **THEN** the effective `mapping_store` SHALL be the environment value

#### Scenario: CLI overrides environment for SQLite path

- **WHEN** **`MAPPING_STORE_SQLITE_PATH`** is set and the user passes **`--mapping-store-sqlite-path`**
- **THEN** the effective `sqlite_path` SHALL be the CLI value

#### Scenario: Default mapping store when all layers omit it

- **WHEN** `mapping_store` and `sqlite_path` are not specified in YAML, environment, or CLI
- **THEN** after defaulting, `mapping_store` SHALL be **`sqlite`** and `sqlite_path` SHALL be **`data/mapping_store.sqlite`**

#### Scenario: Azure table requires endpoint and table name in environment

- **WHEN** effective **`mapping_store`** is **`azure_table`**
- **THEN** **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`** and **`MAPPING_STORE_AZURE_TABLE_NAME`** SHALL both be non-empty after precedence resolution before any command performs mapping store I/O
