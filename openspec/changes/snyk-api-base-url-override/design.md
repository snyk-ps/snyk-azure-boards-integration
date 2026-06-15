## Context

- Snyk regional REST bases are documented at [About the REST API — API URLs](https://docs.snyk.io/developer-tools/snyk-api/rest-api/about-the-rest-api#api-urls).
- Default region **SNYK-US-01**: origin **`https://api.snyk.io`**, REST **`https://api.snyk.io/rest`**, V1 **`https://api.snyk.io/v1`**.
- Current code: `DEFAULT_BASE_URL = "https://api.snyk.io/rest"` in `src/snyk/constants.py`; `sync` and `fetch` call `IssuesClient()` with no override; org-config generator accepts `--base-url` as a full REST URL only (`src/org_config_generator/core.py`).

## Goals / Non-Goals

**Goals:**

- Single configurable **API origin** for all Snyk HTTP clients, with REST and V1 bases derived from it.
- Override via **`SNYK_API_BASE_URL`**, **`snyk.api_base_url`**, and **`--snyk-api-base-url`** on Snyk-calling commands, using existing **defaults → YAML → env → CLI** precedence.
- Wire merged config into **`sync`** and **`fetch`**; align org-config generator with shared URL helpers.
- Document defaults (**SNYK-US-01**), regional lookup, ACA Job recommendation, and **401** troubleshooting.

**Non-Goals:**

- Changing **`app.snyk.io`** UI link composition.
- Auto-detecting region from the token.
- Hot-reload of operator YAML on Azure Files.
- Adding a new V1 HTTP client (only derive and document `{origin}/v1` for future use).

## Decisions

| Topic | Decision | Rationale |
| ----- | -------- | --------- |
| Configured value | **API origin** (scheme + host, no path), default `https://api.snyk.io` | One setting covers REST and V1; matches env var name and user examples |
| Derivation | `rest_base = normalize(origin) + "/rest"`; `v1_base = normalize(origin) + "/v1"` | Matches Snyk URL layout per regional docs |
| `--base-url` (org generator) | Accept **origin** or **full REST base**; if value ends with `/rest`, treat as REST base and infer origin by stripping suffix | Backward compatible with scripts passing full REST URL |
| Precedence | defaults → YAML `snyk.api_base_url` → `SNYK_API_BASE_URL` → CLI | Same as `group_id`, mapping store, etc. |
| Validation | Non-empty HTTPS URL; strip trailing slash; reject invalid URLs at load with clear non-secret error | Fail fast before HTTP |
| ACA deployment | Document **`SNYK_API_BASE_URL`** as primary for scheduled jobs | Non-secret; avoids editing mounted YAML per region |
| Shared helpers | `src/snyk/urls.py` (or `constants.py`) owns origin normalization and REST/V1 derivation | Remove duplicate `DEFAULT_BASE_URL` in org generator |

## Risks / Trade-offs

| Risk | Mitigation |
| ---- | ---------- |
| Operator sets EU origin but US token (or vice versa) | README troubleshooting: **401** + verify [regional API URLs](https://docs.snyk.io/developer-tools/snyk-api/rest-api/about-the-rest-api#api-urls) |
| `links.next` pagination with regional host | Existing `resolve_next_url` handles absolute URLs |
| Operator passes malformed URL | Validate at config load; clear error message |
| Duplicate constants across modules | Single source in `snyk.urls` / `snyk.constants` |

## Migration Plan

- **Deploy:** No breaking change; default remains **SNYK-US-01**. Operators in other regions add **`SNYK_API_BASE_URL`** to Container App Job env (or YAML) and redeploy/restart.
- **Rollback:** Remove or reset **`SNYK_API_BASE_URL`** to default origin.

## Open Questions

- _(none — origin-based model approved in proposal review)_
