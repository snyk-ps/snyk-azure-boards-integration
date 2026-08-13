## MODIFIED Requirements

### Requirement: Supported WIT operations (v1)

The client SHALL support the following operations aligned with `openspec/specs/integration-apis/spec.md`:

- **Create work item:** `POST …/wit/workitems/${type}` with **`application/json-patch+json`** body (JSON Patch operations).
- **Get work item:** `GET …/wit/workitems/{id}`.
- **List work items by ids:** `GET …/wit/workitems?ids=…&errorPolicy=Omit` with **at most 200** ids per request; if the caller supplies more than 200 ids in a single list call, the client SHALL fail before HTTP with a clear error.
- **Update work item:** `PATCH …/wit/workitems/{id}` with **`application/json-patch+json`** body.
- **Add work item comment:** `POST …/wit/workItems/{workItemId}/comments` using the preview `api-version` from `integration-apis`, with a request body including comment text as required by that API.
- **List work item type fields:** `GET …/wit/workitemtypes/{type}/fields` with **`api-version=7.1`**, returning field reference names for the requested work item type in the given project.

The client SHALL NOT implement **`workitemsbatch`**, **WIQL query**, or **Core get project** in v1.

#### Scenario: Create sends JSON Patch

- **WHEN** the caller creates a work item with a work item type and a list of JSON Patch operations
- **THEN** the client SHALL issue `POST` with media type `application/json-patch+json` per `integration-apis`

#### Scenario: List ids cap

- **WHEN** the caller requests list-by-ids with more than 200 ids in one invocation
- **THEN** the client SHALL reject the call before sending HTTP

#### Scenario: List by ids uses errorPolicy Omit

- **WHEN** the caller requests list-by-ids with one or more ids
- **THEN** the client SHALL include **`errorPolicy=Omit`** in the query string per `integration-apis`

#### Scenario: Work item type fields list uses WIT api version

- **WHEN** the caller requests the field list for a work item type with default client settings
- **THEN** the client SHALL issue `GET` with `api-version=7.1` per `integration-apis`
