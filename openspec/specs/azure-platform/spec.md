# Azure platform — runtime, state, secrets, operator config

Recommended Azure services and runtime behavior for the Snyk–Azure Boards integration. Cross-reference **P2-FR-*** in `../sync-lifecycle/spec.md` where cited.

## Major components

| Component | Recommended Azure service | Purpose |
|-----------|---------------------------|---------|
| Synchronization middleware | Azure Container Apps (ACA) | Runs the containerized application that implements Snyk–Azure Boards synchronization logic. |
| State & mapping | Azure Table Storage | Persists the relationship between Snyk finding identifiers and Azure Boards work item IDs to support stable mapping and reopen handling. |
| Secrets | Azure Key Vault | Stores sensitive credentials (`SNYK_TOKEN`, Azure DevOps PAT); ACA references these as environment variables without embedding values in code or config artifacts. |
| Cloud identity | System-assigned managed identity | Authenticates the app to Azure APIs (Key Vault, Table Storage, and other Azure resources that support Microsoft Entra ID) without client secrets in the workload. |
| Logging & observability | ACA OpenTelemetry agent + Application Insights / Log Analytics | Ships logs and telemetry for operations, transaction visibility, and sync latency measurement (supports P2-FR-6, P2-FR-6.2, P2-FR-6.3). |
| Alerting | Azure Monitor (metric alerts, log search alerts) + Action Groups | Notifies operators when health, authentication, or latency thresholds are breached (supports P2-FR-6). |
| Operator configuration | **Azure-only:** YAML on an **Azure Files** share (mounted into the container) and/or **Azure Blob Storage** (downloaded at startup); managed identity grants access | End-user tunables live **only in Azure** (no Git or repo as the required source of truth): severity filters, work item type and template defaults, tags, and related options without rebuilding the container image. |

## Synchronization middleware (Azure Container Apps)

The integration runs as a container on **Azure Container Apps**. It runs on a **scheduled sync** model (for example ACA **cron** or an equivalent periodic job): each run calls the **Snyk Issues API** to list current issues for configured orgs/projects, reconciles them with **Azure Table Storage** mappings, then calls **Azure DevOps** Work Item Tracking APIs to create, update, or close work items per the functional requirements.

## Durable state & mapping (Azure Table Storage)

**Azure Table Storage** holds application state needed for a **stable, unique mapping** between Snyk issues and work items (**P2-FR-7**). The same store supports **re-opened findings** (**P2-FR-8**): when a previously fixed or closed finding becomes open again, the stored history allows the solution to open a **new** work item while retaining traceability to past mappings as required by policy.

**Minimum attributes persisted per mapping row** (exact partition/row key design is implementation detail; together these fields identify the Snyk issue and its Azure Boards counterpart):

| Source | Field | Role |
|--------|-------|------|
| Snyk | **Group ID** | Locates the issue in Snyk’s hierarchy (with org and project). |
| Snyk | **Org ID** | Organization that owns the project and issue. |
| Snyk | **Project ID** | Snyk project containing the issue. |
| Snyk | **Issue ID** | Stable identifier for the Snyk issue (primary logical key with org + project). |
| Snyk | **Snyk status** | **Derived** lifecycle label for sync (**open**, **resolved**, **ignored**) from Issues API **`attributes.status`** and **`attributes.ignored`** per **`sync-lifecycle`** (not authoritative from `coordinates[].state`). |
| Azure DevOps | **Organization** | Azure DevOps organization name (or id) for REST calls. |
| Azure DevOps | **Project** | Team project containing the work item. |
| Azure DevOps | **Work item ID** | Boards work item linked to this Snyk issue. |
| Azure DevOps | **Work item status** | Boards work item state persisted on the mapping row (distinct from Snyk status). |
| Snyk | **Project display name** | Human-readable project label from Snyk Projects API (**`attributes.name`**), when populated. |
| Snyk | **Excluded (origin policy)** | When **`true`**, **`sync`** does not mutate Boards for origin policy; persists with **`exclusion_reason`**. |
| Snyk | **Exclusion reason** | Machine-readable label (**`origin_unknown`**, **`origin_not_in_allowlist`**) when **`excluded`**. |

Additional columns (for example **`created_at`** / **`updated_at`** row metadata in UTC ISO 8601, last sync time, prior work item ids for **P2-FR-8** audit, or issue severity snapshot) may be added by the implementation but are not required beyond the normative mapping requirements below.

## Secrets (Azure Key Vault)

**Azure Key Vault** stores **`SNYK_TOKEN`** and the **Azure DevOps personal access token (PAT)**. **Azure Container Apps** can integrate with Key Vault so secrets are **referenced directly** and exposed to the container as **environment variables**, avoiding plaintext secrets in source control or container images.

## Identity (managed identity & DefaultAzureCredential)

A **system-assigned managed identity** on the Container App satisfies the need to monitor and rely on **authentication health** for Azure-backed dependencies (**P2-FR-6.1**). Application code (e.g. Python) uses **`DefaultAzureCredential`** from the **Azure Identity SDK**, which detects the ACA runtime and acquires tokens for **Key Vault**, **Table Storage**, **Azure Files** / **Blob** (for operator YAML), and other Entra-protected Azure endpoints **without embedding client secrets** in code or shell scripts.

## Runtime configuration (external YAML, Azure-only)

Behavior that must be adjustable **without code changes** is defined in a **YAML file stored in Azure** (reference format: YAML). It is **not** baked into the container image, and **source control is not required**: operators maintain the file **directly in Azure** (for example Azure portal, Storage Explorer, Azure CLI, or scripts using the Storage APIs).

**Preferred delivery to the app:**

- **Azure Files** — mount a file share so the container reads a path such as `/config/app.yaml`.
- **Azure Blob Storage** — alternative: store the YAML in a private container and **download at startup** using the managed identity.

Either pattern uses **DefaultAzureCredential** (or equivalent) for access; permissions are granted via **RBAC on the storage account** to the Container App’s managed identity.

**Typical settings** include (non-exhaustive):

- **Create enablement** — a **global on/off** for creating **new** work items (**P2-FR-11**).
- **Finding filters** — e.g. which **severities** create work items (aligned with **P2-FR-1**), and optional scopes (projects, targets, types).
- **Severity downgrade** — optional **close_on_severity_downgrade**: when enabled, **close** the mapped work item if Snyk severity falls **below** the configured threshold while the issue is still open; when severity returns to policy, the **same** work item is **reopened** (distinct from P2-FR-8 new work item on Snyk fix/reopen).
- **Work item defaults** — work item **type**, **template** or field layout, and default **state** such as Unassigned (**P2-FR-2**).
- **Tags and labels** — default **tags** on created or updated items (**P2-FR-10**).
- **Azure DevOps routing** — organization, project, and team / area path as needed for work item creation.

**Secrets** (tokens, PATs) stay in **Key Vault**; the YAML holds only **non-secret** policy and routing.

**Applying changes:** After the file is updated in **Azure Files** or **Blob**, operators **restart** the Container App or roll a **new revision** so the process **loads configuration at startup**. Hot-reload is out of scope unless added later. For safer rollback without Git, enable **Azure Files share snapshots** and/or **Blob versioning** as an operational practice.

## Requirements (mapping persistence)

### Requirement: Mapping row schema and logical identity

The durable **issues sync persistence** store (historically described as **Snyk↔work-item mapping**; physical SQLite table **`issue_work_item_map`** when using SQLite) SHALL persist at minimum the following attributes per row, using **snake_case** **column** names and **TEXT** storage for all listed fields. Together they support **stable mapping** (**P2-FR-7**), traceability for **re-open** behavior (**P2-FR-8**), and **origin-based exclusion** reporting.

| Field | Role |
|-------|------|
| `group_id` | Snyk group identifier (with org and project) for the issue. |
| `org_id` | Snyk organization that owns the project and issue. |
| `project_id` | Snyk project containing the issue. |
| `issue_id` | Stable Snyk issue identifier. |
| `snyk_status` | **Derived** Snyk lifecycle label for sync policy and audit: exactly one of **`open`**, **`resolved`**, or **`ignored`**, computed from Issues API **`attributes.status`** and **`attributes.ignored`** per **`sync-lifecycle`** (not from `coordinates[].state`, and not a literal undocumented `closed` API status for storage). |
| `organization` | Azure DevOps organization name or id for REST calls. |
| `project` | Azure DevOps team project containing the work item. |
| `work_item_id` | Azure Boards work item id linked to this Snyk issue. |
| `work_item_status` | Azure Boards work item state as persisted for this mapping row. |
| `snyk_project_name` | Display name from Snyk **`GET /orgs/{org_id}/projects/{project_id}`** **`attributes.name`** when known (may be empty until populated). |
| `snyk_project_origin` | Origin label from the same project **`attributes.origin`** when known (may be empty until populated). |
| `excluded` | When **`true`**, the issue is **not** eligible for Azure Boards mutations per **`sync-lifecycle`** origin policy; when **`false`**, origin policy (if any) permits processing. |
| `exclusion_reason` | When **`excluded`** is **`true`**, a non-empty stable machine-readable reason label defined by **`sync-lifecycle`**; otherwise empty. |

The logical identity of one **current** row for a Snyk issue in a given scope SHALL be **`(group_id, org_id, project_id, issue_id)`**. The implementation SHALL enforce **at most one row** per that tuple via a **UNIQUE** constraint on those four columns (or equivalent enforcement).

#### Scenario: Uniqueness prevents duplicate scope rows

- **WHEN** a second insert is attempted with the same `group_id`, `org_id`, `project_id`, and `issue_id` as an existing row
- **THEN** the store SHALL reject the duplicate per the UNIQUE constraint (or equivalent) so a single current row per issue-in-scope is preserved

#### Scenario: snyk_status uses derived vocabulary

- **WHEN** a sync run persists `snyk_status` after evaluating Snyk Issues attributes
- **THEN** the stored value SHALL be one of `open`, `resolved`, or `ignored` as defined by **`sync-lifecycle`**, never a legacy `closed` label for Snyk API `status`

#### Scenario: Excluded rows carry reason when excluded

- **WHEN** **`sync`** persists **`excluded`** as **`true`**
- **THEN** **`exclusion_reason`** SHALL be non-empty and SHALL match a label defined in **`sync-lifecycle`**

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
