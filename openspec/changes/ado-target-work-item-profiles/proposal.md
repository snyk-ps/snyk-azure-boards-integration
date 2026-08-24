## Why

**`repo-mapping.csv`** can route issues from one Snyk org to **multiple Azure DevOps projects**, but work item **type**, **states**, **description field**, and **tags** still come from a single merged **`defaults`** + **`org_mappings[].overrides`** profile for the whole batch. When CSV sends repos to a project whose process template differs from the org-mapping baseline (for example **Task / To Do** vs **Bug / New**), creates fail with ADO **HTTP 400** even though routing is correct.

Operators need **per ADO target** work-item profiles in YAML (IaC-friendly, beside **`config.yaml`** on Azure Files), with optional **per-repo overrides** in CSV — the same pattern already used for **assignee**.

## What Changes

- Add optional **`azure_boards.ado_targets`**: a list of **`(organization, project)`** entries, each carrying work-item taxonomy fields (**`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, **`work_item_template`**) that apply when **`sync`** creates or updates work items in that ADO target.
- Resolve **effective work item config per issue** after ADO target resolution (CSV or YAML), using precedence:
  1. Non-empty optional **CSV** columns (per field)
  2. Matching **`ado_targets`** entry for effective **`(organization, project)`**
  3. **`org_mappings[].overrides`** work-item fields **only when** effective target equals that mapping row's **`(organization, project)`**
  4. **`azure_boards.defaults`**
- Extend **`repo-mapping.csv`** with optional columns: **`Work Item Type (Optional)`**, **`Active State (Optional)`**, **`Closed State (Optional)`**, **`Description Field (Optional)`**, **`Tags (Optional)`** (legacy-friendly header aliases documented in design).
- Warm description-field resolution at startup for every distinct **`ado_targets`** entry and every effective per-issue context used in the run.
- Log **`work_item_config_source`** (and effective type / active state) at INFO alongside existing **`ado_target_source`** routing logs.
- Update **`data/sample-config.yaml`**, **`data/sample-repo-mapping.csv`**, **`CONFIGURATION.md`**, and **`README.md`**.

**Non-breaking:** Existing configs without **`ado_targets`** behave unchanged. Empty optional CSV columns are ignored. **`org_mappings[].overrides`** work-item fields remain valid as fallback for the mapping's own ADO target.

## Capabilities

### New Capabilities

- *(None — extends existing capabilities.)*

### Modified Capabilities

- **`application-config`**: **`ado_targets`** schema, loader validation, merge/precedence rules, sample config and documentation.
- **`sync-lifecycle`**: Per-issue effective work item type/states/description field/template; startup warm for all ADO target profiles; create/update/reopen paths use per-issue config (not batch-level **`boards`** only).
- **`repo-area-path-mapping`**: Optional CSV columns for work-item taxonomy overrides; precedence integrated with **`ado_targets`**.

## Impact

- **`src/config/`** — load and validate **`ado_targets`**; extend **`AppConfig`** / models.
- **`src/sync/effective.py`** — **`resolve_effective_work_item_config(...)`** (or equivalent) with precedence ladder.
- **`src/sync/repo_mapping.py`** — parse optional CSV taxonomy columns; extend **`RepoMappingMatch`** / **`ResolvedRouting`**.
- **`src/sync/run.py`** — use per-issue work item config for patches, WIT **`$type`**, description resolution, and logging.
- **`src/sync/description_field.py`** — warm all **`ado_targets`** contexts at startup.
- **`tests/`** — loader, precedence (CSV vs **`ado_targets`** vs org override vs defaults), cross-project CSV + profile lookup, description warm.
- **Dependency:** Assumes multi-project CSV ADO routing from **`repo-mapping-multi-ado-routing`** is implemented or archived before apply.

**P2-FR impact:** **P2-FR-1** / **P2-FR-10** (creation and tags may vary by ADO target); **P2-FR-8** (reopen/recreate uses per-issue effective type and states for the resolved ADO target).
