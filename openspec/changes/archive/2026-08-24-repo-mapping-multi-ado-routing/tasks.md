## 1. Repo mapping CSV module

- [x] 1.1 Add **`parse_area_path_for_project(path)`** — split on first `\`, validate ≥ two segments; return **`(project, full_path)`**.
- [x] 1.2 Extend **`RepoMappingMatch`** with **`organization`**, **`project`**; extend **`ResolvedRouting`** with **`organization`**, **`project`**, **`ado_target_source`**.
- [x] 1.3 Update CSV loader: required **`ADO Organization`** header and non-empty cells; accept **`Assignee (Optional)`** and legacy **`Assignee`** headers.
- [x] 1.4 Extend **`resolve_routing()`** to accept config org/project fallbacks; CSV match supplies ADO org + project from area path; no match uses config target.
- [x] 1.5 Unit tests in **`tests/test_repo_mapping.py`**: required org, area path segments, header aliases, ADO target resolution, YAML fallback unchanged.

## 2. Sync orchestration — per-issue ADO target

- [x] 2.1 Refactor **`_sync_one_issue`** to use resolved **`organization`** / **`project`** for all WIT calls and store upserts.
- [x] 2.2 Refactor batch prefetch in **`_run_sync_batch`** to partition by stored **(organization, project)**; merge caches per partition.
- [x] 2.3 Log **`ado_target_source`**, **`area_path_source`** at INFO on create/update (no secrets).
- [x] 2.4 Unit tests: multi-project create routing, unmatched issue uses YAML target, batch prefetch partitioning.

## 3. Routing migration

- [x] 3.1 Detect stored ADO target ≠ resolved target before routine update/create paths.
- [x] 3.2 **Open** issues: recreate in new target (existing gates); audit comment on **new** work item (prior id, old/new org/project).
- [x] 3.3 **Resolved/ignored** issues: audit comment on existing work item in **stored** target when reachable; upsert store with new org/project; 404 → store-only update + structured log.
- [x] 3.4 Unit tests: open migration recreate + comment, resolved migration comment, 404 close-path skip.

## 4. Documentation and samples

- [x] 4.1 Update **`data/sample-repo-mapping.csv`**: **`ADO Organization`**, full **`Project\Area`** paths, **`Assignee (Optional)`** header.
- [x] 4.2 Update **`CONFIGURATION.md`**: column definitions, multi-project within one Snyk org, CSV migration, PAT scope note.
- [x] 4.3 Update **`README.md`**: one **`org_mappings`** row + CSV multi-project pattern.

## 5. Verification

- [x] 5.1 Run full test suite; fix regressions.
- [ ] 5.2 Run Snyk Code on changed Python surfaces before merge.

## 6. Archive (human step)

- [ ] 6.1 Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/repo-mapping-multi-ado-routing/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive repo-mapping-multi-ado-routing`** to fold deltas into canonical specs.
