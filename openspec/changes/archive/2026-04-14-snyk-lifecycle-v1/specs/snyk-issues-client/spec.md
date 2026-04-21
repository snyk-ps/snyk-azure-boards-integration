## MODIFIED Requirements

### Requirement: Issue list and get operations

The client SHALL support HTTP `GET` for **listing issues and for retrieving a single issue in group scope only**, using `GET /groups/{group_id}/issues` and `GET /groups/{group_id}/issues/{issue_id}` as documented in `openspec/specs/integration-apis/spec.md`. The client SHALL send the **`version`** query parameter set to **`2025-11-05`** on every Issues request unless overridden in tests. The default base URL SHALL be `https://api.snyk.io/rest`; the client SHALL allow a different base URL to be supplied for testing.

For **list**, the client SHALL request **`limit=100`** on the **first** page URL (maximum page size). The client SHALL support optional list filters aligned with the Snyk REST API for that operation: **`effective_severity_level`** (zero or more values; when none are supplied the client SHALL default to **`high`** and **`critical`**), **`type`** (optional), and **`status`** (optional). Parameters SHALL be expressible from CLI and programmatic APIs so future external configuration can supply the same values without changing HTTP shape.

The client SHALL expose **normalized issue records** for each issue suitable for downstream sync, including at minimum: **`org_id`** (from `data[].relationships.organization.data.id`), **`project_id`** (from `data[].relationships.scan_item.data.id`), **`issue_id`** (from `data[].attributes.key`), **`created_at`** (from `data[].attributes.created_at`), **`severity`** (from `data[].attributes.effective_severity_level`), **`status`** (from `data[].attributes.status`), and **`ignored`** (from `data[].attributes.ignored`, coerced to boolean when the API uses a boolean-like representation). Additional fields MAY be added later; the client design SHALL not block extending the normalized record.

Downstream synchronization SHALL treat **`coordinates[].state`** as **non-authoritative** for open/close lifecycle; normalized records exist to carry **attributes**-based lifecycle fields above.

#### Scenario: List issues for a group

- **WHEN** the caller requests listing issues for a valid `group_id`
- **THEN** the client SHALL call `GET /groups/{group_id}/issues` with `version=2025-11-05`, `limit=100`, default effective severity `high` and `critical` when the caller did not specify severities, optional `type` and `status` when provided, and SHALL yield or return normalized records per this capability

#### Scenario: Get one issue in group scope

- **WHEN** the caller requests a single issue by `group_id` and `issue_id`
- **THEN** the client SHALL call `GET /groups/{group_id}/issues/{issue_id}` with `version=2025-11-05` and SHALL return a normalized issue record including the required fields where present in the response

#### Scenario: Normalized record includes status and ignored

- **WHEN** the API returns `data[].attributes.status` and `data[].attributes.ignored` for an issue
- **THEN** the normalized record SHALL include `status` and `ignored` with those values (with `ignored` represented as a boolean suitable for downstream comparisons)
