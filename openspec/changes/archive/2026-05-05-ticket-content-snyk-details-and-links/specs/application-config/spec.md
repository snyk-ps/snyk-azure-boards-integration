## MODIFIED Requirements

### Requirement: Azure Boards org_mappings entry schema

Each element of **`azure_boards.org_mappings`** SHALL be a mapping containing:

- **`organization`**: non-empty string, Azure DevOps organization name for REST routing for this row.
- **`project`**: non-empty string, Azure DevOps project name or id for REST routing for this row.
- **`snyk_org_id`**: non-empty string, Snyk organization UUID for org-scoped Issues API calls for this row.
- **`snyk_org_slug`**: **required** non-empty string after merge for each row: **human-readable** Snyk organization **slug** for **`app.snyk.io`** URL composition (**non-secret**). The loader SHALL reject rows where **`snyk_org_slug`** is missing or empty with a clear, non-secret error pointing at **`azure_boards.org_mappings[].snyk_org_slug`**.
- **`overrides`**: optional mapping; when present, its keys SHALL be a subset of those allowed under **`azure_boards.defaults`** (**`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_template`**). Omitted override keys SHALL inherit from **`defaults`** after merge per **`application-config`** merge rules.

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

---

### Requirement: Snyk section with group ID and severity threshold

Under **`snyk`**, the configuration defines at least:

- **`group_id`**: String identifying the Snyk **group** (UUID string as used by the Snyk REST Issues API for group-scoped operations). The **resolved** value after applying **defaults → file → environment → CLI** (see precedence requirement) MUST be **non-empty** before issuing **group-scoped** Snyk Issues API requests (list/get by group). **`fetch`** and any command that **only** performs group-scoped list/get SHALL fail with a clear, non-secret error if `group_id` is missing or empty at execution time when that mode is selected. For **`sync`**, when **`azure_boards.org_mappings`** is present with at least one valid row, org-scoped listing does not require **`group_id`** for that path (see **Sync command requires non-empty Snyk group id**). **Help-only** invocations (e.g. `--help`) SHALL NOT require `group_id`.
- **`severity_threshold`**: A string severity level used as the **minimum** threshold for policy (ordering: `low` < `medium` < `high` < `critical`). The default applied when the key is omitted (after defaulting rules) SHALL be **`high`**, consistent with **P2-FR-1** (High/Critical) as the baseline product behavior.

The key **`snyk_org_slug`** SHALL NOT appear under **`snyk`**. Human-readable org slugs for **`app.snyk.io`** links belong **only** under **`azure_boards.org_mappings[].snyk_org_slug`**. If YAML contains **`snyk.snyk_org_slug`**, the loader SHALL fail with a clear, non-secret error that names the supported location.

Additional keys under **`snyk`** MAY be introduced in future changes; the loader SHALL allow forward-compatible preservation or ignore rules as documented for unknown keys (at minimum, documented behavior for known keys).

#### Scenario: Group ID present after merge

- **WHEN** the merged `snyk.group_id` is a non-empty string
- **THEN** group-scoped Snyk Issues API calls MAY use that value

#### Scenario: Fetch or group sync without group ID

- **WHEN** the user runs **`fetch`** or **`sync`** in group-only mode (no effective **`org_mappings`**) and the resolved `group_id` is missing or empty
- **THEN** the command SHALL exit without issuing group-scoped Snyk Issues API calls, with a clear error that does not include secrets

#### Scenario: Severity threshold default

- **WHEN** `snyk.severity_threshold` is omitted from the file and not overridden by a higher-precedence layer
- **THEN** the effective severity threshold SHALL be **`high`**

#### Scenario: snyk.snyk_org_slug rejected

- **WHEN** YAML sets **`snyk.snyk_org_slug`**
- **THEN** loading SHALL fail with a clear error directing operators to **`azure_boards.org_mappings[].snyk_org_slug`**

#### Scenario: azure_boards.snyk_org_slug rejected

- **WHEN** YAML sets **`azure_boards.snyk_org_slug`** at the **`azure_boards`** root
- **THEN** loading SHALL fail with a clear error explaining that slugs belong on **`org_mappings`** rows only
