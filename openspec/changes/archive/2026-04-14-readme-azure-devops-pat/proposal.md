## Why

Operators need a single place in the repo that explains how to create an Azure DevOps personal access token (PAT) and which scopes this integration requires, without reading OpenSpec or other docs. Today that guidance is easy to miss or incomplete in the README configuration story.

## What Changes

- Extend **README.md** only: short step-by-step PAT creation (dev.azure.com → user settings → Personal access tokens → new token).
- Document required scopes:
  - **Work Items: Read** — sufficient for `azure-devops-smoke` / read-only checks.
  - **Work Items: Read & write** (or Azure DevOps UI equivalent) — required for create, update, and comment flows used by the sync integration.
- Link to official Microsoft documentation for PATs.
- Remind operators: never commit the token; use the **`AZURE_DEVOPS_PAT`** environment variable (aligned with existing project conventions).
- **Non-goals (explicitly out of scope here):** Key Vault, Azure Container Apps, or deployment wiring for secrets (covered elsewhere); duplicating full Microsoft UI screenshots; introducing a **new** capability folder under `openspec/specs/` (this change uses a small delta under existing `application-config` only so OpenSpec validation has a traceable requirement for README operator guidance).

## Capabilities

### New Capabilities

- None — no new capability under `openspec/specs/`.

### Modified Capabilities

- `application-config`: Add one **ADDED** requirement that the **README** SHALL document Azure DevOps PAT creation, required Work Item scopes (read vs read/write), the official Microsoft PAT documentation link, and use of **`AZURE_DEVOPS_PAT`** without committing the token (delta in this change’s `specs/application-config/spec.md`; archive merges into `openspec/specs/application-config/spec.md`).

## Impact

- **Documentation:** `README.md` (configuration / secrets section or adjacent operator setup).
- **OpenSpec:** This change includes a delta under **`application-config`**; archiving merges one ADDED README/PAT requirement into `openspec/specs/application-config/spec.md`.
- **Code / APIs / dependencies:** None.
- **Systems:** None — operators still supply PAT via `AZURE_DEVOPS_PAT` as today.
