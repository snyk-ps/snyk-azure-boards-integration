# repo-area-path-mapping Specification

## Purpose
TBD - created by archiving change repo-to-area-path-routing. Update Purpose after archive.
## Requirements
### Requirement: Repo mapping CSV file format

The operator **`repo-mapping.csv`** file SHALL be a UTF-8 CSV with a header row. Required column headers (matched case-insensitively after ASCII **`strip`**) SHALL be:

- **`Source`**
- **`GitHub Org/ADO Project`**
- **`Repo Name`**
- **`Area Path`**

An optional column **`Assignee`** MAY be present. Additional columns SHALL be ignored.

Each data row SHALL supply non-empty **`Source`**, **`Area Path`**, and **`Repo Name`** after trim. **`GitHub Org/ADO Project`** MAY be empty after trim when matching uses repo-only keys (see **Owner/Repo parsing**).

The loader SHALL reject the file when required headers are missing, when any required cell is empty after trim, or when two rows normalize to the same lookup key **(Source, scope, repo)**.

#### Scenario: Valid CSV with optional assignee loads

- **WHEN** the CSV contains headers **`Source`**, **`GitHub Org/ADO Project`**, **`Repo Name`**, **`Area Path`**, **`Assignee`** and valid data rows
- **THEN** loading SHALL succeed and expose an index for lookup

#### Scenario: Missing required header rejected

- **WHEN** the CSV omits the **`Area Path`** column
- **THEN** loading SHALL fail with a clear, non-secret error naming the missing header

#### Scenario: Duplicate lookup key rejected

- **WHEN** two rows normalize to the same **(Source, scope, repo)** key
- **THEN** loading SHALL fail with a clear error identifying the duplicate key

---

### Requirement: CSV Source values and Snyk origin grouping

The **`Source`** column SHALL accept only **`github`** or **`azure-repos`** after trim (case-sensitive).

When matching an issue, the implementation SHALL map Snyk **`snyk_project_origin`** (after trim) to a CSV **Source** as follows:

- **`github`**, **`github-cloud-app`**, **`github-enterprise`**, **`github-server-app`** → CSV Source **`github`**
- **`azure-repos`** → CSV Source **`azure-repos`**
- Any other origin → **no CSV match**

#### Scenario: GitHub cloud app origin maps to github Source

- **WHEN** **`snyk_project_origin`** is **`github-cloud-app`** and a CSV row has **`Source`** **`github`**
- **THEN** the row SHALL be eligible for lookup using that Source value

#### Scenario: Azure Repos origin maps to azure-repos Source

- **WHEN** **`snyk_project_origin`** is **`azure-repos`** and a CSV row has **`Source`** **`azure-repos`**
- **THEN** the row SHALL be eligible for lookup

#### Scenario: CLI origin does not match CSV

- **WHEN** **`snyk_project_origin`** is **`cli`**
- **THEN** no CSV row SHALL match regardless of CSV **Source** values

#### Scenario: Invalid Source cell rejected at load

- **WHEN** a CSV row **`Source`** value is **`gitlab`** after trim
- **THEN** loading SHALL fail with a clear error stating allowed values **`github`** and **`azure-repos`**

---

### Requirement: Owner/Repo parsing from snyk_project_name

For CSV lookup, the implementation SHALL parse **`snyk_project_name`** (after trim) by splitting on the **first** **`/`** character only:

- When a **`/`** is present: **`owner`** = segment before **`/`**, **`repo`** = segment after **`/`** (each trimmed).
- When no **`/`** is present: **`owner`** = empty string, **`repo`** = full trimmed name.

After extracting **`repo`**, the implementation SHALL strip any Snyk target suffix beginning at the first **`(`** character (for example **`nodejs-goof(main):package.json`** → **`nodejs-goof`**).

CSV **`GitHub Org/ADO Project`** SHALL match **`owner`**; CSV **`Repo Name`** SHALL match **`repo`**. All comparisons SHALL be case-sensitive after trim.

#### Scenario: Standard owner/repo name parses

- **WHEN** **`snyk_project_name`** is **`my-org/payments-api`**
- **THEN** lookup uses **`owner=my-org`** and **`repo=payments-api`**

#### Scenario: Branch and manifest suffix stripped from repo segment

- **WHEN** **`snyk_project_name`** is **`my-org/payments-api(main):package.json`**
- **THEN** lookup uses **`owner=my-org`** and **`repo=payments-api`**

#### Scenario: Name without slash uses repo-only key

- **WHEN** **`snyk_project_name`** is **`standalone-repo`** with no **`/`**
- **THEN** lookup uses **`owner=`** (empty) and **`repo=standalone-repo`**

---

### Requirement: Repo mapping CSV path resolution

The loader SHALL resolve an effective **`repo-mapping.csv`** path from **`azure_boards.repo_mapping_csv`**, environment variable **`REPO_MAPPING_CSV_PATH`**, or the default filename beside the loaded YAML configuration file.

When **`repo_mapping_csv`** is omitted and no environment or CLI layer overrides the path, the effective path SHALL be **`repo-mapping.csv`** in the **same directory as the loaded YAML configuration file**.

When **`repo_mapping_csv`** is set to a **relative** path, it SHALL be resolved relative to the directory containing the loaded YAML configuration file. Absolute paths SHALL be used as given.

The implementation SHALL recognize environment variable **`REPO_MAPPING_CSV_PATH`** with the same semantics, participating in **defaults → YAML → environment → CLI** precedence per **`application-config`**.

When the effective CSV path is set (explicitly or by default **`repo-mapping.csv`**) and the file is missing or unreadable, **`sync`** SHALL exit non-zero before the per-issue loop with a clear, non-secret error.

When operators disable repo CSV routing by setting an empty path at all layers (if supported by loader semantics), **`sync`** MAY proceed without CSV lookup; this change's default behavior assumes **`repo-mapping.csv`** beside config unless documented otherwise in **`application-config`**.

#### Scenario: Default path beside config file

- **WHEN** YAML is loaded from **`/config/config.yaml`**, **`repo_mapping_csv`** is omitted, and **`/config/repo-mapping.csv`** exists
- **THEN** **`sync`** SHALL load that file at startup

#### Scenario: Missing default CSV fails sync startup

- **WHEN** the effective path is **`/config/repo-mapping.csv`** and the file does not exist
- **THEN** **`sync`** SHALL exit non-zero before processing issues

#### Scenario: Environment overrides YAML path

- **WHEN** YAML sets **`repo_mapping_csv: mappings/a.csv`** and **`REPO_MAPPING_CSV_PATH=/data/repo-mapping.csv`**
- **THEN** the effective path SHALL be **`/data/repo-mapping.csv`**

---

### Requirement: Area path and assignee precedence

For each issue processed by **`sync`**, effective **area path** resolution SHALL use this order (first non-empty wins):

1. Matching **`repo-mapping.csv`** row **`Area Path`**
2. Merged **`org_mappings[].overrides.area_path`** for the active routing row
3. Merged **`azure_boards.defaults.area_path`**
4. No area path (ADO project default — omit **`System.AreaPath`** patch)

When a CSV row matches, optional **`Assignee`** (non-empty after trim) SHALL be the effective assignee for **`System.AssignedTo`** on **create and update**, **overriding** merged **`work_item_template`** **`json_patch`** assignee values. When the CSV row matches but **`Assignee`** is empty, assignee SHALL follow existing template merge rules.

When no CSV row matches, assignee SHALL follow existing template merge rules only.

#### Scenario: CSV area path beats defaults

- **WHEN** a CSV row matches with **`Area Path`** **`Proj\\TeamA`** and **`defaults.area_path`** is **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamA`**

#### Scenario: Org override beats defaults without CSV match

- **WHEN** no CSV row matches and **`overrides.area_path`** is **`Proj\\TeamC`** with **`defaults.area_path`** **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamC`**

#### Scenario: CSV assignee overrides template

- **WHEN** a CSV row matches with **`Assignee`** **`user@example.com`** and merged template **`json_patch`** sets **`System.AssignedTo`** to another value
- **THEN** the effective assignee for create/update SHALL be **`user@example.com`**

---

### Requirement: Sample repo mapping CSV under data

The repository SHALL include a tracked sample CSV under **`data/sample-repo-mapping.csv`** with placeholder non-secret values demonstrating **`Source`**, **`GitHub Org/ADO Project`**, **`Repo Name`**, **`Area Path`**, and optional **`Assignee`**. The sample SHALL be version-controlled and SHALL NOT be excluded by default **`.gitignore`** rules.

**`CONFIGURATION.md`** and **`README.md`** SHALL document the CSV column definitions, **`github`** / **`azure-repos`** **Source** semantics, origin grouping table, **`Owner/Repo`** parsing, precedence, and co-location with operator YAML on Azure Files (**`repo-mapping.csv`** beside **`config.yaml`**).

#### Scenario: Sample CSV present in clone

- **WHEN** a developer clones the repository
- **THEN** they SHALL find **`data/sample-repo-mapping.csv`** with documented column headers

#### Scenario: CONFIGURATION documents CSV format

- **WHEN** an operator reads **`CONFIGURATION.md`**
- **THEN** they SHALL find column definitions, Source values, and precedence without reading source code

