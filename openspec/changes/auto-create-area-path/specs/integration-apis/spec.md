## ADDED Requirements

### Requirement: Classification Nodes REST endpoints for area paths

The integration SHALL document the following Azure DevOps Work Item Tracking Classification Nodes endpoints for **area path** management, using **`api-version=7.1`** unless superseded in a later change:

| Operation | HTTP |
|-----------|------|
| **Get classification node** | `GET https://dev.azure.com/{organization}/{project}/_apis/wit/classificationnodes/Areas/{path}?api-version=7.1` |
| **Create or update classification node** | `POST https://dev.azure.com/{organization}/{project}/_apis/wit/classificationnodes/Areas/{path}?api-version=7.1` |

For **create or update**, **`{path}`** is the optional parent path under which the new child segment is created (omit or empty for root **`Areas`** children per Microsoft API semantics). The request body SHALL include at minimum **`name`** (string) for the new segment.

**Documentation:** [Classification Nodes - Get](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/classification-nodes/get?view=azure-devops-rest-7.1) and [Classification Nodes - Create Or Update](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/classification-nodes/create-or-update?view=azure-devops-rest-7.1).

These endpoints are used by **`sync`** only when operator configuration enables **`auto_create_area_path`** per **`application-config`**.

#### Scenario: Get URL template matches Microsoft docs

- **WHEN** implementation constructs a get-classification-node URL for organization **`contoso`**, project **`AppTeam`**, and path **`AppTeam\\Snyk`**
- **THEN** the URL SHALL use host **`dev.azure.com`**, path segment **`Areas`**, and query **`api-version=7.1`**

#### Scenario: Create URL uses POST with parent path

- **WHEN** implementation creates child segment **`Snyk`** under parent **`AppTeam`**
- **THEN** the request SHALL be **`POST`** to the **`Areas/{path}`** template with **`path`** representing the parent node
