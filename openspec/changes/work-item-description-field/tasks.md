## 1. Azure DevOps client — WIT field list

- [ ] 1.1 Add URL helper and **`list_work_item_type_fields(organization, project, work_item_type)`** on **`AzureDevOpsClient`** (api-version 7.1); return normalized field reference names.
- [ ] 1.2 Unit tests with mocked HTTP for field list parsing and error handling.

## 2. Configuration model and loader

- [ ] 2.1 Add optional **`work_item_description_field: str | None`** to **`AzureBoardsDefaults`** / merged **`AzureBoardsConfig`**; plumb through **`boards_for_org_mapping`** and override allowlist.
- [ ] 2.2 Load under **`azure_boards.defaults`** and **`org_mappings[].overrides`**; reject non-string; normalize (strip, optional **`/fields/`** prefix removal); reject flat **`azure_boards.work_item_description_field`** at root.
- [ ] 2.3 Unit tests in **`tests/test_config.py`** (omit = auto, explicit override per row, invalid type, flat key rejected).

## 3. Description field resolution

- [ ] 3.1 Implement **`resolve_description_field(...)`** in **`src/sync/`**: auto chain **Description → Repro Steps**; explicit mode; per-run cache keyed by routing context.
- [ ] 3.2 Call resolution at **`sync`** startup for each distinct routing context; integrate with **`sync/validate.py`** so unresolvable auto contexts fail before the issue loop.
- [ ] 3.3 Unit tests: auto prefers Description when both exist; falls back to Repro Steps; explicit skips fallback; failure when neither exists.

## 4. Patch build and sync wiring

- [ ] 4.1 Parameterize **`build_create_patch`** / **`build_update_patch`** with **`description_field`**; update **`run.py`** to pass resolved field for create/update paths (single-target and **`org_mappings`**).
- [ ] 4.2 Update **`tests/test_sync_patch_build.py`** and related tests to assert dynamic field paths (Task/Description, Bug/ReproSteps scenarios).

## 5. Documentation and samples

- [ ] 5.1 **`CONFIGURATION.md`**: document **`work_item_description_field`** (omit = auto Description then Repro Steps; explicit override; per-mapping **`overrides`**).
- [ ] 5.2 **`README.md`**: configuration tables / troubleshooting (Bug empty body fixed by auto mode; explicit override example).
- [ ] 5.3 **`data/sample-config.yaml`**: commented examples for default auto behavior and explicit **`Microsoft.VSTS.TCM.ReproSteps`**; note Bug vs Task.
- [ ] 5.4 **`src/org_config_generator/core.py`**: commented placeholder for new key if applicable.

## 6. Verification

- [ ] 6.1 Run **`pytest`**; **Snyk Code** / Open Source checks per repo guidelines.

## 7. Archive (human)

- [ ] 7.1 Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/work-item-description-field/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive work-item-description-field`** (or project equivalent) to fold deltas into canonical specs.
