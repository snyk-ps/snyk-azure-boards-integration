## 1. Config and models

- [ ] 1.1 Add **`auto_create_fallback_area_path: str | None`** to **`AzureBoardsDefaults`**; default **`None`** (render as **`{project}\Snyk`** when **`auto_create_area_path`** is **`true`**).
- [ ] 1.2 Add **`auto_create_fallback_area_path`** to **`AdoTargetProfile`**; extend **`_ADO_TARGET_ALLOWED_KEYS`** and **`_parse_ado_targets`** in loader.
- [ ] 1.3 Loader validation: non-empty template, **`{project}`** present, renders to valid **`Project\Area`** shape; reject flat **`azure_boards.auto_create_fallback_area_path`**.
- [ ] 1.4 Wire **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH`** in **`_apply_env_overrides`** (overrides **`defaults`** only).
- [ ] 1.5 Add **`auto_create_fallback_area_path`** to **`org_mappings[].overrides`** allowlist and effective merge in **`effective.py`**.
- [ ] 1.6 Add **`resolve_effective_fallback_template(ado_profile, org_override, defaults) -> str`** with precedence **`ado_targets`** → org override → defaults.
- [ ] 1.7 Unit tests: load defaults, custom template, invalid template, env override, ado_targets row, org override, template precedence.

## 2. Area path helpers

- [ ] 2.1 Add **`render_fallback_area_path(template, project) -> str`** (replace **`{project}`**); remove hardcoded **`AUTO_DEFAULT_AREA_SEGMENT`** usage from routing.
- [ ] 2.2 Add **`area_path_exists(client, org, project, full_path, cache) -> bool`** using existing GET classification node (**404** → false; strict full path).
- [ ] 2.3 Add **`finalize_area_path_for_auto_create(...)`**: existence check + **`auto_fallback`** substitution; returns updated path and **`area_path_source`**.
- [ ] 2.4 Unit tests: template render, existence check (mock ADO), strict full-path (parent exists, leaf missing), substitution logic.

## 3. Sync integration

- [ ] 3.1 Update **`resolve_routing`**: use resolved fallback template (not hardcoded **`Snyk`**) for **`auto_default`** branch.
- [ ] 3.2 Update **`run.py`**: call **`finalize_area_path_for_auto_create`** before ensure/patch; narrow **`_ensure_routing_area_path_if_enabled`** to **`auto_default`** / **`auto_fallback`** paths only.
- [ ] 3.3 Add **`_format_fallback_area_path_comment`** for **`auto_default`** and **`auto_fallback`**; wire audit comments on create/recreate/update per **P2-FR-9**.
- [ ] 3.4 INFO log on **`auto_fallback`** with configured missing path; skip duplicate fallback audit when path unchanged.
- [ ] 3.5 Integration tests: CSV missing → fallback + audit; CSV exists → no ensure; unset → **`auto_default`** + audit; ado_targets template wins over defaults.

## 4. Documentation

- [ ] 4.1 **`CONFIGURATION.md`**: fallback vs default semantics, **`auto_create_fallback_area_path`**, env var, **`ado_targets`** / **`org_mappings`** overrides, migration note for CSV auto-create behavior change.
- [ ] 4.2 **`README.md`**: pointer to updated **`auto_create_area_path`** behavior.
- [ ] 4.3 **`data/sample-config.yaml`**: commented examples for fallback template on **`defaults`** and **`ado_targets`**.

## 5. Archive prep

- [ ] 5.1 Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/refine-auto-create-area-path-fallback/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive refine-auto-create-area-path-fallback`** (or project equivalent) to fold deltas into canonical specs.
