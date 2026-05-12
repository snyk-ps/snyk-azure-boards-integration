## Why

Production deployments need the **`mapping_store: azure_table`** path to actually persist issues-sync state on **Azure Table Storage**, with **managed identity** and **Key Vault**–backed secrets as already described in **`azure-platform`**. Today the factory raises if **`azure_table`** is selected, so operators cannot run **`sync`** on Azure Container Apps with durable mappings. Documenting where ACA stdout/stderr appears in the portal closes an operational gap without changing application logging code.

## What Changes

- Implement **`MappingStore`** backed by **Azure Table Storage** when **`mapping_store`** is **`azure_table`**, using the same logical row schema and natural-key semantics as SQLite (**P2-FR-7**, uniqueness equivalent).
- Resolve Table access via **Microsoft Entra ID** (**`DefaultAzureCredential`** / managed identity); **no** storage account keys in config or env for this path.
- Define normative **partition key** and **row key** encoding for table entities so natural keys map deterministically and respect Azure Table key character rules.
- Extend **application-config** with documented **environment variables** for table endpoint URL and table name (non-secret), participating in existing precedence where applicable.
- Extend **`README.md`** **Deployment** / logging guidance: **Log stream** vs **Log Analytics / Logs** (workspace), linking ACA console output to **`ContainerAppConsoleLogs_CL`** (or successor table names), consistent with the existing **Error Handling/Logging** section.

**Non-goals (this change)**

- **IaC** (Bicep, Terraform, ARM) as committed artifacts—operators may provision resources externally; the proposal documents intended Azure components only at the spec/design level.
- **Hot-reload** of operator YAML on Azure Files—restart or new revision remains the reload mechanism per **`azure-platform`**.
- **Custom OpenTelemetry** exporters or new structured log event types beyond existing **`integration_audit`** behavior.

## Capabilities

### New Capabilities

- _(none — behavior extends existing platform and config specs.)_

### Modified Capabilities

- **`azure-platform`**: Normative **Table Storage** entity identity (**PartitionKey** / **RowKey**), adapter behavior behind **`mapping_store: azure_table`**, and authentication expectations (**managed identity** / **`DefaultAzureCredential`**); clarify that the SQLite uniqueness rule has an **equivalent** enforcement strategy for Table (upsert by deterministic keys, no duplicate entities per natural key).
- **`application-config`**: New **environment variables** for Azure Table endpoint and table name when using **`azure_table`**; **README** documentation requirements for **Azure Container Apps** log viewing in the portal.

## Impact

- **`src/mapping_store/`** — new Table implementation; **`factory`** constructs it when **`azure_table`** is selected and required configuration is present.
- **Dependencies** — Azure SDK packages (**Table** client and **identity**) via **uv**; must pass **Snyk Open Source** / **Snyk Code** policy before merge.
- **Tests** — unit tests for key encoding, entity serialization, and store behavior (mocked Table client or emulator-compatible tests per **`design.md`**).
- **Documentation** — **`README.md`** deployment/logging subsection.
- **Azure operators** — Container Apps revision with managed identity, Key Vault references, Files mount for YAML, Table RBAC, storage account table creation.
