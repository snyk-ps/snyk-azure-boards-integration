## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Snyk-derived severity and finding-type work item tags

For each **origin-included** issue where **`sync`** performs an Azure DevOps work item **create** or **update** through the same JSON Patch assembly used for **`System.Title`**, **`System.Description`**, **`System.State`**, and template operations, the application SHALL incorporate **managed** tags derived from the **current** Snyk issue payload for that run into the combined tag list (and therefore into **`System.Tags`** when the combined list is non-empty):

- **Severity:** at most one tag of the form **`Snyk-Severity-{level}`** where **`level`** is **`low`**, **`medium`**, **`high`**, or **`critical`**, normalized from **`effective_severity_level`** (or equivalent field on the normalized issue record). If the level is missing or not one of these after normalization, **no** severity managed tag SHALL be emitted.
- **Finding type:** at most one tag of the form **`Snyk-Type-{kind}`** where **`kind`** is **`open_source`**, **`code`**, **`container`**, or **`iac`**, mapped from Snyk issue **`attributes.type`** (or equivalent) to align with **P2-FR-5.2** classes. If the type is missing or cannot be mapped to one of these four kinds, **no** type managed tag SHALL be emitted.

When the effective severity or mapped kind **changes** between sync runs, the new managed tag values SHALL **replace** the previous values for that dimension **by virtue of** the combined **`System.Tags`** payload for that run (no duplicate **`Snyk-Severity-*`** or **`Snyk-Type-*`** tags from the application).

#### Scenario: Severity downgrade updates managed tag

- **WHEN** a work item was last synced with **`Snyk-Severity-high`** and the current issue **`effective_severity_level`** normalizes to **`medium`**
- **THEN** the **`System.Tags`** payload for that update SHALL include **`Snyk-Severity-medium`** and SHALL NOT include **`Snyk-Severity-high`**

#### Scenario: Origin-excluded issues skip tag mutation

- **WHEN** an issue is **origin-excluded** per inclusive allowlist rules and **`sync`** does not invoke Azure DevOps mutations for it
- **THEN** the application SHALL not add or update managed tags on any work item for that issue on that run

#### Scenario: Unmapped issue type omits type tag only

- **WHEN** severity normalizes to **`high`** but issue type cannot be mapped to **`open_source`**, **`code`**, **`container`**, or **`iac`**
- **THEN** the combined tag list MAY include **`Snyk-Severity-high`** and SHALL omit a **`Snyk-Type-*`** managed tag for that run
