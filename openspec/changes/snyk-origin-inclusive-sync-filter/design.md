## Context

The integration lists Snyk issues, resolves **`snyk_project_origin`** via the Snyk Projects API (already surfaced as **`snyk_project_origin`** and described in **`README.md`**), and persists rows in SQLite today as **`issue_work_item_map`**. Operators need an **inclusive YAML allowlist** so only findings from approved origins (for example **`github`**, **`gitlab`**) qualify for Azure Boards **create/update/close** while excluded issues remain visible in **issues sync persistence** for reporting (**`excluded`**, **`exclusion_reason`**).

## Goals / Non-Goals

**Goals:**

- **`sync_included_snyk_origins`** under **`azure_boards.defaults`**, overrideable in **`org_mappings[].overrides`**, as a comma-separated inclusive filter.
- Validate configured tokens against the documented allowlist (see **`README.md`** + [Snyk Origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin)), plus **`github-cloud-app`** and **`github-server-app`** for parity with common REST values.
- **`sync`** classifies each issue after origin is known; **excluded** issues skip Azure DevOps mutations while persistence records **`excluded=true`** and a stable **`exclusion_reason`**.
- Reposition storage as **issues sync persistence** in docs; keep physical SQLite table name **`issue_work_item_map`** unless a future change migrates it.

**Non-Goals:**

- Pre-filtering the Issues API by project before list (no change to list entrypoint in this proposal).
- Config hot-reload without process restart.
- Automatically closing Boards work items when an issue flips from included to excluded by config tighten (default: **freeze** Boards state; skip mutations until re-included—see **`sync-lifecycle`** scenarios).

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Omitted / empty allowlist ⇒ no filter** | Backward compatible; operators opt in explicitly. |
| **Inclusive list only** | Matches operator intent (“allow these sources”); CLI exclusion is expressible by omitting **`cli`** from the list. |
| **Exact string match** on trimmed origin | Matches Snyk **`attributes.origin`** shape (lowercase tokens per docs); avoid accidental case folding bugs. |
| **Loader allowlist validation** | Reject unknown tokens at YAML load with a pointer to **`README.md`** so misconfiguration fails fast. |
| **TEXT `true`/`false` for `excluded` in SQLite** | Align with all-TEXT column style; implementation MAY coerce in Python layer. |
| **Keep table name** **`issue_work_item_map`** | Avoids migration risk; README clarifies logical name **issues sync persistence**. |
| **Empty `work_item_id` ⇒ create when re-included** | An origin-excluded row may exist with no Boards link; widening the allowlist (or resolving origin) must follow the same **create** path as “no row” for open issues so sync does not attempt an Azure **update** without an id. |

**Alternatives considered:** Separate project-policy table (rejected for this proposal—classification is issue-sourced after Issues API). Client-side filter only without persistence (rejected—operators want **`excluded`** columns for reporting).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| API returns origin not in README/catalog | Loader validation fixes config typos; runtime uses exact match—if Snyk adds new origins, README + allowlist enum updated or sync treats as excluded until listed. |
| Duplicate **`GET …/projects/{id}`** before cache warm | Reuse existing row **`snyk_project_origin`** when present; optional per-sync PID cache during implementation. |
| Mapped work item left open when issue becomes excluded | Documented default: no auto close in v1; operator may close manually or future policy adds closing. |

## Migration Plan

1. Ship **`ALTER TABLE`** idempotent adds for **`excluded`**, **`exclusion_reason`** (default **`false`** / empty).
2. Existing rows backfill **`excluded=false`**, **`exclusion_reason`** empty.
3. Rollback: older code ignores new columns; downgrade script optional (drop column not supported in SQLite—leave columns unused).

## Open Questions

- Whether to add **`origin_unknown`** vs **`origin_not_in_allowlist`** as the only reasons in v1 (spec enumerates).
