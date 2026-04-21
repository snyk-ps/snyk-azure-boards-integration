## MODIFIED Requirements

### Requirement: Mapping row schema and logical identity

The durable mapping store SHALL persist at minimum the following attributes per row, using **snake_case** **column** names and **TEXT** storage for all listed fields. Together they support **stable mapping** (**P2-FR-7**) and traceability for **re-open** behavior (**P2-FR-8**).

| Field | Role |
|-------|------|
| `group_id` | Snyk group identifier (with org and project) for the issue. |
| `org_id` | Snyk organization that owns the project and issue. |
| `project_id` | Snyk project containing the issue. |
| `issue_id` | Stable Snyk issue identifier. |
| `snyk_status` | **Derived** Snyk lifecycle label for sync policy and audit: exactly one of **`open`**, **`resolved`**, or **`ignored`**, computed from Issues API **`attributes.status`** and **`attributes.ignored`** per **`sync-lifecycle`** (not from `coordinates[].state`, and not a literal undocumented `closed` API status for storage). |
| `organization` | Azure DevOps organization name or id for REST calls. |
| `project` | Azure DevOps team project containing the work item. |
| `work_item_id` | Azure Boards work item id linked to this Snyk issue. |
| `work_item_status` | Azure Boards work item state as persisted for this mapping row. |

The logical identity of one **current** mapping for a Snyk issue in a given scope SHALL be **`(group_id, org_id, project_id, issue_id)`**. The implementation SHALL enforce **at most one row** per that tuple via a **UNIQUE** constraint on those four columns (or equivalent enforcement).

#### Scenario: Uniqueness prevents duplicate scope rows

- **WHEN** a second insert is attempted with the same `group_id`, `org_id`, `project_id`, and `issue_id` as an existing row
- **THEN** the store SHALL reject the duplicate per the UNIQUE constraint (or equivalent) so a single current mapping per issue-in-scope is preserved

#### Scenario: snyk_status uses derived vocabulary

- **WHEN** a sync run persists `snyk_status` after evaluating Snyk Issues attributes
- **THEN** the stored value SHALL be one of `open`, `resolved`, or `ignored` as defined by **`sync-lifecycle`**, never a legacy `closed` label for Snyk API `status`
