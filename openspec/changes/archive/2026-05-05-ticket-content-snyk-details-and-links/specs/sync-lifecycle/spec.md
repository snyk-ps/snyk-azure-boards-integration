## ADDED Requirements

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

### Requirement: System.Description is HTML-safe for Azure Boards rendering

The JSON Patch value for **`System.Description`** SHALL be HTML suitable for Azure DevOps work item fields: plain-text assembly split on blank lines into paragraphs (**`<p>...</p>`**), single line breaks within a paragraph as **`<br />`**, and **HTML entity escaping** for dynamic/API-supplied text so **`System.Title`** and **`System.Description`** cannot inject markup from issue payloads.

#### Scenario: Plain assembly becomes paragraphs

- **WHEN** plain-text assembly contains two blocks separated by a blank line
- **THEN** the **`System.Description`** patch value SHALL contain two **`<p>`** paragraphs (or equivalent) preserving separation in the Boards web UI

---

## MODIFIED Requirements

### Requirement: P2-FR-5.1 primary package and title or description body

The **primary package** SHALL be taken from the **first** `coordinates[]` element in API order that contains a `representations[]` entry with a **`dependency`** field set.

The human-readable text used for **`System.Title`** on create SHALL be **`{target} - {issue}`** when **`target`** can be resolved, where:

- **`issue`** is **`attributes.title`** when non-empty; otherwise the primary package line (**`package@version`**); otherwise a short fallback label.
- **`target`** SHALL match the description context: prefer **`snyk_project_name`** on the normalized/enriched issue record when non-empty; otherwise **`{azure_boards.organization} / {azure_boards.project}`** for the active Azure DevOps routing context. When no **`target`** label can be resolved, **`System.Title`** SHALL be **`issue`** only (no **` - `** prefix).

For **`System.Description`**, the application SHALL assemble content in **section blocks** (blank-line-separated in plain assembly before HTML wrapping) so operators see distinct paragraphs in Azure Boards. Assembly SHALL include at minimum:

1. **Context:** Azure Boards target (**organization / project**), **Snyk target** label when **`snyk_project_name`** is known, **severity**, **Snyk issue key**.
2. **Finding:** primary package and optional path hints from **`coordinates[]`** when present.
3. **How to fix:** recommended upgrade/version strings extracted from **`coordinates[].remedies`** (**`upgradeTo`**, **`changes[].upgradeTo`**, etc.) and dependency representation hints when present; formatted **`coordinates[].remedies`** narrative (**`type: description`** style when structured).
4. **`attributes.description`** when present (vulnerability narrative).
5. **Classification:** **P2-FR-5.2**, **P2-FR-5.3**, and fix availability (**P2-FR-5.5** subset—see below).

When the issue record produced by **list** operations omits **`attributes.description`** or **`coordinates[].remedies`** (or other fields needed for the paragraphs above), the application SHALL issue **`GET /groups/{group_id}/issues/{issue_id}`** or **`GET /orgs/{org_id}/issues/{issue_id}`** in the **same** scope as the list operation for that issue’s **`rest_issue_id`** (JSON:API **`data.id`**), merge **`attributes`** and **`coordinates`** from the GET response into the working issue view per the active change **`design.md`**, then assemble **`System.Description`**. The client SHALL use the same **`version`** query parameter as documented for Issues API requests.

If fields remain absent after GET, the description SHALL still include all other available metadata; the run SHALL NOT fail solely because narrative or remedies are missing.

#### Scenario: Primary package from first dependency representation

- **WHEN** multiple coordinates include dependency representations
- **THEN** the sync SHALL select the first such coordinate in API order for the primary package line

#### Scenario: Title uses target prefix when Snyk project name exists

- **WHEN** **`snyk_project_name`** is non-empty and **`attributes.title`** is non-empty
- **THEN** **`System.Title`** SHALL begin with **`{snyk_project_name} - `** followed by the issue title text (subject to length limits)

#### Scenario: Description includes narrative when attributes.description is present

- **WHEN** the working issue attributes include non-empty **`description`**
- **THEN** **`System.Description`** SHALL include that text in addition to other required sections

#### Scenario: GET issue enriches payload when list omits remedies or description

- **WHEN** the list payload lacks **`description`** or **`remedies`** and GET-by-id returns them for the same issue
- **THEN** **`System.Description`** SHALL incorporate those fields after the GET merge

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

#### Scenario: Link uses config slug and API identifiers

- **WHEN** sync composes the **P2-FR-5.4** link for an issue with known **`snyk_org_slug`**, **`scan_item`**, and **`attributes.key`**
- **THEN** the URL SHALL match the canonical template above with those substitutions

#### Scenario: Fragment uses issue key

- **WHEN** **`attributes.key`** is `SNYK-PYTHON-H11-10293728`
- **THEN** the URL fragment SHALL end with `#issue-SNYK-PYTHON-H11-10293728`

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
