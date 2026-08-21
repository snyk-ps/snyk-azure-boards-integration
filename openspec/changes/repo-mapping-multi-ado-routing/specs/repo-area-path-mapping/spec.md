## MODIFIED Requirements

### Requirement: Repo mapping CSV file format

The operator **`repo-mapping.csv`** file SHALL be a UTF-8 CSV with a header row. Required column headers (matched case-insensitively after ASCII **`strip`**) SHALL be:

- **`Source`**
- **`GitHub Org/ADO Project`**
- **`Repo Name`**
- **`ADO Organization`**
- **`Area Path`**

An optional column **`Assignee (Optional)`** MAY be present. The loader SHALL also accept the legacy header **`Assignee`** as an alias for the optional assignee column. Additional columns SHALL be ignored.

Each data row SHALL supply non-empty **`Source`**, **`ADO Organization`**, **`Area Path`**, and **`Repo Name`** after trim. **`GitHub Org/ADO Project`** MAY be empty after trim when matching uses repo-only keys (see **Owner/Repo parsing**).

Each data row **`Area Path`** SHALL contain at least two path segments separated by **`\`** after trim (for example **`PaymentsProject\TeamA`**). The loader SHALL reject rows where **Area Path** has fewer than two segments.

The loader SHALL reject the file when required headers are missing, when any required cell is empty after trim, when any **Area Path** fails the segment rule, or when two rows normalize to the same lookup key **(Source, scope, repo)**.

#### Scenario: Valid CSV with optional assignee loads

- **WHEN** the CSV contains headers **`Source`**, **`GitHub Org/ADO Project`**, **`Repo Name`**, **`ADO Organization`**, **`Area Path`**, **`Assignee (Optional)`** and valid data rows
- **THEN** loading SHALL succeed and expose an index for lookup

#### Scenario: Legacy Assignee header accepted

- **WHEN** the CSV uses header **`Assignee`** instead of **`Assignee (Optional)`**
- **THEN** loading SHALL succeed and treat that column as the optional assignee field

#### Scenario: Missing required header rejected

- **WHEN** the CSV omits the **`ADO Organization`** column
- **THEN** loading SHALL fail with a clear, non-secret error naming the missing header

#### Scenario: Empty ADO Organization rejected

- **WHEN** a data row has an empty **`ADO Organization`** cell after trim
- **THEN** loading SHALL fail with a clear error identifying the row

#### Scenario: Area Path with single segment rejected

- **WHEN** a data row **`Area Path`** is **`TeamA`** with no **`Project\`** prefix
- **THEN** loading SHALL fail with a clear error identifying the row

#### Scenario: Duplicate lookup key rejected

- **WHEN** two rows normalize to the same **(Source, scope, repo)** key
- **THEN** loading SHALL fail with a clear error identifying the duplicate key

---

### Requirement: Area path and assignee precedence

For each issue processed by **`sync`**, effective **ADO organization** and **ADO project** resolution SHALL use this order:

1. When a matching **`repo-mapping.csv`** row exists: **`ADO Organization`** from that row and **ADO project** from the **first segment** of that row's **`Area Path`** (before the first **`\`**).
2. When no CSV row matches: merged active **`org_mappings`** row or **`defaults`** **`organization`** and **`project`** from YAML (unchanged single-target behavior).

Effective **area path** resolution SHALL use this order (first non-empty wins):

1. Matching **`repo-mapping.csv`** row full **`Area Path`** value
2. Merged **`org_mappings[].overrides.area_path`** for the active routing row
3. Merged **`azure_boards.defaults.area_path`**
4. No area path (ADO project default — omit **`System.AreaPath`** patch)

When a CSV row matches, optional **`Assignee (Optional)`** or legacy **`Assignee`** (non-empty after trim) SHALL be the effective assignee for **`System.AssignedTo`** on **create and update**, **overriding** merged **`work_item_template`** **`json_patch`** assignee values. When the CSV row matches but assignee is empty, assignee SHALL follow existing template merge rules.

When no CSV row matches, assignee SHALL follow existing template merge rules only.

The implementation MAY log **`ado_target_source`** as **`csv`** or **`config`** and **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, or **`none`** at INFO without secrets.

#### Scenario: CSV match supplies ADO org project and area path

- **WHEN** a CSV row matches with **`ADO Organization`** **`myado`**, **`Area Path`** **`PaymentsProject\\Payments`**, and **`Assignee (Optional)`** **`user@example.com`**
- **THEN** the effective ADO organization SHALL be **`myado`**, effective ADO project SHALL be **`PaymentsProject`**, effective area path SHALL be **`PaymentsProject\\Payments`**, and effective assignee SHALL be **`user@example.com`**

#### Scenario: No CSV match uses YAML ADO target

- **WHEN** no CSV row matches and merged config **`organization`** is **`myado`** and **`project`** is **`DefaultProject`**
- **THEN** the effective ADO organization SHALL be **`myado`** and effective ADO project SHALL be **`DefaultProject`**

#### Scenario: CSV area path beats defaults

- **WHEN** a CSV row matches with **`Area Path`** **`Proj\\TeamA`** and **`defaults.area_path`** is **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamA`**

#### Scenario: Org override beats defaults without CSV match

- **WHEN** no CSV row matches and **`overrides.area_path`** is **`Proj\\TeamC`** with **`defaults.area_path`** **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamC`**

#### Scenario: CSV assignee overrides template

- **WHEN** a CSV row matches with **`Assignee (Optional)`** **`user@example.com`** and merged template **`json_patch`** sets **`System.AssignedTo`** to another value
- **THEN** the effective assignee for create/update SHALL be **`user@example.com`**

---

### Requirement: Sample repo mapping CSV under data

The repository SHALL include a tracked sample CSV under **`data/sample-repo-mapping.csv`** with placeholder non-secret values demonstrating **`Source`**, **`GitHub Org/ADO Project`**, **`Repo Name`**, **`ADO Organization`**, **`Area Path`**, and optional **`Assignee (Optional)`**. The sample SHALL be version-controlled and SHALL NOT be excluded by default **`.gitignore`** rules.

**`CONFIGURATION.md`** and **`README.md`** SHALL document the CSV column definitions, **`ADO Organization`** and full **`Project\\Area`** **Area Path** semantics, **`github`** / **`azure-repos`** **Source** semantics, origin grouping table, **`Owner/Repo`** parsing, ADO target and area-path precedence, multi-project routing within one Snyk org, PAT scope requirements, and co-location with operator YAML on Azure Files (**`repo-mapping.csv`** beside **`config.yaml`**).

#### Scenario: Sample CSV present in clone

- **WHEN** a developer clones the repository
- **THEN** they SHALL find **`data/sample-repo-mapping.csv`** with documented column headers including **`ADO Organization`** and **`Assignee (Optional)`**

#### Scenario: CONFIGURATION documents CSV format

- **WHEN** an operator reads **`CONFIGURATION.md`**
- **THEN** they SHALL find column definitions, ADO target routing from CSV, Source values, and precedence without reading source code
