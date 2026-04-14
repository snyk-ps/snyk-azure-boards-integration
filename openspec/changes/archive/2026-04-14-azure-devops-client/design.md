## Context

Azure DevOps WIT operations are defined at the REST contract level in `openspec/specs/integration-apis/spec.md`. Runtime secrets and operator YAML are covered by `azure-platform` and `application-config`; sync semantics and P2-FR-* live in `sync-lifecycle`. This change adds a dedicated **`azure-devops-client`** capability so application code has a single place for HTTP, PAT authentication from the environment, response normalization, and bounded retries—without folding those rules into `integration-apis` or `azure-platform`.

## Goals / Non-Goals

**Goals:**

- Ship v1 programmatic APIs for create, get, list-by-ids (≤200 ids per call), update (JSON Patch), and add comment, matching `integration-apis` paths and media types.
- Enforce `AZURE_DEVOPS_PAT` (unset/empty → fail before HTTP); default origin `https://dev.azure.com`; optional injectable base URL for tests.
- Normalize work item responses for downstream mapping/tagging (P2-FR-5.x) and table columns: `work_item_id`, `work_item_status`, `rev`, and full `fields`; comments return at least `id` and `work_item_id`.
- Centralize default WIT `api-version` **`7.1`** and comment preview **`7.0-preview.3`** as module-level constants (or constructor defaults), with optional constructor overrides for automated tests only (no production env overrides for versions).
- Implement HTTP error types that expose status and distinguish auth, 4xx, 429, and 5xx where practical; safe logging (no secrets, no full bodies by default).
- Implement 429 retry with bounded attempts, honoring `Retry-After` when present and otherwise capped exponential backoff. GET may use limited retries for 5xx or connection errors; POST/PATCH retry 429 only (no open-ended 5xx retries for mutating calls).
- Add argparse smoke under `src/commands/` that loads config, passes org/project into the client, and performs one `get_work_item` read.

**Non-Goals:**

- Full sync/reconcile, idempotent POST, WIQL, `workitemsbatch`, Core **get project**, managed identity, Key Vault secret fetch, reading operator YAML or PAT inside `src/integrations/azure_devops/`.

## Decisions

- **Package root `src/integrations/azure_devops/`** — Matches README rule that `integrations/` is for third-party systems outside Snyk; parallels the separation between `src/snyk/` and `src/commands/` for the Snyk client.
- **stdlib HTTP (`urllib.request`) vs `http.client`** — Prefer the same stack as the existing Snyk client if one is already chosen; otherwise default to stdlib HTTP with a thin wrapper for testability (design leaves concrete module split to implementation tasks). Extra third-party HTTP dependencies require Snyk Open Source/Code policy gates.
- **Routing value object optional** — Callers may pass `organization`, `project` as discrete parameters or via a small immutable type constructed in `src/config/`; the integration layer never opens the YAML file.
- **List-by-ids validation** — If more than 200 ids are supplied in one call, the client SHALL reject before HTTP with a clear error (API limit).
- **Comment `api-version` drift** — Single constant (e.g. `AZURE_DEVOPS_COMMENT_API_VERSION`) documented to track `integration-apis`; when that spec updates the preview version, update the constant and tests in the same change.

## Risks / Trade-offs

- **[Risk] Preview comment API** — Organizations may lag supported preview versions. **→ Mitigation:** Constant is documented and tied to `integration-apis`; constructor test override only.
- **[Risk] Mutating retries** — Open-ended 5xx retries on PATCH/POST could duplicate side effects. **→ Mitigation:** Spec limits retries to 429 for mutating verbs; surface 5xx to upper layers.
- **[Risk] PAT in env** — Misconfigured logs could leak. **→ Mitigation:** Never log `Authorization` or token; omit full response bodies from default logs.

## Migration Plan

- No production migration: new capability. Operators add `azure_boards.organization` and `azure_boards.project` to YAML when using DevOps smoke or future sync; PAT continues to be injected as `AZURE_DEVOPS_PAT` per `azure-platform`.

## Open Questions

- None blocking v1; future changes may add batch/WIQL/project connectivity checks.
