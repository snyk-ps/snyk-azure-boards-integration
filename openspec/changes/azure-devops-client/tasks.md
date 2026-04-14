## 1. Specs and configuration model

- [x] 1.1 Merge `openspec/changes/azure-devops-client/specs/application-config/spec.md` into `openspec/specs/application-config/spec.md` (ADDED requirement for `azure_boards.organization` / `azure_boards.project`, README/sample scenarios, and update the `azure_boards` row in the YAML table if needed for discoverability)
- [x] 1.2 Extend `AzureBoardsConfig` in `src/config/models.py` with `organization: str` and `project: str` (defaults empty unless design specifies placeholders), wired through the existing YAML merge path
- [x] 1.3 Update `data/sample-config.yaml` with placeholder `azure_boards.organization` and `azure_boards.project` values (non-secret)

## 2. Azure DevOps integration package

- [x] 2.1 Create `src/integrations/azure_devops/` package with module-level constants for default base URL (`https://dev.azure.com`), WIT `api-version` **`7.1`**, and comment preview **`7.0-preview.3`** (or names documented in `integration-apis`), plus optional constructor overrides for api-versions **for tests only**
- [x] 2.2 Implement URL builders and HTTP layer using stdlib (or match existing project HTTP patterns) with Basic auth from `AZURE_DEVOPS_PAT`, failing before HTTP when unset/empty, never logging secrets or full `Authorization` values
- [x] 2.3 Implement `create_work_item`, `get_work_item`, `list_work_items_by_ids` (reject >200 ids before HTTP), `update_work_item`, and `add_work_item_comment` aligned with `openspec/specs/integration-apis/spec.md` paths and media types
- [x] 2.4 Implement response normalization to work item records (`work_item_id`, `work_item_status`, `rev`, `fields`) and comment records (`id`, `work_item_id`), allowing extension with extra keys later
- [x] 2.5 Implement error taxonomy (status-bearing exceptions or structured errors) and retry policy: bounded 429 retries with `Retry-After` and capped exponential backoff; limited GET retries for 5xx/connection errors; POST/PATCH retry 429 only (no open-ended 5xx retries); no full response body logging by default

## 3. CLI smoke command

- [x] 3.1 Add argparse subcommand module under `src/commands/` (e.g. `azure_devops_smoke.py` or similar) that loads `--config`, reads `azure_boards.organization` and `azure_boards.project`, requires `--work-item-id`, uses `AZURE_DEVOPS_PAT` from the environment only, and issues a single `get_work_item` call
- [x] 3.2 Register the subcommand from `src/main.py` via existing command dispatch patterns; document invocation in `README.md` and ensure help text states PAT is env-only

## 4. Tests

- [x] 4.1 Add unit tests under `tests/` for URL building, auth guard (no PAT → no HTTP), id-list validation (>200), normalization (including missing `System.State`), and error/retry classification using stdlib test doubles or local HTTP fakes (no real secrets in tests)
- [x] 4.2 Add unit tests for the smoke command wiring (argument validation, config → client parameters) using mocks for the client HTTP layer

## 5. Verification

- [x] 5.1 Run the project test suite with `uv` and fix any regressions
- [x] 5.2 Run Snyk Code (and Open Source if dependencies change) before merge per repository policy
