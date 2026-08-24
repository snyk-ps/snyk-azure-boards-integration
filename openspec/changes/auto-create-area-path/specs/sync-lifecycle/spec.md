## ADDED Requirements

### Requirement: Ensure area path exists when auto_create_area_path is enabled

When merged **`auto_create_area_path`** is **`true`** for the active routing context and the effective area path is non-empty after trim, **`sync`** SHALL ensure that the full area path exists in the effective ADO **`(organization, project)`** before issuing create, recreate, or update JSON Patch operations that set **`System.AreaPath`**.

Ensure SHALL use Azure DevOps Classification Nodes REST (**`Areas`**, **`api-version=7.1`**) per **`azure-devops-client`**: for each missing segment in the path hierarchy, create the node under its parent. The implementation MAY cache successful ensures per sync run keyed by **`(organization, project, full_path)`** to avoid duplicate ADO calls.

When ensure fails due to authorization (**HTTP 401** or **403**) or client error (**HTTP 400**), **`sync`** SHALL log a concise non-secret diagnostic, **skip** that issue, and **continue** processing remaining issues per existing per-issue error handling.

When merged **`auto_create_area_path`** is **`false`**, **`sync`** SHALL NOT call Classification Nodes APIs solely for this feature.

#### Scenario: Ensure creates missing segment before create

- **WHEN** effective area path is **`AppTeam\\Snyk`**, the **`Snyk`** node does not exist, merged **`auto_create_area_path`** is **`true`**, and **`sync`** creates a work item
- **THEN** **`sync`** SHALL create the missing area node before the work item create PATCH and SHALL set **`System.AreaPath`** to **`AppTeam\\Snyk`**

#### Scenario: Ensure skipped when auto_create disabled

- **WHEN** merged **`auto_create_area_path`** is **`false`** and effective area path is **`AppTeam\\Snyk`**
- **THEN** **`sync`** SHALL NOT call Classification Nodes APIs and SHALL attempt the work item patch directly

#### Scenario: Ensure permission failure skips issue

- **WHEN** ensure returns **HTTP 403** for a missing area segment and **`sync`** would create a work item for that issue
- **THEN** **`sync`** SHALL skip that issue, log a non-secret diagnostic referencing area-path permissions, and continue the run

## MODIFIED Requirements

### Requirement: Effective area path and assignee resolution for sync

For each issue processed by **`sync`**, after **`snyk_project_name`** and **`snyk_project_origin`** are known (from persisted mapping row and/or Snyk Projects API refresh per existing rules), the run SHALL resolve:

- **Effective ADO organization and project** per **`repo-area-path-mapping`**: CSV row **ADO Organization** and first **Area Path** segment when matched; otherwise merged YAML **`organization`** and **`project`** for the active routing context.
- **Effective area path** per **`repo-area-path-mapping`** precedence: CSV row full **Area Path** → **`org_mappings[].overrides.area_path`** → **`defaults.area_path`** → when merged **`auto_create_area_path`** is **`true`**, **`{effective_ado_project}\Snyk`** → unset.
- **Effective assignee** per **`repo-area-path-mapping`**: when a CSV row matches with non-empty **Assignee (Optional)** or legacy **Assignee**, that value; otherwise merged template assignee rules unchanged.
- **Effective work item taxonomy** per **`repo-area-path-mapping`** **Work item taxonomy precedence**: type, states, description field config, and template/tags.

Resolution SHALL occur per issue. The implementation MAY log **`ado_target_source`** as **`csv`** or **`config`**, **`area_path_source`** as **`csv`**, **`org_override`**, **`defaults`**, **`auto_default`**, or **`none`**, and **`work_item_config_source`** as **`csv`**, **`ado_target`**, **`org_override`**, or **`defaults`** at INFO without secrets. The implementation SHOULD log effective **`work_item_type`** and **`work_item_state_active`** at INFO on create/update paths without secrets.

#### Scenario: CSV match supplies ADO target area path and assignee

- **WHEN** a CSV row matches with **`ADO Organization`** **`myado`**, **`Area Path`** **`Proj\\TeamA`**, and **`Assignee (Optional)`** **`user@example.com`**
- **THEN** the effective ADO organization SHALL be **`myado`**, effective ADO project SHALL be **`Proj`**, effective area path SHALL be **`Proj\\TeamA`**, and effective assignee SHALL be **`user@example.com`**

#### Scenario: CSV-routed issue uses ado_targets taxonomy

- **WHEN** CSV routes to **`myado`/`PaymentsProject`**, **`ado_targets`** defines **`work_item_state_active`** **`New`**, and **`defaults.work_item_state_active`** is **`To Do`**
- **THEN** effective active state SHALL be **`New`** and **`work_item_config_source`** SHALL be **`ado_target`**

#### Scenario: No CSV match uses org override for area path

- **WHEN** no CSV row matches and merged **`overrides.area_path`** is **`Proj\\TeamB`**
- **THEN** the effective area path SHALL be **`Proj\\TeamB`** and ADO org/project SHALL come from YAML

#### Scenario: auto_create_area_path supplies Snyk fallback

- **WHEN** no CSV row matches, org override and **`defaults.area_path`** are unset, merged **`auto_create_area_path`** is **`true`**, and effective ADO project is **`AppTeam`**
- **THEN** the effective area path SHALL be **`AppTeam\\Snyk`** and **`area_path_source`** SHALL be **`auto_default`**

#### Scenario: No path configured omits AreaPath patch

- **WHEN** no CSV row matches, org override and **`defaults.area_path`** are unset, and merged **`auto_create_area_path`** is **`false`**
- **THEN** the effective area path SHALL be unset and **`sync`** SHALL NOT include **`System.AreaPath`** in the patch
