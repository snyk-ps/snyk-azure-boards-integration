## 1. Snyk app URL helpers

- [x] 1.1 Add `DEFAULT_APP_ORIGIN = "https://app.snyk.io"` and `normalize_app_origin()` in `src/snyk/` (reuse or generalize existing origin normalization).
- [x] 1.2 Unit tests for default origin, trailing-slash normalization, and HTTPS validation edge cases.

## 2. Configuration layer

- [x] 2.1 Extend `SnykConfig` / loader defaults with `app_base_url` default `https://app.snyk.io`.
- [x] 2.2 Apply `SNYK_APP_BASE_URL` in `_apply_env_overrides`; add `cli_snyk_app_base_url` to `load_app_config`.
- [x] 2.3 Validate HTTPS + non-empty at config resolution; unit tests for precedence (YAML/env/CLI) and rejection cases.

## 3. Sync wiring

- [x] 3.1 Add `--snyk-app-base-url` to `sync`; pass merged `app_base_url` into description/link assembly (`run.py` → `issue_content.py`).
- [x] 3.2 Update `snyk_ui_issue_url` to accept `app_base_url`; preserve path encoding behavior.
- [x] 3.3 Update `_ado_system_description_html` (and callers) so "Open in Snyk" block detection works with configured app origin, not only `app.snyk.io`.
- [x] 3.4 Update `tests/test_sync_issue_content.py`, `tests/test_sync_patch_build.py`, and any integration tests that assert full URLs.

## 4. Documentation

- [x] 4.1 **CONFIGURATION.md**: document `snyk.app_base_url`, `SNYK_APP_BASE_URL`, `--snyk-app-base-url`, default **SNYK-US-01**, link to [regional hosting URLs](https://docs.snyk.io/snyk-data-and-governance/regional-hosting-and-data-residency#regional-urls), note pairing with `SNYK_API_BASE_URL`.
- [x] 4.2 **README.md**: add to Configuration parameter table / Deployment (regional tenants); optional Troubleshooting row for "Open in Snyk link goes to wrong region".
- [x] 4.3 **data/sample-config.yaml**: commented `# app_base_url: https://app.snyk.io` example under `snyk`.

## 5. Verification and archive prep

- [x] 5.1 Run unit tests; Snyk Code on changed Python (no new dependencies expected).
- [x] **[x]** Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/snyk-app-base-url-override/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive snyk-app-base-url-override`** (or project equivalent) to fold deltas into canonical specs.
