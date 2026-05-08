## ADDED Requirements

### Requirement: Azure Boards defaults — inclusive Snyk project origin allowlist for sync

Under **`azure_boards.defaults`**, the configuration MAY include **`sync_included_snyk_origins`**, a **string** containing a **comma-separated** list of **Snyk project origin** tokens (each segment **`strip`**ped of leading and trailing ASCII whitespace; empty segments after strip discarded). The filter is **inclusive**: when the effective list (after parsing) is **non-empty**, a finding SHALL be treated as **origin-eligible** for Azure Boards **create/update/close** only if its resolved **`snyk_project_origin`** (from the Snyk Projects API **`attributes.origin`**, after **`strip`**) **exactly equals** one parsed token.

When **`sync_included_snyk_origins`** is **omitted**, the **empty string**, or contains **no** non-empty tokens after parsing, the effective configuration SHALL **not** apply origin filtering (all origins remain eligible subject to **P2-FR-1** and other gates).

The loader SHALL reject **`sync_included_snyk_origins`** if it is not a string type. The loader SHALL reject any parsed token that is **not** a member of the **documented allowlist** in **`README.md`** (aligned with [Snyk — Origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin) and including **`github-cloud-app`** and **`github-server-app`**).

#### Scenario: Omitted allowlist does not filter by origin

- **WHEN** YAML omits **`sync_included_snyk_origins`** under **`azure_boards.defaults`** and **`org_mappings` overrides**
- **THEN** loading SHALL succeed and **`sync`** SHALL treat issues as origin-eligible regardless of **`snyk_project_origin`**

#### Scenario: Valid allowlist loads

- **WHEN** YAML sets **`azure_boards.defaults.sync_included_snyk_origins`** to **`github, gitlab`** (with spaces)
- **THEN** loading SHALL succeed and the effective parsed tokens SHALL be **`github`** and **`gitlab`**

#### Scenario: Unknown origin token rejected at load

- **WHEN** YAML sets **`sync_included_snyk_origins`** to include a token not in the **`README.md`** allowlist
- **THEN** loading SHALL fail with a clear, non-secret error pointing operators to **`README.md`** and the Snyk Origin documentation

---

## MODIFIED Requirements

### Requirement: README documents mapping store columns

The **`README.md`** SHALL include a subsection under **Configuration** (or **Mapping store** / **Issues sync persistence**) that lists **every column** (field name and purpose) of the logical row persisted by **`mapping_store`** (referred to as **issues sync persistence**; physical SQLite table **`issue_work_item_map`** when using SQLite), including at minimum those defined in **`azure-platform`** for **`issue_work_item_map`** / Azure Table parity, including **`snyk_project_name`**, **`snyk_project_origin`**, **`excluded`**, and **`exclusion_reason`** when specified by **`sync-lifecycle`**.

The **`README.md`** SHALL document **`azure_boards.defaults.sync_included_snyk_origins`**, the **inclusive** comma-separated semantics, override behavior under **`org_mappings[].overrides`**, and SHALL include a **table or list** of every **acceptable origin token** for configuration, with a **link** to [Snyk — Origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin).

#### Scenario: Operators see mapping schema in README

- **WHEN** an operator reads the README for deployment or troubleshooting
- **THEN** they SHALL find a table or list describing persistence columns (including **`excluded`** and **`exclusion_reason`**) and acceptable **`sync_included_snyk_origins`** values without reading source code

---

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`**, including **`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_template`**, **`organization`**, **`project`**, **`create_new_work_items`**, **`severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`**, **`reopen_work_item_policy`**, **`work_item_description_appendix`**, and **`sync_included_snyk_origins`**. Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

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

#### Scenario: Overrides may set origin allowlist per mapping

- **WHEN** an **`org_mappings`** row includes **`overrides.sync_included_snyk_origins`** with a valid comma-separated allowlist string
- **THEN** loading SHALL succeed and **`sync`** SHALL use that row’s merged effective allowlist when classifying issues for that routing context

---
