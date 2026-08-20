## 1. Configuration schema and loading

- [ ] 1.1 Add optional **`area_path: str | None`** to **`AzureBoardsDefaults`** / merged **`AzureBoardsConfig`**; plumb through **`boards_for_org_mapping`** and org override allowlist.
- [ ] 1.2 Add **`repo_mapping_csv: str | None`** under **`azure_boards`**; resolve default **`repo-mapping.csv`** beside loaded YAML config directory; wire **`REPO_MAPPING_CSV_PATH`** env in loader precedence.
- [ ] 1.3 Reject flat **`azure_boards.area_path`** at root; reject non-string **`area_path`** / **`repo_mapping_csv`**; unit tests for load/merge/rejection paths.

## 2. Repo mapping CSV module

- [ ] 2.1 Implement **`src/sync/repo_mapping.py`** (or equivalent): CSV load with required headers, duplicate-key detection, invalid **Source** validation (**`github`** | **`azure-repos`** only).
- [ ] 2.2 Implement **`snyk_origin_to_csv_source(origin)`** grouping GitHub-family origins → **`github`**; **`parse_owner_repo(name)`**; **`RepoMappingIndex.lookup(source, scope, repo)`** returning area path + assignee.
- [ ] 2.3 Implement **`resolve_routing(...)`** applying precedence CSV → org override → defaults; return source tag (**`csv` | `org_override` | `defaults` | `none`**) for logging.
- [ ] 2.4 Unit tests: origin grouping, owner/repo parsing, precedence, duplicate rows, missing file, invalid Source.

## 3. Patch assembly

- [ ] 3.1 Extend **`build_create_patch`** / **`build_update_patch`** with optional **`area_path`** and **`assigned_to`**; emit **`System.AreaPath`** and CSV **`System.AssignedTo`** when non-empty.
- [ ] 3.2 Adjust assignee filtering so CSV-supplied assignee is not stripped on create.
- [ ] 3.3 Unit tests in **`tests/test_sync_patch_build.py`** for area path and CSV assignee on create/update patches.

## 4. Sync wiring

- [ ] 4.1 Load repo mapping index at **`run_sync`** startup; fail fast on CSV errors before issue loop.
- [ ] 4.2 Pass resolved area path + assignee into create and recreate paths in **`run.py`**.
- [ ] 4.3 On update: compare effective area path to current **`System.AreaPath`** (from work item fields); patch when different; add audit comment with previous and new path; apply CSV assignee on update when set.
- [ ] 4.4 Log **`area_path_source`** at INFO on create/update (no secrets).
- [ ] 4.5 Integration-style unit tests: create with CSV path, update move + comment, CSV assignee overrides template, YAML fallback when no CSV match.

## 5. Documentation and samples

- [ ] 5.1 Add **`data/sample-repo-mapping.csv`** with placeholder rows (github + azure-repos examples).
- [ ] 5.2 Update **`data/sample-config.yaml`** with commented **`area_path`**, **`repo_mapping_csv`**, org **`overrides.area_path`**, pointer to sample CSV.
- [ ] 5.3 Update **`CONFIGURATION.md`**: column definitions, Source semantics, origin grouping table, Owner/Repo parsing, precedence, Azure Files co-location, update move + comment behavior, **`REPO_MAPPING_CSV_PATH`**.
- [ ] 5.4 Update **`README.md`** Configuration and Deployment sections per **`application-config`** delta ( **`repo-mapping.csv`**, **`area_path`**, env var).

## 6. Verification

- [ ] 6.1 Run full test suite; fix regressions.
- [ ] 6.2 Run Snyk Code on changed Python surfaces before merge.

## 7. Archive (human step)

- [ ] 7.1 Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/repo-to-area-path-routing/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive repo-to-area-path-routing`** (or project equivalent) to fold deltas into canonical specs.
