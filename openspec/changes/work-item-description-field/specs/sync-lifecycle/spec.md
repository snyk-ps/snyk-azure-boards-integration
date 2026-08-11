## ADDED Requirements

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

## MODIFIED Requirements

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
