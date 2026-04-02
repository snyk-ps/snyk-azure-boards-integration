## Why

The synchronization job must call the Snyk REST Issues API (JSON:API) to list and read findings before reconciling with Azure Boards and Table Storage. The repository currently has no dedicated, tested client for those endpoints, which blocks incremental delivery of the sync pipeline and manual verification against live or mocked APIs.

## What Changes

- Add Python code under **`src/snyk/`** that performs authenticated HTTP calls to Snyk Issues REST resources (`/groups/{group_id}/issues`, `/orgs/{org_id}/issues`, and get-by-id variants per `openspec/specs/integration-apis/spec.md`), using `SNYK_TOKEN` from the environment.
- **Pagination:** follow `links.next` in each JSON:API response to retrieve the next page. The value Snyk returns is a path or URL segment that includes a leading `rest/`; the client base URL already ends with `/rest` (or equivalent). The implementation **must** resolve the next URL so it is not naïvely appended to the base (which would yield an invalid **`rest/rest/...`** path). Use explicit URL joining or normalization (e.g. treat `links.next` as absolute if full URL, or strip duplicate `rest/` segments when combining with the configured base).
- Parse `application/vnd.api+json` responses into structures the sync job can consume, without logging tokens or raw credentials.
- Extend the CLI (argparse) with an optional command or flags to run a fetch/smoke test for operators or developers.
- Add unit tests with mocked HTTP covering documented behavior and edge cases (empty pages, error responses, pagination boundaries, and **`links.next`** URL resolution including the `rest/` duplication case).

## Capabilities

### New Capabilities

- `snyk-issues-client`: Behavioral and interface requirements for fetching Snyk issues in Python (authentication, endpoints, pagination, JSON:API handling, errors, observability-safe logging).

### Modified Capabilities

- *(none)* — The canonical REST paths and media types remain as documented in `integration-apis`; this change adds an implementation-facing capability without changing that reference table.

## Impact

- New Python package under **`src/snyk/`** (and matching tests under the project’s test layout), plus small additions to CLI entrypoint wiring in `src/main.py` or equivalent.
- Dependencies: prefer the standard library for HTTP; any third-party HTTP client must be justified, vetted with Snyk Open Source, and kept free of high/critical issues per project guidelines.
- Future sync and Azure modules will depend on this client for issue retrieval; no Azure DevOps or Table Storage changes in this change.
