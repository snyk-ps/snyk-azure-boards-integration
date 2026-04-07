## ADDED Requirements

### Requirement: Mapping row schema and logical identity

The durable mapping store SHALL persist at minimum the following attributes per row, using **snake_case** **column** names and **TEXT** storage for all listed fields. Together they support **stable mapping** (**P2-FR-7**) and traceability for **re-open** behavior (**P2-FR-8**).

| Field | Role |
|-------|------|
| `group_id` | Snyk group identifier (with org and project) for the issue. |
| `org_id` | Snyk organization that owns the project and issue. |
| `project_id` | Snyk project containing the issue. |
| `issue_id` | Stable Snyk issue identifier. |
| `snyk_status` | Snyk issue lifecycle (e.g. open, closed, ignored) for sync policy. |
| `organization` | Azure DevOps organization name or id for REST calls. |
| `project` | Azure DevOps team project containing the work item. |
| `work_item_id` | Azure Boards work item id linked to this Snyk issue. |
| `work_item_status` | Azure Boards work item state as persisted for this mapping row. |

The logical identity of one **current** mapping for a Snyk issue in a given scope SHALL be **`(group_id, org_id, project_id, issue_id)`**. The implementation SHALL enforce **at most one row** per that tuple via a **UNIQUE** constraint on those four columns (or equivalent enforcement).

#### Scenario: Uniqueness prevents duplicate scope rows

- **WHEN** a second insert is attempted with the same `group_id`, `org_id`, `project_id`, and `issue_id` as an existing row
- **THEN** the store SHALL reject the duplicate per the UNIQUE constraint (or equivalent) so a single current mapping per issue-in-scope is preserved

---

### Requirement: Row metadata timestamps

The mapping store SHALL persist **`created_at`** and **`updated_at`** for each row, representing when the row was **created** and **last updated** in the store (not the wall-clock time of an external system unless explicitly copied by a future sync). Both SHALL be stored as **UTC** timestamps encoded as **ISO 8601** strings with a `Z` suffix (example: `2026-04-07T14:30:00.000Z`).

#### Scenario: Timestamp format is ISO 8601 UTC

- **WHEN** a row is written or updated by the persistence layer
- **THEN** `created_at` and `updated_at` SHALL use the prescribed ISO 8601 UTC string form

---

### Requirement: Local SQLite mapping store for development and tests

For **local development** and **automated tests**, the product MAY use a **SQLite** database file as a **stand-in** for Azure Table Storage for the **same logical mapping schema** and uniqueness rules. SQLite is **not** a substitute for Azure Table Storage in **production** architecture; production continues to target Table Storage as described elsewhere in this capability.

Documentation SHALL state that the SQLite database path and file are **non-secret** local persistence only; **secrets** (tokens, PATs) MUST NOT be placed in this path or file and SHALL follow existing Key Vault / environment rules.

#### Scenario: Dev uses SQLite without Azure credentials for mapping persistence

- **WHEN** `mapping_store` is configured to **`sqlite`** and a valid SQLite path is resolved
- **THEN** the application or tests MAY persist and query mapping rows without Azure Table Storage credentials

---

### Requirement: Idempotent mapping schema initialization

The repository SHALL include a **committed** initialization entry point under **`scripts/`** that creates the SQLite database file (if needed) and applies schema using **idempotent** DDL: **`CREATE TABLE IF NOT EXISTS`** and, where indexes are defined, **`CREATE INDEX IF NOT EXISTS`**. Re-running initialization SHALL not fail solely because the schema already exists.

The init entry point and the runtime persistence layer SHALL resolve the **SQLite database filesystem path** using the **same rules** as configuration for `sqlite_path` (see **`application-config`** capability) so local setup matches what the application opens.

#### Scenario: Second init run succeeds

- **WHEN** the init script is executed twice against the same path
- **THEN** the second run SHALL complete successfully without error from existing objects

---

### Requirement: Mapping store abstraction

Application code (including CLI and tests) that reads or writes mapping rows SHALL depend on a **small mapping-store abstraction** (e.g. protocol or interface) rather than embedding SQLite calls throughout. **SQLite** SHALL be one implementation; **Azure Table Storage** SHALL be a future alternative implementation behind the same abstraction. This change does not require implementing the Azure Table adapter.

#### Scenario: SQLite implements the shared abstraction

- **WHEN** `mapping_store` is **`sqlite`**
- **THEN** mapping CRUD operations SHALL go through the abstraction backed by the SQLite implementation

---

### Requirement: Azure Table Storage backend must not silently fall back

When **`mapping_store`** is set to **`azure_table`**, the process SHALL **not** fall back to SQLite or another backend if the Azure Table adapter is **unimplemented** or **required credentials or configuration are missing**. The process SHALL **exit with a non-zero status** and print a **clear error** that names the **`mapping_store`** setting and what is missing or unavailable.

#### Scenario: Azure table selected without adapter

- **WHEN** `mapping_store` is **`azure_table`** and the Azure Table implementation or required credentials is not available
- **THEN** the process SHALL exit non-zero with an explicit message (no secret values) and SHALL NOT use SQLite
