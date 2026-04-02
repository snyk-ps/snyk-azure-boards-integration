# Sync lifecycle — work items and Snyk mapping

Normative functional requirements for work item creation, lifecycle, content, mapping, and tagging. Requirement IDs (**P2-FR-***) are stable across proposals and changes.

## Scope

Integrate Snyk security findings with Azure Boards: create and maintain work items for qualifying findings, keep them in sync with Snyk lifecycle, enrich tickets with finding metadata, and maintain a stable Snyk↔work-item mapping (see also `azure-platform` and `integration-apis` capabilities).

## Work item creation and lifecycle

| ID | Requirement |
|----|-------------|
| **P2-FR-1** | Create Azure Boards work items for **new** Snyk findings at **High** or **Critical** severity only. |
| **P2-FR-2** | Set newly created work items to a default **Unassigned** state (per process configuration). |
| **P2-FR-3** | Automatically **close** the linked work item when the corresponding Snyk finding is **fixed**. |
| **P2-FR-4** | Automatically **close** the linked work item when the corresponding Snyk finding is **ignored**. |
| **P2-FR-8** | If a finding that was fixed/closed becomes **open again**, **open a new** work item (do not silently reuse the closed one without a defined new ticket). |
| **P2-FR-9** | When the solution changes work item status, **add an audit comment** on the work item documenting that change. |
| **P2-FR-11** | Provide a **configuration setting** to **globally enable or disable** the creation of **new** Azure Boards work items. |

## Work item content (Snyk metadata)

Populate each created/updated work item with at least:

| ID | Field / content |
|----|-----------------|
| **P2-FR-5** | Required Snyk finding properties and details (see sub-items). |
| **P2-FR-5.1** | Description of the vulnerability. |
| **P2-FR-5.2** | Finding type: Open Source, Code, Container, or IaC. |
| **P2-FR-5.3** | CVE/CWE identifiers, when applicable. |
| **P2-FR-5.4** | Direct link to the finding in Snyk. |
| **P2-FR-5.5** | Fix availability and fix guidance, when available. |

## Mapping and tagging

| ID | Requirement |
|----|-------------|
| **P2-FR-7** | Maintain a **unique, stable mapping** between each Snyk finding and its Azure Boards work item (one finding — one active work item per policy in P2-FR-8). |
| **P2-FR-10** | Support **configurable tags** on work items (e.g. product type, `Snyk`, or other agreed labels). |
