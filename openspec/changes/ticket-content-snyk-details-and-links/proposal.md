## Why

Work items built from Snyk issues today use a **group-scoped** `app.snyk.io` URL that does **not** resolve to the in-product issue view and adds little value. Developers still need the **Snyk web UI** to see vulnerability narrative and fix guidance. **P2-FR-5.1**, **P2-FR-5.4**, and **P2-FR-5.5** are only partially met at the spec level (best-effort URL; flags-only fix summary). This change aligns tickets with **working deep links** and **API-backed remediation text** so engineers can act from Azure Boards alone when Snyk exposes that data.

## What Changes

- **Configurable `snyk_org_slug`** (non-secret) on **`org_mappings`** rows so links use the real **org → project → issue hash** pattern used by the Snyk web app. Group-level sync without **`org_mappings`** does not configure a slug yet (links may be incomplete until a follow-up).
- **Normative Snyk UI URL** shape: `https://app.snyk.io/org/<org-slug>/project/<project-id>#issue-<issue-key>`, with `project-id` and `issue-key` from the Issues API payload and `org-slug` from configuration.
- **Richer `System.Description` (and same content rules on update):** include **`attributes.description`**, structured **`coordinates.remedies`** (and other issue attributes documented for remediation in Snyk GA Issues), plus existing **P2-FR-5.2** / **P2-FR-5.3** / primary-package / fix-flag content so remediation does not depend on opening Snyk.
- **Optional `GET` single-issue** call in the same scope (group or org) when the **list** payload omits fields needed for the above, using existing Issues client operations—no new HTTP surface beyond documented Issues routes.
- **Non-goals:** caching enrichment or link inputs in the mapping store for efficiency; REST discovery of org slug via extra APIs (operators configure slug in YAML).

## Capabilities

### New Capabilities

- _(none — behavior extends existing capabilities.)_

### Modified Capabilities

- **`application-config`**: **`snyk_org_slug`** only on **`azure_boards.org_mappings`** rows (required per row); reject slug under **`snyk`** and under **`azure_boards`** root; group-only **`sync`** omits slug until a later change (links may be incomplete).
- **`sync-lifecycle`**: Replace v1 **P2-FR-5.1**, **P2-FR-5.4**, and **P2-FR-5.5** normative text with requirements for UI-stable URLs, full description/remediation assembly, and explicit optional **GET** issue enrichment.

## Impact

- **`src/sync/`** (`issue_content`, `run`): URL builder, description assembly, conditional **`IssuesClient.get_*_issue`** calls.
- **`src/config/`** (or equivalent loader): merge and validate **`snyk_org_slug`**.
- **`data/`** samples and **`README.md`**: document new keys (implementation phase).
- **Tests:** unit tests for URL and description builders; sync branching when slug missing vs present.
