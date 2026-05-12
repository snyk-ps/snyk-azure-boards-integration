## MODIFIED Requirements

### Requirement: Work item template section

The **`work_item_template`** value SHALL be a **mapping** (YAML dictionary). It MAY be empty. The loader SHALL accept an empty mapping and preserve unknown keys for forward compatibility where the YAML library permits.

For **`sync`**, the following inner keys, when present, SHALL be interpreted by the application:

- **`tags`**: A YAML list of strings representing work item tags to apply on create and update (**P2-FR-10**). These tags SHALL be merged with **managed** tags derived by **`sync`** from Snyk issue data per **`sync-lifecycle`** (**reserved prefixes**: tags starting with **`Snyk-Severity-`** or **`Snyk-Type-`** in operator YAML SHOULD NOT be used; if supplied, **`sync`** SHALL omit them when building operator tag list and SHALL apply canonical managed tags from the issue instead).
- **`json_patch`**: A YAML list of JSON Patch operation objects (`op`, `path`, optional `value`) appended or merged into work item create/update patch lists per merge rules in this capability and the README, without transporting secrets.

This change does not require any other inner keys for a valid configuration file.

#### Scenario: Empty template

- **WHEN** `work_item_template` is `{}` or omitted per defaulting rules
- **THEN** loading SHALL succeed and expose an empty or default template mapping without error

#### Scenario: Tags list accepted

- **WHEN** `work_item_template.tags` is a YAML list of strings
- **THEN** loading SHALL succeed and the merged template SHALL expose `tags` for sync to consume

#### Scenario: Json patch list accepted

- **WHEN** `work_item_template.json_patch` is a YAML list of mappings each containing `op` and `path`
- **THEN** loading SHALL succeed and the merged template SHALL expose `json_patch` for sync to consume

#### Scenario: Reserved-prefix operator tags documented

- **WHEN** an operator reads the README **work item template** / tags documentation
- **THEN** they SHALL find that **`Snyk-Severity-*`** and **`Snyk-Type-*`** are reserved for application-managed tags and SHOULD NOT appear in YAML `tags`
