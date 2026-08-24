# Sync lifecycle — work items and Snyk mapping

Normative functional requirements for work item creation, lifecycle, content, mapping, and tagging. Requirement IDs (**P2-FR-***) are stable across proposals and changes.

## Scope

Integrate Snyk security findings with Azure Boards: create and maintain work items for qualifying findings, keep them in sync with Snyk lifecycle, enrich tickets with finding metadata, and maintain a stable Snyk↔work-item mapping (see also `azure-platform` and `integration-apis` capabilities).

## Work item creation and lifecycle

| ID | Requirement |
|----|-------------|
| **P2-FR-1** | Create Azure Boards work items for **new** Snyk findings at **High** or **Critical** severity only. |
| **P2-FR-2** | Set newly created work items to a default **Unassigned** state (per process configuration). |
| **P2-FR-3** | Automatically **close** the linked work item when the corresponding Snyk finding is **fixed**. |
| **P2-FR-4** | Automatically **close** the linked work item when the corresponding Snyk finding is **ignored**. |
| **P2-FR-8** | If a finding that was fixed/closed becomes **open again**, **open a new** work item (do not silently reuse the closed one without a defined new ticket). |
| **P2-FR-9** | When the solution changes work item status, **add an audit comment** on the work item documenting that change. |
| **P2-FR-11** | Provide a **configuration setting** to **globally enable or disable** the creation of **new** Azure Boards work items. |

## Work item content (Snyk metadata)

Populate each created/updated work item with at least:

| ID | Field / content |
|----|-----------------|
| **P2-FR-5** | Required Snyk finding properties and details (see sub-items). |
| **P2-FR-5.1** | Description of the vulnerability. |
| **P2-FR-5.2** | Finding type: Open Source, Code, Container, or IaC. |
| **P2-FR-5.3** | CVE/CWE identifiers, when applicable. |
| **P2-FR-5.4** | Direct link to the finding in Snyk. |
| **P2-FR-5.5** | Fix availability and fix guidance, when available. |

## Mapping and tagging

| ID | Requirement |
|----|-------------|
| **P2-FR-7** | Maintain a **unique, stable mapping** between each Snyk finding and its Azure Boards work item (one finding — one active work item per policy in P2-FR-8). |
| **P2-FR-10** | Support **configurable tags** on work items (e.g. product type, `Snyk`, or other agreed labels). |
## Requirements
### Requirement: Persist Snyk project display metadata on mapping rows

The **`sync`** run SHALL persist **`snyk_project_name`** (from **`GET /orgs/{org_id}/projects/{project_id}`** **`attributes.name`**) and **`snyk_project_origin`** (from **`attributes.origin`**) on the **issues sync persistence** row for the natural key, updating values when refreshed per **`design.md`**, so routine sync loops avoid repeating project GET for unchanged rows.

#### Scenario: Upsert stores project metadata

- **WHEN** sync obtains non-empty project **`name`** and **`origin`** from the Snyk Projects API for an issue’s **`project_id`**
- **THEN** the persistence upsert SHALL persist **`snyk_project_name`** and **`snyk_project_origin`** alongside existing routing fields

---

### Requirement: Inclusive Snyk origin allowlist gates Azure Boards mutations

When merged configuration yields a **non-empty** effective **`sync_included_snyk_origins`** list per **`application-config`**, **`sync`** SHALL classify each issue **after** resolving **`snyk_project_origin`** (using persisted row values when sufficiently fresh per existing project-metadata rules, otherwise **`GET /orgs/{org_id}/projects/{project_id}`** when org-scoped project fetch applies). An issue SHALL be **origin-included** only if **`strip(snyk_project_origin)`** equals one allowlisted token **exactly**.

For **origin-included** issues, existing **P2-FR-*** work item rules unchanged. For **origin-excluded** issues, **`sync`** SHALL **not** invoke Azure DevOps **create**, **update**, **state transition**, or **comment** operations for that issue on that run.

When **`snyk_project_origin`** cannot be resolved to a non-empty string before classification and a non-empty allowlist is active, the issue SHALL be treated as **origin-excluded** with **`exclusion_reason`** **`origin_unknown`**.

When the origin is known but not in the allowlist, **`exclusion_reason`** SHALL be **`origin_not_in_allowlist`**.

#### Scenario: Allowlist inactive preserves prior Boards behavior

- **WHEN** effective **`sync_included_snyk_origins`** is empty per **`application-config`**
- **THEN** **`sync`** SHALL not exclude issues based on origin and SHALL apply **P2-FR-1** and other gates as before this change

#### Scenario: CLI origin excluded when allowlist omits cli

- **WHEN** effective allowlist is non-empty, **`snyk_project_origin`** is **`cli`**, and **`cli`** is not among the tokens
- **THEN** the issue SHALL be origin-excluded and **`sync`** SHALL skip Azure DevOps mutations for it

#### Scenario: GitHub origin included when listed

- **WHEN** effective allowlist contains **`github`** and **`snyk_project_origin`** after strip is **`github`**
- **THEN** the issue SHALL be origin-included subject to **P2-FR-1** and other requirements

#### Scenario: Re-included open issue with empty work_item_id creates a work item

- **WHEN** issues sync persistence already holds a row for the issue with **empty** **`work_item_id`** (for example the issue was **origin-excluded** on a prior run and Azure Boards was never mutated), the effective allowlist is **non-empty**, the issue is now **origin-included**, **`create_new_work_items`** is **true**, and the derived Snyk status is **open**
- **THEN** **`sync`** SHALL create an Azure Boards work item for that issue (same rules as for a missing row) and SHALL upsert **`work_item_id`** and **`excluded`** **`false`**, except that **reopen** transitions (**resolved** or **ignored** → **open**) SHALL use the existing **reopen** orchestration path (which already **creates** when **`work_item_id`** is empty)

---

### Requirement: Persist exclusion fields on issues sync persistence upserts

On each **`sync`** pass that upserts the **issues sync persistence** row for a natural key, **`sync`** SHALL set **`excluded`** and **`exclusion_reason`** consistent with the **origin classification** for that routing context: **`excluded`** **`false`** and **`exclusion_reason`** empty when origin-included or when no allowlist applies; **`excluded`** **`true`** and non-empty **`exclusion_reason`** when origin-excluded.

#### Scenario: Included issue clears exclusion flags

- **WHEN** an issue is origin-included
- **THEN** the upsert SHALL persist **`excluded`** **`false`** and **`exclusion_reason`** empty

#### Scenario: Excluded issue records reason

- **WHEN** an issue is origin-excluded because **`snyk_project_origin`** is **`cli`** and the allowlist excludes **`cli`**
- **THEN** the upsert SHALL persist **`excluded`** **`true`** and **`exclusion_reason`** **`origin_not_in_allowlist`**

---

### Requirement: One sync run orchestrates Snyk list, mapping, and Azure Boards updates

The application SHALL provide a **`sync`** command (argparse subcommand implemented under **`src/commands/`**, dispatched from **`src/main.py`**) that performs **one** synchronization run by invoking orchestration implemented under **`src/sync/`** (Python package `sync`). That run SHALL load merged configuration, obtain issues from the Snyk Issues API using **group-scoped** list operations **when `azure_boards.org_mappings` is absent or empty**, or using **org-scoped** list operations **for each non-empty `org_mappings` row** when **`org_mappings`** is present and non-empty, with filters aligned to **P2-FR-1**, **`azure_boards.defaults.severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`** (when enabled), **`effective_severity_level`** encoding per **`snyk-issues-client`**, and **effective `sync_included_snyk_origins`** per **`application-config`**, read and write rows through the **`MappingStore`** abstraction, and invoke the **Azure DevOps** client for work item create, update, close, and optional comments **only for issues that are not origin-excluded** when an origin allowlist applies. For each **`org_mappings`** row, the run SHALL use that row’s effective **`organization`**, **`project`**, and **effective** work item and policy settings (**`defaults`** merged with that row’s **`overrides`**) and **effective** **`work_item_template`** per **`application-config`** merge rules. The sync run SHALL obtain **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** only via the same environment-variable rules as the respective clients; it SHALL NOT introduce new secret sources.

#### Scenario: Sync entrypoint lives under commands

- **WHEN** a developer inspects CLI wiring for **`sync`**
- **THEN** argparse registration and argument-to-service wiring SHALL reside under **`src/commands/`** and **`src/main.py`** SHALL delegate without embedding subcommand logic

#### Scenario: Sync orchestration lives under src/sync

- **WHEN** a developer inspects implementation of the per-issue loop, lifecycle derivation, and patch assembly for **`sync`**
- **THEN** that logic SHALL reside under **`src/sync/`** (not under **`src/commands/`**)

#### Scenario: Sync uses merged configuration and mapping store

- **WHEN** the operator runs **`sync`** with a valid configuration path and environment secrets set
- **THEN** the run SHALL use merged **`azure_boards`**, **`snyk`**, **`work_item_template`**, and mapping store settings from the **`application-config`** capability before issuing Snyk or Azure DevOps calls

#### Scenario: Multi-mapping sync uses org-scoped Snyk list per row

- **WHEN** merged configuration includes at least one valid **`org_mappings`** entry
- **THEN** the run SHALL list issues from Snyk using **`snyk_org_id`** for each such entry and SHALL route Azure DevOps operations for issues from that list to that entry’s effective **`organization`** and **`project`** when those issues are not origin-excluded

---

### Requirement: Sync validates snyk_org_slug for org_mappings before work item patches

Before the **`sync`** run issues **any** Snyk Issues API HTTP requests, **`sync`** SHALL resolve the effective **`snyk_org_slug`** per **`application-config`** for each routing context. When **`org_mappings`** is non-empty, each active mapping row’s **`snyk_org_slug`** SHALL be non-empty (loader-enforced for YAML; validation covers in-memory edge cases) or **`sync`** SHALL exit non-zero with a clear, non-secret error. When **group-only** issue listing is used (no effective **`org_mappings`**), there is no configured org slug; composed Snyk UI links MAY use an empty org path segment until a later product change adds configuration for group mode.

#### Scenario: Org mappings sync fails when effective slug missing for a row

- **WHEN** an **`org_mappings`** row has an empty effective **`snyk_org_slug`** (in-memory misconfiguration)
- **THEN** **`sync`** SHALL exit non-zero before any Snyk Issues API request with an error that does not include secrets

---

### Requirement: Normalized issue records MAY carry snyk_project_name from JSON:API included

When the Issues API response includes JSON:API **`included`** resources that resolve **`relationships.scan_item`** (e.g. **`project`** with **`attributes.name`**), the normalized issue record used by **`sync`** SHALL expose **`snyk_project_name`** when that name can be resolved. When **`included`** is absent on list responses but present on **GET issue**, enrichment SHALL merge **`snyk_project_name`** onto the working record when missing.

#### Scenario: Included project supplies scan target display name

- **WHEN** the list or GET response **`included`** array contains the **`scan_item`** project resource with **`attributes.name`**
- **THEN** the normalized or enriched record SHALL include **`snyk_project_name`** for downstream title and description assembly

---

### Requirement: Optional work item description appendix from configuration

When **`sync`** assembles plain text for the **effective work item description field**, it SHALL first produce the default sections defined by **`sync-lifecycle`** (finding metadata, Snyk link block, etc.). When the effective **`work_item_description_appendix`** string per **`application-config`** is **non-empty** after stripping leading and trailing whitespace, **`sync`** SHALL append **`"\n\n"`** followed by that appendix to the plain-text assembly **before** HTML conversion and **before** applying the maximum description length limit.

When the effective appendix is empty (omitted, empty string, or whitespace-only after strip), **`sync`** SHALL NOT add extra paragraphs for this feature.

#### Scenario: Appendix non-empty adds trailing paragraph block

- **WHEN** merged configuration supplies a non-empty **`work_item_description_appendix`** for the active routing context
- **THEN** the plain-text description assembly for the effective description field SHALL end with a block separated from prior content by at least one blank line and SHALL include the appendix text verbatim (subject to truncation)

#### Scenario: Appendix empty leaves assembly unchanged

- **WHEN** the effective **`work_item_description_appendix`** is empty after strip
- **THEN** the plain-text description SHALL match the default assembly with no appendix paragraphs added

---

### Requirement: System.Description is HTML-safe for Azure Boards rendering

The JSON Patch value written to the **effective work item description field** SHALL be HTML suitable for Azure DevOps rich-text fields: plain-text assembly split on blank lines into paragraphs (**`<p>...</p>`**), single line breaks within a paragraph as **`<br />`**, and **HTML entity escaping** for dynamic/API-supplied text **and** for YAML-supplied **`work_item_description_appendix`** text so **`System.Title`** and the description field value cannot inject markup from issue payloads or configuration.

Within each paragraph block (except the dedicated **Open in Snyk** block described in **P2-FR-5.4**), **`http://`** and **`https://`** URL substrings in the plain-text assembly SHALL be rendered as HTML hyperlinks (**`<a href="…">…</a>`**) with **`href`** and visible link text HTML-escaped. Only **`http://`** and **`https://`** schemes SHALL be linkified; other schemes (for example **`javascript:`**) SHALL remain escaped literal text. Trailing punctuation immediately following a detected URL (for example **`.`**, **`,`**, **`;`**, **`:`**, **`)`**) SHALL NOT be included in **`href`**.

#### Scenario: Plain assembly becomes paragraphs

- **WHEN** plain-text assembly contains two blocks separated by a blank line
- **THEN** the description-field patch value SHALL contain two **`<p>`** paragraphs (or equivalent) preserving separation in the Boards web UI

#### Scenario: Appendix text is escaped like other description content

- **WHEN** **`work_item_description_appendix`** contains characters that require HTML escaping (for example **`&`**, **`<`**, **`>`**) outside of an **`http(s)`** URL
- **THEN** the description-field patch value SHALL escape those characters appropriately so they render as literal characters in Azure Boards

#### Scenario: Appendix https URL becomes a hyperlink

- **WHEN** **`work_item_description_appendix`** contains a substring **`https://`** URL
- **THEN** the description-field patch value SHALL include an **`<a href="…">`** element for that URL with escaped **`href`** and escaped visible link text

#### Scenario: Non-http schemes are not linkified

- **WHEN** plain-text assembly contains **`javascript:alert(1)`** or similar non-**`http(s)`** scheme
- **THEN** the description-field patch value SHALL NOT emit a clickable **`href`** for that substring

---

### Requirement: Normative Snyk lifecycle inputs exclude coordinates state

For synchronization policy, the application SHALL derive finding lifecycle **only** from each issue’s **`data[].attributes.status`** and **`data[].attributes.ignored`** as returned by the Snyk Issues API (including values carried on normalized issue records). The application SHALL **not** treat **`coordinates[].state`** as authoritative for whether a finding is open, fixed, ignored, or eligible for create/close/reopen decisions.

#### Scenario: Coordinates state does not override attributes

- **WHEN** `coordinates[].state` disagrees with `attributes.status` / `attributes.ignored`
- **THEN** sync decisions SHALL follow **attributes** only and SHALL NOT use `coordinates[].state` for open/close/reopen policy

---

### Requirement: Derived snyk_status for storage and transitions

The mapping store SHALL persist **`snyk_status`** as exactly one derived string per row, one of **`open`**, **`resolved`**, or **`ignored`**, computed per issue as follows: if **`ignored`** is true → **`ignored`**; else if **`status`** equals **`resolved`** → **`resolved`**; else if **`status`** equals **`open`** and **`ignored`** is false → **`open`**; else if **`status`** is any other value → the issue SHALL be **skipped** for that run and the application SHALL log an **error** that includes the unexpected **`status`** value and SHALL NOT include secrets or credential material.

The **close path** for Azure Boards SHALL apply when derived **`snyk_status`** is **`resolved`** or **`ignored`** (both are “closed path” from a Boards lifecycle perspective). The stored label distinguishes **P2-FR-3** vs **P2-FR-4** for audit (**P2-FR-9**) even though the transition target state may be the same.

#### Scenario: Ignored takes precedence for stored label

- **WHEN** `ignored` is true regardless of other attribute fields needed for logging
- **THEN** the stored `snyk_status` SHALL be **`ignored`** before evaluating `resolved`

#### Scenario: Resolved maps to stored resolved

- **WHEN** `ignored` is false and `status` is **`resolved`**
- **THEN** the stored `snyk_status` SHALL be **`resolved`**

#### Scenario: Open active maps to stored open

- **WHEN** `ignored` is false and `status` is **`open`**
- **THEN** the stored `snyk_status` SHALL be **`open`**

#### Scenario: Unexpected status skips with error log

- **WHEN** `status` is neither `open` nor `resolved` (and the issue is not classified as ignored by the rule above)
- **THEN** the sync run SHALL log an error naming the unexpected `status` and SHALL skip further processing for that issue without terminating the whole run

---

### Requirement: P2-FR-11 creation disabled semantics

When **`azure_boards.defaults.create_new_work_items`** is **`false`** (after merge with **`org_mappings[].overrides`** where applicable), the **`sync`** command SHALL NOT create new Azure Boards work items and SHALL NOT insert new mapping rows. It SHALL still update and close work items that already have a mapping row for the same natural key **`(group_id, org_id, project_id, issue_id)`**. Findings with **no** mapping row SHALL be left untouched (no work item creation and no new mapping insert), even if they satisfy **P2-FR-1**.

#### Scenario: No create and no new mapping when disabled

- **WHEN** **`azure_boards.defaults.create_new_work_items`** is `false` and a qualifying Snyk issue has no mapping row
- **THEN** the run SHALL NOT call Azure DevOps create and SHALL NOT insert a mapping row for that issue

#### Scenario: Updates and closes still allowed when disabled

- **WHEN** `create_new_work_items` is `false` and a mapping row exists for the issue
- **THEN** the run MAY update fields/tags/state and MAY close the linked work item per the close path rules

---

### Requirement: P2-FR-2 default assignee is Unassigned

On work item **create**, the application SHALL **not** set **`System.AssignedTo`** unless the merged **`work_item_template`** explicitly supplies an operation or field mapping that assigns a user. Omitting assignee SHALL represent the operator’s **Unassigned** default (**P2-FR-2**) as “no assignee set” for the work item process, not as a Boards **state** name.

#### Scenario: Create omits assignee without template assignment

- **WHEN** `work_item_template` does not specify `System.AssignedTo`
- **THEN** the JSON Patch for create SHALL not include an assignment for `System.AssignedTo`

---

### Requirement: P2-FR-8 reopen creates a new work item

When a finding previously warranted a **closed** Boards work item under this policy (stored derived **`snyk_status`** was **`resolved`** or **`ignored`**) and later satisfies **`ignored` == false** and **`status` == `open`**, behavior SHALL be governed by merged **`azure_boards.defaults.reopen_work_item_policy`** (and per-row **`overrides`**):

- When **`new_work_item`**, the application SHALL **create a new** Azure Boards work item for the active finding. The **prior** work item SHALL remain in its closed disposition unless separately updated by policy; the application SHALL **not** silently reactivate the old work item as the active ticket.
- When **`reopen_existing`**, the application SHALL attempt to transition the **existing** mapped work item (**`work_item_id`** on the mapping row) to **`azure_boards.defaults.work_item_state_active`** (merged). If that work item **cannot be found** (for example Azure DevOps returns not found for the stored id), the application SHALL **fallback** to the **`new_work_item`** path for this transition and SHALL record the prior id in the audit comment.

In all cases, **`sync`** SHALL add an audit comment per **P2-FR-9** on the **active** work item being commented (new or reopened): when **`new_work_item`** creates a replacement ticket, the comment SHALL reference the **previous** work item id and SHOULD include a Boards URL when safely constructible; when **`reopen_existing`** succeeds, the comment SHALL document the lifecycle transition.

#### Scenario: New work item id replaces mapping on reopen policy new_work_item

- **WHEN** effective **`reopen_work_item_policy`** is **`new_work_item`** and a new work item is created for a reopened finding with the same natural key
- **THEN** the mapping store SHALL upsert the row so **`work_item_id`** (and related fields) refer to the **new** work item

#### Scenario: Reopen existing transitions mapped work item when found

- **WHEN** effective **`reopen_work_item_policy`** is **`reopen_existing`** and the stored **`work_item_id`** exists in Azure DevOps
- **THEN** the sync SHALL transition that work item toward **`work_item_state_active`** and SHALL not create a second open work item for the same natural key unless fallback applies

#### Scenario: Reopen existing falls back when work item missing

- **WHEN** effective **`reopen_work_item_policy`** is **`reopen_existing`** but the stored **`work_item_id`** no longer exists in Azure DevOps
- **THEN** the sync SHALL create a new work item as in **`new_work_item`** and the audit trail SHALL mention the missing prior id

---

### Requirement: P2-FR-9 audit comment on derived snyk_status change

When the sync run detects that the newly derived **`snyk_status`** differs from the **`snyk_status`** previously stored in the mapping row for the same natural key, the application SHALL add a **work item comment** via the Azure DevOps comments API whose text includes the **old → new** derived status transition, the **Snyk issue key**, and safe non-secret identifiers as needed. The comment SHALL NOT include secrets, tokens, or full raw API bodies. If the composed text exceeds **4000** characters, the application SHALL truncate and append **`[truncated]`** while preserving the prohibition on secrets.

#### Scenario: Comment on transition only

- **WHEN** derived `snyk_status` equals the stored value for that issue
- **THEN** the application SHALL NOT add a **P2-FR-9** audit comment solely for that equality

#### Scenario: Comment includes old and new labels

- **WHEN** stored `snyk_status` was `resolved` and the newly derived value is `open`
- **THEN** the added comment text SHALL include both the previous and new derived labels in a clear `old → new` form along with the Snyk issue key

---

### Requirement: P2-FR-10 configurable tags from work_item_template

On work item **create** and **update**, the application SHALL set **`System.Tags`** (when a tags patch is emitted per existing rules) from the **combined** tag list:

1. **Operator tags:** every tag from the merged **`work_item_template.tags`** list after **`application-config`** merge and dedupe, **except** that any operator-supplied tag whose string starts with **`Snyk-Severity-`** or **`Snyk-Type-`** SHALL be **omitted** from this segment (reserved for managed tags; see **`application-config`**).
2. **Managed tags:** zero, one, or two tags derived from the **current** Snyk issue on that sync run, as specified in **Snyk-derived severity and finding-type work item tags**.

**Order** on the work item SHALL be: all operator tags from (1) in their merge order, then managed tags from (2) in the order **severity**, then **type**. **No operator tag** from (1) SHALL be dropped solely because managed tags are present.

Tags SHALL be applied using Azure DevOps–compatible JSON Patch for the configured work item type. When the combined list from (1) and (2) is **empty**, **`System.Tags`** patch operations SHALL be **omitted** (sync SHALL not fail solely for tags).

#### Scenario: Empty tags list is valid

- **WHEN** `work_item_template.tags` is absent or an empty list after merge and no managed severity or type tag is derivable for the issue
- **THEN** the sync run SHALL not fail solely for tags and SHALL proceed without adding tags beyond those implied by other patch operations

#### Scenario: Config tags preserved with derived tags

- **WHEN** merged `work_item_template.tags` contains `Snyk` and `Security` and the issue yields managed tags `Snyk-Severity-high` and `Snyk-Type-open_source`
- **THEN** the applied `System.Tags` value SHALL include `Snyk`, `Security`, `Snyk-Severity-high`, and `Snyk-Type-open_source` in that order (semicolon-separated per Azure DevOps rules)

---

### Requirement: Snyk-derived severity and finding-type work item tags

For each **origin-included** issue where **`sync`** performs an Azure DevOps work item **create** or **update** through the same JSON Patch assembly used for **`System.Title`**, the **effective work item description field**, **`System.State`**, and template operations, the application SHALL incorporate **managed** tags derived from the **current** Snyk issue payload for that run into the combined tag list (and therefore into **`System.Tags`** when the combined list is non-empty):

- **Severity:** at most one tag of the form **`Snyk-Severity-{level}`** where **`level`** is **`low`**, **`medium`**, **`high`**, or **`critical`**, normalized from **`effective_severity_level`** (or equivalent field on the normalized issue record). If the level is missing or not one of these after normalization, **no** severity managed tag SHALL be emitted.
- **Finding type:** at most one tag of the form **`Snyk-Type-{suffix}`**. The suffix SHALL map deterministically from Snyk issue **`attributes.type`** after normalization (**strip**, **lowercase**, **hyphens/spaces→underscore**). Supported REST enums include **`package_vulnerability`**, **`license`**, **`cloud`**, **`code`**, **`custom`**, and **`config`**. The application SHALL emit **`Snyk-Type-license`** when the enum is **`license`** (synonym **`licensing`** maps like **`license`**). It SHALL emit **`Snyk-Type-custom`** when the enum is **`custom`**. It SHALL map **`package_vulnerability`** to **`Snyk-Type-open_source`** (aligning OSS-style findings). It SHALL map **`cloud`** and **`config`** to **`Snyk-Type-iac`**. It SHALL map **`code`** to **`Snyk-Type-code`**. Implementation MAY recognize additional synonyms (for example **`container`** → **`Snyk-Type-container`**) documented in **`README.md`**. Values that normalize to unrecognized tokens omit the managed type tag.

When the effective severity or **mapped type suffix** **changes** between sync runs, the new managed tag values SHALL **replace** the previous values for that dimension **by virtue of** the combined **`System.Tags`** payload for that run (no duplicate **`Snyk-Severity-*`** or **`Snyk-Type-*`** tags from the application).

#### Scenario: Severity downgrade updates managed tag

- **WHEN** a work item was last synced with **`Snyk-Severity-high`** and the current issue **`effective_severity_level`** normalizes to **`medium`**
- **THEN** the **`System.Tags`** payload for that update SHALL include **`Snyk-Severity-medium`** and SHALL NOT include **`Snyk-Severity-high`**

#### Scenario: Origin-excluded issues skip tag mutation

- **WHEN** an issue is **origin-excluded** per inclusive allowlist rules and **`sync`** does not invoke Azure DevOps mutations for it
- **THEN** the application SHALL not add or update managed tags on any work item for that issue on that run

#### Scenario: Unmapped issue type omits type tag only

- **WHEN** severity normalizes to **`high`** but issue **`attributes.type`** normalizes to a token with no **`Snyk-Type-*`** mapping
- **THEN** the combined tag list MAY include **`Snyk-Severity-high`** and SHALL omit a **`Snyk-Type-*`** managed tag for that run

#### Scenario: License issue yields Snyk-Type-license tag

- **WHEN** **`attributes.type`** is **`license`**
- **THEN** the managed finding-type tag SHALL be **`Snyk-Type-license`**

---

### Requirement: P2-FR-5.1 primary package and title or description body

The **primary package** SHALL be taken from the **first** `coordinates[]` element in API order that contains a `representations[]` entry with a **`dependency`** field set.

For **code** issues (**`attributes.type`** indicating code analysis, for example **`code`**), the description assembly SHALL include **file path** and **line range** derived from **`coordinates[].representations[].sourceLocation`** when present (see **`data/sample_coord.local.json`**: **`file`**, **`region.start.line`**, **`region.end.line`**).

The human-readable text used for **`System.Title`** on create SHALL be **`{target} - {issue}`** when **`target`** can be resolved, where:

- **`issue`** is **`attributes.title`** when non-empty; otherwise the primary package line (**`package@version`**); otherwise a short fallback label.
- **`target`** SHALL prefer **`snyk_project_name`** persisted on the mapping row when non-empty; next **`snyk_project_name`** on the normalized/enriched issue record when non-empty; next **`{effective_organization} / {effective_project}`** from merged **`azure_boards.defaults`** and **`org_mappings`** context. When no **`target`** label can be resolved, **`System.Title`** SHALL be **`issue`** only (no **` - `** prefix).

For the **effective work item description field**, the application SHALL assemble content in **section blocks** (blank-line-separated in plain assembly before HTML wrapping) so operators see distinct paragraphs in Azure Boards. Assembly SHALL include at minimum:

1. **Context:** **Snyk project** display name and **origin** when known (**`snyk_project_name`**, **`snyk_project_origin`** from mapping row or APIs), **severity**, **Snyk issue key**.
2. **Finding:** primary package and optional path hints from **`coordinates[]`** when present; for **code** issues, **file + lines** per **`sourceLocation`** when present.
3. **How to fix:** recommended upgrade/version strings extracted from **`coordinates[].remedies`** (**`upgradeTo`**, **`changes[].upgradeTo`**, etc.) and dependency representation hints when present; formatted **`coordinates[].remedies`** narrative (**`type: description`** style when structured).
4. **`attributes.description`** when present (vulnerability narrative).
5. **Classification:** **P2-FR-5.2**, **P2-FR-5.3**, and fix availability (**P2-FR-5.5** subset—see below).

When the issue record produced by **list** operations omits **`attributes.description`** or **`coordinates[].remedies`** (or other fields needed for the paragraphs above), the application SHALL issue **`GET /groups/{group_id}/issues/{issue_id}`** or **`GET /orgs/{org_id}/issues/{issue_id}`** in the **same** scope as the list operation for that issue’s **`rest_issue_id`** (JSON:API **`data.id`**), merge **`attributes`** and **`coordinates`** from the GET response into the working issue view per the active change **`design.md`**, then assemble the description body for the effective description field. The client SHALL use the same **`version`** query parameter as documented for Issues API requests.

If fields remain absent after GET, the description SHALL still include all other available metadata; the run SHALL NOT fail solely because narrative or remedies are missing.

#### Scenario: Primary package from first dependency representation

- **WHEN** multiple coordinates include dependency representations
- **THEN** the sync SHALL select the first such coordinate in API order for the primary package line

#### Scenario: Title uses mapping-backed Snyk project name when present

- **WHEN** **`snyk_project_name`** on the mapping row is non-empty and **`attributes.title`** is non-empty
- **THEN** **`System.Title`** SHALL begin with **`{snyk_project_name} - `** followed by the issue title text (subject to length limits)

#### Scenario: Description includes narrative when attributes.description is present

- **WHEN** the working issue attributes include non-empty **`description`**
- **THEN** the effective description field body SHALL include that text in addition to other required sections

#### Scenario: GET issue enriches payload when list omits remedies or description

- **WHEN** the list payload lacks **`description`** or **`remedies`** and GET-by-id returns them for the same issue
- **THEN** the effective description field body SHALL incorporate those fields after the GET merge

#### Scenario: Code issue includes file and line location when sourceLocation present

- **WHEN** **`sourceLocation.file`** and line fields exist under **`coordinates[].representations[]`**
- **THEN** the effective description field body SHALL include human-readable file path and line range for that finding

---

### Requirement: P2-FR-5.2 finding type verbatim

The work item metadata SHALL record the Snyk **`attributes.type`** string **verbatim** (for example `package_vulnerability`, `license`, `cloud`, `code`, `custom`, `config`) without mapping tables to alternate labels.

#### Scenario: Type copied verbatim

- **WHEN** `attributes.type` is `package_vulnerability`
- **THEN** the value written to the chosen work item field for “finding type” SHALL be exactly `package_vulnerability`

---

### Requirement: P2-FR-5.3 CWE and CVE extraction

The application SHALL extract **CWE** identifiers from **`attributes.classes`** entries where **`source`** equals **`CWE`**. It SHALL extract **CVE** identifiers from **`attributes.problems`** entries whose **`id`** matches the pattern **`CVE-*`**, and SHALL include each such problem’s **`url`** in work item text or fields when present.

When a CVE **`url`** appears in the effective work item description field body, it SHALL be rendered as an HTML hyperlink per **System.Description is HTML-safe for Azure Boards rendering** (in addition to appearing alongside the CVE id in plain-text assembly).

#### Scenario: CVE includes url when present

- **WHEN** a matching `attributes.problems` entry includes a `url`
- **THEN** the created or updated work item content SHALL include that URL alongside the CVE id

#### Scenario: CVE NVD url is clickable in description

- **WHEN** plain-text assembly includes a CVE line containing an **`https://`** URL from **`attributes.problems`**
- **THEN** the description-field patch value SHALL include an **`<a href="…">`** element for that URL

---

### Requirement: P2-FR-5.4 direct Snyk web UI issue URL

The application SHALL construct exactly **one** canonical HTTPS URL per work item that satisfies **P2-FR-5.4** using this structure:

`{app_base_url}/org/{snyk_org_slug}/project/{project_id}#issue-{issue_key}`

where:

- **`{app_base_url}`** is the effective Snyk **web app origin** from **`application-config`** (default **`https://app.snyk.io`**, override via **`snyk.app_base_url`**, **`SNYK_APP_BASE_URL`**, or **`--snyk-app-base-url`** on **`sync`**).
- **`{snyk_org_slug}`** is the effective organization slug from **`application-config`** for the routing context processing the issue (**`org_mappings`** rows supply it; group-only sync MAY leave it empty until configuration exists).
- **`{project_id}`** is **`relationships.scan_item.data.id`** from the issue resource.
- **`{issue_key}`** is **`attributes.key`** from the issue resource.

The fragment SHALL be **`#issue-`** immediately followed by **`attributes.key`** verbatim; URL-encoding SHALL be applied only as required for a valid HTTP URL.

The application SHALL NOT emit **`https://app.snyk.io/group/{group_id}/issues/{id}`** or other deprecated **best-effort** link patterns as the primary **P2-FR-5.4** link line.

When the URL is rendered inside the **effective work item description field**, it SHALL appear as an HTML **hyperlink** (**`<a href="...">...</a>`**) with **href** set to the canonical URL and link text that identifies the issue in Snyk, subject to the same HTML entity escaping rules as other dynamic description content (**HTML-safe** assembly). The **"Open in Snyk"** description block SHALL receive the same hyperlink treatment regardless of the configured **`app_base_url`** origin.

#### Scenario: Link uses config slug and API identifiers

- **WHEN** sync composes the **P2-FR-5.4** link for an issue with known **`snyk_org_slug`**, **`scan_item`**, and **`attributes.key`**
- **THEN** the URL SHALL match the canonical template above with those substitutions

#### Scenario: Regional app base URL in link

- **WHEN** merged configuration sets **`snyk.app_base_url`** to **`https://app.eu.snyk.io`** and sync composes the **P2-FR-5.4** link for an issue with known slug, project id, and issue key
- **THEN** the URL origin SHALL be **`https://app.eu.snyk.io`** and the path and fragment SHALL match the canonical template

#### Scenario: Fragment uses issue key

- **WHEN** **`attributes.key`** is `SNYK-PYTHON-H11-10293728`
- **THEN** the URL fragment SHALL end with `#issue-SNYK-PYTHON-H11-10293728`

#### Scenario: Description renders link as HTML anchor

- **WHEN** the **P2-FR-5.4** URL is written into the effective work item description field
- **THEN** the stored HTML SHALL include a single **`a`** element with **`href`** equal to the canonical HTTPS URL (escaped as required)

### Requirement: P2-FR-5.5 fix availability and fix guidance

The application SHALL read boolean fix signals from each **`coordinates[]`** object: **`is_upgradeable`**, **`is_patchable`**, **`is_fixable_manually`**, **`is_fixable_snyk`**, **`is_fixable_upstream`**.

The work item description SHALL **not** surface **`is_pinnable`** in the human-readable fix-availability summary (low signal for typical developer workflows).

The work item description SHALL summarize **true** flags using **human-readable** labels (not raw field names) together with the issue **title** and the **primary package** line from **P2-FR-5.1** where applicable.

When **`coordinates[].remedies`** or other structured fix guidance is present on the issue payload (including after **GET** enrichment per **P2-FR-5.1**), the work item description SHALL include that guidance in human-readable form. When structured fields carry **recommended upgrade** or **target version** identifiers (**`upgradeTo`**, **`changes[].upgradeTo`**, or dependency version hints documented in **`design.md`**), the description SHALL surface those as explicit **upgrade / fix version** guidance when available.

#### Scenario: Summary omits is_pinnable

- **WHEN** only **`is_pinnable`** is true among fix signals
- **THEN** the human-readable fix-availability line SHALL NOT imply a meaningful automated upgrade path solely from pin semantics (implementation MAY omit **`is_pinnable`** from the displayed summary)

#### Scenario: Remedies rendered when coordinates contain remedies

- **WHEN** **`coordinates[].remedies`** is present after list and GET merge
- **THEN** the work item description SHALL include formatted remedy guidance

---

### Requirement: System.Title required on create

Every **`POST`** work item **create** SHALL include a JSON Patch operation that sets **`System.Title`** to the non-empty string composed per **P2-FR-5.1** / primary package rule. Additional patch operations for fields such as **Area Path**, **Iteration Path**, **tags**, and custom fields SHALL come from **`work_item_template`** (including **`json_patch`** list entries) merged according to the active change **`design.md`**, without reading secrets from YAML.

#### Scenario: Create rejected without title operation

- **WHEN** internal patch assembly would omit `System.Title`
- **THEN** the implementation tests SHALL treat that as a defect and the sync SHALL not send create requests without `System.Title`

---

### Requirement: Recreate Azure Boards work item when mapped id is missing and finding is open

When issues sync persistence holds a row with a **non-empty** **`work_item_id`**, **`sync`** batch-prefetches Azure DevOps work items for the active routing context, and the stored id is **not** returned (for example the work item was deleted or is unreadable with **`errorPolicy=Omit`**), behavior SHALL depend on the **derived Snyk status** for that issue:

- When derived status is **`open`** and **`create_new_work_items`** is **true**, **`sync`** SHALL create a **new** Azure Boards work item using the **current** merged effective **`work_item_type`** and the same gates as unmapped creation (**`create_only_when_fix_available`**, origin allowlist, severity/list filters already applied). It SHALL upsert the mapping row so **`work_item_id`** refers to the **new** work item and SHALL add an audit comment on the new work item referencing the **prior** work item id (and SHOULD include a Boards edit URL when safely constructible), consistent with **P2-FR-8** replacement semantics.
- When derived status is **`open`** and **`create_new_work_items`** is **false**, **`sync`** SHALL log and skip Azure DevOps mutation for that issue without failing the run.
- When derived status is **`resolved`** or **`ignored`**, **`sync`** SHALL **not** create a replacement work item; it SHALL log and skip Azure DevOps mutation for that issue without failing the run.

Batch prefetch of mapped work item ids SHALL **not** cause a global sync failure when individual ids are missing from Azure DevOps.

#### Scenario: Open issue with deleted mapped work item is recreated

- **WHEN** the mapping row has **`work_item_id`** **123**, batch prefetch omits **123**, derived status is **`open`**, **`create_new_work_items`** is **true**, and other create gates pass
- **THEN** **`sync`** SHALL create a new work item using the current merged **`work_item_type`**, upsert the mapping with the new id, and add an audit comment mentioning prior id **123**

#### Scenario: Resolved issue with deleted mapped work item is not recreated

- **WHEN** the mapping row has **`work_item_id`** **123**, batch prefetch omits **123**, and derived status is **`resolved`**
- **THEN** **`sync`** SHALL skip Azure DevOps mutation for that issue and SHALL NOT create a new work item

#### Scenario: One missing id does not fail the sync run

- **WHEN** batch prefetch includes at least one missing work item id and at least one valid id
- **THEN** the sync run SHALL complete the per-issue loop and SHALL exit **0** unless a separate global failure occurs

#### Scenario: create_new_work_items false skips recreate

- **WHEN** the mapped work item id is missing, derived status is **`open`**, and **`create_new_work_items`** is **false**
- **THEN** **`sync`** SHALL skip Azure DevOps mutation for that issue

---

### Requirement: Work item type and Boards state names from configuration

Work item **create** SHALL use the merged effective **`work_item_type`** from **`azure_boards.defaults`** (and **`org_mappings[].overrides`**) as the WIT **`$type`** segment (default **`Task`** when omitted after merge). **Create** includes new work items for unmapped issues, reopen replacement paths, and replacement creates when a mapped work item id is missing and derived status is **`open`** per **Recreate Azure Boards work item when mapped id is missing and finding is open**. **Update** paths (**`PATCH`** on an existing id) SHALL **not** change the Boards work item type; configuration changes to **`work_item_type`** apply to **new** work items only, not re-typing of existing mapped items. When a work item shall represent an **active** finding, the sync SHALL transition or set Boards **`System.State`** to the merged **`work_item_state_active`**. When a finding is on the **close path** (**derived `snyk_status`** is **`resolved`** or **`ignored`**), the sync SHALL set the Boards closed disposition using the merged **`work_item_state_closed`**. Operators MUST configure values that exist for their process; the application SHALL treat these as opaque strings after non-empty validation.

#### Scenario: Defaults apply when keys omitted

- **WHEN** the three keys are omitted from YAML and not overridden by higher-precedence layers
- **THEN** the effective values SHALL be **`Task`**, **`New`**, and **`Closed`** respectively for sync

#### Scenario: Config type change does not re-type existing mapped work items

- **WHEN** a mapping row references an existing Azure DevOps work item id and the operator changes merged **`work_item_type`** from **`Bug`** to **`Task`**
- **THEN** **`sync`** SHALL continue to **`PATCH`** that existing work item by id and SHALL NOT recreate it solely because the configured type changed

---

### Requirement: Per-issue errors do not fail the whole sync run

For errors attributable to a **single** issue (for example Azure PATCH failure for one id, skip due to unexpected Snyk **`status`**, or a mapped Azure DevOps work item id that no longer exists), the application SHALL **log** a concise diagnostic without secrets, **skip** or **self-heal** that issue per the **Recreate Azure Boards work item when mapped id is missing and finding is open** requirement, and **continue** processing remaining issues. The process exit code SHALL be **`0`** when the run completes the full per-issue loop after startup succeeded, even if one or more issues were skipped or healed. **Non-zero** exit codes SHALL be reserved for failures that prevent starting the run or invalidate it globally (for example missing configuration, missing tokens, or client preflight errors before the per-issue loop).

#### Scenario: Exit zero with skips

- **WHEN** at least one issue is skipped due to a per-issue error and no global failure occurred
- **THEN** the process SHALL still exit with code **`0`**

#### Scenario: Exit zero after recreating missing mapped work items

- **WHEN** at least one issue is healed by creating a replacement work item because the prior mapped id was missing
- **THEN** the process SHALL still exit with code **`0`** when no global failure occurred

#### Scenario: Global config failure is non-zero

- **WHEN** required merged configuration or secrets for startup are missing
- **THEN** the process SHALL exit non-zero before issuing per-issue network calls

---

### Requirement: MappingStore is authoritative for current work item linkage

The **`MappingStore`** SHALL be the source of truth for whether a Snyk natural key **`(group_id, org_id, project_id, issue_id)`** currently maps to an Azure work item (**P2-FR-7**). The sync SHALL **upsert** rows on create and update paths and SHALL refresh stored **`snyk_status`**, **`work_item_id`**, and **`work_item_status`** (and other persisted routing fields) when new Snyk or Azure state is observed for that key.

#### Scenario: Upsert replaces work item id on reopen mapping update

- **WHEN** a new work item is created for an existing natural key per reopen rules
- **THEN** the store SHALL contain exactly one row for that tuple whose `work_item_id` matches the new work item

---

### Requirement: Azure reconciliation uses get or list-by-ids with cap 200

When the sync design requires reading Boards state for reconciliation, the application SHALL use **`GET` work item** or **`GET` work items by ids** via the **azure-devops-client**, requesting **at most 200** ids per list call (the client SHALL enforce the cap). The sync SHALL chunk larger sets into multiple calls of up to 200 ids each.

#### Scenario: More than 200 mapped ids are chunked

- **WHEN** more than 200 distinct mapped work items need refresh in one run
- **THEN** the application SHALL issue multiple list-by-ids calls with no more than 200 ids each

---

### Requirement: Sync run correlation and duration summary

The **`sync`** orchestration SHALL bind a unique **`sync_run_id`** for the duration of each **`sync`** invocation (via **`observability.sync_context`**) so **P2-FR-6.2** HTTP audit logs can be correlated.

The **`sync`** orchestration SHALL emit exactly **one** summary log record at the end of every **`sync`** invocation (all exit paths) containing **`sync_duration_seconds`**, **`sync_outcome`**, and **`sync_run_id`**, as specified in the **`observability`** capability.

#### Scenario: sync_run_id ties HTTP audits to summary

- **WHEN** **`sync`** runs to completion with logging enabled
- **THEN** HTTP audit logs from Snyk and Azure DevOps for that invocation SHALL carry the same **`sync_run_id`** as the final summary log

#### Scenario: Summary emitted once per invocation

- **WHEN** **`sync`** is invoked once
- **THEN** exactly one summary log with **`sync_duration_seconds`** SHALL be emitted for that invocation

### Requirement: Effective work item description field resolution

For each ADO routing context (**organization**, **project**, effective **`work_item_type`**, and merged **`work_item_description_field`** configuration), **`sync`** SHALL determine an **effective description field reference name** used for all Snyk narrative JSON Patch operations (create and update) in that context.

When **`work_item_description_field`** is **not** configured (auto mode), **`sync`** SHALL query Azure DevOps for fields defined on the effective work item type and SHALL select the first available reference name in this order:

1. **`System.Description`**
2. **`Microsoft.VSTS.TCM.ReproSteps`**

If neither reference name is present, **`sync`** SHALL exit non-zero **before** the per-issue loop with a clear, non-secret error identifying the organization, project, work item type, and attempted reference names.

When **`work_item_description_field`** **is** configured to a non-empty string, **`sync`** SHALL use that reference name directly without fallback. When ADO is reachable at startup, **`sync`** SHALL validate that the explicit reference name appears on the effective work item type’s field list and SHALL exit non-zero before the per-issue loop if validation fails.

Resolution SHALL occur at **`sync`** startup for each distinct routing context used in the run and MAY be cached for the duration of that run.

#### Scenario: Auto mode selects Description for Task

- **WHEN** auto mode is active, the effective work item type is **`Task`**, and **`System.Description`** exists on that type
- **THEN** the effective description field SHALL be **`System.Description`**

#### Scenario: Auto mode selects Repro Steps for Bug without Description

- **WHEN** auto mode is active, the effective work item type is **`Bug`**, **`System.Description`** is not defined on that type, and **`Microsoft.VSTS.TCM.ReproSteps`** is defined
- **THEN** the effective description field SHALL be **`Microsoft.VSTS.TCM.ReproSteps`**

#### Scenario: Explicit override bypasses fallback

- **WHEN** merged configuration sets **`work_item_description_field`** to **`Microsoft.VSTS.TCM.ReproSteps`** and **`System.Description`** also exists on the type
- **THEN** the effective description field SHALL be **`Microsoft.VSTS.TCM.ReproSteps`** only

#### Scenario: Auto mode fails when no supported field exists

- **WHEN** auto mode is active and neither **`System.Description`** nor **`Microsoft.VSTS.TCM.ReproSteps`** is defined on the effective work item type
- **THEN** **`sync`** SHALL fail before processing issues

---

### Requirement: Effective area path and assignee resolution for sync

For each issue processed by **`sync`**, after **`snyk_project_name`** and **`snyk_project_origin`** are known (from persisted mapping row and/or Snyk Projects API refresh per existing rules), the run SHALL resolve:

- **Effective ADO organization and project** per **`repo-area-path-mapping`**: CSV row **ADO Organization** and first **Area Path** segment when matched; otherwise merged YAML **`organization`** and **`project`** for the active routing context.
- **Effective area path** per **`repo-area-path-mapping`** precedence: CSV row full **Area Path** → **`org_mappings[].overrides.area_path`** → **`defaults.area_path`** → unset.
- **Effective assignee** per **`repo-area-path-mapping`**: when a CSV row matches with non-empty **Assignee (Optional)** or legacy **Assignee**, that value; otherwise merged template assignee rules unchanged.

Resolution SHALL occur per issue. The implementation MAY log **`ado_target_source`** as **`csv`** or **`config`** and **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, or **`none`** at INFO without secrets.

#### Scenario: CSV match supplies ADO target area path and assignee

- **WHEN** a CSV row matches with **`ADO Organization`** **`myado`**, **`Area Path`** **`Proj\\TeamA`**, and **`Assignee (Optional)`** **`user@example.com`**
- **THEN** the effective ADO organization SHALL be **`myado`**, effective ADO project SHALL be **`Proj`**, effective area path SHALL be **`Proj\\TeamA`**, and effective assignee SHALL be **`user@example.com`**

#### Scenario: No CSV match uses org override for area path

- **WHEN** no CSV row matches and merged **`overrides.area_path`** is **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamB`** and ADO org/project SHALL come from YAML

#### Scenario: No path configured omits AreaPath patch

- **WHEN** no CSV row matches and both org override and **`defaults.area_path`** are unset or whitespace-only
- **THEN** the effective area path SHALL be unset and **`sync`** SHALL NOT include **`System.AreaPath`** in the patch

---

### Requirement: System.AreaPath on work item create and recreate

When **`sync`** creates a new Azure Boards work item or recreates a work item (including missing mapped work item replacement, **routing migration** recreation, and **`reopen_work_item_policy`** paths that create a new item), and the effective area path is non-empty after trim, the JSON Patch sent to Azure DevOps SHALL include an **`add`** operation on **`/fields/System.AreaPath`** with that value.

Create and recreate operations SHALL target the **effective ADO organization and project** resolved for that issue (CSV or YAML).

When the effective assignee from resolution is non-empty, the create patch SHALL include **`/fields/System.AssignedTo`** with that value, overriding template assignee when CSV supplied it.

When effective area path is unset, create behavior for other fields SHALL be unchanged from prior requirements.

#### Scenario: Create sets area path from CSV in CSV ADO project

- **WHEN** **`sync`** creates a work item in CSV project **`PaymentsProject`** and effective area path is **`PaymentsProject\\Payments`**
- **THEN** the create JSON Patch SHALL include **`/fields/System.AreaPath`** with that value and REST calls SHALL use project **`PaymentsProject`**

#### Scenario: Create without resolved area path

- **WHEN** **`sync`** creates a work item and effective area path is unset
- **THEN** the create JSON Patch SHALL NOT include **`/fields/System.AreaPath`**

#### Scenario: Recreate applies area path like create

- **WHEN** **`sync`** recreates a work item (including routing migration) and effective area path is non-empty
- **THEN** the create JSON Patch for the new work item SHALL include **`/fields/System.AreaPath`**

---

### Requirement: System.AreaPath update and audit comment on path change

When **`sync`** updates an existing mapped work item in the **stored** ADO target (stored **`organization`** and **`project`** match the effective resolved target), and the effective area path is non-empty and **differs** from the work item’s current **`System.AreaPath`** field value (read from the normalized work item record or an explicit **`get_work_item`** fetch), **`sync`** SHALL:

1. Include **`/fields/System.AreaPath`** in the update JSON Patch with the new effective value.
2. After a successful update (or as part of the same successful mutation sequence), add a work item **audit comment** per **P2-FR-9** stating that the area path moved from the previous value to the new value.

When the previous **`System.AreaPath`** is missing or empty, the comment SHALL indicate the prior location as **`(unset)`** or equivalent non-secret placeholder documented in implementation.

When effective area path equals the current value, **`sync`** SHALL NOT patch **`System.AreaPath`** solely for this feature and SHALL NOT add an area-path move comment.

When effective assignee from CSV resolution is non-empty and differs from current **`System.AssignedTo`**, the update patch SHALL set **`/fields/System.AssignedTo`** to the CSV value.

When stored ADO target differs from effective resolved target, **`sync`** SHALL follow **Routing migration when CSV ADO target changes** instead of patching the work item in the old target.

#### Scenario: Update moves area path and comments

- **WHEN** the mapped work item has **`System.AreaPath`** **`Old\\Path`**, effective area path is **`New\\Path`**, stored and effective ADO targets match, and **`sync`** updates the work item
- **THEN** the update patch SHALL set **`System.AreaPath`** to **`New\\Path`** and an audit comment SHALL reference **`Old\\Path`** and **`New\\Path`**

#### Scenario: Unchanged area path skips move comment

- **WHEN** effective area path equals the work item’s current **`System.AreaPath`**
- **THEN** **`sync`** SHALL NOT add an area-path move audit comment for this feature

#### Scenario: CSV assignee applied on update

- **WHEN** a CSV row matches with **`Assignee (Optional)`** **`user@example.com`** and the work item’s assignee differs
- **THEN** the update patch SHALL set **`System.AssignedTo`** to **`user@example.com`**

#### Scenario: ADO target change triggers migration not in-place update

- **WHEN** stored mapping target is **`myado/OldProject`** and effective resolved target is **`myado/NewProject`**
- **THEN** **`sync`** SHALL NOT PATCH the work item in **`OldProject`** for routine open-issue updates and SHALL follow routing migration rules

---

### Requirement: Repo mapping CSV loaded at sync startup

**`sync`** SHALL load the effective **`repo-mapping.csv`** index once at startup after configuration merge and before the per-issue loop, per **`repo-area-path-mapping`**. CSV load failures SHALL cause **`sync`** to exit non-zero before processing issues.

Hot-reload of CSV content during a single run is out of scope; a new run after file update on Azure Files (following container restart/revision) reloads the file.

#### Scenario: Sync fails fast on invalid CSV

- **WHEN** the CSV contains duplicate lookup keys
- **THEN** **`sync`** SHALL exit non-zero before the per-issue loop

#### Scenario: Sync proceeds with valid CSV

- **WHEN** the CSV loads successfully
- **THEN** **`sync`** SHALL use the in-memory index for all issues in that run

---

### Requirement: Per-issue ADO target from repo mapping CSV

When a **`repo-mapping.csv`** row matches an issue, **`sync`** SHALL use the CSV-resolved **ADO organization** and **ADO project** (first **Area Path** segment) for all Azure DevOps Work Item Tracking REST calls for that issue, including create, update, comment, batch prefetch partition, and mapping-store **`organization`** / **`project`** fields on upsert.

When no CSV row matches, **`sync`** SHALL use the merged YAML **`organization`** and **`project`** for the active **`org_mappings`** iteration or group-scoped defaults (unchanged behavior).

**`sync`** SHALL NOT require multiple **`org_mappings`** rows for the same **`snyk_org_id`** to achieve multi-project routing; CSV supplies per-repo ADO targets within one Snyk org.

#### Scenario: Matched repo routes to CSV ADO project

- **WHEN** an issue's Snyk project matches a CSV row with **`ADO Organization`** **`myado`** and **`Area Path`** **`FrontendProject\\UI`**
- **THEN** **`sync`** SHALL create or update work items using organization **`myado`** and project **`FrontendProject`**

#### Scenario: Unmatched repo uses YAML ADO target

- **WHEN** no CSV row matches and the active **`org_mappings`** row has **`organization`** **`myado`** and **`project`** **`DefaultProject`**
- **THEN** **`sync`** SHALL use **`myado`** and **`DefaultProject`** for Azure DevOps calls for that issue

---

### Requirement: Multi-project batch work item prefetch

When **`sync`** batch-prefetches mapped work items before the per-issue loop, it SHALL group work item ids by the **stored** **`organization`** and **`project`** on each mapping row (using the active config target when no row exists). It SHALL invoke Azure DevOps **List work items (by ids)** once per distinct **(organization, project)** partition with **`errorPolicy=Omit`**.

A missing id in one partition SHALL NOT cause the entire **`sync`** run to fail.

#### Scenario: Prefetch partitions by stored ADO target

- **WHEN** mapping rows reference work items in **`myado/ProjectA`** and **`myado/ProjectB`**
- **THEN** **`sync`** SHALL issue separate batch list calls for each project before processing issues

#### Scenario: Single missing id does not abort run

- **WHEN** one mapped work item id is missing from ADO in a batch partition
- **THEN** **`sync`** SHALL continue processing other issues in the run

---

### Requirement: Routing migration when CSV ADO target changes

When a mapping row exists and the stored **`organization`** or **`project`** differs from the newly resolved effective ADO target for that issue, **`sync`** SHALL apply the following rules:

- If derived Snyk status is **`open`**, **`sync`** SHALL treat the row as requiring recreation in the new ADO target (subject to **`create_new_work_items`**, origin allowlist, and **`create_only_when_fix_available`** gates). After creating the replacement work item, **`sync`** SHALL upsert the mapping row with the new **`work_item_id`**, **`organization`**, and **`project`**, and SHALL add an audit comment on the **new** work item per **P2-FR-9** documenting the prior **`work_item_id`** and old and new ADO targets.

- If derived Snyk status is **`resolved`** or **`ignored`**, **`sync`** SHALL NOT recreate. When the prior work item is reachable in the **stored** ADO target, **`sync`** SHALL add an audit comment on that work item per **P2-FR-9** documenting the mapping retarget to the new ADO target. **`sync`** SHALL then upsert the mapping row with the new **`organization`** and **`project`** while retaining the existing **`work_item_id`**.

- When the prior work item returns **404** on the close path, **`sync`** SHALL upsert the mapping row with the new ADO target without ADO mutation and SHALL emit a structured log record (no secrets).

#### Scenario: Open issue routing migration recreates with audit comment

- **WHEN** a mapping row references work item **`W`** in **`O1/P1`**, CSV now resolves **`O2/P2`**, and derived Snyk status is **`open`**
- **THEN** **`sync`** SHALL create a new work item in **`O2/P2`**, upsert the mapping to the new id, and add an audit comment on the new work item referencing **`W`**, **`O1/P1`**, and **`O2/P2`**

#### Scenario: Resolved issue routing migration comments on existing work item

- **WHEN** derived status is **`resolved`**, the mapped work item exists in the stored old target, and CSV resolves a new ADO target
- **THEN** **`sync`** SHALL add an audit comment on the existing work item documenting the mapping retarget and SHALL upsert the store with the new **`organization`** and **`project`** without recreating

#### Scenario: Resolved issue migration skips comment when work item missing

- **WHEN** derived status is **`resolved`**, the mapped work item returns **404** in the stored old target, and CSV resolves a new ADO target
- **THEN** **`sync`** SHALL upsert the store with the new ADO target and SHALL NOT fail the run

