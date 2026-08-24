## Why

Today, when **`sync`** resolves no area path (`area_path_source=none`), work items omit **`System.AreaPath`** and land on the ADO project root board. Operators who want a dedicated **Snyk** area must pre-create that path in Azure DevOps and configure **`defaults.area_path`** (or CSV rows) manually. When a configured path is misspelled or not yet provisioned, create/update fails with ADO **HTTP 400** instead of self-healing.

Operators need an optional, IaC-friendly toggle that (1) supplies a sensible default area when none is configured, and (2) creates missing area-path nodes via the ADO Classification Nodes API before assigning work items.

## What Changes

- Add optional boolean **`auto_create_area_path`** under **`azure_boards.defaults`**, overridable per **`org_mappings[].overrides`** (default **`false`**).
- When **`auto_create_area_path`** is **`true`**:
  1. **Fallback area path:** If area-path precedence yields unset (`area_path_source=none`), synthesize **`{effective_ado_project}\Snyk`** as the effective area path (log **`area_path_source=auto_default`**). The fallback segment name is fixed to **`Snyk`** in v1 (Option A — no separate segment config key).
  2. **Ensure exists:** Before create/recreate/update paths that set **`System.AreaPath`**, ensure the full effective area path exists in the effective ADO target; create missing segments via Classification Nodes REST (**`Areas`**) when absent.
- Extend the Azure DevOps client with **get** and **create-or-update** classification node operations (**`api-version=7.1`**).
- Per-sync-run in-memory cache of ensured paths to avoid duplicate ADO calls.
- Document **optional** permissions: PAT scope remains **Work Items: Read & write**; additionally, the PAT user needs project **Create child nodes** (and related area-path object permissions) on the parent nodes — only required when this setting is enabled. Pre-creating paths manually remains valid when the setting is **`false`**.
- Update **`CONFIGURATION.md`**, **`README.md`**, and **`data/sample-config.yaml`**.

**Non-breaking:** Default **`false`** preserves current behavior (unset area path → omit **`System.AreaPath`**; configured but missing path → ADO error).

## Capabilities

### New Capabilities

- *(None — extends existing capabilities.)*

### Modified Capabilities

- **`application-config`**: **`auto_create_area_path`** schema, loader validation, merge under **`defaults`** / **`org_mappings[].overrides`**, sample config and operator docs (including optional area-path permissions).
- **`azure-devops-client`**: Classification Nodes get + create-or-update for **`Areas`**.
- **`integration-apis`**: REST path templates for classification nodes.
- **`sync-lifecycle`**: Ensure area path before patch; fallback **`{project}\Snyk`** when enabled and path unset; logging.
- **`repo-area-path-mapping`**: Extend area-path precedence and **`area_path_source`** values; optional-permissions note for multi-project CSV.

## Impact

- **`src/config/`** — model, loader, effective merge, override allowlist
- **`src/integrations/azure_devops/`** — classification node client methods + URL helpers
- **`src/sync/`** — area-path ensure helper, **`resolve_routing`** / **`run.py`** integration
- **`tests/`** — config loader, ensure logic (mock ADO), fallback precedence, client unit tests
- **`CONFIGURATION.md`**, **`README.md`**, **`data/sample-config.yaml`**
- **No mapping-store migration**
- **No new Python dependencies** (stdlib HTTP client as today)
