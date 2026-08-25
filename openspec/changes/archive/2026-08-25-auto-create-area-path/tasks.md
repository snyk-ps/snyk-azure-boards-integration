## 1. Configuration

- [x] 1.1 Add **`auto_create_area_path: bool = False`** to **`AzureBoardsDefaults`** (and effective merge in **`effective.py`**).
- [x] 1.2 Loader: validate boolean; add to override allowlist; reject flat root key under **`azure_boards`**.
- [x] 1.3 Unit tests: default **`false`**, override merge per org-mapping row, invalid type rejected, flat key rejected.

## 2. Azure DevOps client

- [x] 2.1 Add URL helpers for Classification Nodes (**GET**, **POST** create-or-update) under **`Areas`** with **`api-version=7.1`**.
- [x] 2.2 Implement **`get_classification_node`** and **`create_classification_node`** on **`WorkItemsClient`**.
- [x] 2.3 Unit tests with mocked HTTP: 200 exists, 404 not found, 201 created, 403 auth surfaced without secrets.

## 3. Area path ensure logic

- [x] 3.1 Add **`ensure_area_path_exists(client, org, project, full_path, cache)`** — walk segments, GET each node, POST missing children.
- [x] 3.2 Extend **`resolve_routing`**: when merged **`auto_create_area_path`** and unset path, set **`{effective_ado_project}\Snyk`** and **`area_path_source=auto_default`**.
- [x] 3.3 Call ensure from **`run.py`** before create/recreate/update paths that patch **`System.AreaPath`** when **`auto_create_area_path`** is enabled.
- [x] 3.4 Unit tests: fallback precedence, ensure for CSV/defaults/auto-default paths, per-run cache dedupes, 403 skips issue and continues run.

## 4. Documentation and samples

- [x] 4.1 **`CONFIGURATION.md`**: **`auto_create_area_path`**, **`{project}\Snyk`** fallback, optional **Create child nodes** permissions subsection.
- [x] 4.2 **`README.md`**: brief mention + link to CONFIGURATION optional permissions.
- [x] 4.3 **`data/sample-config.yaml`**: commented example with **`auto_create_area_path: true`**.

## 5. Verification

- [x] 5.1 Run full test suite; fix regressions.
- [x] 5.2 Run Snyk Code on changed Python surfaces before merge.

## 6. Archive (human step)

- [ ] 6.1 Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/auto-create-area-path/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive auto-create-area-path`** to fold deltas into canonical specs.
