# Snyk issues client (Python)

## Purpose

Define normative behavior for the Python client that calls the Snyk REST Issues API (authentication, group and org list/get, pagination via `links.next`, query filters, normalized issue records, rate limiting on 429, errors, and optional CLI smoke). REST paths and media types are defined in `openspec/specs/integration-apis/spec.md`.

## Requirements

### Requirement: Python package layout for Snyk API code

All modules that perform HTTP calls to the Snyk REST Issues API for this capability SHALL live under the **`src/snyk/`** package (submodules as needed). **Argparse definitions, subcommand registration, and wiring from parsed arguments to the client SHALL live under `src/commands/`** (submodules as needed). The process entry module **`src/main.py`** SHALL remain the executable entry point and SHALL delegate CLI construction and dispatch to `src/commands/` without embedding subcommand logic. Application and tests SHALL import the client from `src/snyk/` and command wiring from `src/commands/` as appropriate.

#### Scenario: Imports from application code

- **WHEN** application or test code uses the Snyk issues client
- **THEN** HTTP and Snyk API logic is imported from the `snyk` package rooted at `src/snyk/`

#### Scenario: CLI wiring lives under commands

- **WHEN** code registers or runs argparse subcommands for this application
- **THEN** that logic resides under `src/commands/` and not under `src/snyk/`

---

### Requirement: Authenticated access to Snyk Issues REST API

The Snyk issues client SHALL obtain the Snyk API token from the environment variable `SNYK_TOKEN` and SHALL send it on every request using the authentication scheme required by the Snyk REST API for Issues (see `openspec/specs/integration-apis/spec.md` and Snyk OpenAPI). The client SHALL NOT read tokens from files, CLI arguments, or source code. The client SHALL NOT log the token, full `Authorization` headers, or other credentials.

#### Scenario: Missing token

- **WHEN** code that performs a Snyk Issues request runs and `SNYK_TOKEN` is unset or empty
- **THEN** the client SHALL fail without issuing the HTTP request, with a clear error that does not echo secret material

#### Scenario: Successful authorized request

- **WHEN** `SNYK_TOKEN` is set to a valid service token and the client issues a supported Issues request
- **THEN** the request SHALL include authentication acceptable to `https://api.snyk.io/rest` for that operation

**Related:** Underpins future sync behavior that depends on Snyk issue data (e.g. lifecycle and mapping in `sync-lifecycle`); does not by itself satisfy P2-FR-* items that concern Azure Boards.

---

### Requirement: Issue list and get operations

The client SHALL support HTTP `GET` for **listing issues and for retrieving a single issue** in **group** scope **and** in **org** scope, using **`GET /groups/{group_id}/issues`**, **`GET /groups/{group_id}/issues/{issue_id}`**, **`GET /orgs/{org_id}/issues`**, and **`GET /orgs/{org_id}/issues/{issue_id}`** as documented in `openspec/specs/integration-apis/spec.md`. The client SHALL send the **`version`** query parameter set to **`2025-11-05`** on every Issues request unless overridden in tests. The default base URL SHALL be `https://api.snyk.io/rest`; the client SHALL allow a different base URL to be supplied for testing.

For **list** (group or org), the client SHALL request **`limit=100`** on the **first** page URL (maximum page size). The client SHALL support optional list filters aligned with the Snyk REST API for that operation: **`effective_severity_level`** (zero or more values; when none are supplied the client SHALL default to **`high`** and **`critical`**), **`type`** (optional), and **`status`** (optional). Parameters SHALL be expressible from CLI and programmatic APIs so future external configuration can supply the same values without changing HTTP shape.

The client SHALL expose **normalized issue records** for each issue suitable for downstream sync, including at minimum: **`org_id`** (from `data[].relationships.organization.data.id`), **`project_id`** (from `data[].relationships.scan_item.data.id`), **`issue_id`** (from `data[].attributes.key`), **`created_at`** (from `data[].attributes.created_at`), **`severity`** (from `data[].attributes.effective_severity_level`), **`status`** (from `data[].attributes.status`), and **`ignored`** (from `data[].attributes.ignored`, coerced to boolean when the API uses a boolean-like representation). Additional fields MAY be added later; the client design SHALL not block extending the normalized record.

Downstream synchronization SHALL treat **`coordinates[].state`** as **non-authoritative** for open/close lifecycle; normalized records exist to carry **attributes**-based lifecycle fields above.

#### Scenario: List issues for a group

- **WHEN** the caller requests listing issues for a valid `group_id`
- **THEN** the client SHALL call `GET /groups/{group_id}/issues` with `version=2025-11-05`, `limit=100`, default effective severity `high` and `critical` when the caller did not specify severities, optional `type` and `status` when provided, and SHALL yield or return normalized records per this capability

#### Scenario: List issues for an org

- **WHEN** the caller requests listing issues for a valid `org_id` (org scope)
- **THEN** the client SHALL call `GET /orgs/{org_id}/issues` with `version=2025-11-05`, `limit=100` on the first page, default effective severity `high` and `critical` when the caller did not specify severities, optional `type` and `status` when provided, and SHALL yield or return normalized records per this capability

#### Scenario: Get one issue in group scope

- **WHEN** the caller requests a single issue by `group_id` and `issue_id`
- **THEN** the client SHALL call `GET /groups/{group_id}/issues/{issue_id}` with `version=2025-11-05` and SHALL return a normalized issue record including the required fields where present in the response

#### Scenario: Get one issue in org scope

- **WHEN** the caller requests a single issue by `org_id` and `issue_id` (org scope)
- **THEN** the client SHALL call `GET /orgs/{org_id}/issues/{issue_id}` with `version=2025-11-05` and SHALL return a normalized issue record including the required fields where present in the response

#### Scenario: Normalized record includes status and ignored

- **WHEN** the API returns `data[].attributes.status` and `data[].attributes.ignored` for an issue
- **THEN** the normalized record SHALL include `status` and `ignored` with those values (with `ignored` represented as a boolean suitable for downstream comparisons)

---

### Requirement: Pagination for list operations

For list operations in **group or org** scope, the client SHALL follow **`links.next`** in each JSON:API response until `links.next` is absent or null, so that callers can retrieve the full issue set without silently truncating at the first page. The **first** request URL for a **group or org** list SHALL include **`limit=100`**. Subsequent pages SHALL use the URL from **`links.next`** without stripping parameters added by the API.

The value of **`links.next`** MAY include a leading `rest/` segment relative to the API host while the configured base URL already ends with `/rest`. The client SHALL resolve the HTTP URL for the next request without producing an invalid path such as **`rest/rest/...`** (e.g. use `urllib.parse.urljoin` with a stable origin, accept absolute URLs when provided, or normalize duplicate `rest/` segments when combining with the base).

#### Scenario: Multiple pages

- **WHEN** the Snyk API returns a first page and a non-empty `links.next`
- **THEN** the client SHALL issue a GET to the correctly resolved next URL, repeat until `links.next` is absent, and expose results according to its public API (e.g. iteration or aggregated list as specified in tasks)

#### Scenario: Single page

- **WHEN** the Snyk API returns one page with no next link
- **THEN** the client SHALL complete without error after processing that page

#### Scenario: Next link path avoids duplicate rest segment

- **WHEN** `links.next` contains a path that starts with `rest/` and the client base URL is `https://api.snyk.io/rest` (or test equivalent)
- **THEN** the resolved request URL SHALL NOT contain a duplicated `rest/rest/` path segment

---

### Requirement: HTTP errors and safe diagnostics

On non-success HTTP status codes, the client SHALL raise or return errors that include the HTTP status and allow callers to handle auth failures, client errors, rate limiting, and server errors distinctly where practical. The client SHALL NOT write full response bodies to logs by default; diagnostic messages SHALL omit secrets.

On **`429 Too Many Requests`**, the client SHALL treat the response as **rate limiting** (Snyk documents a per-key limit of **1620 requests per minute** and 429 until the rate-limiting interval resets). The client SHALL **retry** the same logical GET with bounded backoff (e.g. honoring **`Retry-After`** when present, otherwise waiting until it is reasonable to retry within the one-minute window) without logging full response bodies or credentials.

#### Scenario: Unauthorized

- **WHEN** the API responds with `401` or `403`
- **THEN** the error surfaced to the caller SHALL indicate authorization failure without including the token

#### Scenario: Rate limited

- **WHEN** the API responds with `429`
- **THEN** the client SHALL retry according to the rate-limiting behavior above and surface a failure only if retries are exhausted or the condition persists beyond bounded limits

#### Scenario: Server error

- **WHEN** the API responds with `5xx`
- **THEN** the client SHALL surface a retriable or server-error class of failure suitable for retry policies in higher layers

---

### Requirement: Optional CLI for fetch smoke test

The application CLI SHALL expose an argparse-based command or option group **under `src/commands/`** that invokes the Snyk issues client for **group scope and/or org scope** (list or get) using `SNYK_TOKEN` from the environment, for operator or developer smoke verification. The CLI SHALL not accept the token as a command-line argument. The fetch command SHALL accept arguments needed to exercise **normalized output** and **list filters** (including effective severity, type, and status where exposed), consistent with the client’s public parameters.

#### Scenario: CLI without token

- **WHEN** the user runs the fetch smoke command without setting `SNYK_TOKEN`
- **THEN** the process SHALL exit non-zero with a concise message and no network call

#### Scenario: CLI can exercise org-scoped list when implemented

- **WHEN** the user runs the fetch command with parameters that select org-scoped issue listing per documented help
- **THEN** the process SHALL invoke the org-scoped list operation with a valid `org_id` as required by that mode
