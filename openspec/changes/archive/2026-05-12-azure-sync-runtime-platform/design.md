## Context

The repository already defines **`MappingStore`**, a SQLite implementation, and reserved **`mapping_store: azure_table`**, which currently fails fast with **`AzureTableMappingStoreUnavailableError`**. **`openspec/specs/azure-platform/spec.md`** describes production use of **Azure Container Apps**, **Key Vault**, **managed identity**, **Azure Files** for YAML, and **Azure Table Storage** for durable mappings (**P2-FR-7**, **P2-FR-8**). This change implements the missing Table adapter and documents ACA log discovery in **`README.md`**.

## Goals / Non-Goals

**Goals:**

- Provide a **production-capable** **`MappingStore`** implementation using **Azure Table Storage** with **Microsoft Entra ID** authentication (**`DefaultAzureCredential`**), suitable for a **system-assigned managed identity** on Container Apps.
- Preserve **logical schema parity** with SQLite (`MappingRow` fields, natural key **`(group_id, org_id, project_id, issue_id)`**, UTC **`created_at`** / **`updated_at`**).
- Define deterministic **PartitionKey** / **RowKey** encoding compatible with [Azure Table Storage key restrictions](https://learn.microsoft.com/en-us/rest/api/storageservices/understanding-the-table-service-data-model).
- Wire configuration via **documented environment variables** (non-secret): table **service endpoint** and **table name**.
- Document **where operators view stdout/stderr** for Container Apps (**Log stream** vs **Log Analytics**).

**Non-Goals:**

- Committed **IaC** (Bicep/Terraform) for ACA, storage, Key Vault, or Files mounts.
- **Hot-reload** of operator YAML from Azure Files.
- **Connection strings** or **storage account keys** for the Table adapter in production paths.
- Changing structured logging shape or adding new **`integration_audit`** event types.

## Decisions

### Dependencies: Azure SDK for Python

- **Decision:** Add **`azure-data-tables`** (Table client) and **`azure-identity`** (**`DefaultAzureCredential`**) via **uv**.
- **Rationale:** Official clients handle Entra token exchange and Table REST semantics; stdlib-only Table access is impractical.
- **Alternatives:** Raw REST with manual AAD tokens (high maintenance); Cosmos DB Table API (same SDK surface but different ops expectations—avoid unless explicitly required).

### Authentication

- **Decision:** **`TableServiceClient`** / **`TableClient`** constructed with **`credential=DefaultAzureCredential()`** and endpoint from env; **no** account key in env for this backend.
- **Rationale:** Matches **`azure-platform`** managed identity posture and ACA Key Vault integration for **`SNYK_TOKEN`** / **`AZURE_DEVOPS_PAT`**.
- **Alternatives:** Connection string (rejected for production path per Non-Goals).

### Configuration surface

- **Decision:** When **`mapping_store`** resolves to **`azure_table`**, require:
  - **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`** — HTTPS URL of the Table service (e.g. `https://<account>.table.core.windows.net`).
  - **`MAPPING_STORE_AZURE_TABLE_NAME`** — table name (letters and digits only per Azure table naming rules).
- **Rationale:** Keeps YAML free of Azure-specific endpoints; ACA can inject env from configuration or template; aligns with existing **`MAPPING_STORE`** / **`MAPPING_STORE_SQLITE_PATH`** pattern.
- **Alternatives:** YAML keys under **`mapping_store_azure_table`** — defer unless operators demand file-based routing.

### PartitionKey and RowKey

- **Decision:**
  - **`PartitionKey`** = literal **`group_id`** string.
  - **`RowKey`** = if **`org_id`**, **`project_id`**, and **`issue_id`** each contain **none** of the forbidden characters **`/`**, **`\\`**, **`#`**, **`?`**, then **`org_id + "|" + project_id + "|" + issue_id`**; otherwise **`base64url(segment)`** each component **without padding**, joined by **`_`**, using UTF-8 encoding before base64url (implementation helper; behavior fixed by spec).
- **Rationale:** Readable rows in Storage Explorer for typical Snyk/Azure DevOps IDs; safe fallback for unusual identifiers.
- **Alternatives:** Always base64url (simpler code, opaque keys); hash-based RowKey (collision policy complexity).

### Entity property mapping

- **Decision:** Persist **`MappingRow`** fields as Table entity string properties using **snake_case** property names matching SQLite columns / **`MappingRow`** attributes for parity (`group_id`, `org_id`, …). **`PartitionKey`** / **`RowKey`** duplicate **`group_id`** and encoded identity for addressing; optional **`group_id`** property remains for diagnostics (spec may allow omission if redundant—prefer **including** for simpler debugging and parity with export tooling).

Actually Table always has PartitionKey, RowKey - we can store group_id also as property for clarity.

### Table creation

- **Decision:** Application **`upsert`** path assumes table **exists**; document that operators create the table out-of-band **or** implementation MAY call **`create_table_if_not_exists`** once at factory startup (idempotent). Prefer **create_if_not_exists at startup** for smoother UX—document in tasks.

I'll put create_if_not_exists in design as recommended.

### Testing

- **Decision:** Unit-test **RowKey** encoding and mapping **serialization** with mocked **`TableClient`** (no emulator requirement for CI). Optional local Azurite noted as future enhancement.
- **Rationale:** Keeps CI dependency-free beyond mocks.

## Risks / Trade-offs

- **[Risk] New Azure SDK dependencies introduce vulnerabilities** → **Mitigation:** Run **Snyk Open Source** before merge; pin versions in **`pyproject.toml`** / lockfile.
- **[Risk] `DefaultAzureCredential` behavior differs locally vs ACA** → **Mitigation:** Document local dev: use **`az login`** or explicit env-based credentials for Azure developer workflows; production uses managed identity.
- **[Risk] Partition hot spots** → **Mitigation:** **`PartitionKey = group_id`** matches sync grouping; acceptable unless a single group grows to extreme entity counts—operational monitoring only.
- **[Risk] Concurrent upserts** → **Mitigation:** Natural key maps to single entity; Table **`upsert_merge`** semantics provide last-writer-wins consistent with SQLite concurrent-file caveats; sync is typically single-worker scheduled.

## Migration Plan

1. Provision storage account (Tables), create table, grant Container App managed identity **Table Data Contributor** (or equivalent RBAC).
2. Deploy image with new dependencies; set **`MAPPING_STORE=azure_table`**, endpoint and table name env vars; Key Vault refs for secrets unchanged.
3. Mount Azure Files with operator YAML; restart revision after config edits (existing rule).
4. **Rollback:** Revert revision to prior image and/or set **`MAPPING_STORE=sqlite`** only for non-production diagnostics (not recommended for ACA without persistent volume).

## Open Questions

- Whether to add optional **YAML** keys mirroring endpoint/table name—defer until operators request it.
