## Why

Operators need Snyk findings routed to the correct Azure DevOps **area path** (and optionally **assignee**) by repository. Today **`sync`** creates work items without setting **`System.AreaPath`**, so everything lands on the ADO project default board. Multi-team deployments maintain repo-to-area mappings in a shared CSV on the same Azure Files mount as **`config.yaml`**, with YAML fallbacks when no row matches.

## What Changes

- Load a **`repo-mapping.csv`** file (default filename beside the loaded config) at **`sync`** startup; optional path via **`azure_boards.repo_mapping_csv`** and environment variable **`REPO_MAPPING_CSV_PATH`**.
- Match CSV rows on **(Source, GitHub Org/ADO Project, Repo Name)** using existing Snyk project metadata: **`snyk_project_origin`** (mapped to CSV **Source**) and **`snyk_project_name`** parsed as **`Owner/Repo`** (Owner → scope column, Repo → repo column).
- CSV **Source** accepts only **`github`** or **`azure-repos`**. **`github`** matches all GitHub-family Snyk origins (`github`, `github-cloud-app`, `github-enterprise`, `github-server-app`). **`azure-repos`** matches **`azure-repos`** exactly.
- Add optional **`azure_boards.defaults.area_path`** as the global fallback when no CSV row matches.
- Allow **`area_path`** under **`org_mappings[].overrides`** as a per–Snyk-org / ADO-target fallback (between CSV and global default).
- Apply resolved **`System.AreaPath`** on work item **create** and **recreate**; on **update**, move area path when the resolved value differs from the current work item and add an **audit comment** stating the previous and new location (**P2-FR-9**-style).
- When a CSV row matches, optional **Assignee** column **always overrides** YAML/template assignee on **create and update** (most granular mapping wins).
- Document precedence, CSV format, origin grouping, Azure Files co-location, and ship a tracked sample CSV under **`data/sample-repo-mapping.csv`**.

## Capabilities

### New Capabilities

- **`repo-area-path-mapping`**: CSV schema, loading, origin-to-Source grouping, **`Owner/Repo`** parsing, lookup index, precedence with YAML fallbacks, optional assignee from CSV, and operator documentation for **`repo-mapping.csv`**.

### Modified Capabilities

- **`application-config`**: Schema and merge for **`area_path`** under **`defaults`** and **`org_mappings[].overrides`**, **`repo_mapping_csv`** under **`azure_boards`**, **`REPO_MAPPING_CSV_PATH`**, sample YAML and **`CONFIGURATION.md`** / **`README.md`** updates.
- **`sync-lifecycle`**: Resolve and apply area path and CSV assignee on create/recreate/update; area-path move audit comments; logging of resolution source (`csv`, `org_override`, `defaults`, `none`).

## Impact

- **`src/config/`** — models, loader, override allowlist, env wiring
- **`src/sync/`** — CSV loader/resolver, **`patch_build`**, **`run.py`** create/update/recreate paths
- **`tests/`** — unit tests for parsing, matching, precedence, patch assembly, update move + comment
- **`CONFIGURATION.md`**, **`README.md`**, **`data/sample-config.yaml`**, **`data/sample-repo-mapping.csv`**
- No new runtime dependencies expected (stdlib CSV); no mapping-store schema migration required for v1 (compare current area path via **`get_work_item`** on update when needed)
