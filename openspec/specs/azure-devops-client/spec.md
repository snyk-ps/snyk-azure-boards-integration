# Azure DevOps client (Python)

## Purpose

Define normative behavior for the Python client that calls **Azure DevOps Work Item Tracking (WIT)** REST APIs for work item create, read, list-by-ids, update, and comments. REST paths, default `api-version` values for WIT vs comments, and media types are defined in `openspec/specs/integration-apis/spec.md`. Sync lifecycle rules (P2-FR-*) remain in `openspec/specs/sync-lifecycle/spec.md`; this capability covers **how** the application talks to Azure DevOps, not full reconciliation.

## Requirements

### Requirement: Python package layout for Azure DevOps API code

All modules that perform HTTP calls to Azure DevOps WIT for this capability SHALL live under the **`src/integrations/azure_devops/`** package (submodules as needed). **Argparse definitions, subcommand registration, and wiring from parsed arguments to the client SHALL live under `src/commands/`** (submodules as needed). The process entry module **`src/main.py`** SHALL remain the executable entry point and SHALL delegate CLI construction and dispatch to `src/commands/` without embedding subcommand logic. Application and tests SHALL import the client from `integrations.azure_devops` (package root under `src/integrations/azure_devops/`) and command wiring from `src/commands/` as appropriate.

The Azure DevOps client SHALL NOT read operator YAML files, PATs from disk, or PATs from CLI arguments. It SHALL accept **`organization`** and **`project`** as explicit call parameters (or as fields on a small caller-supplied value object) and SHALL NOT infer them from environment variables dedicated to secrets.

#### Scenario: Imports from application code

- **WHEN** application or test code uses the Azure DevOps client
- **THEN** HTTP and Azure DevOps API logic is imported from the `integrations.azure_devops` package rooted at `src/integrations/azure_devops/`

#### Scenario: CLI wiring lives under commands

- **WHEN** code registers or runs argparse subcommands for this application
- **THEN** that logic resides under `src/commands/` and not under `src/integrations/azure_devops/`

---

### Requirement: Authenticated access with PAT from environment

The client SHALL read the Azure DevOps personal access token **only** from the environment variable **`AZURE_DEVOPS_PAT`** and SHALL send it using the authentication scheme required for Azure DevOps REST (HTTP Basic with an empty username and the PAT as password, or equivalent documented scheme). The client SHALL NOT accept a PAT via CLI flags, YAML, or other files. The client SHALL NOT log the PAT, full `Authorization` headers, or other credentials.

If **`AZURE_DEVOPS_PAT`** is unset or empty, the client SHALL fail with a clear error **before** issuing any HTTP request.

#### Scenario: Missing PAT

- **WHEN** code that performs an Azure DevOps request runs and `AZURE_DEVOPS_PAT` is unset or empty
- **THEN** the client SHALL fail without issuing the HTTP request and the error SHALL NOT echo secret material

#### Scenario: Authorized request shape

- **WHEN** `AZURE_DEVOPS_PAT` is set and the client issues a supported WIT request
- **THEN** the request SHALL include authentication acceptable to the configured Azure DevOps host for that operation

**Related:** Runtime injection of the PAT (for example from Key Vault via ACA) is described in `openspec/specs/azure-platform/spec.md`; this capability assumes the process environment is already populated.

---

### Requirement: Base URL, routing parameters, and API versions

The client SHALL use **`https://dev.azure.com`** as the default API origin, matching `openspec/specs/integration-apis/spec.md`. The client SHALL allow a different base URL to be supplied for testing while preserving the same path templates relative to that origin.

For **create, get, list-by-ids, and update**, the client SHALL send **`api-version=7.1`** by default on requests, consistent with `integration-apis`. For **add work item comment**, the client SHALL send the **preview** `api-version` documented in `integration-apis` for that operation (**`7.0-preview.3`** until that spec changes). These defaults SHALL be centralized as named constants in the implementation. The client MAY accept optional constructor parameters to override the WIT and comment `api-version` **for automated tests only**; production configuration SHALL NOT define environment-based overrides for those versions.

The client SHALL use caller-supplied **`organization`** and **`project`** path segments in URLs and SHALL NOT read organization or project from `AZURE_DEVOPS_PAT` or from configuration files inside this package.

#### Scenario: Default host and WIT version

- **WHEN** the caller uses default client settings and issues create, get, list-by-ids, or update
- **THEN** requests SHALL target `https://dev.azure.com` path templates from `integration-apis` and include `api-version=7.1` unless a test-only override is in effect

#### Scenario: Comment preview version

- **WHEN** the caller adds a work item comment with default client settings
- **THEN** the request SHALL use the preview `api-version` documented in `integration-apis` for comments (`7.0-preview.3` until superseded there)

#### Scenario: Test base URL override

- **WHEN** the caller constructs the client with a non-default base URL for tests
- **THEN** issued URLs SHALL use that origin with the same relative path templates as `integration-apis`

---

### Requirement: Supported WIT operations (v1)

The client SHALL support the following operations aligned with `openspec/specs/integration-apis/spec.md`:

- **Create work item:** `POST …/wit/workitems/${type}` with **`application/json-patch+json`** body (JSON Patch operations).
- **Get work item:** `GET …/wit/workitems/{id}`.
- **List work items by ids:** `GET …/wit/workitems?ids=…` with **at most 200** ids per request; if the caller supplies more than 200 ids in a single list call, the client SHALL fail before HTTP with a clear error.
- **Update work item:** `PATCH …/wit/workitems/{id}` with **`application/json-patch+json`** body.
- **Add work item comment:** `POST …/wit/workItems/{workItemId}/comments` using the preview `api-version` from `integration-apis`, with a request body including comment text as required by that API.

The client SHALL NOT implement **`workitemsbatch`**, **WIQL query**, or **Core get project** in v1.

#### Scenario: Create sends JSON Patch

- **WHEN** the caller creates a work item with a work item type and a list of JSON Patch operations
- **THEN** the client SHALL issue `POST` with media type `application/json-patch+json` per `integration-apis`

#### Scenario: List ids cap

- **WHEN** the caller requests list-by-ids with more than 200 ids in one invocation
- **THEN** the client SHALL reject the call before sending HTTP

---

### Requirement: Normalized work item and comment records

For **create, get, list-by-ids, and update**, the client SHALL return a **normalized work item record** that includes at minimum:

- **`work_item_id`**: integer or string consistent with the API work item `id` field
- **`work_item_status`**: value from `fields['System.State']`, or **`None`** if absent
- **`rev`**: revision from the API response when present
- **`fields`**: the full fields mapping from the API response for downstream P2-FR-5.x / tagging

For **list-by-ids**, the client SHALL return a **list** of normalized work item records.

For **add work item comment**, the client SHALL return a **normalized comment record** including at least **`id`** and **`work_item_id`**.

The design SHALL allow **additional keys** on these records in later versions without breaking callers, provided the minimum keys remain stable.

#### Scenario: Get maps state

- **WHEN** the API returns a work item with `fields.System.State` set
- **THEN** the normalized record’s `work_item_status` SHALL equal that value and `work_item_id` SHALL reflect the work item id

#### Scenario: Missing state

- **WHEN** the API returns a work item without `System.State`
- **THEN** `work_item_status` SHALL be `None` and other required keys SHALL still be populated per this requirement

---

### Requirement: HTTP errors, logging, and retries

On non-success HTTP status codes, the client SHALL surface errors that include the **HTTP status** and SHALL allow callers to distinguish **authentication failures (`401`/`403`)**, **other client errors (4xx)**, **rate limiting (`429`)**, and **server errors (`5xx`)** where practical. Diagnostic messages and logs SHALL **omit secrets** and SHALL **not** log full response bodies by default.

On **`429`**, for **all** supported HTTP methods, the client SHALL retry the same logical operation with **bounded** attempts, honoring the **`Retry-After`** header when present and otherwise using **capped exponential backoff**.

For **`GET`** operations (**get**, **list-by-ids**), the client MAY apply **limited** retries for **`5xx`** responses or connection-level failures.

For **`POST`** and **`PATCH`** operations (**create**, **update**, **add comment**), the client SHALL retry **`429`** as above and SHALL **not** implement open-ended **`5xx`** retries; failures SHALL be surfaced so higher layers may treat them as retriable without assuming idempotent side effects.

The client does **not** guarantee idempotency for mutating **`POST`**/**`PATCH`** side effects.

#### Scenario: Unauthorized

- **WHEN** the API responds with `401` or `403`
- **THEN** the error surfaced to the caller SHALL indicate authorization failure without including the PAT

#### Scenario: Rate limited with Retry-After

- **WHEN** the API responds with `429` and a `Retry-After` value
- **THEN** the client SHALL wait per that header (within bounded retry limits) before retrying and SHALL not log full response bodies

#### Scenario: Mutating 5xx not endlessly retried

- **WHEN** a create, update, or comment request receives `5xx` from the server
- **THEN** the client SHALL not apply open-ended automatic retries for that response class

---

### Requirement: Optional CLI smoke for Azure DevOps connectivity

The application CLI SHALL expose an argparse-based subcommand **under `src/commands/`** that:

- Accepts **`--config`** (and any other documented config path flags consistent with `application-config`)
- Loads merged configuration sufficient to read **`azure_boards.organization`** and **`azure_boards.project`**
- Reads **`AZURE_DEVOPS_PAT`** from the environment only
- Requires **`--work-item-id`** and performs **exactly one read-only** call: **`get_work_item`** for that id

The smoke command SHALL NOT accept a PAT as a CLI flag. By default it SHALL NOT perform create, update, or add-comment operations.

#### Scenario: Smoke without PAT

- **WHEN** the user runs the smoke subcommand without `AZURE_DEVOPS_PAT`
- **THEN** the process SHALL exit non-zero with a concise message and no network call

#### Scenario: Smoke uses config routing

- **WHEN** the user runs the smoke subcommand with valid config containing `azure_boards.organization` and `azure_boards.project`
- **THEN** the client SHALL be invoked with those routing values and a single `get_work_item` request

**Related:** Audit comments on lifecycle transitions (**P2-FR-9**) will use the programmatic add-comment API in future sync work; this requirement only defines smoke and client capability.
