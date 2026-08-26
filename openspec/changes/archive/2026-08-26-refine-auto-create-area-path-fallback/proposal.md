## Why

The **`auto_create_area_path`** feature shipped with two behaviors bundled under one flag: (1) synthesize a default area path when none is configured, and (2) ensure/create **any** effective area path in Azure DevOps before work item create/update. Operators expected **`auto_create_area_path`** to act as a **fallback and default only** — routing unmapped or misconfigured issues to a dedicated area (e.g. `{project}\Snyk`) — not to auto-provision arbitrary paths from **`repo-mapping.csv`** or YAML **`area_path`** values. When CSV specifies `testProjectBug\area` and that node does not exist, work items should land on `testProjectBug\Snyk`, not trigger creation of the `area` segment.

## What Changes

- **Split semantics**: When **`auto_create_area_path: true`**, **`sync`** SHALL:
  1. **Default** — when area-path precedence yields unset, synthesize the effective fallback path from a configurable template (default `{project}\Snyk`).
  2. **Fallback** — when a configured path (CSV row, **`org_mappings[].overrides.area_path`**, or **`defaults.area_path`**) is resolved but **does not exist** in the effective ADO target (strict full-path GET), substitute the fallback template instead of auto-creating the configured path.
  3. **Ensure/create only the fallback path** — Classification Nodes REST ensure runs **only** for fallback-resolved paths (`area_path_source` **`auto_default`** or **`auto_fallback`**), not for configured paths that exist or for configured paths that were substituted away.
- **New config key**: **`auto_create_fallback_area_path`** — template string with **`{project}`** placeholder. Configurable under **`azure_boards.defaults`**, **`ado_targets[]`**, and **`org_mappings[].overrides`**. Environment variable **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH`** overrides **`defaults`** at load time (same precedence as other **`AZURE_BOARDS_*`** vars).
- **Logging and audit**: INFO log on fallback resolution; **P2-FR-9** audit comment on create/update when fallback is assigned (`auto_default` or **`auto_fallback`**). No duplicate fallback audit when the work item already has the effective fallback path.
- **Docs**: update **`CONFIGURATION.md`**, **`README.md`**, **`data/sample-config.yaml`**.

- **BREAKING (intentional)**: operators who relied on auto-creating CSV/YAML-configured area segments must pre-create those paths in ADO or leave **`auto_create_area_path: false`**.

**Non-breaking when disabled:** **`auto_create_area_path: false`** (default) preserves current behavior.

## Capabilities

### New Capabilities

- *(None — extends existing capabilities.)*

### Modified Capabilities

- **`application-config`**: **`auto_create_fallback_area_path`** schema, loader validation, env var **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH`**, merge under **`defaults`** / **`ado_targets`** / **`org_mappings[].overrides`**; amend **`auto_create_area_path`** requirement semantics.
- **`repo-area-path-mapping`**: fallback substitution when configured path missing (strict full-path check); configurable template; new **`area_path_source=auto_fallback`**; runtime template precedence (**`ado_targets`** → **`org_mappings` overrides** → **`defaults`**).
- **`sync-lifecycle`**: narrow ensure scope; existence check before fallback substitution; fallback audit comments (**P2-FR-9**); logging for **`auto_fallback`**.

## Impact

- **`src/config/`** — model, loader, effective merge, **`ado_targets`** allowlist, env override
- **`src/sync/area_path.py`** — path existence check (strict full path), template rendering
- **`src/sync/repo_mapping.py`** — fallback template in **`auto_default`** branch
- **`src/sync/run.py`** — finalize area path with existence check + fallback; audit comments; narrow ensure
- **`tests/`** — config loader, template precedence, strict full-path, fallback audit, sync integration
- **`CONFIGURATION.md`**, **`README.md`**, **`data/sample-config.yaml`**
- **No mapping-store migration**
- **No new Python dependencies**
