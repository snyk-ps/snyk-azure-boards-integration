## Context

**`sync`** creates and updates Azure DevOps work items via JSON Patch in **`patch_build.build_create_patch`** / **`build_update_patch`**. Today patches set **`System.Title`**, the effective description field, **`System.State`**, **`System.Tags`**, and merged template **`json_patch`** — but never **`System.AreaPath`**. Work items therefore remain on each ADO project's default area.

Operators already configure ADO routing via **`azure_boards.defaults`** and **`org_mappings`**, and persist **`snyk_project_name`** / **`snyk_project_origin`** on mapping rows (from the Snyk Projects API). For Git-integrated targets, Snyk project **`attributes.name`** is typically **`Owner/Repo`**, where **Owner** is the GitHub organization or Azure DevOps project name.

Production deployments mount operator YAML on **Azure Files** (see **`azure-platform`**). Repo-level mappings live in a sibling **`repo-mapping.csv`** on the same share.

## Goals / Non-Goals

**Goals:**

- Load **`repo-mapping.csv`** once per **`sync`** run (path from config, default beside loaded YAML, overridable via **`REPO_MAPPING_CSV_PATH`**).
- Match rows on **(Source, scope, repo)** using **`snyk_project_origin`** → CSV **Source** (`github` | `azure-repos`) and **`snyk_project_name`** split on the first **`/`**.
- Resolve effective **area path** with precedence: **CSV row** → **`org_mappings[].overrides.area_path`** → **`defaults.area_path`** → omit (ADO default).
- Patch **`/fields/System.AreaPath`** on create/recreate; on update when resolved path differs from current work item, patch and add audit comment (**P2-FR-9**).
- When a CSV row matches, optional **Assignee** column **always overrides** YAML/template assignee on create **and** update.
- Document CSV format, origin grouping, precedence, Azure Files layout; ship **`data/sample-repo-mapping.csv`**.

**Non-Goals:**

- Hot-reload of CSV or YAML mid-run.
- ADO area-path taxonomy validation at load time (invalid paths fail at PATCH with ADO error).
- Extending Snyk Projects API parsing beyond existing **`name`** and **`origin`**.
- Persisting resolved area path on the mapping store in v1 (read current path from **`get_work_item`** when comparing on update).
- CSV **Source** values beyond **`github`** and **`azure-repos`** in v1.

## Decisions

1. **CSV filename and config key**  
   **Decision:** **`azure_boards.repo_mapping_csv`**; when omitted, default resolved path is **`repo-mapping.csv`** in the **directory of the loaded YAML config file**. Environment **`REPO_MAPPING_CSV_PATH`** participates in **defaults → YAML → env → CLI** precedence (same as other path settings).  
   **Alternatives:** Hard-coded absolute path only (rejected — breaks local dev).

2. **CSV schema (headers)**  
   **Decision:** Required columns (case-insensitive header match after strip): **`Source`**, **`GitHub Org/ADO Project`**, **`Repo Name`**, **`Area Path`**. Optional: **`Assignee`**. Extra columns ignored. Duplicate **(Source, scope, repo)** keys after normalization → load fails.  
   **Alternatives:** Machine-only snake_case headers (rejected — operator-facing names match customer spreadsheets).

3. **Source ↔ Snyk origin grouping**  
   **Decision:** CSV **Source** accepts only **`github`** or **`azure-repos`** (case-sensitive after trim). Map Snyk **`snyk_project_origin`** to CSV Source:
   - **`github`**, **`github-cloud-app`**, **`github-enterprise`**, **`github-server-app`** → **`github`**
   - **`azure-repos`** → **`azure-repos`**
   - Any other origin → no CSV match (YAML fallbacks only).  
   **Alternatives:** Per-variant CSV rows (rejected by operator).

4. **Owner/Repo parsing**  
   **Decision:** Split **`snyk_project_name`** on the **first** **`/`** only → **`(owner, repo)`**. Trim each segment. **Scope** column matches **`owner`**; **Repo Name** column matches **`repo`**. If no **`/`**, treat full name as **`repo`** with empty **`owner`** (document edge case; most Git/ADO targets use **`owner/repo`**). Matching is **case-sensitive** after trim on all three key parts.  
   **Alternatives:** Case-insensitive match (rejected — consistent with org-config generator).

5. **Area path precedence**  
   **Decision:** CSV match → **`org_mappings[].overrides.area_path`** → **`defaults.area_path`** → do not emit **`System.AreaPath`** patch.  
   **Alternatives:** Org override beats CSV (rejected — CSV is most granular).

6. **Assignee precedence**  
   **Decision:** When CSV row matches and **Assignee** is non-empty after trim, **`System.AssignedTo`** from CSV wins on **create and update**, overriding **`work_item_template`** **`json_patch`**. When CSV row matches but Assignee empty, use normal template merge. When no CSV match, existing template rules unchanged.  
   **Alternatives:** Template wins over CSV (rejected by operator).

7. **Patch assembly**  
   **Decision:** Extend **`build_create_patch`** / **`build_update_patch`** with optional **`area_path: str | None`** and **`assigned_to: str | None`**. Emit **`add`/`replace`** on **`/fields/System.AreaPath`** and **`/fields/System.AssignedTo`** when non-empty. CSV assignee bypasses **`filter_assignee_from_create_patch`** when supplied from resolver.  
   **Alternatives:** Only **`json_patch`** in template (rejected — CSV assignee must override template).

8. **Update path area move**  
   **Decision:** On update/recreate flows that PATCH an existing work item, when resolved **`area_path`** is non-empty and differs from **`fields['System.AreaPath']`** on the current work item (from **`get_work_item`** or normalized record already fetched), include area path in update patch and call **`add_work_item_comment`** with text:  
   `Snyk sync moved work item area path from '{previous}' to '{new}'.`  
   Empty/missing previous path → use **`(project default)`** or **`(unset)`** in comment text.  
   **Alternatives:** Store last area path on mapping row (deferred — avoids schema migration).

9. **Module layout**  
   **Decision:** New **`src/sync/repo_mapping.py`** (or **`src/config/repo_mapping.py`**) for CSV load, origin grouping constants, **`parse_owner_repo(name)`**, **`RepoMappingIndex.lookup(...)`**, and **`resolve_routing(area_path, assignee, source)`** result type. **`run_sync`** loads index at startup after config merge.  
   **Alternatives:** Inline in **`run.py`** only (rejected — testability).

10. **Logging**  
    **Decision:** At INFO when applying routing for a create/update, log non-secret fields: **`area_path_source`** ∈ **`csv` | `org_override` | `defaults` | `none`**, optional CSV row key, whether assignee came from CSV.  
    **Alternatives:** Silent (rejected — operator debugging).

11. **Flat config keys**  
    **Decision:** Reject **`azure_boards.area_path`** at root (same as other **`defaults`**-only keys). **`repo_mapping_csv`** is a direct child of **`azure_boards`** (like routing metadata, not a secret).

## Risks / Trade-offs

- **[Risk]** **`snyk_project_name`** not in **`Owner/Repo`** form → CSV miss, YAML fallback only.  
  **→ Mitigation:** Document in **`CONFIGURATION.md`**; log **`area_path_source=none`** at INFO when no path resolved.

- **[Risk]** Extra **`get_work_item`** reads on update when comparing area path.  
  **→ Mitigation:** Reuse work item record when update path already fetched item; cache per work item id within one issue handler invocation.

- **[Risk]** Invalid **`Area Path`** string → ADO 400 on create/update.  
  **→ Mitigation:** Document valid path format; surface ADO error in logs without secrets.

- **[Risk]** CSV edited between runs moves many items → comment noise.  
  **→ Mitigation:** Expected operator behavior; comments are audit trail per **P2-FR-9**.

- **[Risk]** Assignee identity string invalid for ADO → PATCH failure.  
  **→ Mitigation:** Same as existing template assignee behavior; document display-name/email format.

## Migration Plan

No mapping-store migration. Existing configs without **`area_path`** or CSV behave as today (ADO project default area). Operators add **`repo-mapping.csv`** beside **`config.yaml`** on Azure Files and optionally set **`defaults.area_path`**. Container App **restart/revision** reloads CSV at next **`sync`**.

## Open Questions

- *(None for v1.)*
