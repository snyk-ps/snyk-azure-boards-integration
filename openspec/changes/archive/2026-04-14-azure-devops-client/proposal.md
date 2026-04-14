## Why

The product needs a first-class Python client for Azure DevOps Work Item Tracking (WIT) so scheduled sync and operators can create, read, update, and comment on work items in a consistent, testable way. Today REST paths and media types are documented under `integration-apis`, but there is no dedicated capability that owns HTTP shaping, PAT authentication from the environment, normalized records, and CLI smoke wiring—blocking a future full sync/reconcile change that remains anchored in `sync-lifecycle` (P2-FR-*).

## What Changes

- Introduce a new capability **`azure-devops-client`** with normative requirements in `openspec/specs/azure-devops-client/spec.md` (v1: create work item, get work item, list work items by ids ≤200, update work item, add work item comment; default `api-version=7.1` for WIT; preview version for comments per `integration-apis`; overridable base URL for tests; PAT only from `AZURE_DEVOPS_PAT`; structured HTTP errors and bounded 429 handling per spec).
- Add Python package layout under `src/integrations/azure_devops/` for all Azure DevOps HTTP/auth/normalization; keep argparse and subcommand wiring under `src/commands/` with `src/main.py` delegating (same split as `snyk-issues-client`).
- Extend operator configuration: under `azure_boards`, add non-secret **`organization`** and **`project`** strings for DevOps routing; mirror on `AzureBoardsConfig` in `src/config/models.py`; document in `data/sample-config.yaml` and README per `application-config`.
- Add a read-only CLI smoke subcommand that loads `--config`, reads `azure_boards.organization` / `azure_boards.project`, uses `AZURE_DEVOPS_PAT`, and calls `get_work_item` with required `--work-item-id` (no PAT on CLI; no create/update/comment by default).
- Register the capability in repo metadata: `SPEC.md`, `openspec/AGENTS.md`, and a one-line pointer under `openspec/config.yaml` context APIs list.
- **Non-goals (v1):** full sync/reconcile (stays in future `sync-lifecycle` work); `workitemsbatch`, WIQL, Core get project; managed identity / Key Vault in this capability (runtime supplies env per `azure-platform`); PAT or YAML loading inside the integration package (callers pass org/project; PAT from env only).

## Capabilities

### New Capabilities

- `azure-devops-client`: Python WIT client behavior—package location under `src/integrations/azure_devops/`, `AZURE_DEVOPS_PAT` auth, URL building aligned with `integration-apis`, normalized work item and comment records, HTTP/retry policy, optional constructor overrides for `api-version` in tests only, CLI smoke for connectivity.

### Modified Capabilities

- `application-config`: Add `azure_boards.organization` and `azure_boards.project` (non-secret routing); require documentation/sample/README updates consistent with existing configuration rules.

## Impact

- New modules under `src/integrations/azure_devops/` and new command module under `src/commands/`; `src/main.py` subcommand registration.
- `src/config/` models and loader defaults for `azure_boards`; `data/sample-config.yaml` and `README.md` configuration sections.
- New unit tests under `tests/` for client, normalization, HTTP behavior, and command wiring.
- No change to REST path definitions in `integration-apis` unless a separate editorial update is needed; `azure-platform` remains infra/mapping/operator concerns, not the Python WIT client home.
