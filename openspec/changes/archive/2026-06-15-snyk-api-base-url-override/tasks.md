## 1. Snyk URL helpers

- [x] 1.1 Add `DEFAULT_API_ORIGIN`, origin normalization, `rest_base_from_origin`, `v1_base_from_origin`, and `resolve_snyk_rest_base` in `src/snyk/` (single source of truth; remove duplicate constant in org generator).
- [x] 1.2 Unit tests for normalization, default origin (**SNYK-US-01**), `/rest` suffix input, and derived REST/V1 bases.

## 2. Configuration layer

- [x] 2.1 Extend `SnykConfig` / loader defaults with `api_base_url` default `https://api.snyk.io`.
- [x] 2.2 Apply `SNYK_API_BASE_URL` in `_apply_env_overrides`; add `cli_snyk_api_base_url` to `load_app_config`.
- [x] 2.3 Validate HTTPS + non-empty at config resolution; unit tests for precedence (YAML/env/CLI) and rejection cases.

## 3. Command wiring

- [x] 3.1 Add `--snyk-api-base-url` to `sync` and `fetch`; pass derived REST base to `IssuesClient`.
- [x] 3.2 Align `scripts/generate_org_mapping_config.py` with shared resolver (keep `--base-url` working; honor `SNYK_API_BASE_URL`).
- [x] 3.3 Tests: sync/fetch construct client with merged base URL (mock or spy).

## 4. Documentation

- [x] 4.1 **CONFIGURATION.md**: `snyk.api_base_url`, `SNYK_API_BASE_URL`, CLI flags, default **SNYK-US-01**, link to [Snyk API URLs by region](https://docs.snyk.io/developer-tools/snyk-api/rest-api/about-the-rest-api#api-urls), ACA Job recommendation.
- [x] 4.2 **README.md**: mention in Configuration/Deployment; **Troubleshooting** row for Snyk **401** — verify token **and** `SNYK_API_BASE_URL` matches Snyk region.
- [x] 4.3 **data/sample-config.yaml**: commented `# api_base_url: https://api.snyk.io` example under `snyk`.
- [x] 4.4 **openspec/config.yaml** context: note configurable Snyk API origin.

## 5. Verification and archive prep

- [x] 5.1 Run unit tests; Snyk Code/Open Source on any new deps (none expected).
- [x] **[x]** Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/snyk-api-base-url-override/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive snyk-api-base-url-override`** (or project equivalent) to fold deltas into canonical specs.
