## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: System.Description is HTML-safe for Azure Boards rendering

The JSON Patch value for **`System.Description`** SHALL be HTML suitable for Azure DevOps work item fields: plain-text assembly split on blank lines into paragraphs (**`<p>...</p>`**), single line breaks within a paragraph as **`<br />`**, and **HTML entity escaping** for dynamic/API-supplied text **and** for YAML-supplied **`work_item_description_appendix`** text so **`System.Title`** and **`System.Description`** cannot inject markup from issue payloads or configuration.

#### Scenario: Plain assembly becomes paragraphs

- **WHEN** plain-text assembly contains two blocks separated by a blank line
- **THEN** the **`System.Description`** patch value SHALL contain two **`<p>`** paragraphs (or equivalent) preserving separation in the Boards web UI

#### Scenario: Appendix text is escaped like other description content

- **WHEN** **`work_item_description_appendix`** contains characters that require HTML escaping (for example **`&`**, **`<`**, **`>`**)
- **THEN** the **`System.Description`** patch value SHALL escape those characters appropriately so they render as literal characters in Azure Boards
