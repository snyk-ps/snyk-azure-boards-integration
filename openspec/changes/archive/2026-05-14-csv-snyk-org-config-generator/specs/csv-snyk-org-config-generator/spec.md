# CSV Snyk org config generator (operator tool)

Requirements for a developer/operator CLI that builds a starter **`config.yaml`** with **`azure_boards.org_mappings`** resolved from Snyk’s group org list API. Output aligns with the shapes described in **`application-config`** and repository **`data/`** examples. This capability does not change sync runtime behavior.

## ADDED Requirements

### Requirement: CSV input schema

The tool SHALL accept a path to a **UTF-8** CSV file via a **required** CLI flag (e.g. **`--input`**). The file SHALL contain a **header row** with exactly these column names: **`ado_organization`**, **`ado_project`**, **`snyk_org_name`**. The tool SHALL reject files with missing columns, duplicated header names, or empty required cell values for any data row with a clear, non-secret error.

#### Scenario: Valid header and rows

- **WHEN** the CSV contains the three required headers and at least one data row with non-empty values in each column
- **THEN** parsing SHALL succeed and each row SHALL be available for mapping resolution

#### Scenario: Missing column

- **WHEN** the CSV omits one of the required headers
- **THEN** the tool SHALL exit non-zero before calling the Snyk API and SHALL report which header is missing

### Requirement: CLI flags and defaults

The tool SHALL expose:

- **`--input`**: path to the CSV (required).
- **`--group-id`**: Snyk **group** UUID (required).
- **`--output`**: path for the generated YAML; default **`data/config.yaml`** relative to the current working directory unless an absolute path is given.
- Optional **`--base-url`**: Snyk REST base URL; default **`https://api.snyk.io/rest`** (no trailing slash), consistent with **`integration-apis`**.
- Optional **`--api-version`**: query parameter **`version`** for the org list; default **`2024-03-12`** as specified in [Snyk REST API — List orgs in a group](https://apidocs.snyk.io/?version=2024-03-12#get-/groups/-group_id-/orgs).

Authentication SHALL use **`SNYK_TOKEN`** from the **environment** only (never read from CLI flags or YAML). The tool MUST NOT log the token or any credential material.

#### Scenario: Missing token

- **WHEN** **`SNYK_TOKEN`** is unset or empty at runtime
- **THEN** the tool SHALL exit non-zero with a clear error before or upon the first API call

#### Scenario: Default output path

- **WHEN** the user omits **`--output`**
- **THEN** the tool SHALL write to **`data/config.yaml`**

### Requirement: Snyk group org listing and pagination

For the given **`group_id`**, the tool SHALL retrieve all organizations by calling **`GET /groups/{group_id}/orgs`** against the configured base URL, including query parameters **`version`** (see **`--api-version`**) and **`limit=100`**. The tool SHALL follow **JSON:API pagination** using **`links.next`** until no further page exists, aggregating org resources from all pages into a single in-memory collection before resolving CSV rows.

#### Scenario: Multiple pages

- **WHEN** the API returns a **`links.next`** link and a non-empty **`data`** array with **`limit=100`**
- **THEN** the tool SHALL request subsequent pages until **`links.next`** is absent and SHALL include orgs from every page in the aggregated set

#### Scenario: Single page

- **WHEN** the first response has no **`links.next`** (or empty next)
- **THEN** the tool SHALL resolve rows using only orgs from that response

### Requirement: Match `snyk_org_name` to org id and slug

For each CSV row, the tool SHALL find **exactly one** org in the aggregated API results whose **display name** matches the row’s **`snyk_org_name`** after **trimming ASCII whitespace** from the CSV value. The match rule (including case sensitivity) SHALL be documented in the implementation’s module or package docstring and SHALL remain consistent for all rows.

When a match exists, the tool SHALL populate:

- **`azure_boards.org_mappings[].organization`** from **`ado_organization`**
- **`azure_boards.org_mappings[].project`** from **`ado_project`**
- **`azure_boards.org_mappings[].snyk_org_id`** from the matched org’s **id**
- **`azure_boards.org_mappings[].snyk_org_slug`** from the matched org’s **slug** (or the field the API exposes for app.snyk.io slug semantics for **`2024-03-12`**)

#### Scenario: Successful resolution

- **WHEN** each row’s **`snyk_org_name`** maps to exactly one org in the group
- **THEN** the generated **`org_mappings`** entry for that row SHALL contain the four fields above with non-empty **`snyk_org_id`** and **`snyk_org_slug`**

#### Scenario: No matching org

- **WHEN** a row’s **`snyk_org_name`** matches no org after full pagination
- **THEN** the tool SHALL exit non-zero and SHALL name the **`snyk_org_name`** and a row index (or equivalent locator) without emitting a partial output file, or SHALL emit no file if the spec prefers atomic write—implementation chooses one behavior and documents it; **atomic write** is preferred

#### Scenario: Ambiguous duplicate names

- **WHEN** two or more orgs in the aggregated set share the same display name that equals the row’s **`snyk_org_name`** under the documented match rule
- **THEN** the tool SHALL exit non-zero with a clear error indicating ambiguity

### Requirement: Generated YAML structure

The tool SHALL write YAML that includes:

1. **`azure_boards.defaults`**: present as a mapping but with **no active scalar/list values** for policy keys; instead, **commented** example lines that mirror the guidance in **`data/sample-config.yaml`** (e.g. organization, project, booleans, severity, issues sync bounds, reopen policy, work item type/states, optional appendix, **`work_item_template`** subkeys) so operators paste/uncomment deliberately.
2. **`azure_boards.org_mappings`**: a **non-empty** list when the CSV has rows, fully populated per the resolution requirement.
3. **`snyk.group_id`**: the **`--group-id`** value (string as in examples).
4. **Mapping store section**: **`azure_table`** configuration SHALL appear **only as YAML comments** (e.g. **`# mapping_store: azure_table`**, **`# mapping_store_azure_table_endpoint: ...`**, **`# mapping_store_azure_table_name: ...`**), per operator request. The tool MAY additionally include commented **`sqlite`** dev lines for consistency with **`data/sample-config.yaml`**.

The output MUST NOT contain secrets. The tool SHOULD use **stable, readable ordering** (e.g. org_mappings in CSV order).

#### Scenario: Starter file mirrors examples semantically

- **WHEN** generation succeeds for a multi-row CSV
- **THEN** the file SHALL be parseable YAML, SHALL list **`org_mappings`** with ADO and Snyk fields, SHALL set **`snyk.group_id`**, and SHALL keep **`azure_boards.defaults`** and **`mapping_store`** as commented templates without asserting production-ready mapping-store settings

### Requirement: Tests for public behavior

Every **public** function and **CLI-facing** behavior SHALL have **automated unit tests** that assert documented behavior, including: CSV validation errors, pagination aggregation (mocked HTTP), unique match success, no-match failure, duplicate-name failure, and stable YAML structure for representative inputs. Tests SHALL use **mocked HTTP** and **no live **`SNYK_TOKEN`**.

#### Scenario: Regression safety

- **WHEN** a maintainer runs the project’s standard test command
- **THEN** tests for this tool SHALL run without network access and SHALL validate the behaviors above
