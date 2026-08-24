## Why

Operators often have **one Snyk organization** whose monitored repositories belong to **multiple Azure DevOps projects**. Today **`org_mappings`** is 1:1 (Snyk org → one ADO org/project), and **`repo-mapping.csv`** only sets **area path and assignee within that single ADO project**. Repos in other ADO projects cannot be routed correctly without splitting Snyk orgs or running separate sync deployments.

Operators maintain repo-to-boards routing in **`repo-mapping.csv`** on the same Azure Files mount as **`config.yaml`**. They need each CSV row to specify the full ADO destination — **organization**, **project** (via area path), and **team area** — while **`config.yaml`** remains the 1:1 Snyk-org baseline and fallback.

## What Changes

- Extend **`repo-mapping.csv`** with a required **`ADO Organization`** column; every data row MUST supply a non-empty value after trim.
- Treat **`Area Path`** as the full ADO path **`{Project}\{Area}[\\{SubArea}…]`**; derive the effective ADO **project** from the first path segment for REST routing and **`System.AreaPath`** patching. Load fails when **Area Path** has fewer than two segments.
- When a CSV row matches, **`sync`** SHALL create/update work items in the CSV-resolved **(organization, project)** instead of the YAML-only target; when no row matches, behavior is unchanged (YAML **`organization`** / **`project`** + existing area-path fallbacks).
- Rename the optional assignee header to **`Assignee (Optional)`** in samples and documentation; loader SHALL accept **`Assignee (Optional)`** and legacy **`Assignee`** (case-insensitive).
- Group batch work-item prefetch by effective **(organization, project)** so multi-project sync within one Snyk org does not fail or mis-route.
- When a mapping row's stored ADO **organization** or **project** differs from the newly resolved CSV target, apply **routing migration**: recreate open issues (subject to existing create gates) with an audit comment on the **new** work item; for **resolved** / **ignored** issues, add an audit comment on the **existing** work item when reachable, then retarget the mapping store without recreate.
- **BREAKING:** Existing **`repo-mapping.csv`** files MUST add **`ADO Organization`** and use full **`Project\Area`** paths (not area-only values relative to the config project).
- Update **`data/sample-repo-mapping.csv`**, **`CONFIGURATION.md`**, and **`README.md`**.

## Capabilities

### New Capabilities

- *(None — extends existing **`repo-area-path-mapping`**.)*

### Modified Capabilities

- **`repo-area-path-mapping`**: CSV schema (**`ADO Organization`**, full **`Area Path`** semantics, **`Assignee (Optional)`** header), ADO target resolution from CSV, precedence with YAML fallbacks.
- **`sync-lifecycle`**: Per-issue effective ADO org/project from CSV; multi-project batch prefetch; routing-migration recreate and audit-comment policy; logging of **`ado_target_source`**.
- **`application-config`**: Document updated CSV columns and precedence; no new YAML keys (**`config.yaml`** stays 1:1).

## Impact

- **`src/sync/repo_mapping.py`** — extend **`RepoMappingMatch`** / **`ResolvedRouting`** with ADO org/project; parse area path; header alias for assignee.
- **`src/sync/run.py`** — per-issue ADO target; batch prefetch grouped by **(org, project)**; routing-migration handling and audit comments.
- **`tests/`** — CSV load, routing precedence, multi-project batch, migration recreate and audit comments.
- **`data/sample-repo-mapping.csv`**, **`CONFIGURATION.md`**, **`README.md`**
- No mapping-store schema migration (existing **`organization`** / **`project`** columns already stored per row).
