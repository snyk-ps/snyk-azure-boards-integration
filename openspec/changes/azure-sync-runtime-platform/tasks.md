## 1. Dependencies and configuration model

- [ ] 1.1 Add **`azure-data-tables`** and **`azure-identity`** with **uv**; run **Snyk Open Source** (and **Snyk Code** on new code) before merge; pin versions per repo convention.
- [ ] 1.2 Extend **`AppConfig`** / loader to read **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`** and **`MAPPING_STORE_AZURE_TABLE_NAME`** when **`mapping_store`** is **`azure_table`**, with validation errors that name missing variables (no secrets).
- [ ] 1.3 Add unit tests for config resolution and validation for **`azure_table`** (missing env, invalid endpoint shape if validated).

## 2. Table identity encoding and entity mapping

- [ ] 2.1 Implement **`table_row_key(org_id, project_id, issue_id)`** (and related helpers) per **`design.md`**: delimiter form vs base64url-when-forbidden; document edge cases in module docstring.
- [ ] 2.2 Implement bidirectional mapping between **`MappingRow`** fields and Table entity string properties (**snake_case** keys); include **`PartitionKey`** / **`RowKey`** handling without leaking secrets in repr/logs.
- [ ] 2.3 Unit tests for **`table_row_key`**: typical identifiers, delimiter branch; components containing **`/`**, **`#`**, **`?`**, **`\\`** forcing base64url branch; UTF-8 non-ASCII if applicable.

## 3. Azure Table **`MappingStore`** implementation

- [ ] 3.1 Add **`AzureTableMappingStore`** (or equivalent) implementing **`MappingStore`**: **`get_by_natural_key`**, **`upsert`**, **`delete_by_natural_key`** using **`TableClient`** + **`DefaultAzureCredential`**.
- [ ] 3.2 On factory initialization, ensure table exists via **`create_table_if_not_exists`** (idempotent) or equivalent documented behavior aligned with **`design.md`**.
- [ ] 3.3 Preserve **`created_at`** on update (**`updated_at`** refreshed) consistent with SQLite behavior and **`azure-platform`** timestamps requirement.
- [ ] 3.4 Unit tests with mocked **`TableClient`** (or Azure SDK test stubs) covering get hit/miss, upsert insert vs update, delete true/false, and error propagation without fallback.

## 4. Factory wiring and failure modes

- [ ] 4.1 Update **`create_mapping_store`** to return **`AzureTableMappingStore`** when **`mapping_store`** is **`azure_table`** and configuration is complete; retain **`AzureTableMappingStoreUnavailableError`** / non-zero exit for incomplete config or credential failures at wiring time (no SQLite fallback).
- [ ] 4.2 Integration smoke: optional manual note in **`README`** or **`design.md`** only—keep automated tests mock-based unless emulator task is explicitly added later.

## 5. Documentation

- [ ] 5.1 Update **`README.md`**: **`Deployment`** subsection per **`application-config`** delta (ACA, Files, Key Vault, managed identity, **`mapping_store: azure_table`** env vars, **Log stream** vs **Log Analytics** / **`ContainerAppConsoleLogs_CL`**, link to Microsoft docs as appropriate).
- [ ] 5.2 Document **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`** and **`MAPPING_STORE_AZURE_TABLE_NAME`** in **`Parameter Descriptions`** / environment variable tables alongside existing **`MAPPING_STORE`** variables.

## 6. Spec apply / archive prep

- [ ] 6.1 After implementation, run **`openspec apply`** workflow to merge **`openspec/changes/azure-sync-runtime-platform/specs/`** deltas into **`openspec/specs/`** per project convention (during `/openspec:apply`, not ad hoc).
- [ ] 6.2 Confirm **`pytest`** passes for the repository **uv** environment.
