# Delta: application-config

## ADDED Requirements

### Requirement: Azure DevOps routing under azure_boards

Under **`azure_boards`**, the configuration SHALL include **`organization`** and **`project`**, each a **non-secret** string used as Azure DevOps routing inputs (Azure DevOps organization name and project name or id as accepted by the REST path templates in `openspec/specs/integration-apis/spec.md`). These values SHALL NOT be used to transport secrets. The **`azure-devops-client`** and related commands SHALL obtain these fields from merged configuration or explicit CLI overrides per this capability’s precedence rules; the integration package SHALL NOT read the YAML file directly.

The sample configuration file under **`data/`** and the **`README.md`** configuration documentation SHALL include **`azure_boards.organization`** and **`azure_boards.project`** with placeholder non-secret values so operators can run DevOps smoke and future sync flows without inventing keys.

#### Scenario: Sample lists routing keys

- **WHEN** a developer opens the tracked sample YAML under `data/`
- **THEN** it SHALL include `azure_boards.organization` and `azure_boards.project` alongside existing `azure_boards` keys

#### Scenario: README documents routing keys

- **WHEN** an operator reads the README Configuration / parameter descriptions
- **THEN** they SHALL find `azure_boards.organization` and `azure_boards.project` described as non-secret routing fields for Azure DevOps
