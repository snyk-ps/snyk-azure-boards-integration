## 1. Configuration model and loader

- [x] 1.1 Add **`work_item_description_appendix: str = ""`** to **`AzureBoardsDefaults`** in **`src/config/models.py`**; plumb through merged **`AzureBoardsConfig`** / org-mapping resolution so **`sync`** can read the effective value per routing context.
- [x] 1.2 Load and validate under **`azure_boards.defaults`** and **`org_mappings[].overrides`**: string only; clear **`ConfigError`** on wrong type; extend override key allowlist per change spec.
- [x] 1.3 Unit tests in **`tests/test_config.py`** (defaults, per-mapping override, invalid type, optional omission).

## 2. Description assembly and sync

- [x] 2.1 Append effective appendix in **`src/sync/issue_content.py`** (or immediately after **`build_system_description`** in **`run.py`**) per **`design.md`**: strip; if non-empty, append **`"\n\n"` + appendix** before existing length truncation.
- [x] 2.2 Wire effective appendix from merged boards config in **`src/sync/run.py`** for all code paths that build description (single-target and **`org_mappings`**).
- [x] 2.3 Tests in **`tests/test_sync_issue_content.py`** and/or **`tests/test_sync_patch_build.py`**: appendix present in final plain/HTML output; empty/whitespace-only; escaping of **`&` `<` `>`** in appendix; truncation when combined body exceeds limit.

## 3. Documentation and samples

- [x] 3.1 Update **`README.md`**: document **`work_item_description_appendix`** under **`azure_boards.defaults`** and **`org_mappings[].overrides`** in configuration tables or parameter list.
- [x] 3.2 Update **`data/sample-config.yaml`** and other tracked **`data/*.yaml`** examples with a **commented** optional **`work_item_description_appendix`** example (placeholder URLs only; no secrets).
- [x] 3.3 Run **`pytest`**; run **Snyk Code** / Open Source checks per repo guidelines before merge.
