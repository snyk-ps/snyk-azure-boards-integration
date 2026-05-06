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

## Normative requirements

### Requirement: Persist Snyk project display metadata on mapping rows

The **`sync`** run SHALL persist **`snyk_project_name`** (from **`GET /orgs/{org_id}/projects/{project_id}`** **`attributes.name`**) and **`snyk_project_origin`** (from **`attributes.origin`**) on the mapping store row for the natural key, updating values when refreshed per **`design.md`**, so routine sync loops avoid repeating project GET for unchanged rows.

#### Scenario: Upsert stores project metadata

- **WHEN** sync obtains non-empty project **`name`** and **`origin`** from the Snyk Projects API for an issue’s **`project_id`**
- **THEN** the mapping upsert SHALL persist **`snyk_project_name`** and **`snyk_project_origin`** alongside existing routing fields

---

### Requirement: One sync run orchestrates Snyk list, mapping, and Azure Boards updates

The application SHALL provide a **`sync`** command (argparse subcommand implemented under **`src/commands/`**, dispatched from **`src/main.py`**) that performs **one** synchronization run by invoking orchestration implemented under **`src/sync/`** (Python package `sync`). That run SHALL load merged configuration, obtain issues from the Snyk Issues API using **group-scoped** list operations **when `azure_boards.org_mappings` is absent or empty**, or using **org-scoped** list operations **for each non-empty `org_mappings` row** when **`org_mappings`** is present and non-empty, with filters aligned to **P2-FR-1**, **`azure_boards.defaults.severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`** (when enabled), and **`effective_severity_level`** encoding per **`snyk-issues-client`**, read and write rows through the **`MappingStore`** abstraction, and invoke the **Azure DevOps** client for work item create, update, close, and optional comments. For each **`org_mappings`** row, the run SHALL use that row’s effective **`organization`**, **`project`**, and **effective** work item and policy settings (**`defaults`** merged with that row’s **`overrides`**) and **effective** **`work_item_template`** per **`application-config`** merge rules. The sync run SHALL obtain **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** only via the same environment-variable rules as the respective clients; it SHALL NOT introduce new secret sources.

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
- **THEN** the run SHALL list issues from Snyk using **`snyk_org_id`** for each such entry and SHALL route Azure DevOps operations for issues from that list to that entry’s effective **`organization`** and **`project`**

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

When **`sync`** assembles plain text for **`System.Description`**, it SHALL first produce the default sections defined by **`sync-lifecycle`** (finding metadata, Snyk link block, etc.). When the effective **`work_item_description_appendix`** string per **`application-config`** is **non-empty** after stripping leading and trailing whitespace, **`sync`** SHALL append **`"\n\n"`** followed by that appendix to the plain-text assembly **before** HTML conversion and **before** applying the maximum description length limit.

When the effective appendix is empty (omitted, empty string, or whitespace-only after strip), **`sync`** SHALL NOT add extra paragraphs for this feature.

#### Scenario: Appendix non-empty adds trailing paragraph block

- **WHEN** merged configuration supplies a non-empty **`work_item_description_appendix`** for the active routing context
- **THEN** the plain-text **`System.Description`** assembly SHALL end with a block separated from prior content by at least one blank line and SHALL include the appendix text verbatim (subject to truncation)

#### Scenario: Appendix empty leaves assembly unchanged

- **WHEN** the effective **`work_item_description_appendix`** is empty after strip
- **THEN** the plain-text description SHALL match the default assembly with no appendix paragraphs added

---

### Requirement: System.Description is HTML-safe for Azure Boards rendering

The JSON Patch value for **`System.Description`** SHALL be HTML suitable for Azure DevOps work item fields: plain-text assembly split on blank lines into paragraphs (**`<p>...</p>`**), single line breaks within a paragraph as **`<br />`**, and **HTML entity escaping** for dynamic/API-supplied text **and** for YAML-supplied **`work_item_description_appendix`** text so **`System.Title`** and **`System.Description`** cannot inject markup from issue payloads or configuration.

#### Scenario: Plain assembly becomes paragraphs

- **WHEN** plain-text assembly contains two blocks separated by a blank line
- **THEN** the **`System.Description`** patch value SHALL contain two **`<p>`** paragraphs (or equivalent) preserving separation in the Boards web UI

#### Scenario: Appendix text is escaped like other description content

- **WHEN** **`work_item_description_appendix`** contains characters that require HTML escaping (for example **`&`**, **`<`**, **`>`**)
- **THEN** the **`System.Description`** patch value SHALL escape those characters appropriately so they render as literal characters in Azure Boards

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

On work item **create** and **update**, the application SHALL apply **tags** supplied by the merged **`work_item_template.tags`** list (zero or more strings). Tags SHALL be applied using Azure DevOps–compatible JSON Patch for the configured work item type.

#### Scenario: Empty tags list is valid

- **WHEN** `work_item_template.tags` is absent or an empty list
- **THEN** the sync run SHALL not fail solely for tags and SHALL proceed without adding tags beyond those implied by other patch operations

---

### Requirement: P2-FR-5.1 primary package and title or description body

The **primary package** SHALL be taken from the **first** `coordinates[]` element in API order that contains a `representations[]` entry with a **`dependency`** field set.

For **code** issues (**`attributes.type`** indicating code analysis, for example **`code`**), the description assembly SHALL include **file path** and **line range** derived from **`coordinates[].representations[].sourceLocation`** when present (see **`data/sample_coord.local.json`**: **`file`**, **`region.start.line`**, **`region.end.line`**).

The human-readable text used for **`System.Title`** on create SHALL be **`{target} - {issue}`** when **`target`** can be resolved, where:

- **`issue`** is **`attributes.title`** when non-empty; otherwise the primary package line (**`package@version`**); otherwise a short fallback label.
- **`target`** SHALL prefer **`snyk_project_name`** persisted on the mapping row when non-empty; next **`snyk_project_name`** on the normalized/enriched issue record when non-empty; next **`{effective_organization} / {effective_project}`** from merged **`azure_boards.defaults`** and **`org_mappings`** context. When no **`target`** label can be resolved, **`System.Title`** SHALL be **`issue`** only (no **` - `** prefix).

For **`System.Description`**, the application SHALL assemble content in **section blocks** (blank-line-separated in plain assembly before HTML wrapping) so operators see distinct paragraphs in Azure Boards. Assembly SHALL include at minimum:

1. **Context:** **Snyk project** display name and **origin** when known (**`snyk_project_name`**, **`snyk_project_origin`** from mapping row or APIs), **severity**, **Snyk issue key**.
2. **Finding:** primary package and optional path hints from **`coordinates[]`** when present; for **code** issues, **file + lines** per **`sourceLocation`** when present.
3. **How to fix:** recommended upgrade/version strings extracted from **`coordinates[].remedies`** (**`upgradeTo`**, **`changes[].upgradeTo`**, etc.) and dependency representation hints when present; formatted **`coordinates[].remedies`** narrative (**`type: description`** style when structured).
4. **`attributes.description`** when present (vulnerability narrative).
5. **Classification:** **P2-FR-5.2**, **P2-FR-5.3**, and fix availability (**P2-FR-5.5** subset—see below).

When the issue record produced by **list** operations omits **`attributes.description`** or **`coordinates[].remedies`** (or other fields needed for the paragraphs above), the application SHALL issue **`GET /groups/{group_id}/issues/{issue_id}`** or **`GET /orgs/{org_id}/issues/{issue_id}`** in the **same** scope as the list operation for that issue’s **`rest_issue_id`** (JSON:API **`data.id`**), merge **`attributes`** and **`coordinates`** from the GET response into the working issue view per the active change **`design.md`**, then assemble **`System.Description`**. The client SHALL use the same **`version`** query parameter as documented for Issues API requests.

If fields remain absent after GET, the description SHALL still include all other available metadata; the run SHALL NOT fail solely because narrative or remedies are missing.

#### Scenario: Primary package from first dependency representation

- **WHEN** multiple coordinates include dependency representations
- **THEN** the sync SHALL select the first such coordinate in API order for the primary package line

#### Scenario: Title uses mapping-backed Snyk project name when present

- **WHEN** **`snyk_project_name`** on the mapping row is non-empty and **`attributes.title`** is non-empty
- **THEN** **`System.Title`** SHALL begin with **`{snyk_project_name} - `** followed by the issue title text (subject to length limits)

#### Scenario: Description includes narrative when attributes.description is present

- **WHEN** the working issue attributes include non-empty **`description`**
- **THEN** **`System.Description`** SHALL include that text in addition to other required sections

#### Scenario: GET issue enriches payload when list omits remedies or description

- **WHEN** the list payload lacks **`description`** or **`remedies`** and GET-by-id returns them for the same issue
- **THEN** **`System.Description`** SHALL incorporate those fields after the GET merge

#### Scenario: Code issue includes file and line location when sourceLocation present

- **WHEN** **`sourceLocation.file`** and line fields exist under **`coordinates[].representations[]`**
- **THEN** **`System.Description`** SHALL include human-readable file path and line range for that finding

---

### Requirement: P2-FR-5.2 finding type verbatim

The work item metadata SHALL record the Snyk **`attributes.type`** string **verbatim** (for example `package_vulnerability`, `license`, `cloud`, `code`, `custom`, `config`) without mapping tables to alternate labels.

#### Scenario: Type copied verbatim

- **WHEN** `attributes.type` is `package_vulnerability`
- **THEN** the value written to the chosen work item field for “finding type” SHALL be exactly `package_vulnerability`

---

### Requirement: P2-FR-5.3 CWE and CVE extraction

The application SHALL extract **CWE** identifiers from **`attributes.classes`** entries where **`source`** equals **`CWE`**. It SHALL extract **CVE** identifiers from **`attributes.problems`** entries whose **`id`** matches the pattern **`CVE-*`**, and SHALL include each such problem’s **`url`** in work item text or fields when present.

#### Scenario: CVE includes url when present

- **WHEN** a matching `attributes.problems` entry includes a `url`
- **THEN** the created or updated work item content SHALL include that URL alongside the CVE id

---

### Requirement: P2-FR-5.4 direct Snyk web UI issue URL

The application SHALL construct exactly **one** canonical HTTPS URL per work item that satisfies **P2-FR-5.4** using this structure:

`https://app.snyk.io/org/{snyk_org_slug}/project/{project_id}#issue-{issue_key}`

where:

- **`{snyk_org_slug}`** is the effective organization slug from **`application-config`** for the routing context processing the issue (**`org_mappings`** rows supply it; group-only sync MAY leave it empty until configuration exists).
- **`{project_id}`** is **`relationships.scan_item.data.id`** from the issue resource.
- **`{issue_key}`** is **`attributes.key`** from the issue resource.

The fragment SHALL be **`#issue-`** immediately followed by **`attributes.key`** verbatim; URL-encoding SHALL be applied only as required for a valid HTTP URL.

The application SHALL NOT emit **`https://app.snyk.io/group/{group_id}/issues/{id}`** or other deprecated **best-effort** link patterns as the primary **P2-FR-5.4** link line.

When the URL is rendered inside **`System.Description`**, it SHALL appear as an HTML **hyperlink** (**`<a href="...">...</a>`**) with **href** set to the canonical URL and link text that identifies the issue in Snyk, subject to the same HTML entity escaping rules as other dynamic description content (**HTML-safe** assembly).

#### Scenario: Link uses config slug and API identifiers

- **WHEN** sync composes the **P2-FR-5.4** link for an issue with known **`snyk_org_slug`**, **`scan_item`**, and **`attributes.key`**
- **THEN** the URL SHALL match the canonical template above with those substitutions

#### Scenario: Fragment uses issue key

- **WHEN** **`attributes.key`** is `SNYK-PYTHON-H11-10293728`
- **THEN** the URL fragment SHALL end with `#issue-SNYK-PYTHON-H11-10293728`

#### Scenario: Description renders link as HTML anchor

- **WHEN** the **P2-FR-5.4** URL is written into **`System.Description`**
- **THEN** the stored HTML SHALL include a single **`a`** element with **`href`** equal to the canonical HTTPS URL (escaped as required)

---

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

### Requirement: Work item type and Boards state names from configuration

Work item **create** SHALL use the merged effective **`work_item_type`** from **`azure_boards.defaults`** (and **`org_mappings[].overrides`**) as the WIT **`$type`** segment (default **`Task`** when omitted after merge). When a work item shall represent an **active** finding, the sync SHALL transition or set Boards **`System.State`** to the merged **`work_item_state_active`**. When a finding is on the **close path** (**derived `snyk_status`** is **`resolved`** or **`ignored`**), the sync SHALL set the Boards closed disposition using the merged **`work_item_state_closed`**. Operators MUST configure values that exist for their process; the application SHALL treat these as opaque strings after non-empty validation.

#### Scenario: Defaults apply when keys omitted

- **WHEN** the three keys are omitted from YAML and not overridden by higher-precedence layers
- **THEN** the effective values SHALL be **`Task`**, **`New`**, and **`Closed`** respectively for sync

---

### Requirement: Per-issue errors do not fail the whole sync run

For errors attributable to a **single** issue (for example Azure PATCH failure for one id or skip due to unexpected Snyk `status`), the application SHALL **log** a concise diagnostic without secrets, **skip** that issue, and **continue** processing remaining issues. The process exit code SHALL be **`0`** when the run completes the full per-issue loop after startup succeeded, even if one or more issues were skipped. **Non-zero** exit codes SHALL be reserved for failures that prevent starting the run or invalidate it globally (for example missing configuration, missing tokens, or client preflight errors before the per-issue loop).

#### Scenario: Exit zero with skips

- **WHEN** at least one issue is skipped due to a per-issue error and no global failure occurred
- **THEN** the process SHALL still exit with code `0`

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
