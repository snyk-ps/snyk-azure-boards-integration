## 1. Client module and configuration

- [x] 1.1 Add the **`src/snyk/`** package with a client class or module functions that read `SNYK_TOKEN` from the environment, validate presence before HTTP calls, and support a configurable base URL defaulting to `https://api.snyk.io/rest` per `design.md`.
- [x] 1.2 Centralize Snyk REST version / `Accept` header values as required by the current Snyk OpenAPI for Issues (single module-level constants or small helper under `src/snyk/`), documented in docstrings.

## 2. HTTP operations and errors

- [x] 2.1 Implement HTTPS `GET` for org- and group-scoped list and get issue paths from `openspec/specs/integration-apis/spec.md`, using the stdlib HTTP stack chosen in `design.md`, with explicit timeouts.
- [x] 2.2 Map non-success responses to distinct, testable error types or exceptions (e.g. auth vs client vs server) without logging secrets or full response bodies by default.

## 3. Pagination and response parsing

- [x] 3.1 Implement list pagination by following **`links.next`** until absent; implement **`links.next` URL resolution** so combining the configured base (ending in `/rest`) with Snyk’s next value (which may start with `rest/`) never yields an invalid **`rest/rest/...`** URL (see `design.md` and `specs/snyk-issues-client/spec.md`).
- [x] 3.2 Parse JSON:API JSON into structures (e.g. `TypedDict` or dataclasses) sufficient for callers and tests; handle empty lists and missing `data` safely.

## 4. CLI smoke command

- [x] 4.1 Extend `src/main.py` argparse to add a fetch/smoke subcommand (or mutually exclusive option group) for list/get with org or group scope, taking IDs as arguments, using only `SNYK_TOKEN` from the environment; exit non-zero with a concise message when the token is missing.

## 5. Tests and quality

- [x] 5.1 Add unit tests with mocked HTTP for token-missing behavior, successful list/get JSON, multi-page pagination via **`links.next`**, explicit coverage for **`rest/rest/`** avoidance when resolving the next URL, `401`/`403`, and `5xx` handling; cover every new public and protected function per project guidelines.
- [x] 5.2 Run the project test suite and fix any regressions; run Snyk Open Source / Code on any new third-party dependency (avoid new deps unless justified in `design.md`).
