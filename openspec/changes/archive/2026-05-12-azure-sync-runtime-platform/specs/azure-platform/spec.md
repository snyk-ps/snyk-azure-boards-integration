## MODIFIED Requirements

### Requirement: Mapping store abstraction

Application code (including CLI and tests) that reads or writes mapping rows SHALL depend on a **small mapping-store abstraction** (e.g. protocol or interface) rather than embedding SQLite calls throughout. **SQLite** SHALL be one implementation; **Azure Table Storage** SHALL be another implementation behind the same abstraction when **`mapping_store`** is **`azure_table`** and required Table configuration and credentials are available per **`application-config`** and this capability.

#### Scenario: SQLite implements the shared abstraction

- **WHEN** `mapping_store` is **`sqlite`**
- **THEN** mapping CRUD operations SHALL go through the abstraction backed by the SQLite implementation

#### Scenario: Azure Table implements the shared abstraction

- **WHEN** `mapping_store` is **`azure_table`** and Table configuration and authentication succeed at startup
- **THEN** mapping CRUD operations SHALL go through the abstraction backed by the Azure Table Storage implementation

---

### Requirement: Azure Table Storage backend must not silently fall back

When **`mapping_store`** is set to **`azure_table`**, the process SHALL **not** fall back to SQLite or another backend if **required Azure Table configuration is missing**, **authentication to Azure Table Storage fails**, or the Table-backed adapter cannot complete initialization. The process SHALL **exit with a non-zero status** and print a **clear error** that names the **`mapping_store`** setting and what is missing or unavailable (without emitting secret values).

#### Scenario: Azure table selected with incomplete configuration

- **WHEN** `mapping_store` is **`azure_table`** and any required Table configuration value defined in **`application-config`** is missing or invalid after precedence resolution
- **THEN** the process SHALL exit non-zero with an explicit message and SHALL NOT use SQLite

#### Scenario: Azure table selected without usable credentials

- **WHEN** `mapping_store` is **`azure_table`** and the Table client cannot authenticate using **`DefaultAzureCredential`** (or equivalent documented credential chain) during adapter initialization
- **THEN** the process SHALL exit non-zero with an explicit message and SHALL NOT use SQLite

---

## ADDED Requirements

### Requirement: Azure Table Storage partition and row keys for mapping entities

For **`mapping_store: azure_table`**, each persisted mapping SHALL be stored as one **Azure Table** entity with:

- **`PartitionKey`** SHALL equal the **`group_id`** string for that row’s natural key.
- **`RowKey`** SHALL be derived deterministically from **`org_id`**, **`project_id`**, and **`issue_id`** such that the triple **`(org_id, project_id, issue_id)`** maps to exactly one **`RowKey`** string within the partition. **`PartitionKey`** and **`RowKey`** SHALL NOT contain the characters **`/`**, **`\\`**, **`#`**, or **`?`**.

When **`org_id`**, **`project_id`**, and **`issue_id`** each contain **none** of **`/`**, **`\\`**, **`#`**, **`?`**, **`RowKey`** SHALL be the concatenation **`org_id + "|" + project_id + "|" + issue_id`**.

When **any** of **`org_id`**, **`project_id`**, or **`issue_id`** contains at least one of **`/`**, **`\\`**, **`#`**, **`?`**, **`RowKey`** SHALL be built by encoding **each** component as **base64url without padding** over its **UTF-8** octets and joining the three encoded strings with a single **`_`** separator (implementation-fixed convention).

#### Scenario: Typical Snyk identifiers use delimiter RowKey

- **WHEN** a mapping row is written with **`org_id`**, **`project_id`**, and **`issue_id`** that omit **`/`**, **`\\`**, **`#`**, and **`?`**
- **THEN** the stored entity **`RowKey`** SHALL equal **`org_id + "|" + project_id + "|" + issue_id`**

#### Scenario: Forbidden characters trigger base64url RowKey

- **WHEN** at least one of **`org_id`**, **`project_id`**, or **`issue_id`** contains **`/`**, **`\\`**, **`#`**, or **`?`**
- **THEN** the stored entity **`RowKey`** SHALL use the base64url-without-padding encoding convention for all three components joined by **`_`**

---

### Requirement: Azure Table Storage mapping entity properties and uniqueness

For **`mapping_store: azure_table`**, Table entities SHALL persist at minimum the same logical attributes as **`openspec/specs/azure-platform/spec.md`** defines for issues sync persistence (**`MappingRow`** parity), using **snake_case** property names and **string** values for all mapped fields, including **`created_at`** and **`updated_at`** as **UTC ISO 8601** strings with a **`Z`** suffix.

Uniqueness of the natural key **`(group_id, org_id, project_id, issue_id)`** SHALL be enforced by **deterministic addressing**: **`get`**, **upsert**, and **delete** by natural key SHALL target exactly one entity identified by **`PartitionKey`** ( **`group_id`** ) and **`RowKey`** derived per **Azure Table Storage partition and row keys for mapping entities**. The adapter SHALL use **upsert** semantics so retries do not create duplicate entities for the same natural key.

#### Scenario: Upsert by natural key updates a single entity

- **WHEN** **`upsert`** is invoked twice with the same **`group_id`**, **`org_id`**, **`project_id`**, and **`issue_id`** but different mutable field values
- **THEN** exactly **one** Table entity SHALL hold the latest values at the same **`PartitionKey`** and **`RowKey`**

---

### Requirement: Azure Table Storage authentication for the mapping store

For **`mapping_store: azure_table`**, the Table client SHALL authenticate to the storage account using **`DefaultAzureCredential`** (Azure Identity SDK) or a credential chain **documented in `design.md`** that includes managed identity for Azure hosts. The implementation SHALL **not** require a **storage account key** or **connection string secret** for this adapter in production configurations described by **`azure-platform`**.

#### Scenario: No storage account key in configuration layer

- **WHEN** operators configure **`mapping_store`** as **`azure_table`** per **`application-config`**
- **THEN** required configuration SHALL consist only of **non-secret** endpoint and table identity variables plus Entra-based credential acquisition — **not** account keys in YAML or environment variables for this adapter
