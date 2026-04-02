## Why

The Snyk issues client and CLI should match the repository’s documented `src/` layout (`commands/` for argparse wiring, `snyk/` for HTTP and Snyk-specific logic) and align with the product’s group-scoped sync model. The REST client should use the current Issues API contract (`version=2025-11-05`), request up to 100 issues per page, support list filters that future config will mirror (effective severity, type, status), normalize list output for downstream mapping, and handle Snyk’s per-key rate limit (429) reliably.

## What Changes

- Move CLI argument parsing and fetch subcommand dispatch from `src/main.py` into **`src/commands/`** (per README); keep `src/main.py` as a thin entry that delegates to the command module.
- **Remove** org-scoped issue list/get from the Python client and CLI surface; **group scope only** for listing and single-issue fetch (`GET /groups/{group_id}/issues`, `GET /groups/{group_id}/issues/{issue_id}`).
- Set **`limit=100`** on list requests (maximum page size per Snyk Issues API) while retaining full pagination via `links.next`.
- Add optional query parameters for group list: **effective severity level** (multi-value; default **`high` and `critical`**), **type** (optional; API-defined values), and **status** (optional), structured so future external config can set the same parameters without API redesign.
- Bump REST **`version`** query parameter to **`2025-11-05`**.
- Define a **stable extraction** of fields from JSON:API issue resources for list/get: `org_id` (from `data[].relationships.organization.data.id` — spelling per API), `project_id` (`data[].relationships.scan_item.data.id`), `issue_id` (`data[].attributes.key`), `created_at`, `severity` (`data[].attributes.effective_severity_level`); design for extension as more fields are needed.
- **Rate limiting:** treat HTTP **429** as retryable within a **one-minute** window respecting Snyk’s documented **1620 requests per minute per API key** policy; backoff/retry without logging secrets or full bodies by default.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `snyk-issues-client`: Update layout rules (`commands/` vs `snyk/`), group-only operations, API version, `limit`, optional filters and defaults, extracted issue fields, pagination unchanged, HTTP/429 and rate-limit behavior, CLI smoke behavior.

## Impact

- **Code:** `src/main.py`, new `src/commands/` module(s), `src/snyk/` (client, constants, parser/types for extracted fields, errors for 429/rate limit), tests under `tests/`.
- **APIs:** Snyk REST Issues only; no Azure DevOps changes.
- **Dependencies:** Prefer stdlib; no new packages unless required for rate limiting (prefer stdlib sleep/backoff).
- **Breaking:** **BREAKING** — org-scoped list/get removed from the client and CLI; consumers must use group scope.
