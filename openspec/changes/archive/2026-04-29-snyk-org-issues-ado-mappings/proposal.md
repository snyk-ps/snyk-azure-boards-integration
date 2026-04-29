## Why

Operators often manage **multiple Azure DevOps projects** that correspond to **different Snyk organizations**. Today’s configuration assumes a **single** ADO org/project pair and **group-scoped** Snyk Issues listing. That model cannot drive sync per team or route issues to the correct Boards project and work-item defaults. We need **org-scoped** Snyk issue retrieval and an explicit **ADO ↔ Snyk org** mapping in YAML, with **inherited defaults** and **per-mapping overrides** for work item type, states, and template.

## What Changes

- Add **Snyk REST** org-scoped issue **list** and **get** operations to the integration contract and implement them in the **Python Snyk issues client** (pagination, filters, normalized records, same safety rules as group scope).
- Extend **`azure_boards`** configuration with:
  - **`defaults`**: `work_item_type`, `work_item_state_active`, `work_item_state_closed`, `work_item_template` (same semantics as today’s work item template keys where applicable).
  - **`org_mappings`**: list of entries with **`organization`**, **`project`**, **`snyk_org_id`**, optional **`overrides`** (partial overrides of the same keys as under **`defaults`**).
- Define **effective configuration** per mapping: **`defaults`** merged with **`overrides`** (override wins); integrate **top-level** **`work_item_template`** per **`design.md`** merge rules.
- Update **`sync`** orchestration so that when **`org_mappings`** is used, each run processes **each mapping** (org-scoped Snyk list + ADO routing + effective template); preserve **single-target** group listing when **`org_mappings`** is absent or empty.
- Work item type/state strings MUST live under **`azure_boards.defaults`** only — flat **`azure_boards.work_item_*`** keys are **rejected** at load with a clear error.
- Document **`defaults`**, **`org_mappings`**, inheritance, and assignee via **`work_item_template.json_patch`** (including **`System.AssignedTo`**) in **`README.md`** **`Configuration`** and update **`data/`** sample YAML.

## Capabilities

### New Capabilities

_None — behavior extends existing capabilities._

### Modified Capabilities

- **`integration-apis`**: Document org-scoped Snyk Issues REST paths alongside existing group paths.
- **`snyk-issues-client`**: Org-scoped list/get; extend pagination and optional **`fetch`** CLI for org smoke tests; align group/org wording with **`integration-apis`**.
- **`application-config`**: Introduce **`azure_boards.defaults`** and **`azure_boards.org_mappings`**; merge semantics; reject flat work-item keys under **`azure_boards`**; README/sample deltas.
- **`sync-lifecycle`**: **`sync`** iterations over **`org_mappings`**, effective ADO target and template per mapping; rules for **`snyk.group_id`** when org mapping mode is active.

## Impact

- **Code**: `src/snyk/` (issues client), `src/config/` (loader, merged config types), `src/sync/` (orchestration), `src/commands/` (CLI flags for org fetch if added).
- **APIs**: Snyk REST Issues org routes (documented in **`integration-apis`**); Azure DevOps usage unchanged except **per-mapping** org/project routing.
- **Operators**: YAML must use **`azure_boards.defaults`** for work item policy fields; migrate any flat **`work_item_*`** keys from older drafts.
