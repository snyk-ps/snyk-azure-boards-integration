## Context

**`sync`** resolves effective area path per **`repo-area-path-mapping`** precedence (CSV → org override → defaults → unset). Patches set **`System.AreaPath`** only when non-empty. ADO rejects unknown area paths on create/update with **HTTP 400**.

Microsoft exposes area hierarchy management via [Classification Nodes](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/classification-nodes/create-or-update?view=azure-devops-rest-7.1):

- **GET** `…/_apis/wit/classificationnodes/Areas/{path}?api-version=7.1` — check existence
- **POST** `…/_apis/wit/classificationnodes/Areas/{parentPath}?api-version=7.1` with `{ "name": "Segment" }` — create child

PAT scope **`vso.work_write`** (Work Items Read & write) covers WIT metadata including area paths per Microsoft OAuth scope docs. **Object-level** permissions still apply: the user must have **Create child nodes** on the parent area node (see [Set permissions for area paths](https://learn.microsoft.com/en-us/azure/devops/organizations/security/set-permissions-access-work-tracking?view=azure-devops#set-permissions-area-path)). Creating directly under the project root area may require **Project Administrators** in some tenants — document this as an operator prerequisite.

## Goals / Non-Goals

**Goals:**

- Optional self-service area path creation aligned with existing **`defaults`** / **`overrides`** merge.
- Dedicated **Snyk** board for unmapped issues when no **`area_path`** is configured and **`auto_create_area_path`** is enabled.
- Clear docs separating base PAT scope (always required) from optional area-management permissions.

**Non-Goals:**

- Auto-create iteration paths
- Rename/delete/reparent area nodes
- Hot-reload of config mid-run
- Startup bulk sync of entire area tree
- Configurable fallback segment name in v1 (fixed **`Snyk`**; defer a separate segment config key if operators ask)

## Decisions

1. **Config shape**
   - **`auto_create_area_path`**: boolean, default **`false`**
   - Allowed under **`azure_boards.defaults`** and **`org_mappings[].overrides`** only (reject flat **`azure_boards.auto_create_area_path`** like other defaults keys)
   - Merge: per active org-mapping row, override wins over global defaults

2. **Fallback when path unset (Option A)**
   - When **`auto_create_area_path`** is **`true`** and precedence yields unset, effective path = **`{effective_ado_project}\Snyk`**
   - First segment MUST match effective ADO project (consistent with CSV **`Area Path`** rules)
   - New log value: **`area_path_source=auto_default`**
   - Fallback segment name is hardcoded to **`Snyk`** in v1

3. **Ensure algorithm** (before any patch that sets **`System.AreaPath`**)
   - Parse full path into segments after project root (e.g. **`Proj\Team\Sub`** → create **`Team`** under **`Proj`**, then **`Sub`** under **`Proj\Team`**)
   - For each segment: GET node; if **404**, POST create-or-update under parent; if **403**, surface per-issue skip with clear non-secret message
   - Cache **`(organization, project, full_path) → ensured`** for the sync run

4. **When ensure runs**
   - Only when **`auto_create_area_path`** is **`true`** for the active merged config context
   - Applies to CSV-, override-, defaults-, and auto-default-resolved paths
   - Does **not** run when effective area path is unset and setting is **`false`**

5. **Error handling**
   - **403/401** on ensure: log at WARN/ERROR, skip issue (same per-issue continue model as PATCH failures)
   - **400** on ensure (invalid name): skip issue with diagnostic
   - Do **not** fail entire sync run for one bad path

6. **Permissions documentation**
   - **`CONFIGURATION.md` § Azure DevOps PAT**: add subsection **Optional — auto-create area paths**
   - Base requirement unchanged: **Work Items: Read & write**
   - When **`auto_create_area_path: true`**: PAT user also needs **Create child nodes** = Allow on parent area nodes (Project Settings → Project configuration → Areas → Security)
   - Note: some orgs require **Project Administrators** to add top-level areas under the project node
   - Emphasize: optional; pre-creating paths and leaving setting **`false`** avoids extra permissions

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Insufficient area-path permissions → 403 on ensure | Document optional permissions; clear log message naming **Create child nodes** |
| Typo in CSV **`Area Path`** auto-creates wrong hierarchy | Operators should review CSV; consider future dry-run command |
| Race: two sync replicas create same node | ADO create-or-update is idempotent enough for duplicate POST attempts; cache per process |
| Fixed **`Snyk`** segment not desired | Document workaround via **`defaults.area_path`** + ensure; defer configurable segment |

## Migration Plan

No schema migration. Existing configs without **`auto_create_area_path`** behave unchanged. Operators opt in:

```yaml
azure_boards:
  defaults:
    auto_create_area_path: true
    # optional explicit path; ensure creates if missing:
    # area_path: "MyProject\\Snyk"
```

Per-org override example:

```yaml
org_mappings:
  - snyk_org_id: "…"
    overrides:
      auto_create_area_path: true
      area_path: "OtherProject\\Security\\Snyk"
```

## Open Questions

- *(None for v1 — Option A fixed fallback segment accepted.)*
