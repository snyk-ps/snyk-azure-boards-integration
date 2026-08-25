## ADDED Requirements

### Requirement: Classification Nodes operations for area paths

The client SHALL support the following Classification Nodes operations aligned with `openspec/specs/integration-apis/spec.md`, using caller-supplied **`organization`** and **`project`** and default **`api-version=7.1`**:

- **Get classification node:** `GET …/wit/classificationnodes/{structureGroup}/{path}` where **`structureGroup`** is **`Areas`** (or **`Iterations`** if extended in a future change — this change requires **`Areas`** only).
- **Create or update classification node:** `POST …/wit/classificationnodes/{structureGroup}/{path}` with a JSON body including at minimum **`name`** for the new child segment.

For **get**, a **404** response SHALL be surfaced to the caller as a distinguishable outcome (for example **`None`**, a dedicated exception type, or an error the caller maps to “not found”) without logging secrets.

For **create or update**, the client SHALL send **`Content-Type: application/json`** and SHALL apply the same authentication, **`429`** retry, and error surfacing rules as other WIT mutating operations in this capability.

The client SHALL NOT read operator YAML or infer area paths from configuration; callers supply **`organization`**, **`project`**, **`structureGroup`**, **`path`**, and segment **`name`** explicitly.

#### Scenario: Get existing area node

- **WHEN** the caller requests **`Areas`** node path **`AppTeam\\Snyk`** and ADO returns **200**
- **THEN** the client SHALL return the normalized node payload to the caller without logging credentials

#### Scenario: Get missing area node

- **WHEN** the caller requests an **`Areas`** path that does not exist and ADO returns **404**
- **THEN** the client SHALL surface a not-found outcome distinguishable from transport or auth failures

#### Scenario: Create child area segment

- **WHEN** the caller creates a child segment **`Snyk`** under parent path **`AppTeam`** with default client settings
- **THEN** the client SHALL issue **`POST`** to the Classification Nodes create-or-update URL with **`api-version=7.1`** and a JSON body containing **`name`** **`Snyk`**

#### Scenario: Create surfaces auth failure without secrets

- **WHEN** create-or-update returns **403**
- **THEN** the error surfaced to the caller SHALL indicate authorization failure without including the PAT
