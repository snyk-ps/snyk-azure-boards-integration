## 1. README — Azure DevOps PAT

- [x] 1.1 Add a dedicated subsection under the README configuration / secrets area (see `design.md` for placement) with step-by-step PAT creation: **https://dev.azure.com** → user **Settings** → **Personal access tokens** → **New Token** (use wording that matches the current Azure DevOps UI).
- [x] 1.2 Document scope tiers: **Work Items: Read** (or UI equivalent) for **`azure-devops-smoke`** / read-only; **Work Items: Read & write** (or UI equivalent) for create, update, and comment flows.
- [x] 1.3 Add a markdown link to Microsoft’s official PAT documentation (current `learn.microsoft.com` page for Azure DevOps PATs).
- [x] 1.4 State that the PAT must **never** be committed and must be provided via **`AZURE_DEVOPS_PAT`**; optionally one sentence pointing to existing deployment/Key Vault docs without duplicating ACA/Key Vault steps.

## 2. Verification

- [x] 2.1 Re-read `README.md` as an operator: confirm “how do I get a PAT and what permissions?” is answered without opening other repository files.
- [x] 2.2 Run `openspec validate readme-azure-devops-pat` and resolve any validation issues.
