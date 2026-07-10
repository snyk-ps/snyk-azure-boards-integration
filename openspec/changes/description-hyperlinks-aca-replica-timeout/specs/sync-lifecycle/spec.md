## MODIFIED Requirements

### Requirement: System.Description is HTML-safe for Azure Boards rendering

The JSON Patch value for **`System.Description`** SHALL be HTML suitable for Azure DevOps work item fields: plain-text assembly split on blank lines into paragraphs (**`<p>...</p>`**), single line breaks within a paragraph as **`<br />`**, and **HTML entity escaping** for dynamic/API-supplied text **and** for YAML-supplied **`work_item_description_appendix`** text so **`System.Title`** and **`System.Description`** cannot inject markup from issue payloads or configuration.

Within each paragraph block (except the dedicated **Open in Snyk** block described in **P2-FR-5.4**), **`http://`** and **`https://`** URL substrings in the plain-text assembly SHALL be rendered as HTML hyperlinks (**`<a href="…">…</a>`**) with **`href`** and visible link text HTML-escaped. Only **`http://`** and **`https://`** schemes SHALL be linkified; other schemes (for example **`javascript:`**) SHALL remain escaped literal text. Trailing punctuation immediately following a detected URL (for example **`.`**, **`,`**, **`;`**, **`:`**, **`)`**) SHALL NOT be included in **`href`**.

#### Scenario: Plain assembly becomes paragraphs

- **WHEN** plain-text assembly contains two blocks separated by a blank line
- **THEN** the **`System.Description`** patch value SHALL contain two **`<p>`** paragraphs (or equivalent) preserving separation in the Boards web UI

#### Scenario: Appendix text is escaped like other description content

- **WHEN** **`work_item_description_appendix`** contains characters that require HTML escaping (for example **`&`**, **`<`**, **`>`**) outside of an **`http(s)`** URL
- **THEN** the **`System.Description`** patch value SHALL escape those characters appropriately so they render as literal characters in Azure Boards

#### Scenario: Appendix https URL becomes a hyperlink

- **WHEN** **`work_item_description_appendix`** contains a substring **`https://`** URL
- **THEN** the **`System.Description`** patch value SHALL include an **`<a href="…">`** element for that URL with escaped **`href`** and escaped visible link text

#### Scenario: Non-http schemes are not linkified

- **WHEN** plain-text assembly contains **`javascript:alert(1)`** or similar non-**`http(s)`** scheme
- **THEN** the **`System.Description`** patch value SHALL NOT emit a clickable **`href`** for that substring

---

### Requirement: P2-FR-5.3 CWE and CVE extraction

The application SHALL extract **CWE** identifiers from **`attributes.classes`** entries where **`source`** equals **`CWE`**. It SHALL extract **CVE** identifiers from **`attributes.problems`** entries whose **`id`** matches the pattern **`CVE-*`**, and SHALL include each such problem’s **`url`** in work item text or fields when present.

When a CVE **`url`** appears in **`System.Description`**, it SHALL be rendered as an HTML hyperlink per **System.Description is HTML-safe for Azure Boards rendering** (in addition to appearing alongside the CVE id in plain-text assembly).

#### Scenario: CVE includes url when present

- **WHEN** a matching `attributes.problems` entry includes a `url`
- **THEN** the created or updated work item content SHALL include that URL alongside the CVE id

#### Scenario: CVE NVD url is clickable in description

- **WHEN** plain-text assembly includes a CVE line containing an **`https://`** URL from **`attributes.problems`**
- **THEN** the **`System.Description`** patch value SHALL include an **`<a href="…">`** element for that URL
