## Why

Operator YAML mixes Azure Boards routing, sync filters, and severity policy across `azure_boards` root and `snyk`, which is hard to reason about and duplicate per mapping. The Snyk Issues list API expects **`effective_severity_level`** as **comma-separated severities in a single query parameter** (matching Snyk pagination links); the current client encoding does not match that contract and can yield **HTTP 400**. The product is **not yet in production**, so we can adopt a **breaking, single-shape** configuration without legacy compatibility.

## What Changes

- **BREAKING**: Move **`create_new_work_items`**, **`organization`**, and **`project`** from **`azure_boards`** root into **`azure_boards.defaults`**. Reject the old flat locations at load time with a clear error (no silent migration).
- **BREAKING**: Move **`severity_threshold`** from **`snyk`** to **`azure_boards.defaults`** (same ordered levels: `low` < `medium` < `high` < `critical`; default **`high`**). Remove **`snyk.severity_threshold`** from the schema.
- Add under **`azure_boards.defaults`** (each overridable via **`azure_boards.org_mappings[].overrides`**): **`issues_sync_from`** (`historical` default, or an RFC 3339 / ISO 8601 UTC timestamp to bound Issues list filtering); **`create_only_when_fix_available`** (boolean, default `false`); **`reopen_work_item_policy`** (`new_work_item` | `reopen_existing`, exact strings as implemented).
- **Issues API list**: Build **`effective_severity_level`** as **one** query parameter whose value is comma-separated severities derived from the threshold (e.g. threshold **`high`** → **`high,critical`**). Pin behavior with unit/integration-style tests on the first-list URL.
- **Sync lifecycle**: When a finding becomes **`open`** again after **`resolved`**/**`ignored`**, behavior SHALL follow **`reopen_work_item_policy`**: either create a new work item (current default semantics) with audit comment including link/reference to the prior work item, or reopen the existing mapped work item with audit comment; if reopen is chosen and the stored work item **no longer exists** in Azure DevOps, **fallback** to creating a new work item and reference the previous id in the audit comment.
- **Work item content**: For **code** (`type=code`) findings, include **file path** and **line range** from **`coordinates[].representations[].sourceLocation`** (see fixture **`data/sample_coord.local.json`**). Render the **P2-FR-5.4** Snyk UI URL as an **HTML hyperlink** inside **`System.Description`** (escaped per HTML-safe rules), not plain text only.
- **Snyk project display**: Prefer **`GET /orgs/{org_id}/projects/{project_id}`** **`attributes.name`** and **`attributes.origin`** for title/description context; persist **`snyk_project_name`** and **`snyk_project_origin`** on the mapping row to avoid refetching every run (refresh when missing or per **`design.md`**).
- **Documentation**: Update **`README.md`** (configuration, **`issues_sync_from`** / severity / reopen policy / mapping DB **column reference**). Update **`data/`** samples to the new schema; expand **`data/sample-config.yaml`** with commented examples of **`defaults`** vs **`org_mappings[].overrides`** (style aligned with **`data/config.local.org.yaml`**).

## Capabilities

### New Capabilities

- *(None — requirements change only under existing capabilities.)*

### Modified Capabilities

- **`application-config`**: YAML schema, defaults merge, `org_mappings` overrides, README/sample requirements; remove `snyk.severity_threshold`; relocate routing and sync policy keys under **`azure_boards.defaults`**.
- **`sync-lifecycle`**: Sync orchestration filters and references; **P2-FR-8** becomes policy-driven; **P2-FR-5.1** / **P2-FR-5.4** for SAST location and hyperlink; mapping-backed **Snyk project name**/**origin**; optional list time/fix filters.
- **`snyk-issues-client`**: Normative encoding of **`effective_severity_level`** on list URLs (comma-separated single parameter); optional list filters for date/fix when configuration supplies them.
- **`azure-platform`**: Mapping row schema adds **`snyk_project_name`** and **`snyk_project_origin`** (logical attributes for Table/SQLite).
- **`integration-apis`**: Document **Snyk** **`GET /orgs/{org_id}/projects/{project_id}`** for project metadata used by sync.

## Impact

- **`src/config/`** (loader, models, validation), **`src/snyk/client.py`**, **`src/sync/`**, **`src/mapping_store/`**, **`src/commands/`** (`fetch` list params), tests, **`README.md`**, **`data/sample-config.yaml`**, and other **`data/*.yaml`** samples.
