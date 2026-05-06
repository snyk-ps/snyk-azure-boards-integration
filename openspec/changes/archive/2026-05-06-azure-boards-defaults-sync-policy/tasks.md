## 1. Configuration loader and models

- [x] 1.1 Move **`create_new_work_items`**, **`organization`**, **`project`**, **`severity_threshold`**, and new keys (**`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**) under **`azure_boards.defaults`** in **`AppConfig`** / loader; reject legacy **`azure_boards.*`** flat keys and **`snyk.severity_threshold`** with clear errors.
- [x] 1.2 Extend **`org_mappings[].overrides`** merge to include all new **`defaults`** keys; add validation for enums/timestamps per **`application-config`** delta.
- [x] 1.3 Update **`tests/test_config.py`** (and related) for new schema and rejection cases.

## 2. Snyk Issues client — list URL encoding

- [x] 2.1 Implement **`effective_severity_level`** as **one** comma-separated query value (e.g. **`high,critical`** for threshold **`high`**) in **`src/snyk/client.py`**; keep **`links.next`** pagination unchanged.
- [x] 2.2 Add tests asserting first-page URLs match **`effective_severity_level=high%2Ccritical`** for threshold-derived levels; update existing tests that expected repeated keys.

## 3. Fetch and sync — filters and policy

- [x] 3.1 Wire merged **`severity_threshold`** from **`azure_boards.defaults`** into group/org **`fetch`** and **`sync`** list params (remove **`config.snyk.severity_threshold`** usage).
- [x] 3.2 Apply **`issues_sync_from`** (**`historical`** vs timestamp) and **`create_only_when_fix_available`** per **`design.md`** and Issues OpenAPI (document chosen query parameter names in **`design.md`** if adjusted during implementation).
- [x] 3.3 Implement **`reopen_work_item_policy`** in **`src/sync/`** with audit comments, hyperlink rules, and Azure **404** fallback per **`sync-lifecycle`** delta.
- [x] 3.4 Add or extend **`tests/test_sync_lifecycle.py`** (and integration-style client tests) for reopen branches and list filters.

## 4. Mapping store

- [x] 4.1 Add **`snyk_project_name`** and **`snyk_project_origin`** columns to SQLite schema (**`ALTER TABLE`** migration path) and **`MappingRow`** / upsert API.
- [x] 4.2 Unit tests for schema apply and upsert/read round-trip.

## 5. Project metadata and enrichment

- [x] 5.1 Implement **`GET /orgs/{org_id}/projects/{project_id}`** in **`src/snyk/`** (reuse client patterns); call during sync when metadata missing per **`design.md`**.
- [x] 5.2 Persist display name and origin on mapping upsert; use for title and description per **`sync-lifecycle`** delta.

## 6. Work item content

- [x] 6.1 Extend **`issue_content`** / HTML assembly: **code** **`sourceLocation`** (file + lines) from **`data/sample_coord.local.json`** shape; render **P2-FR-5.4** URL as **`<a href>`** with escaping.
- [x] 6.2 Tests for description HTML containing anchor **`href`** and location lines.

## 7. Documentation and samples

- [x] 7.1 Update **`README.md`**: configuration tables, **`azure_boards.defaults`** keys, **`org_mappings` overrides**, mapping DB column reference.
- [x] 7.2 Update **`data/sample-config.yaml`** with richer commented examples (defaults vs **`org_mappings.overrides`**); align other **`data/*.yaml`** samples with new schema (**no secrets**).
- [x] 7.3 Run **`pytest`**; run **Snyk Code** / Open Source policy checks per repo guidelines before merge.
