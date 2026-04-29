## Context

The product already uses the Snyk Issues REST API in **group** scope (`GET /groups/{group_id}/issues`), merged YAML configuration (`azure_boards`, top-level `work_item_template`, `snyk`), and **`sync`** under **`src/sync/`**. Operators need **many-to-many** routing: each **Azure DevOps organization + project** pair tied to a **Snyk organization UUID**, with shared defaults and optional per-target overrides for Boards work item type, states, and template content.

## Goals / Non-Goals

**Goals:**

- Normatively document and implement **org-scoped** issue **list** (and **get** where applicable) consistent with Snyk OpenAPI for the pinned **`version`** query parameter.
- Add **`azure_boards.defaults`** and **`azure_boards.org_mappings`** with clear **merge order** for effective settings per mapping row.
- Extend **`sync`** to process **each** mapping when **`org_mappings`** is non-empty, using org-scoped issue lists and the correct ADO **organization** / **project** for that row.
- Keep **single-target** sync behavior when **`org_mappings`** is omitted or an empty list.
- **Reject** **`work_item_type`**, **`work_item_state_active`**, and **`work_item_state_closed`** as direct children of **`azure_boards`** (operators use **`defaults`** only).

**Non-Goals:**

- Hot-reload of configuration; **Azure Table** mapping store schema migration (unless a later change requires new columns—out of scope here).
- Supporting alternate legacy YAML shapes for work item policy (flat **`azure_boards`** keys).
- Resolving Snyk org UUIDs from ADO automatically (operators supply **`snyk_org_id`** in YAML).

## Decisions

1. **Snyk REST paths (org scope)**  
   **Decision:** Add **`GET /orgs/{org_id}/issues`** and **`GET /orgs/{org_id}/issues/{issue_id}`** to **`integration-apis`**, matching Snyk’s published Issues API for the same **`version`** as group scope.  
   **Rationale:** Single source of truth for the Python client and tests.  
   **Alternatives:** Hard-code paths only in code—rejected to keep spec-driven contracts.

2. **Where defaults live**  
   **Decision:** Place **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, and **`work_item_template`** under **`azure_boards.defaults`**.  
   **Rationale:** Matches the user’s model; groups all “default ADO work item policy” in one object.  
   **Alternatives:** Only top-level keys—rejected for this change.

3. **Flat work item keys**  
   **Decision:** If **`azure_boards.work_item_type`** (or **`work_item_state_*`**) appears at the **`azure_boards`** root, the loader SHALL raise **`ConfigError`** with a message pointing to **`azure_boards.defaults`**.  
   **Rationale:** One canonical shape; avoids duplicate/conflicting sources of truth.

4. **Top-level `work_item_template` vs `defaults.work_item_template`**  
   **Decision:** Effective template for a mapping is built as: start from top-level **`work_item_template`**, deep-merge **`azure_boards.defaults.work_item_template`**, then deep-merge **`overrides.work_item_template`** for that **`org_mappings`** entry (later wins for conflicting keys; **`json_patch`** lists **concatenate** in that order, with **override** list last—final **assignee** behavior remains subject to existing **`System.AssignedTo`** filtering in **`patch_build`**).  
   **Rationale:** Preserves global tags/patch while allowing defaults and per-ADO-target overrides.  
   **Alternatives:** Only one template location—rejected; would break global merge semantics.

5. **`snyk.group_id` when `org_mappings` is active**  
   **Decision:** When **`org_mappings`** is **non-empty**, **`sync`** SHALL list issues per mapping using **org** scope and **SHALL NOT** require **`snyk.group_id`** for those list operations. When **`org_mappings`** is **absent or empty**, existing **non-empty `snyk.group_id`** rules apply for group-scoped **`sync`** and **`fetch`**.  
   **Rationale:** Org listing does not use group id; avoids redundant config.  
   **Alternatives:** Always require **`group_id`**—rejected as unnecessary for org-only runs.

6. **Matching issues to mappings**  
   **Decision:** Each **`sync`** iteration uses one mapping row: request Snyk issues for **`snyk_org_id`**, and send ADO traffic to **`organization`** + **`project`** for that row. Issues returned for that org are processed only in that iteration (no cross-merge between orgs in one pass).  
   **Rationale:** Deterministic routing; aligns **`normalized` `org_id`** on issues with the configured Snyk org.

## Risks / Trade-offs

- **[Risk]** Snyk OpenAPI path or query parameters for org issues differ from group issues → **Mitigation:** Implement against **`integration-apis`** spec; add contract tests; adjust spec if OpenAPI differs.
- **[Risk]** Deep-merge mistakes for **`work_item_template`** → **Mitigation:** Unit tests for merge order and **`json_patch`** list ordering; document assignee via **`/fields/System.AssignedTo`** in README.
- **[Risk]** Long **`sync`** runs with many mappings + pagination → **Mitigation:** Reuse existing 429 behavior; consider future observability (out of scope).

## Migration Plan

1. Ship loader that requires **`azure_boards.defaults`** for work item policy fields and rejects flat **`azure_boards.work_item_*`** keys.
2. Update **sample** YAML and README with **`defaults`** and an example **`org_mappings`** block (placeholders only).
3. Enable org client + **`sync`** behind the same CLI; operators opt in by adding **`org_mappings`**.
4. Rollback: remove **`org_mappings`** and rely on previous group-scoped single-target flow (config + code version).

## Open Questions

- Confirm exact Snyk OpenAPI operation id and any org-only query parameters (e.g. filter parity with group list) before implementation.
- Whether **`fetch`** should gain a dedicated **`--org-id`** (or config-only) smoke path for org list—spec leaves CLI details to **`snyk-issues-client`** delta.
