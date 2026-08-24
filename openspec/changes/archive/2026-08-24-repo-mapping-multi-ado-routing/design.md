## Context

**`sync`** in **`org_mappings`** mode lists all issues for one **`snyk_org_id`** and passes a single **`ado_org`** / **`ado_proj`** into **`_run_sync_batch`**. **`resolve_routing()`** today returns only **area path** and **assignee**; ADO REST paths always use the YAML target.

**`repo-mapping.csv`** match key stays **(Source, GitHub Org/ADO Project, Repo Name)** — the **GitHub Org/ADO Project** column remains the **Snyk-side owner** for lookup, not the ADO routing destination.

ADO **`System.AreaPath`** values are project-scoped. Creating a work item in **`ProjectB`** requires REST calls against **`.../ProjectB/...`**, not setting **`ProjectB\Team`** on a work item in **`ProjectA`**.

Production deployments mount operator YAML and **`repo-mapping.csv`** on **Azure Files** (see **`azure-platform`**). The PAT must have access to every ADO organization and project referenced in the CSV.

## Goals / Non-Goals

**Goals:**

- Keep **`azure_boards.org_mappings`** 1:1: one row per Snyk org, one default ADO org/project baseline.
- When a CSV row matches, route the issue to CSV **ADO Organization** + ADO **project** derived from the first segment of **Area Path**.
- **Area Path** column carries the full path written to **`System.AreaPath`** (e.g. **`PaymentsProject\TeamA`**); load rejects rows with fewer than two path segments.
- Require non-empty **ADO Organization** on every CSV data row.
- Optional **`Assignee (Optional)`** column; accept legacy **`Assignee`** header.
- YAML fallbacks unchanged when no CSV match: config org/project + **`overrides.area_path`** / **`defaults.area_path`**.
- Self-heal when CSV routing changes ADO target for an already-mapped issue, with **P2-FR-9** audit comments on work items.
- Batch prefetch work items grouped by effective **(organization, project)**.

**Non-Goals:**

- Multiple **`org_mappings`** rows for the same **`snyk_org_id`** (still unsupported).
- Hot-reload of CSV mid-run.
- ADO taxonomy validation at CSV load (invalid paths fail at PATCH time).
- Separate **`ADO Project`** column (project is encoded in **Area Path** first segment).
- Empty **ADO Organization** fallback to config (column is required on every row).

## Decisions

1. **CSV schema (headers)**  
   **Decision:** Required (case-insensitive after strip): **`Source`**, **`GitHub Org/ADO Project`**, **`Repo Name`**, **`ADO Organization`**, **`Area Path`**. Optional: **`Assignee (Optional)`** (alias: **`Assignee`**). Extra columns ignored. Duplicate **(Source, scope, repo)** → load fails.  
   **Alternatives:** Separate **`ADO Project`** column (rejected — operator requested project in area path).

2. **ADO Organization column**  
   **Decision:** Required header **and** required non-empty cell on every data row. Load fails when the column is missing or any row has an empty value after trim.  
   **Alternatives:** Empty → config org fallback (rejected by operator).

3. **ADO project from Area Path**  
   **Decision:** Split **Area Path** on the **first** `\` (backslash). First segment = **`ado_project`** for REST routing; full string = **`System.AreaPath`**. Require at least **two** segments after trim at CSV load.  
   **Alternatives:** Area-only paths relative to config project (rejected — breaks multi-project routing).

4. **Routing precedence**  
   **Decision:** When CSV row matches:
   - **ADO org/project:** CSV (**ADO Organization** + first **Area Path** segment)
   - **Area path:** full CSV **Area Path**
   - **Assignee:** non-empty **Assignee (Optional)** → wins over template  
   When no CSV match:
   - **ADO org/project:** YAML (**unchanged**)
   - **Area path:** org override → defaults → omit (**unchanged**)

5. **Per-issue ADO target in sync**  
   **Decision:** Extend **`ResolvedRouting`** with **`organization`**, **`project`**, **`ado_target_source`** ∈ **`csv` | `config`**. **`_sync_one_issue`** uses resolved org/project for all WIT calls and mapping-store upserts.  
   **Alternatives:** Keep batch-level org/project only (rejected — cannot reach other projects).

6. **Batch prefetch across projects**  
   **Decision:** Before the issue loop, partition mapped work item ids by **stored** **(organization, project)** on each mapping row (fallback to config target when row missing). Call **`batch_get_work_items`** once per partition using **`errorPolicy=Omit`**. Per-issue handler uses **resolved** target for mutations; cache lookup uses stored org/project for the row's work item id.  
   **Alternatives:** Single batch at config project only (rejected — 404 / wrong project).

7. **Routing migration (stored target ≠ resolved target)**  
   **Decision:** If mapping row exists and stored **`organization`** / **`project`** differ from newly resolved CSV target:
   - **Derived status `open`:** Recreate in new target (existing gates: **`create_new_work_items`**, origin allowlist, **`create_only_when_fix_available`**). **Required:** audit comment on the **new** work item documenting prior **`work_item_id`**, old **(org, project)**, and new **(org, project)**.
   - **`resolved` / `ignored`:** Do not recreate. **Required:** when prior work item is reachable in the **old** stored target, audit comment on that work item documenting mapping retarget; then upsert store with new **`organization`** / **`project`**; keep **`work_item_id`**.
   - **404 on prior work item (close path):** Update store only; structured log; no ADO comment.  
   **Alternatives:** Always recreate (rejected — unnecessary noise for closed items).

8. **Assignee header rename**  
   **Decision:** Normalize headers **`assignee (optional)`** and **`assignee`** to the same optional assignee field. Samples and docs use **`Assignee (Optional)`** only.  
   **Alternatives:** Break legacy **`Assignee`** header (rejected — migration friction).

9. **Logging**  
   **Decision:** Log **`ado_target_source`**, effective **`organization`**, **`project`**, **`area_path_source`** at INFO on create/update (no secrets).  
   **Alternatives:** Silent routing (rejected — operator debugging).

10. **Module layout**  
    **Decision:** Extend **`src/sync/repo_mapping.py`** with **`parse_area_path_for_project(path)`**, ADO target fields on **`RepoMappingMatch`** / **`ResolvedRouting`**, and updated **`resolve_routing(..., config_org, config_project)`**. Routing-migration helpers and audit comment formatters live in **`src/sync/run.py`** or a small **`src/sync/routing_migration.py`** if **`run.py`** grows too large.  
    **Alternatives:** New top-level package (rejected — scope fits sync).

## Risks / Trade-offs

- **[Risk]** Operator typo in **Area Path** first segment → work items created in wrong project.  
  **→ Mitigation:** Document format; two-segment load validation; clear ADO errors in logs.

- **[Risk]** CSV routing change moves many open issues → recreate burst + comment noise.  
  **→ Mitigation:** Expected migration behavior; structured audit logs.

- **[Risk]** Multi-project batch prefetch increases ADO list calls.  
  **→ Mitigation:** One batch per distinct **(org, project)** per run; typical cardinality is small.

- **[Risk]** PAT scope must cover all ADO orgs/projects referenced in CSV.  
  **→ Mitigation:** Document in **`CONFIGURATION.md`**.

- **[Risk]** Routing migration comment on old work item fails (permissions / 404).  
  **→ Mitigation:** Best-effort comment; proceed with store retarget; log failure without aborting run.

## Migration Plan

- Existing **`repo-mapping.csv`** files **must** add **`ADO Organization`** (non-empty per row) and expand **Area Path** to **`{Project}\{Area}`** form.
- Legacy **`Assignee`** header continues to work; operators should adopt **`Assignee (Optional)`** in new files.
- No mapping-store schema change; Container App **restart/revision** reloads CSV on next **`sync`**.
- Operators should verify PAT access to all ADO orgs/projects in the CSV before rollout.

## Open Questions

- *(None — operator confirmed required ADO Organization, routing migration with audit comments, and two-segment Area Path validation.)*
