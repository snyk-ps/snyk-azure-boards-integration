# repo-area-path-mapping Specification

## Purpose
TBD - created by archiving change repo-to-area-path-routing. Update Purpose after archive.
## Requirements
### Requirement: Repo mapping CSV file format

The operator **`repo-mapping.csv`** file SHALL be a UTF-8 CSV with a header row. Required column headers (matched case-insensitively after ASCII **`strip`**) SHALL be:

- **`Source`**
- **`GitHub Org/ADO Project`**
- **`Repo Name`**
- **`ADO Organization`**
- **`Area Path`**

Optional columns **`Assignee (Optional)`** (alias: **`Assignee`**) and the optional work-item taxonomy columns defined in **Optional CSV work item taxonomy columns** MAY be present. Additional unrecognized columns SHALL be ignored.

Each data row SHALL supply non-empty **`Source`**, **`ADO Organization`**, **`Area Path`**, and **`Repo Name`** after trim. **`GitHub Org/ADO Project`** MAY be empty after trim when matching uses repo-only keys (see **Owner/Repo parsing**).

Each data row **`Area Path`** SHALL contain at least two path segments separated by **`\`** after trim (for example **`PaymentsProject\TeamA`**). The loader SHALL reject rows where **Area Path** has fewer than two segments.

The loader SHALL reject the file when required headers are missing, when any required cell is empty after trim, when any **Area Path** fails the segment rule, or when two rows normalize to the same lookup key **(Source, scope, repo)**.

#### Scenario: Valid CSV with optional assignee loads

- **WHEN** the CSV contains required headers and valid data rows with optional **`Assignee (Optional)`**
- **THEN** loading SHALL succeed and expose an index for lookup

#### Scenario: Valid CSV with optional taxonomy columns loads

- **WHEN** the CSV adds optional headers **`Work Item Type (Optional)`** and **`Tags (Optional)`**
- **THEN** loading SHALL succeed

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

### Requirement: Optional CSV work item taxonomy columns

The operator **`repo-mapping.csv`** SHALL support optional column headers (matched case-insensitively after ASCII **`strip`**):

- **`Work Item Type (Optional)`** (alias: **`Work Item Type`**)
- **`Active State (Optional)`** (alias: **`Active State`**)
- **`Closed State (Optional)`** (alias: **`Closed State`**)
- **`Description Field (Optional)`** (alias: **`Description Field`**)
- **`Tags (Optional)`** (alias: **`Tags`**)

When a CSV row matches an issue, a **non-empty** cell in any optional taxonomy column SHALL override that field only for that issue, per **Work item taxonomy precedence**. Empty or whitespace-only cells SHALL be ignored (fall through to lower precedence).

**`Tags (Optional)`** values SHALL be semicolon-separated tag strings (Azure Boards **`System.Tags`** convention). Tags from CSV SHALL be **merged** with effective profile/template tags: profile tags first, then CSV tag tokens, deduplicated while preserving order.

The loader SHALL NOT require these columns. Unrecognized extra columns SHALL continue to be ignored.

#### Scenario: CSV work item type override applies

- **WHEN** a matching CSV row has **`Work Item Type (Optional)`** **`Bug`**
- **THEN** the effective work item type for that issue SHALL be **`Bug`** regardless of **`ado_targets`** or **`defaults`**

#### Scenario: Empty CSV taxonomy cell falls through

- **WHEN** a matching CSV row has empty **`Active State (Optional)`** and **`ado_targets`** defines **`work_item_state_active`** **`New`**
- **THEN** the effective active state SHALL be **`New`**

#### Scenario: CSV tags merge with profile tags

- **WHEN** effective profile tags are **`Snyk;Security`** and CSV **`Tags (Optional)`** is **`TeamA`**
- **THEN** effective tags SHALL include **`Snyk`**, **`Security`**, and **`TeamA`** in that order without duplicates

#### Scenario: Legacy header alias accepted

- **WHEN** the CSV uses header **`Work Item Type`** instead of **`Work Item Type (Optional)`**
- **THEN** loading SHALL succeed and treat that column as the optional work item type field

---

### Requirement: Work item taxonomy precedence

For each issue, after effective ADO **`(organization, project)`** is resolved per **Area path and assignee precedence**, the implementation SHALL resolve each work-item taxonomy field (**`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_description_field`**, effective **`work_item_template`** / tags) using this order **per field** (first applicable wins):

1. Non-empty matching CSV optional taxonomy column for that field (or tags merge rule for **`Tags (Optional)`**).
2. Matching **`azure_boards.ado_targets`** entry for effective **`(organization, project)`** when that field is set on the entry.
3. **`org_mappings[].overrides`** for the active Snyk org mapping row **only when** that row's **`(organization, project)`** equals the effective ADO target.
4. **`azure_boards.defaults`**.

Snyk-side policy fields (**`severity_threshold`**, **`sync_included_snyk_origins`**, **`issues_sync_from`**, etc.) SHALL **not** use this ladder; they remain merged from **`org_mappings[].overrides`** and **`defaults`** only.

When CSV routes to an ADO project different from the active **`org_mappings`** row's **`(organization, project)`**, step 3 SHALL NOT apply for work-item taxonomy (steps 1, 2, 4 only).

The implementation MAY log **`work_item_config_source`** as **`csv`**, **`ado_target`**, **`org_override`**, or **`defaults`** at INFO without secrets.

#### Scenario: ado_targets applies for CSV-routed project

- **WHEN** CSV routes to **`myado`/`PaymentsProject`**, **`ado_targets`** defines **`work_item_type`** **`Bug`** and **`work_item_state_active`** **`New`**, and the active **`org_mappings`** row targets a different project
- **THEN** effective work item type SHALL be **`Bug`** and effective active state SHALL be **`New`**

#### Scenario: Org override applies only for same ADO target

- **WHEN** no CSV row matches, effective target is **`myado`/`DefaultProject`** from the active **`org_mappings`** row, no **`ado_targets`** entry exists, and **`overrides.work_item_type`** is **`Task`**
- **THEN** effective work item type SHALL be **`Task`**

#### Scenario: CSV field beats ado_targets

- **WHEN** CSV row matches with **`Active State (Optional)`** **`Active`** and **`ado_targets`** defines **`work_item_state_active`** **`New`**
- **THEN** effective active state SHALL be **`Active`**

#### Scenario: Defaults when no higher source

- **WHEN** no CSV taxonomy override, no **`ado_targets`** entry, and org override does not apply
- **THEN** work-item taxonomy fields SHALL come from **`azure_boards.defaults`**

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

For each issue processed by **`sync`**, effective **ADO organization** and **ADO project** resolution SHALL use this order:

1. When a matching **`repo-mapping.csv`** row exists: **`ADO Organization`** from that row and **ADO project** from the **first segment** of that row's **`Area Path`** (before the first **`\`**).
2. When no CSV row matches: merged active **`org_mappings`** row or **`defaults`** **`organization`** and **`project`** from YAML (unchanged single-target behavior).

Effective **area path** resolution SHALL use this order (first non-empty wins):

1. Matching **`repo-mapping.csv`** row full **`Area Path`** value
2. Merged **`org_mappings[].overrides.area_path`** for the active routing row
3. Merged **`azure_boards.defaults.area_path`**
4. When merged **`auto_create_area_path`** is **`true`**: synthesize **`{effective_ado_project}\Snyk`** (fixed segment **`Snyk`** in v1)
5. No area path (ADO project default — omit **`System.AreaPath`** patch)

When a CSV row matches, optional **`Assignee (Optional)`** or legacy **`Assignee`** (non-empty after trim) SHALL be the effective assignee for **`System.AssignedTo`** on **create and update**, **overriding** merged **`work_item_template`** **`json_patch`** assignee values. When the CSV row matches but assignee is empty, assignee SHALL follow existing template merge rules.

When no CSV row matches, assignee SHALL follow existing template merge rules only.

The implementation MAY log **`ado_target_source`** as **`csv`** or **`config`** and **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, **`auto_default`**, or **`none`** at INFO without secrets.

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

#### Scenario: auto_create_area_path synthesizes Snyk fallback

- **WHEN** no CSV row matches, org override and **`defaults.area_path`** are unset, merged **`auto_create_area_path`** is **`true`**, and effective ADO project is **`AppTeam`**
- **THEN** the effective area path SHALL be **`AppTeam\\Snyk`** and **`area_path_source`** SHALL be **`auto_default`**

#### Scenario: auto_create_area_path false preserves unset behavior

- **WHEN** no CSV row matches, org override and **`defaults.area_path`** are unset, and merged **`auto_create_area_path`** is **`false`**
- **THEN** the effective area path SHALL be unset and **`area_path_source`** SHALL be **`none`**

#### Scenario: CSV assignee overrides template

- **WHEN** a CSV row matches with **`Assignee (Optional)`** **`user@example.com`** and merged template **`json_patch`** sets **`System.AssignedTo`** to another value
- **THEN** the effective assignee for create/update SHALL be **`user@example.com`**

### Requirement: Sample repo mapping CSV under data

The repository SHALL include a tracked sample CSV under **`data/sample-repo-mapping.csv`** with placeholder non-secret values demonstrating **`Source`**, **`GitHub Org/ADO Project`**, **`Repo Name`**, **`ADO Organization`**, **`Area Path`**, optional **`Assignee (Optional)`**, and documented optional taxonomy column headers. The sample SHALL be version-controlled and SHALL NOT be excluded by default **`.gitignore`** rules.

**`CONFIGURATION.md`** and **`README.md`** SHALL document the CSV column definitions (including optional taxonomy columns), **`ADO Organization`** and full **`Project\\Area`** **Area Path** semantics, work-item taxonomy precedence with **`ado_targets`**, **`github`** / **`azure-repos`** **Source** semantics, origin grouping table, **`Owner/Repo`** parsing, ADO target and area-path precedence, multi-project routing within one Snyk org, PAT scope requirements, and co-location with operator YAML on Azure Files (**`repo-mapping.csv`** beside **`config.yaml`**).

#### Scenario: Sample CSV present in clone

- **WHEN** a developer clones the repository
- **THEN** they SHALL find **`data/sample-repo-mapping.csv`** with documented column headers including **`ADO Organization`** and **`Assignee (Optional)`**

#### Scenario: CONFIGURATION documents CSV format and ado_targets precedence

- **WHEN** an operator reads **`CONFIGURATION.md`**
- **THEN** they SHALL find optional taxonomy columns, **`ado_targets`**, and precedence without reading source code

