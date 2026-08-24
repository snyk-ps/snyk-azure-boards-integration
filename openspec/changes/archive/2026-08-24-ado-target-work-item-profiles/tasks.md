## 1. Configuration loader

- [x] 1.1 Add **`AdoTarget`** model and **`ado_targets`** list on **`AzureBoardsConfig`**; allowed keys mirror work-item taxonomy subset of **`defaults`**.
- [x] 1.2 Loader: validate required **`organization`** / **`project`**; reject duplicate **`(organization, project)`**; reject invalid types and template shape.
- [x] 1.3 Build index **`(organization, project)` → profile** for runtime lookup.
- [x] 1.4 Unit tests: valid entries, duplicates, partial entries, omitted **`ado_targets`**.

## 2. Effective work item config resolution

- [x] 2.1 Implement **`resolve_effective_work_item_config(...)`** with per-field precedence: CSV → **`ado_targets`** → org override (same ADO target) → **`defaults`**.
- [x] 2.2 Extend CSV loader for optional taxonomy columns and header aliases (**`Work Item Type (Optional)`**, etc.).
- [x] 2.3 Add **`EffectiveWorkItemConfig`** (or extend **`ResolvedRouting`**) with type, states, description field config, template, tags merge, **`work_item_config_source`**.
- [x] 2.4 Unit tests: cross-project CSV ignores org-mapping overrides; **`ado_targets`** beats org override for same target; CSV overrides single field; tags merge.

## 3. Sync integration

- [x] 3.1 **`_sync_one_issue`**: use per-issue effective config for create/update/reopen/recreate/migration patches and WIT **`$type`**.
- [x] 3.2 **`description_fields.resolve`**: per-issue org/project/type/field; **`warm_description_fields_for_sync`** warms all **`ado_targets`** entries.
- [x] 3.3 Log **`work_item_config_source`**, effective type, active state at INFO on create/update.
- [x] 3.4 Unit/integration tests: multi-project CSV + distinct **`ado_targets`** profiles (e.g. Task/To Do vs Bug/New).

## 4. Documentation and samples

- [x] 4.1 Update **`data/sample-config.yaml`** with **`ado_targets`** multi-project example.
- [x] 4.2 Update **`data/sample-repo-mapping.csv`** header comment or example documenting optional taxonomy columns.
- [x] 4.3 Update **`CONFIGURATION.md`** and **`README.md`**: **`ado_targets`**, taxonomy precedence, CSV optional columns.

## 5. Verification

- [x] 5.1 Run full test suite; fix regressions.
- [x] 5.2 Run Snyk Code on changed Python surfaces before merge.

## 6. Archive (human step)

- [x] 6.1 Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/ado-target-work-item-profiles/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive ado-target-work-item-profiles`** to fold deltas into canonical specs.
