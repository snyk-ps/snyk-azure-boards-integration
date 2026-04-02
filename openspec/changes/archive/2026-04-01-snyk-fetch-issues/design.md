## Context

The product syncs Snyk security findings to Azure Boards (`openspec/config.yaml`). The canonical REST surface for Issues is documented in `openspec/specs/integration-apis/spec.md` (base `https://api.snyk.io/rest`, JSON:API). Local development and the future ACA job both need a small Python layer under **`src/snyk/`** that performs authenticated list/get calls, handles pagination, and returns parsed document data without leaking secrets. The repository today only has a stub CLI (`src/main.py`).

## Goals / Non-Goals

**Goals:**

- Provide a testable Python API to list and fetch Snyk Issues at org or group scope using `SNYK_TOKEN` from the environment (in production, populated from Key Vault via ACA).
- Follow Snyk REST semantics: correct `Accept` / API version headers as required by the Snyk OpenAPI for Issues, and complete pagination via **`links.next`** so all pages can be consumed, with correct URL resolution (see Decisions).
- Keep logging safe (no tokens, no PAT strings in log messages).
- Support an optional CLI entry path for smoke checks (argparse), consistent with project guidelines.

**Non-Goals:**

- Azure DevOps calls, Table Storage, or full sync/reconcile logic (separate changes).
- OAuth or interactive login flows; only service token via `SNYK_TOKEN`.
- Defining new REST routes or changing the normative path table in `integration-apis` (reference remains the source of truth for URLs).

## Decisions

| Decision | Choice | Rationale | Alternatives considered |
|----------|--------|-----------|---------------------------|
| HTTP stack | Prefer **stdlib** (`urllib.request` and/or `http.client`) for HTTPS GET with explicit timeouts | Matches guidelines to avoid extra dependencies unless necessary; sufficient for JSON GET + pagination | `httpx` / `requests`: fewer lines but new dependency and Snyk OSS gate |
| Configuration | **Base URL** default `https://api.snyk.io/rest`; optional override via constructor or env for testing | Matches `integration-apis`; allows mock servers in tests | Hard-coded only: worse for tests |
| Pagination | **Iterator or generator** that follows **`links.next`** in each JSON:API response until absent | Matches live Snyk behavior; no silent truncation | Single-request only: incorrect for production scale |
| **`links.next` URL resolution** | **`urllib.parse.urljoin`** (or equivalent) against a stable origin plus path normalization: Snyk may return a `links.next` value that begins with `rest/` while the configured base URL already ends with `/rest`. Naïve concatenation produces **`rest/rest/...`**. Resolve next requests by treating full URLs as absolute, or by normalizing path segments so the effective request URL has a single `/rest` prefix before the resource path | Invalid URLs break pagination in production | String concat of base + `links.next` without normalization |
| Auth | **`Authorization: token <SNYK_TOKEN>`** or the scheme required by current Snyk REST docs (verify against OpenAPI during implementation) | Standard service-to-service pattern | Custom headers without doc check: risk of drift |
| Response handling | Parse JSON with **`json`**, expose minimal typed structures (e.g. dataclasses or TypedDict) for resources the sync needs first | Clear contracts for tests and callers | Raw dict only everywhere: harder to evolve |
| Errors | Map non-success HTTP to **small exception types** carrying status and optional parsed error body; no full response body in logs by default | Operators can distinguish auth vs rate limit vs server errors | Silent fallback: hides failures |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Snyk API pagination or version headers change | Pin behavior to OpenAPI / docs at implementation time; unit tests for pagination parsing and **`links.next`** URL resolution (including `rest/` duplication case); shallow logging of HTTP status only |
| Malformed next-page URL | Implement and test URL resolution per row above; log only status / high-level failure, not full URLs with secrets |
| Large responses memory use | Stream or page iteratively; avoid loading all pages into one giant list if the public API offers incremental consumption |
| Duplication with future Azure credential code | Keep this module Snyk-only; Key Vault injects `SNYK_TOKEN`—no `DefaultAzureCredential` inside this client |

## Migration Plan

- **Introduce** the `src/snyk/` package and tests in one change; no existing production traffic to migrate.
- **Rollback**: revert the change; no persistent schema migration.
- **Deploy**: when ACA runs the job, ensure Key Vault secret mapping exposes `SNYK_TOKEN` to the container (documented in `azure-platform` for later work; not required to complete this client’s code).

## Open Questions

- Exact **Snyk REST API version** query/header (e.g. `version=2024-01-01`) for Issues: confirm from [Snyk REST OpenAPI](https://apidocs.snyk.io/) during implementation and encode in one place (constant or small helper).
- Whether the first iteration exposes **only org-scoped** list or **both** org and group list entry points (proposal includes both; implementation can ship one path first if tasks split).
