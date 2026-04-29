## ADDED Requirements

### Requirement: Snyk Issues API org-scoped list and get

The normative **Snyk REST Issues** operations SHALL include **org** scope alongside **group** scope already documented in this capability:

| | Method | Path |
|---|--------|------|
| List issues (org) | `GET` | `/orgs/{org_id}/issues` |
| Get issue (org) | `GET` | `/orgs/{org_id}/issues/{issue_id}` |

These operations SHALL use the same base URL, **`version`** query parameter expectations, and **`application/vnd.api+json`** media type conventions as the existing group-scoped Issues operations unless a future change documents an exception.

#### Scenario: Org list path documented

- **WHEN** implementers need to call the Snyk Issues API for all issues in a Snyk organization
- **THEN** they SHALL find **`GET /orgs/{org_id}/issues`** defined in this capability with the same normative status as the group list operation

#### Scenario: Org get path documented

- **WHEN** implementers need to retrieve a single issue in org scope
- **THEN** they SHALL find **`GET /orgs/{org_id}/issues/{issue_id}`** defined in this capability
