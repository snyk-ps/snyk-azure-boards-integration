## ADDED Requirements

### Requirement: Audit comment when fallback area path is used

When **`sync`** assigns an effective area path with **`area_path_source`** **`auto_default`** or **`auto_fallback`**, it SHALL add a work item audit comment per **P2-FR-9** documenting the fallback assignment after a successful create, recreate, or update that sets **`System.AreaPath`**.

For **`auto_fallback`**, the comment SHALL reference the configured area path that was not found in Azure DevOps and the fallback path applied.

For **`auto_default`**, the comment SHALL reference the fallback path applied and that no area path was configured.

When the work item already has the effective fallback area path and no area-path change occurs, **`sync`** SHALL NOT add a duplicate fallback audit comment on subsequent runs.

#### Scenario: Create with missing CSV path adds fallback audit comment

- **WHEN** CSV **`Area Path`** **`testProjectBug\\area`** does not exist, fallback renders **`testProjectBug\\Snyk`**, and **`sync`** creates a work item
- **THEN** an audit comment SHALL state that **`testProjectBug\\area`** was not found and **`testProjectBug\\Snyk`** was assigned

#### Scenario: Create with auto_default adds fallback audit comment

- **WHEN** no area path is configured, fallback renders **`AppTeam\\Snyk`**, and **`sync`** creates a work item
- **THEN** an audit comment SHALL state that default fallback area path **`AppTeam\\Snyk`** was assigned

#### Scenario: Unchanged fallback path skips duplicate audit

- **WHEN** the work item already has **`System.AreaPath`** **`AppTeam\\Snyk`**, effective area path remains **`AppTeam\\Snyk`**, and **`sync`** updates other fields
- **THEN** **`sync`** SHALL NOT add a fallback audit comment solely for this feature

---

### Requirement: Strict full-path existence check for configured area paths

When verifying whether a configured area path exists before fallback substitution, **`sync`** SHALL treat the path as existing only when Classification Nodes GET returns success for the **full** configured path (all segments). A partial match (parent area exists, configured leaf missing) SHALL be treated as **not found**.

#### Scenario: Full configured path exists

- **WHEN** Classification Nodes GET for **`Proj\\TeamA`** returns success
- **THEN** **`sync`** SHALL use **`Proj\\TeamA`** and SHALL NOT substitute the fallback template

#### Scenario: Parent exists but full path missing

- **WHEN** **`Proj`** exists but **`Proj\\Missing`** does not, and configured path is **`Proj\\Missing`**
- **THEN** **`sync`** SHALL treat the configured path as missing and substitute the fallback template

## MODIFIED Requirements

### Requirement: Effective area path and assignee resolution for sync

For each issue processed by **`sync`**, after **`snyk_project_name`** and **`snyk_project_origin`** are known (from persisted mapping row and/or Snyk Projects API refresh per existing rules), the run SHALL resolve:

- **Effective ADO organization and project** per **`repo-area-path-mapping`**: CSV row **ADO Organization** and first **Area Path** segment when matched; otherwise merged YAML **`organization`** and **`project`** for the active routing context.
- **Effective area path** per **`repo-area-path-mapping`** precedence: CSV row full **Area Path** → **`org_mappings[].overrides.area_path`** → **`defaults.area_path`** → when merged **`auto_create_area_path`** is **`true`** and no configured path applies, rendered **`auto_create_fallback_area_path`** (default **`{project}\Snyk`**) → unset. When a configured path is missing in ADO and **`auto_create_area_path`** is **`true`**, substitute rendered fallback (**`area_path_source=auto_fallback`**).
- **Effective assignee** per **`repo-area-path-mapping`**: when a CSV row matches with non-empty **Assignee (Optional)** or legacy **Assignee**, that value; otherwise merged template assignee rules unchanged.
- **Effective work item taxonomy** per **`repo-area-path-mapping`** **Work item taxonomy precedence**: type, states, description field config, and template/tags.

Resolution SHALL occur per issue. The implementation MAY log **`ado_target_source`** as **`csv`** or **`config`**, **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, **`auto_default`**, **`auto_fallback`**, or **`none`**, and **`work_item_config_source`** as **`csv`**, **`ado_target`**, **`org_override`**, or **`defaults`** at INFO without secrets. When **`area_path_source`** is **`auto_fallback`**, the implementation SHALL log the configured path that was missing (non-secret). The implementation SHOULD log effective **`work_item_type`** and **`work_item_state_active`** at INFO on create/update paths without secrets.

#### Scenario: CSV match supplies ADO target area path and assignee

- **WHEN** a CSV row matches with **`ADO Organization`** **`myado`**, **`Area Path`** **`Proj\\TeamA`**, and **`Assignee (Optional)`** **`user@example.com`**
- **THEN** the effective ADO organization SHALL be **`myado`**, effective ADO project SHALL be **`Proj`**, effective area path SHALL be **`Proj\\TeamA`**, and effective assignee SHALL be **`user@example.com`**

#### Scenario: CSV-routed issue uses ado_targets taxonomy

- **WHEN** CSV routes to **`myado`/`PaymentsProject`**, **`ado_targets`** defines **`work_item_state_active`** **`New`**, and **`defaults.work_item_state_active`** is **`To Do`**
- **THEN** effective active state SHALL be **`New`** and **`work_item_config_source`** SHALL be **`ado_target`**

#### Scenario: No CSV match uses org override for area path

- **WHEN** no CSV row matches and merged **`overrides.area_path`** is **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamB`** and ADO org/project SHALL come from YAML

#### Scenario: auto_create_area_path supplies fallback default

- **WHEN** no CSV row matches, org override and **`defaults.area_path`** are unset, merged **`auto_create_area_path`** is **`true`**, fallback template is **`{project}\\Snyk`**, and effective ADO project is **`AppTeam`**
- **THEN** the effective area path SHALL be **`AppTeam\\Snyk`** and **`area_path_source`** SHALL be **`auto_default`**

#### Scenario: Missing configured path supplies auto_fallback

- **WHEN** CSV resolves **`Proj\\Missing`**, that full path does not exist in ADO, merged **`auto_create_area_path`** is **`true`**, and fallback template is **`{project}\\Snyk`**
- **THEN** the effective area path SHALL be **`Proj\\Snyk`** and **`area_path_source`** SHALL be **`auto_fallback`**

#### Scenario: No path configured omits AreaPath patch

- **WHEN** no CSV row matches, org override and **`defaults.area_path`** are unset, and merged **`auto_create_area_path`** is **`false`**
- **THEN** the effective area path SHALL be unset and **`sync`** SHALL NOT include **`System.AreaPath`** in the patch

---

### Requirement: Ensure area path exists when auto_create_area_path is enabled

When merged **`auto_create_area_path`** is **`true`** for the active routing context and the effective area path was resolved via **`auto_default`** or **`auto_fallback`**, **`sync`** SHALL ensure that the full fallback area path exists in the effective ADO **`(organization, project)`** before issuing create, recreate, or update JSON Patch operations that set **`System.AreaPath`**.

When the effective area path came from CSV, org override, or defaults **and** exists in ADO (strict full-path GET), **`sync`** SHALL NOT call Classification Nodes APIs for that issue.

Ensure SHALL use Azure DevOps Classification Nodes REST (**`Areas`**, **`api-version=7.1`**) per **`azure-devops-client`**: for each missing segment in the **fallback** path hierarchy, create the node under its parent. The implementation MAY cache successful ensures per sync run keyed by **`(organization, project, full_path)`** to avoid duplicate ADO calls.

When ensure fails due to authorization (**HTTP 401** or **403**) or client error (**HTTP 400**), **`sync`** SHALL log a concise non-secret diagnostic, **skip** that issue, and **continue** processing remaining issues per existing per-issue error handling.

When merged **`auto_create_area_path`** is **`false`**, **`sync`** SHALL NOT call Classification Nodes APIs solely for this feature.

#### Scenario: Ensure creates missing fallback segment before create

- **WHEN** effective area path is **`AppTeam\\Snyk`** with **`area_path_source`** **`auto_default`**, the **`Snyk`** node does not exist, merged **`auto_create_area_path`** is **`true`**, and **`sync`** creates a work item
- **THEN** **`sync`** SHALL create the missing area node before the work item create PATCH and SHALL set **`System.AreaPath`** to **`AppTeam\\Snyk`**

#### Scenario: Ensure does not run for existing configured path

- **WHEN** effective area path is **`Proj\\TeamA`** from CSV, **`TeamA`** exists (full-path GET success), and **`auto_create_area_path`** is **`true`**
- **THEN** **`sync`** SHALL NOT call Classification Nodes create APIs

#### Scenario: Ensure skipped when auto_create disabled

- **WHEN** merged **`auto_create_area_path`** is **`false`** and effective area path is **`AppTeam\\Snyk`**
- **THEN** **`sync`** SHALL NOT call Classification Nodes APIs and SHALL attempt the work item patch directly

#### Scenario: Ensure permission failure skips issue

- **WHEN** ensure returns **HTTP 403** for a missing fallback area segment and **`sync`** would create a work item for that issue
- **THEN** **`sync`** SHALL skip that issue, log a non-secret diagnostic referencing area-path permissions, and continue the run

#### Scenario: Missing configured path ensures fallback only

- **WHEN** CSV resolves **`Proj\\Missing`**, **`Missing`** does not exist, fallback is **`Proj\\Snyk`**, and **`auto_create_area_path`** is **`true`**
- **THEN** **`sync`** SHALL ensure **`Proj\\Snyk`** exists and SHALL NOT create the **`Missing`** segment
