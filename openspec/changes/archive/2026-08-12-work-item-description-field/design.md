## Context

Work item body text is assembled in **`issue_content.build_system_description()`**, converted to HTML in **`patch_build._ado_system_description_html()`**, and patched to a **hardcoded** **`/fields/System.Description`** path. Bug work items in standard Agile/Scrum processes expose **Repro Steps** (`Microsoft.VSTS.TCM.ReproSteps`) as the primary narrative field instead of **Description**. Operators already configure **`work_item_type`**, states, and templates per **`defaults`** / **`org_mappings[].overrides`**.

## Goals / Non-Goals

**Goals:**

- **Auto mode (default):** Prefer **`System.Description`**, fall back to **`Microsoft.VSTS.TCM.ReproSteps`** based on fields defined for the effective work item type in the target ADO project.
- **Explicit mode:** Optional **`work_item_description_field`** string override per routing context; no fallback when set.
- Resolve once per unique **(organization, project, work_item_type, configured_field_or_auto)** per **`sync`** run and reuse for all issues in that context.
- Same HTML pipeline and **`work_item_description_appendix`** behavior regardless of target field reference name.
- Clear startup failure when auto mode cannot resolve any supported field.
- Document default auto behavior in **`CONFIGURATION.md`**, **`README.md`**, and **`data/`** samples.

**Non-goals:**

- Storing the chosen field reference in the mapping store (resolution is deterministic from config + ADO WIT metadata each run).
- Hot-reload of config.
- Querying ADO on every individual issue create/update (cache per sync run).
- Auto-discovery beyond the two built-in fallback candidates (operators use explicit config for other fields).
- Changing **`json_patch`** semantics; operators remain responsible for not conflicting with the resolved description field path.

## Decisions

1. **Config key:** **`work_item_description_field`** under **`azure_boards.defaults`**, overridable via **`org_mappings[].overrides`**. Omitted or whitespace-only after trim ⇒ **auto mode**. Non-empty string ⇒ **explicit mode** (Azure DevOps field reference name only, e.g. `System.Description` or `Microsoft.VSTS.TCM.ReproSteps`; loader strips optional `/fields/` prefix if operators paste a patch path).

2. **Auto resolution:** At **`sync`** startup (after config merge, before the per-issue loop), for each distinct routing context the run will use, call:

   `GET .../_apis/wit/workitemtypes/{workItemTypeName}/fields?api-version=7.1`

   Build a set of **`referenceName`** values. Choose the first match in order:
   1. **`System.Description`**
   2. **`Microsoft.VSTS.TCM.ReproSteps`**

   If no match, exit non-zero with an error naming the org, project, work item type, and attempted reference names.

3. **Explicit mode:** Skip fallback; use the configured reference name directly. Validate membership in the WIT field list at startup (same API); if validation fails, exit non-zero before the issue loop.

4. **Patch assembly:** **`build_create_patch`** / **`build_update_patch`** accept **`description_field: str`** and emit **`/fields/{description_field}`** instead of hardcoding **`System.Description`**.

5. **Caching:** In-memory cache keyed by **(organization, project, work_item_type, explicit_field_or_auto_token)** for the lifetime of one **`sync`** invocation.

6. **Loader / flat keys:** Reject **`azure_boards.work_item_description_field`** at the **`azure_boards`** root (same rule as other **`work_item_*`** keys under **`defaults`** only). Reject non-string types. Whitespace-only after trim ⇒ auto mode (same as omit).

7. **Documentation defaults:** Docs SHALL state that when the key is omitted, **`sync`** tries **Description** then **Repro Steps** automatically; explicit override is for custom processes or future field names without code changes.

## Risks / Trade-offs

- **[Risk]** Extra ADO REST call(s) at sync startup → **Mitigation:** One call per distinct routing context per run; cache results.
- **[Risk]** Operator changes **`work_item_description_field`** or **`work_item_type`** mid-life → existing mapped items may receive updates on a different field → **Mitigation:** Document that changing description field or WIT after items exist may require manual cleanup or remapping.
- **[Risk]** Explicit field invalid for WIT → patch 400 at runtime → **Mitigation:** Startup WIT field list validation when ADO is reachable.
- **[Risk]** Both Description and Repro Steps exist on Bug (some processes) → auto mode writes **Description only** → **Mitigation:** Document; operators targeting Repro Steps on those processes set explicit **`Microsoft.VSTS.TCM.ReproSteps`**.

## Migration Plan

No mapping store migration. Existing configs without the new key behave differently for **Bug** (body content will appear in Repro Steps via auto fallback instead of being written to an unused Description). **Task** behavior unchanged (Description still preferred). Operators who relied on invisible Description on Bug may see content move to the visible field—desired outcome.

## Open Questions

- *(None for v1.)*
