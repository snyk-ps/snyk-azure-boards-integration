## 1. Layout and entry point

- [x] 1.1 Add `src/commands/` package with fetch subcommand module: `build_parser` / subparser registration and `run_fetch` (or equivalent) that wire argparse to `IssuesClient`; no argparse under `src/snyk/`.
- [x] 1.2 Slim `src/main.py` to delegate to `commands` only (import and dispatch).

## 2. Client: group scope, version, query parameters

- [x] 2.1 Set `SNYK_REST_API_VERSION` to `2025-11-05` in `snyk/constants.py` and use it on all group list/get URLs.
- [x] 2.2 Remove org-scoped list/get methods and URL builders from `IssuesClient`; retain only group list (`iter_group_issues` or renamed API) and `get_group_issue`.
- [x] 2.3 Build first-page group list URL with `limit=100` and optional query params: `effective_severity_level` (default `high`, `critical` when unset), optional `type`, optional `status`; use stdlib URL encoding for repeated keys per API.
- [x] 2.4 Keep pagination via `links.next` unchanged for subsequent pages.

## 3. Normalized issue records

- [x] 3.1 Implement mapping from JSON:API issue resource objects to a normalized dict (or small type) with `org_id`, `project_id`, `issue_id`, `created_at`, `severity` per delta spec; document handling of missing relationships.
- [x] 3.2 Use normalized mapping in list iteration and single-issue get return value (or parallel accessor used by CLI).

## 4. Rate limiting (429)

- [x] 4.1 Map HTTP 429 to a retriable path; implement bounded retry with backoff (honor `Retry-After` when present; injectable sleep/clock for tests); do not log full bodies or secrets.
- [x] 4.2 Add/extend error types so callers can distinguish rate limit from other client errors where practical.

## 5. CLI

- [x] 5.1 Update fetch command to group-only (`list` / `get`), `group_id`, optional `issue_id` for get; add flags/options for effective severity (default high+critical), type, status as needed; print normalized output (e.g. JSON lines or JSON) without exposing `SNYK_TOKEN` on argv.

## 6. Tests and verification

- [x] 6.1 Update or replace unit tests: `tests/test_client.py`, `tests/test_main.py`, parser/URL tests; add tests for query building, normalization, 429 retry, and command wiring.
- [x] 6.2 Run `uv run pytest` and fix failures; run Snyk Code/Open Source on changed deps if any.

## 7. Spec consolidation

- [x] 7.1 After implementation, merge delta into `openspec/specs/snyk-issues-client/spec.md` (during OpenSpec archive) so the source-of-truth matches shipped behavior.
