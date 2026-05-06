## ADDED Requirements

### Requirement: Snyk REST Projects — get project by org

The integration SHALL use **`GET /orgs/{org_id}/projects/{project_id}`** (Snyk REST API, same **`version`** query parameter convention as Issues) to retrieve **project metadata** including **`attributes.name`** (display string for **`snyk_project_name`**) and **`attributes.origin`** (for **`snyk_project_origin`**) per **`sync-lifecycle`**.

#### Scenario: Documented path for project display name

- **WHEN** implementers need the Snyk human-readable project label for work item titles and descriptions
- **THEN** they SHALL find **`GET /orgs/{org_id}/projects/{project_id}`** referenced in this capability alongside Issues routes
