## Context

The repository README defines `src/commands/` for argparse and CLI wiring and `src/snyk/` for Snyk HTTP/API code. Current code places `build_parser` and fetch dispatch in `src/main.py`, and the `IssuesClient` implements both org and group scopes. Product sync is group-scoped; org endpoints are unnecessary surface area. Snyk documents a dated `version` query parameter (latest target **`2025-11-05`**, see [Snyk Issues API](https://docs.snyk.io/snyk-api/reference/issues)), list **`limit`** up to 100, and optional filters (`effective_severity_level`, `type`, `status` on `GET /groups/{group_id}/issues`). Rate limits: **1620 requests per minute per API key**, with **429 Too Many Requests** when exceeded until the window resets.

## Goals / Non-Goals

**Goals:**

- Enforce README layout: **`src/commands/`** owns argparse subcommands and wiring; **`src/snyk/`** owns `IssuesClient`, URL/query building, parsing, and error mapping; **`src/main.py`** only bootstraps and delegates.
- **Group scope only** for list and get in this client.
- First-page list URLs include **`limit=100`** and **`version=2025-11-05`**; optional CLI/programmatic parameters for **`effective_severity_level`** (repeatable; default **`high`**, **`critical`**), **`type`**, and **`status`** as supported by the API.
- Expose a **normalized** structure (dict or small typed object) with: `org_id`, `project_id`, `issue_id`, `created_at`, `severity` — sourced from JSON:API per proposal (relationships `organization`, `scan_item`; attributes `key`, `created_at`, `effective_severity_level`).
- **429**: classify as rate-limit exceeded; **retry** with bounded backoff (e.g. respect `Retry-After` when present, else sleep until the next minute boundary or a capped exponential backoff) without logging response bodies or secrets.

**Non-Goals:**

- Org-scoped issues endpoints in the Python client.
- Full external YAML/config loading (CLI flags and client parameters only; config file wiring is future work).
- Azure DevOps, Table Storage, or managed identity (unchanged).

## Decisions

1. **Module layout:** Use `src/commands/fetch.py` (or `src/commands/__init__.py` + `fetch.py`) exporting `build_parser` / `add_fetch_subparser` and `run_fetch` (or similar); `main.py` imports from `commands` and calls `main()`. Keeps a single entry point path for Docker (`python src/main.py`).

2. **Query encoding:** Build the first list URL with `urllib.parse.urlencode` / `parse_qsl` so multi-value `effective_severity_level` matches Snyk’s expected query shape; pass through **`links.next`** unchanged for pagination (Snyk preserves filter context in the next URL).

3. **API version:** Central constant `SNYK_REST_API_VERSION = "2025-11-05"` in `snyk/constants.py`; all group list/get URLs include `version=...`.

4. **Normalized output:** Add `snyk` helper(s) e.g. `issue_record_from_resource(data: dict) -> dict` used by list iteration and get, so CLI and future sync share one mapping. Missing optional relationships MAY yield `None` or omitted keys — document behavior.

5. **429 / rate limit:** Introduce `SnykRateLimitError` or reuse a retriable base; implement retry **inside** `_get_json` (or a thin wrapper) with a **maximum** retry count and **total** time cap (e.g. up to ~70s to span a rate window) so tests stay deterministic via injectable clock/sleep. Document alignment with **1620/min** (client does not pre-count requests globally; relies on 429 + backoff).

6. **Alternatives considered:** Dropping pagination in favor of single page — rejected (need full issue set). Third-party HTTP library — rejected per project preference for stdlib unless unavoidable.

## Risks / Trade-offs

- **[Risk]** Typo in Snyk JSON:API (`organization` vs historic typos) — **Mitigation:** follow live API field names; unit tests with fixture payloads.
- **[Risk]** Aggressive retry amplifies load — **Mitigation:** cap retries, jitter optional, honor 429 semantics.
- **[Trade-off]** Global retry in `_get_json` affects all GETs — acceptable; 429 is generic.

## Migration Plan

- **Consumers** of org-scoped methods: remove calls; use `group_id` and group endpoints only.
- **CLI:** `fetch` no longer accepts `org` scope; document new flags in README when implementation lands (implementation task, not this doc).

## Open Questions

- Exact **query parameter names** for `type` and `status` should match the OpenAPI for `version=2025-11-05` (confirm against Snyk spec at apply time if CLI validation needs enumerations).
