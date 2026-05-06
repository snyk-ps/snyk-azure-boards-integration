## ADDED Requirements

### Requirement: Azure Boards defaults — optional work item description appendix

Under **`azure_boards.defaults`**, the configuration MAY include **`work_item_description_appendix`**, a **string** containing **plain text** (including newlines via YAML block scalars). When omitted, the effective value SHALL be an **empty string**. The value SHALL NOT be used to transport secrets; operators SHOULD use non-secret runbook or portal URLs only.

The loader SHALL reject a non-string value for **`work_item_description_appendix`** with a clear, non-secret error.

#### Scenario: Omitted appendix defaults to empty

- **WHEN** YAML omits **`azure_boards.defaults.work_item_description_appendix`**
- **THEN** loading SHALL succeed and the effective value SHALL be an empty string

#### Scenario: Non-string appendix rejected

- **WHEN** YAML sets **`work_item_description_appendix`** to a non-string type (for example a number or mapping)
- **THEN** loading SHALL fail with a clear error that does not include secrets

---

## MODIFIED Requirements

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`**, including **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_template`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, and **`work_item_description_appendix`**. Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

The loader SHALL reject entries missing required keys or containing empty strings for **`organization`**, **`project`**, or **`snyk_org_id`** with a clear, non-secret error.

#### Scenario: Valid org_mappings row loads

- **WHEN** YAML contains one **`org_mappings`** row with non-empty **`organization`**, **`project`**, **`snyk_org_id`**, and **`snyk_org_slug`**
- **THEN** loading SHALL succeed and expose that row for **`sync`**

#### Scenario: Invalid org_mappings row rejected

- **WHEN** a row omits **`snyk_org_id`** or supplies an empty **`organization`**
- **THEN** loading SHALL fail with a clear error that does not include secrets

#### Scenario: Org_mappings row missing snyk_org_slug rejected at load

- **WHEN** a row omits **`snyk_org_slug`** or supplies an empty string for **`snyk_org_slug`**
- **THEN** loading SHALL fail with a clear error that does not include secrets

#### Scenario: Overrides may set description appendix per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.work_item_description_appendix`** with a string value
- **THEN** loading SHALL succeed and merged configuration SHALL expose that override for **`sync`** description assembly for issues routed through that row
