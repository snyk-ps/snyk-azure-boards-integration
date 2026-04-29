# Integration APIs — Snyk and Azure DevOps

REST API contracts used by the synchronization job. **Azure DevOps Services (cloud)** at `dev.azure.com` unless otherwise stated.

## Snyk REST API reference (Issues)

Scheduled sync uses the **Snyk REST API** **Issues** resources (JSON:API-style responses; not the legacy **V1** API or **`aggregated-issues`**).

Responses use **`application/vnd.api+json`** unless stated otherwise.

**Base URL:** `https://api.snyk.io/rest`

**Primary Issues paths** (see OpenAPI for operation ids, parameters, and permissions):

| | Method | Path |
|---|--------|------|
| List issues (group) | `GET` | `/groups/{group_id}/issues` |
| Get issue (group) | `GET` | `/groups/{group_id}/issues/{issue_id}` |
| List issues (org) | `GET` | `/orgs/{org_id}/issues` |
| Get issue (org) | `GET` | `/orgs/{org_id}/issues/{issue_id}` |

### Normative: Snyk Issues API org-scoped list and get

The normative **Snyk REST Issues** operations SHALL include **org** scope alongside **group** scope. Org-scoped operations SHALL use the same base URL, **`version`** query parameter expectations, and **`application/vnd.api+json`** media type conventions as the existing group-scoped Issues operations unless a future change documents an exception.

#### Scenario: Org list path documented

- **WHEN** implementers need to call the Snyk Issues API for all issues in a Snyk organization
- **THEN** they SHALL find **`GET /orgs/{org_id}/issues`** defined in this capability with the same normative status as the group list operation

#### Scenario: Org get path documented

- **WHEN** implementers need to retrieve a single issue in org scope
- **THEN** they SHALL find **`GET /orgs/{org_id}/issues/{issue_id}`** defined in this capability

Other issue-related routes (for example under **`/orgs/{org_id}/packages/...`**) are defined in the same spec if the implementation needs them.

## Azure DevOps REST API reference

Unless noted, use **`api-version=7.1`** for Work Item Tracking. The integration authenticates to `dev.azure.com` with a **PAT** (from Key Vault) or equivalent; scopes such as **`vso.work`** (read) and **`vso.work_write`** (create, update, comment) apply as documented for each operation.

### Create work item

| | |
|---|---|
| **HTTP** | `POST https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/${type}?api-version=7.1` |
| **Purpose** | Open a new work item; supply `type` in the URL (e.g. `Bug`). |
| **Request body** | `application/json-patch+json` — JSON Patch (`op`, `path`, `value`) for fields (e.g. `/fields/System.Title`, `/fields/System.Tags`). |

**Documentation:** [Work Items - Create](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/create?view=azure-devops-rest-7.1&tabs=HTTP).

### Get work item

| | |
|---|---|
| **HTTP** | `GET https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{id}?api-version=7.1` |
| **Purpose** | Read current revision, state, and fields before updates; optional query params include `fields`, `asOf`, `$expand`. |

**Documentation:** [Work Items - Get Work Item](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/get-work-item?view=azure-devops-rest-7.1&tabs=HTTP).

### List work items (by ids)

| | |
|---|---|
| **HTTP** | `GET https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids={ids}&api-version=7.1` |
| **Purpose** | Fetch up to **200** work items in one GET; use when batch POST is not used. |

**Documentation:** [Work Items - List](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/list?view=azure-devops-rest-7.1&tabs=HTTP).

### Update work item

| | |
|---|---|
| **HTTP** | `PATCH https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{id}?api-version=7.1` |
| **Purpose** | Change state (e.g. closed), description, tags, and other fields; same JSON Patch media type as create. |

**Documentation:** [Work Items - Update](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/update?view=azure-devops-rest-7.1&tabs=HTTP).

### Add work item comment (audit)

| | |
|---|---|
| **HTTP** | `POST https://dev.azure.com/{organization}/{project}/_apis/wit/workItems/{workItemId}/comments?api-version=7.0-preview.3` |
| **Purpose** | Append discussion text when the solution changes work item state (**P2-FR-9**). Request body includes `text`. |
| **Note** | Microsoft documents this operation under a **preview** `api-version`; confirm the version your organization supports and update if a newer stable version is available. |

**Documentation:** [Comments - Add](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/comments/add?view=azure-devops-rest-7.1&tabs=HTTP).

### Optional APIs

| Operation | HTTP (summary) | Purpose |
|-----------|----------------|---------|
| **Get work items batch** | `POST https://dev.azure.com/{organization}/{project}/_apis/wit/workitemsbatch?api-version=7.1` with JSON body (`ids`, optional `fields`) | Bulk read up to **200** IDs per call; fewer round-trips than many GETs. [Docs](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/get-work-items-batch?view=azure-devops-rest-7.1&tabs=HTTP) |
| **Query by WIQL** | `POST https://dev.azure.com/{organization}/{project}/{team}/_apis/wit/wiql?api-version=7.1` with body `{ "query": "<WIQL>" }` | Reconciliation or ad hoc queries if not relying solely on Table Storage mapping. [Docs](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/wiql/query-by-wiql?view=azure-devops-rest-7.1&tabs=HTTP) |
| **Get project** | `GET https://dev.azure.com/{organization}/_apis/projects/{projectId}?api-version=7.1` | Lightweight connectivity check against the target project (**P2-FR-6.1**). [Docs](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects/get?view=azure-devops-rest-7.1&tabs=HTTP) |
