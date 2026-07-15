## Context

- Snyk regional **web app** URLs are documented at [Regional hosting and data residency — Regional URLs](https://docs.snyk.io/snyk-data-and-governance/regional-hosting-and-data-residency#regional-urls) (for example **SNYK-US-02** → `https://app.us.snyk.io`, **SNYK-EU-01** → `https://app.eu.snyk.io`).
- **`snyk-api-base-url-override`** (archived) intentionally left UI links separate from API origin.
- Current code:
  - `snyk_ui_issue_url` hard-codes `https://app.snyk.io` (`src/sync/issue_content.py`).
  - `_ado_system_description_html` detects the "Open in Snyk" block only when the URL starts with `https://app.snyk.io/` (`src/sync/patch_build.py`).
  - `sync` already loads merged config and passes routing context through `run.py` → `issue_content`.

## Goals / Non-Goals

**Goals:**

- Single configurable **app origin** for all **P2-FR-5.4** deep links and related description HTML.
- Override via **`SNYK_APP_BASE_URL`**, **`snyk.app_base_url`**, and **`--snyk-app-base-url`** on **`sync`**, using **defaults → YAML → env → CLI** precedence.
- Default remains **`https://app.snyk.io`** (no breaking change for SNYK-US-01).
- Document regional app URLs and relationship to **`SNYK_API_BASE_URL`** in **`README.md`** and **`CONFIGURATION.md`**.

**Non-Goals:**

- Deriving app origin from API origin automatically.
- Changing **`fetch`**, org-config generator, or Snyk HTTP clients (API-only surfaces).
- Hot-reload of operator YAML on Azure Files.

## Decisions

| Topic | Decision | Rationale |
| ----- | -------- | --------- |
| Configured value | **App origin** (scheme + host, no path), default `https://app.snyk.io` | Matches Snyk regional login/app URL table; parallel to `api_base_url` |
| YAML key | `snyk.app_base_url` | Consistent namespace with `snyk.api_base_url` |
| Env var | `SNYK_APP_BASE_URL` | Parallel naming to `SNYK_API_BASE_URL` |
| CLI flag | `--snyk-app-base-url` on **`sync` only** | Only `sync` composes work item Snyk UI links |
| Precedence | defaults → YAML → env → CLI | Same as existing multi-layer settings |
| Validation | Non-empty HTTPS URL; strip trailing slash; reject invalid at load | Fail fast; reuse `_validate_api_base_url` pattern or shared HTTPS-origin validator |
| Link template | `{app_base}/org/{slug}/project/{pid}#issue-{key}` | Preserves **P2-FR-5.4** path/fragment semantics |
| patch_build detection | Pass effective `app_base_url` into `_ado_system_description_html` (or prefix check against normalized origin) | Regional URLs must still get "view in Snyk" anchor treatment |
| API vs app | Independent settings; docs list both for regional tenants | Snyk hosts differ (`api.*` vs `app.*`); prior change explicitly kept them separate |

## Risks / Trade-offs

| Risk | Mitigation |
| ---- | ---------- |
| Operator sets regional API but default app host | README/CONFIGURATION: set **both** `SNYK_API_BASE_URL` and `SNYK_APP_BASE_URL`; link to regional URL table |
| Operator passes origin with trailing slash or path | Normalize at load (strip `/`, reject paths) |
| Tests assert hard-coded `app.snyk.io` | Update tests to cover default and override |

## Migration Plan

- **Deploy:** No breaking change; default unchanged. Regional operators add **`SNYK_APP_BASE_URL`** (and verify **`SNYK_API_BASE_URL`**) on Container App Job env.
- **Rollback:** Remove or reset **`SNYK_APP_BASE_URL`** to default origin.

## Open Questions

- _(none — mirror `api_base_url` model unless review prefers a different env var name)_
