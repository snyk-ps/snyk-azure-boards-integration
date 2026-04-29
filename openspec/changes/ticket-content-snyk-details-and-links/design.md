## Context

Sync lists issues via **`GET /groups/{group_id}/issues`** or **`GET /orgs/{org_id}/issues`**, normalizes records, and builds Azure Boards JSON Patch including **`System.Title`** and **`System.Description`**. Today **`issue_content`** emits a best-effort **`app.snyk.io/group/{group}/issues/{rest_uuid}`** link and summarizes fix booleans only. Snyk’s GA Issues model includes **`attributes.description`**, **`coordinates.remedies`**, and expanded **`coordinates`** / **`representations`** for OSS fixes per public migration guidance.

## Goals / Non-Goals

**Goals:**

- **Working** in-app link: `https://app.snyk.io/org/<snyk_org_slug>/project/<project_uuid>#issue-<issue_key>`.
- Description body sufficient for remediation **without** Snyk UI when the API returns narrative/remedy fields.
- Use **configuration** for **`snyk_org_slug`** only (no runtime slug discovery API).
- Enrich from **GET issue** in the same scope when list payloads omit needed attributes.

**Non-Goals:**

- Persisting cached enrichment or slug in the **mapping store** for fewer API calls.
- Hot-reload of configuration.
- Guaranteeing parity with legacy V1 APIs where Snyk documents **`N/A`** for REST.

## Decisions

1. **URL composition**  
   - **`issue_key`**: `attributes.key` (e.g. `SNYK-PYTHON-H11-10293728`).  
   - **`project_id`**: `relationships.scan_item.data.id` (UUID).  
   - **`snyk_org_slug`**: from merged config—see below.  
   - Fragment: `#issue-<issue_key>`; URL-encode slug/path segments per RFC 3986 where needed.  
   **Rationale:** Matches operator-provided browser URLs; avoids broken group-based routes.

2. **Where `snyk_org_slug` lives**
   - **`azure_boards.org_mappings[].snyk_org_slug`**: **required** on each row when using **`org_mappings`**; this is the **only** YAML location for the slug. **Group-only** sync (no **`org_mappings`**) does not configure a slug yet; links in work items may be incomplete.
   **Rationale:** One slug per org row avoids misrouting when a group lists multiple orgs; single slug under **`snyk`** suffices for single-org group deployments.

3. **Validation**  
   - **`sync`** SHALL exit non-zero **before** the per-issue loop if **`snyk_org_slug`** is missing on any **`org_mappings`** row used for routing (YAML loader enforces per-row slug). **Group-only** listing does not validate a slug.  
   **Rationale:** Operators rely on a working link; silent omission recreates “garbage” output.

4. **Remediation body**  
   - Prefer fields from the **normalized issue** after merge: **`attributes.description`** (plain text where present), render **`coordinates[].remedies`** (structure as returned by API—formatted as readable lines/blocks for Boards).  
   - Retain existing **P2-FR-5.3** CVE/CWE, **P2-FR-5.2** type, primary package line, and fix booleans; ordering: title/package, description narrative, remedies/fix guidance, type/CVE/CWE, flags, **Snyk link** line.  
   **Rationale:** Aligns with GA Issues schema without inventing new REST resources.

5. **Extra GET**  
   - After receiving a list record, if **`description`** and **`remedies`** (and any other fields mandated by the updated **`sync-lifecycle`** spec) are absent but needed, call **`GET /groups/{group_id}/issues/{issue_id}`** or **`GET /orgs/{org_id}/issues/{issue_id}`** using **`rest_issue_id`** from the list payload and the same **`version`** query as today.  
   - Merge GET **`attributes`** into the working issue view used for **`issue_content`** (implementation detail: shallow merge of attributes/coordinates).  
   **Rationale:** List responses may be sparse; GET returns full issue resource.

6. **Failure handling**  
   - Per-issue GET failures follow **`sync-lifecycle`** “per-issue errors” (log, skip issue, exit 0 unless global failure). Slug/config failures before loop are global errors.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **Multi-org group** with a single shared slug mis-links issues from another org | Document use **`org_mappings`** with per-row **`snyk_org_slug`** when multiple Snyk orgs appear under one group. |
| **ADO description size** limits | Truncate or summarize longest sections with ellipsis and reference link (implementation follows Boards limits). |
| **429** from extra GETs | Existing client rate-limit behavior; no extra mapping cache in this change. |
| **Some issue types** lack `description` / `remedies` | Spec allows best-effort; always include what the API returns. |

## Migration Plan

- Operators add **`snyk_org_slug`** (and per-row slugs) to YAML; deploy new revision; next **sync** updates work item descriptions and links.  
- No database migration (no new mapping columns in this change).

## Open Questions

- Exact **character set** for fragment (`#issue-...`) if Snyk ever returns keys requiring encoding—validate against one production issue in implementation.
