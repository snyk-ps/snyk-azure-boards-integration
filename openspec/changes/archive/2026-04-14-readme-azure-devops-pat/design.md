## Context

Operators configure non-secret YAML and environment-backed secrets separately. The product already expects Azure DevOps authentication via **`AZURE_DEVOPS_PAT`** (see `openspec/specs/azure-platform/spec.md` and project README). The README’s configuration story should stand alone for “how do I get a PAT and what permissions?” without reading OpenSpec files day-to-day.

## Goals / Non-Goals

**Goals:**

- Add concise, accurate PAT creation steps in **README.md** (Azure DevOps web UI path: dev.azure.com → user settings → Personal access tokens → new token).
- Document scope tiers: **Work Items: Read** for `azure-devops-smoke` / read-only validation; **Work Items: Read & write** (or Azure DevOps UI equivalent) for create, update, and comment flows.
- Link to Microsoft’s official PAT documentation.
- State clearly: never commit the token; set **`AZURE_DEVOPS_PAT`** in the environment (or secret store in production — high level only here if already covered elsewhere).

**Non-Goals:**

- Key Vault, ACA wiring, or deployment runbooks (handled in other docs/specs).
- Full UI walkthroughs or screenshot galleries.
- Changing application code, YAML schema, or Azure DevOps client behavior.

## Decisions

- **Placement:** Extend the existing README **Configuration** (and/or **Secrets** / **Environment variables**) section so one scroll answers PAT questions; use a short subsection heading (e.g. “Azure DevOps personal access token (PAT)”).
- **Scope naming:** Mirror Azure DevOps PAT scope labels as shown in the current Azure DevOps UI (e.g. “Work Items (Read)” vs “Work Items (Read & write)”) and note that labels may vary slightly by org/version, pointing readers to Microsoft docs for authority.
- **Normative traceability:** Record the operator-facing documentation obligation as an **ADDED** requirement under existing capability **`application-config`** (README is already in scope there) so `openspec validate` and archive have a single testable requirement without creating a new top-level capability.

## Risks / Trade-offs

- **Azure DevOps UI wording drift** → Mitigation: link to Microsoft PAT docs; describe intent (read-only vs mutate work items) alongside exact scope names.
- **Spec delta for a doc-only change** → Mitigation: one focused ADDED requirement; no change to YAML loader or runtime behavior.

## Migration Plan

Not applicable — documentation and spec delta only. After merge, no data migration.

## Open Questions

None — Microsoft PAT doc URL should be the current `learn.microsoft.com` PAT page at implementation time.
