## ADDED Requirements

### Requirement: Python package layout for Snyk API code

All modules that perform HTTP calls to the Snyk REST Issues API for this capability SHALL live under the **`src/snyk/`** package (submodules as needed). The CLI entrypoint MAY remain in `src/main.py` or equivalent and SHALL import from `src/snyk/`.

#### Scenario: Imports from application code

- **WHEN** application or test code uses the Snyk issues client
- **THEN** that client implementation is imported from the `snyk` package rooted at `src/snyk/`

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

The client SHALL support HTTP `GET` for listing issues and for retrieving a single issue, for both org and group scopes, using the paths documented in `openspec/specs/integration-apis/spec.md` (`/orgs/{org_id}/issues`, `/orgs/{org_id}/issues/{issue_id}`, `/groups/{group_id}/issues`, `/groups/{group_id}/issues/{issue_id}`). The default base URL SHALL be `https://api.snyk.io/rest`; the client SHALL allow a different base URL to be supplied for testing.

#### Scenario: List issues for an org

- **WHEN** the caller requests listing issues for a valid `org_id`
- **THEN** the client SHALL call the corresponding list endpoint and return parsed JSON:API payload data needed for downstream processing

#### Scenario: Get one issue

- **WHEN** the caller requests a single issue by `org_id` and `issue_id` (or group scope equivalents)
- **THEN** the client SHALL call the corresponding get endpoint and return parsed JSON:API payload data for that issue

---

### Requirement: Pagination for list operations

For list operations, the client SHALL follow **`links.next`** in each JSON:API response until `links.next` is absent or null, so that callers can retrieve the full issue set without silently truncating at the first page.

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

On non-success HTTP status codes, the client SHALL raise or return errors that include the HTTP status and allow callers to handle auth failures, client errors, and server errors distinctly where practical. The client SHALL NOT write full response bodies to logs by default; diagnostic messages SHALL omit secrets.

#### Scenario: Unauthorized

- **WHEN** the API responds with `401` or `403`
- **THEN** the error surfaced to the caller SHALL indicate authorization failure without including the token

#### Scenario: Server error

- **WHEN** the API responds with `5xx`
- **THEN** the client SHALL surface a retriable or server-error class of failure suitable for retry policies in higher layers

---

### Requirement: Optional CLI for fetch smoke test

The application CLI SHALL expose an argparse-based command or option group that invokes the Snyk issues client (org or group, list or get) using `SNYK_TOKEN` from the environment, for operator or developer smoke verification. The CLI SHALL not accept the token as a command-line argument.

#### Scenario: CLI without token

- **WHEN** the user runs the fetch smoke command without setting `SNYK_TOKEN`
- **THEN** the process SHALL exit non-zero with a concise message and no network call
