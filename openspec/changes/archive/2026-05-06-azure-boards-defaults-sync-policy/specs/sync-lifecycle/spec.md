## ADDED Requirements

### Requirement: Persist Snyk project display metadata on mapping rows

The **`sync`** run SHALL persist **`snyk_project_name`** (from **`GET /orgs/{org_id}/projects/{project_id}`** **`attributes.name`**) and **`snyk_project_origin`** (from **`attributes.origin`**) on the mapping store row for the natural key, updating values when refreshed per **`design.md`**, so routine sync loops avoid repeating project GET for unchanged rows.

#### Scenario: Upsert stores project metadata

- **WHEN** sync obtains non-empty project **`name`** and **`origin`** from the Snyk Projects API for an issue’s **`project_id`**
- **THEN** the mapping upsert SHALL persist **`snyk_project_name`** and **`snyk_project_origin`** alongside existing routing fields

---

## MODIFIED Requirements

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

### Requirement: P2-FR-5.1 primary package and title or description body

The **primary package** SHALL be taken from the **first** `coordinates[]` element in API order that contains a `representations[]` entry with a **`dependency`** field set.

For **code** issues (**`attributes.type`** indicating code analysis, for example **`code`**), the description assembly SHALL include **file path** and **line range** derived from **`coordinates[].representations[].sourceLocation`** when present (see **`data/sample_coord.local.json`**: **`file`**, **`region.start.line`**, **`region.end.line`**).

The human-readable text used for **`System.Title`** on create SHALL be **`{target} - {issue}`** when **`target`** can be resolved, where:

- **`issue`** is **`attributes.title`** when non-empty; otherwise the primary package line (**`package@version`**); otherwise a short fallback label.
- **`target`** SHALL prefer **`snyk_project_name`** persisted on the mapping row when non-empty; next **`snyk_project_name`** on the normalized/enriched issue record when non-empty; next **`{effective_organization} / {effective_project}`** from merged **`azure_boards.defaults`** and **`org_mappings`** context. When no **`target`** label can be resolved, **`System.Title`** SHALL be **`issue`** only (no **` - `** prefix).

For **`System.Description`**, the application SHALL assemble content in **section blocks** (blank-line-separated in plain assembly before HTML wrapping) so operators see distinct paragraphs in Azure Boards. Assembly SHALL include at minimum:

1. **Context:** Azure Boards target (**organization / project**), **Snyk project** display name and **origin** when known (**`snyk_project_name`**, **`snyk_project_origin`** from mapping row or APIs), **severity**, **Snyk issue key**.
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
