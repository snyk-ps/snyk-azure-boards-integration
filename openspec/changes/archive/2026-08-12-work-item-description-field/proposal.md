## Why

Azure DevOps work item types do not share a single narrative field. **Task** (and many other types) use **`System.Description`**, while **Bug** (Agile/Scrum) primarily uses **Repro Steps** (`Microsoft.VSTS.TCM.ReproSteps`). Today **`sync`** always JSON-Patches **`/fields/System.Description`**, so Bug work items appear to have empty bodies even when sync succeeds. Operators need sensible default behavior for Bug without a code change per process template, plus an optional explicit field override per **`defaults`** / **`org_mappings[].overrides`** (same pattern as **`work_item_type`** and state keys).

## What Changes

- **Default (auto) behavior:** When **`work_item_description_field`** is omitted, **`sync`** resolves the target field for each routing context (**ADO org + project + effective `work_item_type`**) by querying Azure DevOps work item type fields. It SHALL prefer **`System.Description`** when that field exists on the type; otherwise SHALL use **`Microsoft.VSTS.TCM.ReproSteps`** when present. If neither exists, **`sync`** SHALL fail before the per-issue loop with a clear, non-secret error.
- **Optional explicit override:** **`azure_boards.defaults.work_item_description_field`** (and per-row **`overrides`**) MAY set a non-empty Azure DevOps field **reference name** (for example `Microsoft.VSTS.TCM.ReproSteps`). When set, **`sync`** SHALL use that field only (no fallback) for creates and updates in that routing context.
- **Unchanged content pipeline:** Snyk finding assembly, **`work_item_description_appendix`**, HTML escaping, linkification, and truncation apply to the resolved target field—the same plain/HTML body as today.
- **Documentation:** Update **`CONFIGURATION.md`**, **`README.md`**, and tracked **`data/`** samples to document default auto behavior, explicit override, and Bug vs Task examples.

## Capabilities

### New Capabilities

- *(None.)*

### Modified Capabilities

- **`application-config`**: Schema, merge, validation, and docs for **`work_item_description_field`** under **`defaults`** and **`org_mappings[].overrides`**; reject flat **`azure_boards.work_item_description_field`**.
- **`sync-lifecycle`**: Normative description targeting uses the **effective description field** (auto-resolved or configured) instead of assuming **`System.Description`**; **P2-FR-5.x** body content requirements unchanged.
- **`azure-devops-client`**: Client support for **Work Item Types Field — List** to resolve fields for auto mode.

## Impact

- **`src/integrations/azure_devops/`** (URLs, client method for WIT fields list)
- **`src/config/`** (models, loader, override allowlist)
- **`src/sync/`** (`patch_build`, field resolution helper, `run.py`, startup validation)
- Tests, **`CONFIGURATION.md`**, **`README.md`**, **`data/sample-config.yaml`**, org-mapping generator comments
