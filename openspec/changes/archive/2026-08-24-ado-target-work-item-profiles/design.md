## Context

**`repo-mapping-multi-ado-routing`** resolves **effective ADO `(organization, project)`** per issue from CSV or YAML. **`_sync_one_issue`** still uses batch-level **`boards.work_item_type`** and **`boards.work_item_state_*`** from **`boards_for_org_mapping()`**, which reflects the **`org_mappings`** row's baseline target — not the CSV-routed project.

Production operators mount **`config.yaml`** and **`repo-mapping.csv`** on Azure Files. PAT must cover every ADO org/project in CSV and **`ado_targets`**.

## Goals / Non-Goals

**Goals:**

- **`azure_boards.ado_targets[]`**: explicit work-item profiles keyed by **`organization`** + **`project`** (list form — ADO project names may contain spaces).
- Per-issue resolution of **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, and effective **`work_item_template`** (tags + **`json_patch`**) after ADO target is known.
- Optional CSV columns override individual taxonomy fields when non-empty (same ergonomics as assignee).
- Backward compatible: no **`ado_targets`** → current behavior; **`org_mappings[].overrides`** work-item fields still apply for the mapping's own ADO target when no **`ado_targets`** entry exists.
- Startup warm of description fields for all **`ado_targets`** entries plus existing org-mapping / defaults contexts.
- INFO logging: **`work_item_config_source`** ∈ **`csv` | `ado_target` | `org_override` | `defaults`**.

**Non-Goals:**

- Hot-reload of YAML or CSV mid-run.
- ADO process-template validation at load (invalid states fail at create/update with ADO errors).
- **`json_patch`** in CSV.
- Per-target Snyk policy (**`severity_threshold`**, **`sync_included_snyk_origins`**, etc.) — stays on **`org_mappings.overrides`** / **`defaults`**.
- Replacing **`org_mappings`** or duplicating **`snyk_org_id`** rows.
- Auto-migrating existing work items when **`ado_targets`** or CSV taxonomy changes on the same ADO target.

## Decisions

### 1. YAML shape — **`ado_targets`**

```yaml
azure_boards:
  defaults:
    work_item_type: Task
    work_item_state_active: "To Do"
    work_item_state_closed: Done
  ado_targets:
    - organization: torstencannell
      project: testProjectBug
      work_item_type: Bug
      work_item_state_active: New
      work_item_state_closed: Closed
      work_item_description_field: Microsoft.VSTS.TCM.ReproSteps
      work_item_template:
        tags: [Snyk, Security]
    - organization: torstencannell
      project: "test Project Spaces"
      work_item_type: Task
      work_item_state_active: "To Do"
      work_item_state_closed: Done
```

- Allowed keys on each entry: **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`** (**`tags`**, **`json_patch`**).
- **`organization`** and **`project`** required on each entry; non-empty after trim.
- Duplicate **`(organization, project)`** after trim → load fails.
- Omitted taxonomy keys on an entry inherit via the precedence ladder (entry need not repeat every field).

**Alternatives:** String composite key **`org/project`** (rejected — project names contain spaces and slashes).

### 2. Work item taxonomy precedence (per field)

After **`resolve_routing()`** yields **`effective_org`** / **`effective_proj`**:

| Priority | Source | Condition |
| -------- | ------ | --------- |
| 1 | CSV optional column | Row matches; cell non-empty after trim |
| 2 | **`ado_targets[(org, project)]`** | Entry exists; field set on entry |
| 3 | **`org_mappings[].overrides`** | Active mapping row's **`(organization, project)`** equals effective target; field in overrides |
| 4 | **`defaults`** | Baseline |

Step 3 does **not** apply when CSV routes to a **different** project than the org-mapping row.

Snyk-side policy remains org-mapping merge only.

**Alternatives:** CSV references **`ado_targets`** by name (rejected — implicit lookup by destination is simpler for operators).

### 3. CSV optional columns

| Header | Alias(es) | Semantics |
| ------ | --------- | --------- |
| **`Work Item Type (Optional)`** | **`Work Item Type`** | WIT **`$type`** on create |
| **`Active State (Optional)`** | **`Active State`** | **`System.State`** for active/open paths |
| **`Closed State (Optional)`** | **`Closed State`** | **`System.State`** on close path |
| **`Description Field (Optional)`** | **`Description Field`** | Explicit field ref; empty → fall through |
| **`Tags (Optional)`** | **`Tags`** | Semicolon-separated; merged with profile/template tags |

### 4. Template and tags merge

- Base template: global **`work_item_template`** → **`defaults.work_item_template`** → **`ado_targets`** / org-override template.
- CSV **`Tags (Optional)`** **merges** (profile tags first, then CSV additions; dedupe preserving order).
- CSV does not supply **`json_patch`**.

### 5. Sync integration

- Add **`EffectiveWorkItemConfig`** (or extend **`ResolvedRouting`**) with type, states, description field config, template, **`work_item_config_source`**.
- **`_sync_one_issue`**: WIT mutations use **`effective_wit.*`**; **`boards`** retained for Snyk policy gates.
- Reopen, routing migration, and missing-WI recreate use the same per-issue effective config.

**Alternatives:** Per-issue clone of full **`AzureBoardsConfig`** (rejected — over-broad; only taxonomy fields vary).

### 6. Startup warm

**`warm_description_fields_for_sync`** resolves description fields for every **`ado_targets`** entry, every **`org_mappings`** row, and group-scoped **`defaults`** when applicable.

### 7. Backward compatibility

- Missing or empty **`ado_targets`**: unchanged behavior.
- **`org_mappings[].overrides.work_item_*`**: valid fallback when no explicit **`ado_targets`** row for same **`(organization, project)`**. Explicit **`ado_targets`** wins over org-mapping overrides for work-item taxonomy.

## Risks / Trade-offs

- **[Risk]** Operator omits **`ado_targets`** for a CSV-routed project → falls back to defaults; may repeat ADO 400 failures.
  **→ Mitigation:** Document requirement; sample config shows multi-target pattern.

- **[Risk]** CSV typo in state name → ADO 400 at runtime.
  **→ Mitigation:** Same as today; optional follow-up for ADO error body in logs.

- **[Risk]** Tags merge semantics surprise operators expecting CSV to replace all tags.
  **→ Mitigation:** Document merge behavior in **`CONFIGURATION.md`**.

- **[Risk]** Description warm increases startup ADO field-list calls.
  **→ Mitigation:** One call per distinct **`ado_targets`** entry; typical cardinality is small.

## Migration Plan

- **Non-breaking** additive YAML and CSV columns.
- Operators with multi-project CSV routing should add **`ado_targets`** for each distinct ADO **`(organization, project)`** in CSV **Area Path** first segments and org-mapping baseline.
- Container App restart/revision reloads config on next **`sync`**.

## Open Questions

- *(None for v1 — precedence and CSV tags merge confirmed with operator.)*
