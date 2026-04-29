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

### Requirement: One sync run orchestrates Snyk list, mapping, and Azure Boards updates

The application SHALL provide a **`sync`** command (argparse subcommand implemented under **`src/commands/`**, dispatched from **`src/main.py`**) that performs **one** synchronization run by invoking orchestration implemented under **`src/sync/`** (Python package `sync`). That run SHALL load merged configuration, obtain issues from the Snyk Issues API using **group-scoped** list operations **when `azure_boards.org_mappings` is absent or empty**, or using **org-scoped** list operations **for each non-empty `org_mappings` row** when **`org_mappings`** is present and non-empty, with filters aligned to **P2-FR-1** and **`snyk.severity_threshold`**, read and write rows through the **`MappingStore`** abstraction, and invoke the **Azure DevOps** client for work item create, update, close, and optional comments. For each **`org_mappings`** row, the run SHALL use that row’s **`organization`**, **`project`**, and **effective** work item settings (**`defaults`** merged with that row’s **`overrides`**) and **effective** **`work_item_template`** per **`application-config`** merge rules. The sync run SHALL obtain **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** only via the same environment-variable rules as the respective clients; it SHALL NOT introduce new secret sources.

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
- **THEN** the run SHALL list issues from Snyk using **`snyk_org_id`** for each such entry and SHALL route Azure DevOps operations for issues from that list to that entry’s **`organization`** and **`project`**

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

When **`azure_boards.create_new_work_items`** is **`false`**, the **`sync`** command SHALL NOT create new Azure Boards work items and SHALL NOT insert new mapping rows. It SHALL still update and close work items that already have a mapping row for the same natural key **`(group_id, org_id, project_id, issue_id)`**. Findings with **no** mapping row SHALL be left untouched (no work item creation and no new mapping insert), even if they satisfy **P2-FR-1**.

#### Scenario: No create and no new mapping when disabled

- **WHEN** `create_new_work_items` is `false` and a qualifying Snyk issue has no mapping row
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

When a finding previously warranted a **closed** Boards work item under this policy (stored derived **`snyk_status`** was **`resolved`** or **`ignored`**) and later satisfies **`ignored` == false** and **`status` == `open`**, the application SHALL **create a new** Azure Boards work item for the active finding. The **prior** work item SHALL remain in its closed disposition; the application SHALL **not** silently reactivate the old work item as the active ticket for that finding.

#### Scenario: New work item id replaces mapping on reopen

- **WHEN** a new work item is created for a reopened finding with the same natural key
- **THEN** the mapping store SHALL upsert the row so **`work_item_id`** (and related fields) refer to the **new** work item

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

The **primary package** SHALL be taken from the **first** `coordinates[]` element in API order that contains a `representations[]` entry with a **`dependency`** field set. The human-readable body text used for **`System.Title`** on create (and the description field chosen by the implementation, if distinct) SHALL combine **`attributes.title`** with that primary package line using the same composition rule for both **P2-FR-5.1** and the **System.Title** requirement in this change.

#### Scenario: Primary package from first dependency representation

- **WHEN** multiple coordinates include dependency representations
- **THEN** the sync SHALL select the first such coordinate in API order for the primary package line

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

### Requirement: P2-FR-5.4 best-effort Snyk issue URL without org slug

The application SHALL construct a **best-effort** HTTP URL to the Snyk issue using stable API identifiers (for example group and issue key) **without** requiring an organization slug. Full UI-parity links that depend on slug resolution are **explicitly deferred** to a later change, which MAY add slug discovery.

#### Scenario: Link does not require org slug

- **WHEN** sync composes a Snyk link for a work item
- **THEN** the URL SHALL be derivable from non-secret identifiers already present in configuration or issue payloads without calling undocumented slug services

---

### Requirement: P2-FR-5.5 fix availability flags summary

The application SHALL read boolean fix signals from each **`coordinates[]`** object: **`is_upgradeable`**, **`is_patchable`**, **`is_pinnable`**, **`is_fixable_manually`**, **`is_fixable_snyk`**, **`is_fixable_upstream`**. Version 1 human guidance SHALL summarize these flags together with the issue **title** and the **primary package** line from **P2-FR-5.1**; long-form narrative remediation beyond this summary remains out of scope unless a future change adds another API for it.

#### Scenario: Summary mentions true flags

- **WHEN** at least one of the boolean flags is true
- **THEN** the work item description or structured fields SHALL include a concise enumeration of which flags are true

---

### Requirement: System.Title required on create

Every **`POST`** work item **create** SHALL include a JSON Patch operation that sets **`System.Title`** to the non-empty string composed per **P2-FR-5.1** / primary package rule. Additional patch operations for fields such as **Area Path**, **Iteration Path**, **tags**, and custom fields SHALL come from **`work_item_template`** (including **`json_patch`** list entries) merged according to the active change **`design.md`**, without reading secrets from YAML.

#### Scenario: Create rejected without title operation

- **WHEN** internal patch assembly would omit `System.Title`
- **THEN** the implementation tests SHALL treat that as a defect and the sync SHALL not send create requests without `System.Title`

---

### Requirement: Work item type and Boards state names from configuration

Work item **create** SHALL use **`azure_boards.work_item_type`** as the WIT **`$type`** segment (default **`Task`** when omitted after merge). When a work item shall represent an **active** finding, the sync SHALL transition or set Boards **`System.State`** to **`azure_boards.work_item_state_active`** (default **`New`**). When a finding is on the **close path** (**derived `snyk_status`** is **`resolved`** or **`ignored`**), the sync SHALL set the Boards closed disposition using **`azure_boards.work_item_state_closed`** (default **`Closed`**). Operators MUST configure values that exist for their process; the application SHALL treat these as opaque strings after non-empty validation.

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
