## Context

Work item tags are applied via JSON Patch to **`System.Tags`** (semicolon-separated string in Azure DevOps). Today **`build_create_patch`** / **`build_update_patch`** in **`src/sync/patch_build.py`** use only **`work_item_template.tags`**. The **`sync`** orchestration already has access to normalized issue attributes (**`effective_severity_level`**, **`attributes.type`**) when building title/description.

## Goals / Non-Goals

**Goals:**

- Emit **two** managed dimensions as tags: **severity** and **finding type**, stable for reporting.
- **Union** operator template tags with managed tags; **never drop** a configured non-reserved tag because managed tags exist.
- Refresh managed tags on **each** sync that performs a work item create or update for that issue.

**Non-Goals:**

- Preserving **manual** tags added only in the Azure Boards UI (today a non-empty template still replaces `System.Tags` when a tags patch is sent; this change does not add a read-merge of existing WI state unless explicitly required later).
- **Origin-excluded** issues: no Azure DevOps mutations; tags unchanged there (already true).
- New YAML toggles to disable derived tags (out of scope unless a follow-up change requests it).

## Decisions

1. **Managed prefix vocabulary**

   - **`Snyk-Severity-{level}`** where **`level`** is one of **`low`**, **`medium`**, **`high`**, **`critical`**, normalized from Snyk **`effective_severity_level`** (case-insensitive input).
   - **`Snyk-Type-{kind}`** where **`kind`** is one of **`open_source`**, **`code`**, **`container`**, **`iac`**, normalized from Snyk issue **`attributes.type`** (mapping from API tokens to these four buckets per **`sync-lifecycle`** / **P2-FR-5.2** taxonomy).
   - If severity or type is **missing or unmapped**, **omit** that managed tag for that run (do not synthesize placeholders).

   *Alternatives:* single combined tag **`Snyk-meta-severity-high`** — rejected as harder to filter; custom ADO fields — rejected as template/process burden for this iteration.

2. **Combine order**

   - **Operator tags first** (merged template order after existing **`template_merge`** dedupe rules).
   - **Managed tags second**: severity tag (if present), then type tag (if present).

   *Alternative:* alphabetical — rejected; operator-first matches “do not bury config labels.”

3. **Reserved-prefix collision**

   - Before building the operator portion, **strip** any operator-supplied tag string that starts with **`Snyk-Severity-`** or **`Snyk-Type-`** so the canonical managed tags (from issue data) are the sole tags for those dimensions — avoids stale config contradicting Snyk.

4. **Implementation shape**

   - Add a single helper (for example **`combine_work_item_tags(template, severity_level, finding_type)`** or derive tag list in **`sync`** and pass into **`patch_build`**) so **create** and **update** paths share logic.
   - **`json_patch`** from the template stays unchanged; **`System.Tags`** remains one **`add`**/**`replace`** with **`"; ".join(combined_tags)`** when **`combined`** is non-empty.

   When **combined** is **empty**, omit **`System.Tags`** patch operations (current behavior) so work item tags are not cleared accidentally.

## Risks / Trade-offs

- **[Risk]** Operator uses reserved prefixes intentionally for something other than managed dimensions → **Mitigation**: document in README; strip-and-replace rule makes behavior deterministic.
- **[Risk]** Unmapped **`attributes.type`** from API leaves no **`Snyk-Type-*`** tag → **Mitigation**: acceptable; operators rely on WIQL/description until mapping extended.
- **[Risk]** ADO tag length / count limits → **Mitigation**: managed tags add at most two short strings.

## Migration Plan

- Deploy code; **next successful sync** refreshes **`System.Tags`** on touched work items with **operator tags + managed** set.
- No database migration.

## Open Questions

- None for this change; extend **`Snyk-Type-*`** normalization if new Snyk issue types appear in production payloads.
