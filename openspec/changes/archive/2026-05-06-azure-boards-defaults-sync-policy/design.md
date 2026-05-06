## Context

The integration loads non-secret YAML (`application-config`), lists Snyk issues (`snyk-issues-client`), persists mappings (`azure-platform` / SQLite), and updates Azure Boards (`azure-devops-client`). Today **`severity_threshold`** lives under **`snyk`**, while Azure routing and **`create_new_work_items`** sit at **`azure_boards`** root; **`org_mappings`** merges **`overrides`** with **`defaults`** only for work-item strings/templates. Live Snyk issue list responses show **`links.self`** using **`effective_severity_level=high%2Chigh`** (comma-separated **within one parameter value**), while the Python client builds **repeated** `effective_severity_level=` keys—misalignment likely drives **HTTP 400**. The app is pre-production; **breaking YAML moves** without legacy shims are acceptable.

## Goals / Non-Goals

**Goals:**

- Single consistent **`azure_boards.defaults`** surface for ADO routing (`organization`, `project`), **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, and **`reopen_work_item_policy`**, with **`org_mappings[].overrides`** overriding any of these keys (same merge semantics as existing work-item defaults).
- Issues list URLs use **`effective_severity_level=<comma-separated-levels>`** (one query parameter), e.g. **`high,critical`** when the minimum threshold is **`high`**.
- Optional **lower-bound timestamp** for issue listing (`historical` = no extra filter) and optional **fix-available-only** creation gate when supported by the Issues API list filters (exact parameter names verified against Snyk OpenAPI during implementation).
- Configurable **reopen** behavior with **audit comments** and **fallback** when reopening fails because the work item was deleted.
- Richer work items: **code** findings include **file + lines** from **`coordinates`**; **Snyk link** as **`HTML` `<a href>`**; **project name** and **origin** from **GET project**, cached on mapping rows.

**Non-Goals:**

- Hot-reload of YAML; Azure Files/Blob delivery unchanged.
- Backward-compatible loaders for old key paths (reject with errors instead).

## Decisions

1. **`effective_severity_level` encoding** — Build **one** query pair: `("effective_severity_level", ",".join(levels))` after deriving ordered distinct levels from **`severity_threshold`** (`effective_severity_levels_from_threshold` stays the source of level inclusion). **Rationale:** Matches Snyk’s own **`links.next`** / **`links.self`** shape (`data/sample_coord.local.json`). **Alternative rejected:** Repeated keys—observed mismatch with API pagination links.

2. **Config placement** — All listed keys live under **`azure_boards.defaults`**; **`snyk`** retains **`group_id`** only (plus forward-compatible unknown keys per loader rules). **Rationale:** Policy for “what becomes an Azure ticket” belongs next to Boards routing.

3. **`issues_sync_from`** — Literal **`historical`** or an **ISO 8601 UTC** timestamp string; merged effective value drives optional Issues API filters (**implementation MUST confirm** whether filtering uses **`created_after`**, **`updated_after`**, or API-documented equivalents). Default **`historical`** means **do not** send a time filter.

4. **`create_only_when_fix_available`** — When **true**, suppress **new** work item creation unless the issue satisfies “fix available” per **`sync-lifecycle`** (reuse/coordinate fix signals already surfaced for **P2-FR-5.5**); combined with list filters if the API exposes a matching parameter.

5. **`reopen_work_item_policy`** — `new_work_item`: keep current **P2-FR-8** style (new WI, mapping points to new id); audit comment includes **previous work item id** and **HTML link** when URL constructible. `reopen_existing`: PATCH stored **`work_item_id`** to **`work_item_state_active`** when Azure GET succeeds; **if GET/PATCH returns not-found**, **fallback** to **`new_work_item`** path and mention former id in comment.

6. **Project metadata** — Call **`GET /orgs/{org_id}/projects/{project_id}`** with the same **`version`** as other REST calls when **`snyk_project_name`** or **`origin`** is absent on the mapping row or stale (policy: fill-on-missing each upsert, or once per row—pick simplest consistent behavior in code). Persist **`snyk_project_name`** / **`snyk_project_origin`** on upsert.

7. **SAST lines** — Prefer **`representations[].sourceLocation`** (`file`, **`region.start.line`**–**`region.end.line`**) from **`data/sample_coord.local.json`**; skip gracefully when absent.

## Risks / Trade-offs

- **[Risk]** Exact Issues API query names for time/fix filters differ by version → **Mitigation:** Lock parameters against OpenAPI + add tests that fail if wrong.
- **[Risk]** SQLite migration adds columns → **Mitigation:** Idempotent **`ALTER TABLE`** in schema apply step for dev/tests.
- **[Risk]** HTML anchor + escaping → **Mitigation:** Run URL and anchor text through the same escaping pipeline as **`System.Description`**.

## Migration Plan

Operators replace YAML with the new shape; **no automated migration**. Deploy/restart after editing config in Azure. Rollback = revert YAML + prior binary revision.

## Open Questions

- Confirm **Snyk Issues** list parameters for **created/updated** bounds and **fix-available** filter names for the pinned **`version`** string in code.
- Whether **`links.next`** after switching encoding preserves comma style (assume yes if first page is correct).
