## MODIFIED Requirements

### Requirement: Area path and assignee precedence

For each issue processed by **`sync`**, effective **ADO organization** and **ADO project** resolution SHALL use this order:

1. When a matching **`repo-mapping.csv`** row exists: **`ADO Organization`** from that row and **ADO project** from the **first segment** of that row's **`Area Path`** (before the first **`\`**).
2. When no CSV row matches: merged active **`org_mappings`** row or **`defaults`** **`organization`** and **`project`** from YAML (unchanged single-target behavior).

Effective **area path** resolution SHALL use this order (first non-empty wins for configured paths):

1. Matching **`repo-mapping.csv`** row full **`Area Path`** value
2. Merged **`org_mappings[].overrides.area_path`** for the active routing row
3. Merged **`azure_boards.defaults.area_path`**
4. When merged **`auto_create_area_path`** is **`true`** and steps 1–3 yield unset: synthesize fallback from **`auto_create_fallback_area_path`** (default template **`{project}\Snyk`**) → **`area_path_source=auto_default`**
5. No area path (ADO project default — omit **`System.AreaPath`** patch)

When merged **`auto_create_area_path`** is **`true`** and a configured path from steps 1–3 is resolved but **does not exist** in the effective ADO target (strict full-path Classification Nodes GET), **`sync`** SHALL substitute the rendered fallback template at sync time and set **`area_path_source=auto_fallback`**. Configured paths from steps 1–3 SHALL **not** be auto-created.

**Fallback template runtime precedence** (per effective **`(organization, project)`**): matching **`ado_targets`** entry → **`org_mappings[].overrides`** (when org-mapping target matches) → merged **`defaults`** (env var **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH`** may seed **`defaults`** at load).

When a CSV row matches, optional **`Assignee (Optional)`** or legacy **`Assignee`** (non-empty after trim) SHALL be the effective assignee for **`System.AssignedTo`** on **create and update**, **overriding** merged **`work_item_template`** **`json_patch`** assignee values. When the CSV row matches but assignee is empty, assignee SHALL follow existing template merge rules.

When no CSV row matches, assignee SHALL follow existing template merge rules only.

The implementation MAY log **`ado_target_source`** as **`csv`** or **`config`** and **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, **`auto_default`**, **`auto_fallback`**, or **`none`** at INFO without secrets.

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

#### Scenario: auto_create_area_path synthesizes fallback default

- **WHEN** no CSV row matches, org override and **`defaults.area_path`** are unset, merged **`auto_create_area_path`** is **`true`**, fallback template is **`{project}\\Snyk`**, and effective ADO project is **`AppTeam`**
- **THEN** the effective area path SHALL be **`AppTeam\\Snyk`** and **`area_path_source`** SHALL be **`auto_default`**

#### Scenario: auto_create_area_path false preserves unset behavior

- **WHEN** no CSV row matches, org override and **`defaults.area_path`** are unset, and merged **`auto_create_area_path`** is **`false`**
- **THEN** the effective area path SHALL be unset and **`area_path_source`** SHALL be **`none`**

#### Scenario: Missing CSV area path triggers fallback

- **WHEN** a CSV row matches with **`Area Path`** **`testProjectBug\\area`**, that full path does not exist in ADO, merged **`auto_create_area_path`** is **`true`**, and fallback template is **`{project}\\Snyk`**
- **THEN** the effective area path SHALL be **`testProjectBug\\Snyk`** and **`area_path_source`** SHALL be **`auto_fallback`**

#### Scenario: Existing CSV area path used without auto-create

- **WHEN** a CSV row matches with **`Area Path`** **`Proj\\TeamA`**, that full path exists in ADO, and merged **`auto_create_area_path`** is **`true`**
- **THEN** the effective area path SHALL be **`Proj\\TeamA`**, **`area_path_source`** SHALL be **`csv`**, and **`sync`** SHALL NOT call Classification Nodes create APIs for that issue

#### Scenario: Parent exists but configured leaf missing triggers fallback

- **WHEN** **`Proj`** exists in ADO but **`Proj\\Missing`** does not, CSV specifies **`Proj\\Missing`**, and **`auto_create_area_path`** is **`true`**
- **THEN** the effective area path SHALL be the rendered fallback template and **`area_path_source`** SHALL be **`auto_fallback`**

#### Scenario: ado_targets overrides defaults fallback template

- **WHEN** **`defaults.auto_create_fallback_area_path`** is **`{project}\\Snyk`**, **`ado_targets`** for **`myado`/`PaymentsProject`** sets **`{project}\\Security`**, and CSV routes to **`PaymentsProject`**
- **THEN** the effective fallback template for that issue SHALL be **`{project}\\Security`**

#### Scenario: CSV assignee overrides template

- **WHEN** a CSV row matches with **`Assignee (Optional)`** **`user@example.com`** and merged template **`json_patch`** sets **`System.AssignedTo`** to another value
- **THEN** the effective assignee for create/update SHALL be **`user@example.com`**
