## ADDED Requirements

### Requirement: README documents Azure DevOps PAT acquisition and scopes

The repository **README** SHALL document how operators create an Azure DevOps **personal access token (PAT)** for this integration, including:

- Step-by-step UI navigation starting from **https://dev.azure.com** through **User settings** → **Personal access tokens** → **New Token** (or equivalent labels in the current Azure DevOps UI).
- Required **Work Items** scopes by use case:
  - **Read** (e.g. **Work Items: Read**, or the Azure DevOps UI equivalent) for **`azure-devops-smoke`** and other read-only validation.
  - **Read and write** (e.g. **Work Items: Read & write**, or the Azure DevOps UI equivalent) for work item **create**, **update**, and **comment** flows used by synchronization.
- A link to Microsoft’s **official** documentation for creating and using PATs with Azure DevOps.
- That the PAT **MUST NOT** be committed to source control or embedded in YAML configuration files, and **SHALL** be provided via the **`AZURE_DEVOPS_PAT`** environment variable for local and application use (production secret storage such as Key Vault remains documented elsewhere and **MAY** be referenced briefly without duplicating deployment steps).

#### Scenario: Operator finds PAT guidance in README

- **WHEN** an operator reads the README section that covers Azure DevOps authentication or configuration
- **THEN** they SHALL find PAT creation steps, the read vs read/write scope guidance, a link to Microsoft’s PAT documentation, and explicit instruction to use **`AZURE_DEVOPS_PAT`** and never commit the token
