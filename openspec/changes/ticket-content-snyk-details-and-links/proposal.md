## Why

Work items built from Snyk issues today use a **group-scoped** `app.snyk.io` URL that does **not** resolve to the in-product issue view and adds little value. Developers still need the **Snyk web UI** to see vulnerability narrative and fix guidance. **P2-FR-5.1**, **P2-FR-5.4**, and **P2-FR-5.5** are only partially met at the spec level (best-effort URL; flags-only fix summary). This change aligns tickets with **working deep links** and **API-backed remediation text** so engineers can act from Azure Boards alone when Snyk exposes that data.

## What Changes

- **Configurable `snyk_org_slug`** (non-secret) only on **`azure_boards.org_mappings`** rows so links use the real **org → project → issue hash** pattern used by the Snyk web app. Group-level sync without **`org_mappings`** does not configure a slug yet (links may be incomplete until a follow-up).
- **Normative Snyk UI URL** shape: `https://app.snyk.io/org/<org-slug>/project/<project-id>#issue-<issue-key>`, with `project-id` and `issue-key` from the Issues API payload and `org-slug` from **`org_mappings`** per row.
- **`System.Title`**: **`{target} - {issue}`** where **`target`** matches the description header context—prefer **Snyk scan target** display name (from JSON:API **`included`** when present), else **`Azure Boards organization / project`** for the active routing row.
- **Richer `System.Description`:** structured sections (Azure Boards target, Snyk target, severity, issue key, affected package, paths, **how to fix** with recommended upgrade/version hints from **`coordinates[].remedies`** / dependency metadata, details narrative, classification, Snyk link). Delivered to Azure DevOps as **HTML** (`<p>` per blank-line-separated block, `<br />` for line breaks, escaped text) so spacing renders in the Boards web UI.
- **Fix signals:** human-readable labels; **omit `is_pinnable`** from the summary as low signal for most workflows.
- **Optional `GET` single-issue** in the same scope (group or org) when the **list** payload omits fields needed for the above; merge GET payload including **`snyk_project_name`** when **`included`** supplies it on GET only.
- **Non-goals:** caching enrichment or link inputs in the mapping store for efficiency; REST discovery of org slug via extra APIs (operators configure slug in YAML).

## Capabilities

### New Capabilities

- _(none — behavior extends existing capabilities.)_

### Modified Capabilities

- **`application-config`**: **`snyk_org_slug`** only on **`azure_boards.org_mappings`** rows (required per row); reject slug under **`snyk`** and under **`azure_boards`** root; group-only **`sync`** omits slug until a later change (links may be incomplete).
- **`sync-lifecycle`**: Replace v1 **P2-FR-5.1**, **P2-FR-5.4**, and **P2-FR-5.5** normative text with requirements for UI-stable URLs, **`target - issue`** titles, HTML **`System.Description`**, full description/remediation assembly, **`included`**-based scan target name on normalized issues, and explicit optional **GET** issue enrichment.

## Impact

- **`src/sync/`** (`issue_content`, `run`, `enrichment`, `patch_build`): URL builder, title **`effective_target_label_for_title`**, description assembly, HTML wrapping for **`System.Description`**, conditional **`IssuesClient.get_*_issue`** calls.
- **`src/snyk/`** (`parser`, `client`): parse **`included`** for **`snyk_project_name`** on normalized list and GET issue records.
- **`src/config/`**: loader rejects misplaced slugs; **`org_mappings`** row slug validation.
- **`data/`** samples and **`README.md`**: operator guidance (implementation phase).
- **Tests:** URL/title/description/HTML patch builders; enrichment and parser **`included`** behavior.
