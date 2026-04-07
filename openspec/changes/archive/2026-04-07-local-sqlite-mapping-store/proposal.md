## Why

Developers and automated tests need **durable Snyk↔work-item mappings** without Azure Table Storage or cloud credentials. A **local SQLite** database and shared `src/` persistence layer provide the same logical mapping contract for dev/CI while production continues to target **Azure Table Storage** in later work.

## What Changes

- Add an **idempotent** SQL init path under **`scripts/`** (committed): `CREATE TABLE IF NOT EXISTS` and optional `CREATE INDEX IF NOT EXISTS` for the mapping table; creates/opens the DB file using the **same path resolution** as runtime.
- Define a **mapping table schema** with **snake_case** columns: `group_id`, `org_id`, `project_id`, `issue_id`, `snyk_status`, `organization`, `project`, `work_item_id`, `work_item_status`, `created_at`, `updated_at` — all **TEXT**; **UNIQUE** on `(group_id, org_id, project_id, issue_id)` for stable one-row-per-issue-in-scope (**P2-FR-7**).
- Rename the prior “Status” concept to **Snyk status** (Snyk issue lifecycle); add **work item status** (Azure Boards work item state).
- Store **`created_at`** and **`updated_at`** as **UTC ISO 8601** strings (e.g. `2026-04-07T14:30:00.000Z`).
- Add **configuration** for backend choice and SQLite file path: explicit **`mapping_store`** (e.g. `sqlite`; **`azure_table`** reserved), **`sqlite_path`** / env / optional CLI flag, following **defaults → YAML → env → CLI** with **later wins**; document **default DB path** when unset (predictable for local/CI).
- Document: **secrets MUST NOT** be stored in the SQLite path or mapping DB; tokens/PATs stay in env/Key Vault per existing rules.
- When **`mapping_store` is `azure_table`** and the adapter or credentials are missing, the process **SHALL exit non-zero** with a **clear message** — **no silent fallback to SQLite**.
- Introduce a **small mapping-store abstraction** in **`src/`** with a **SQLite implementation** (CRUD against the mapping table) shared by app and tests; **sync orchestration** (Snyk fetch, rules, ADO calls) remains **out of scope**.

## Capabilities

### New Capabilities

- _(none — persistence behavior extends existing platform and config specs.)_

### Modified Capabilities

- **`azure-platform`**: Extend durable mapping contract (field names including Snyk vs work item status, row timestamps, TEXT storage, natural key / uniqueness); describe **SQLite** as an allowed **local dev/test** stand-in; specify **fail-fast** behavior when **`azure_table`** is selected but not usable.
- **`application-config`**: Add **`mapping_store`**, **`sqlite_path`**, environment variable names, optional CLI override for SQLite path, default path when omitted, and README / `data/` sample alignment; reinforce that the SQLite file is **non-secret** local persistence only.

## Impact

- **`scripts/`**: new idempotent init entry point (SQL or thin wrapper).
- **`src/`**: config models/loader extensions, mapping repository protocol + SQLite adapter, shared types for mapping rows.
- **`openspec/specs/`**: delta updates under this change for **`azure-platform`** and **`application-config`**.
- **`README.md`** / **`data/`** sample YAML: document mapping store settings and security note (per **application-config** requirements).
- **Tests**: unit tests for path resolution, init idempotency behavior as exposed, and public repository/API surfaces.
- **Dependencies**: prefer **stdlib** `sqlite3`; any new third-party deps require Snyk policy checks before merge.
