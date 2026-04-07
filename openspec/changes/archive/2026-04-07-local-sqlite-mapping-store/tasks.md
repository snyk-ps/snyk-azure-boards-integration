## 1. Configuration and path resolution

- [x] 1.1 Extend config models (`MappingStoreConfig` or fields on `AppConfig`) with `mapping_store` and `sqlite_path`; document defaults (`sqlite`, `data/mapping_store.sqlite`) in code aligned with `design.md`.
- [x] 1.2 Merge YAML keys `mapping_store` / `sqlite_path`, environment **`MAPPING_STORE`** / **`MAPPING_STORE_SQLITE_PATH`**, and CLI **`--mapping-store-sqlite-path`** per **defaults → YAML → env → CLI** (later wins).
- [x] 1.3 Add unit tests for merge precedence and defaults (including edge cases: empty string, unknown `mapping_store` handling as defined in implementation notes from `design.md`).

## 2. Schema and idempotent initialization

- [x] 2.1 Define a single DDL source for table **`issue_work_item_map`** (or the chosen name) with **TEXT** columns: `group_id`, `org_id`, `project_id`, `issue_id`, `snyk_status`, `organization`, `project`, `work_item_id`, `work_item_status`, `created_at`, `updated_at`, plus **UNIQUE (`group_id`, `org_id`, `project_id`, `issue_id`)** and indexes as needed; use **`CREATE TABLE IF NOT EXISTS`** / **`CREATE INDEX IF NOT EXISTS`**.
- [x] 2.2 Add a committed entry point under **`scripts/`** that resolves **`sqlite_path`** the same way as runtime and applies the DDL idempotently (creating parent directories for the DB file if required).
- [x] 2.3 Add unit or integration tests proving a second init run succeeds and schema matches expectations.

## 3. Mapping-store abstraction and SQLite implementation

- [x] 3.1 Introduce a small **`src/`** abstraction (protocol or ABC) for mapping persistence (CRUD: insert/upsert, get by natural key, update, delete as needed for tests) without sync orchestration.
- [x] 3.2 Implement the SQLite-backed adapter using **`sqlite3`** (stdlib); set **`created_at`** on insert and **`updated_at`** on write using **UTC ISO 8601** `Z` strings.
- [x] 3.3 Enforce natural-key uniqueness via SQLite constraint and map violations to clear, non-secret errors.
- [x] 3.4 Add unit tests for the repository (happy paths, duplicate key, round-trip read after write).

## 4. Backend selection and fail-fast

- [x] 4.1 When resolved **`mapping_store`** is **`azure_table`**, exit **non-zero** with a message naming **`mapping_store`** and the missing adapter or credentials (no SQLite fallback); cover with unit tests.
- [x] 4.2 Wire factory or entry-level selection so CLI/tests can obtain a **`sqlite`** store when configured (without implementing full sync).

## 5. Documentation and samples

- [x] 5.1 Update **`README.md`** Configuration: `mapping_store`, `sqlite_path`, env vars, **`--mapping-store-sqlite-path`**, precedence, default path, and **secrets MUST NOT** live in the SQLite path/file.
- [x] 5.2 Update **`data/`** sample YAML with **`mapping_store`** and **`sqlite_path`** placeholder values; ensure `.gitignore` does not exclude the sample.

## 6. Spec merge (post-implementation)

- [x] 6.1 After implementation review, merge delta specs from `openspec/changes/local-sqlite-mapping-store/specs/` into `openspec/specs/azure-platform/spec.md` and `openspec/specs/application-config/spec.md` per project archive workflow (or as a final apply task if your process merges before archive).
