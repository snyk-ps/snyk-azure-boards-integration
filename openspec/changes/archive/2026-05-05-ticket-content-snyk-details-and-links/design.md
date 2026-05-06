## Context

Sync lists issues via **`GET /groups/{group_id}/issues`** or **`GET /orgs/{org_id}/issues`**, normalizes records, and builds Azure Boards JSON Patch including **`System.Title`** and **`System.Description`**. The GA Issues model includes **`attributes.description`**, **`coordinates.remedies`**, **`included`** project resources for **`scan_item`**, and **`coordinates`** / **`representations`** for OSS fixes.

## Goals / Non-Goals

**Goals:**

- **Working** in-app link: `https://app.snyk.io/org/<snyk_org_slug>/project/<project_uuid>#issue-<issue_key>`.
- **`System.Title`** aligned with description context: **`{target} - {issue}`** (see decisions).
- Description body sufficient for remediation **without** Snyk UI when the API returns narrative/remedy/upgrade fields.
- **`snyk_org_slug`** only on **`org_mappings`** rows (required per row when using mappings); reject misplaced slug keys in YAML.
- Enrich from **GET issue** in the same scope when list payloads omit narrative/remedies/project **`included`** data.

**Non-Goals:**

- Persisting cached enrichment or slug in the **mapping store** for fewer API calls.
- Hot-reload of configuration.
- Guaranteeing parity with legacy V1 APIs where Snyk documents **`N/A`** for REST.

## Decisions

1. **URL composition**  
   - **`issue_key`**: `attributes.key` (e.g. `SNYK-PYTHON-H11-10293728`).  
   - **`project_id`**: `relationships.scan_item.data.id` (UUID).  
   - **`snyk_org_slug`**: from **`azure_boards.org_mappings[].snyk_org_slug`** for the active mapping row (group-only sync has no slug config yet; link org segment may be empty).  
   - Fragment: `#issue-<issue_key>`; URL-encode slug/path segments per RFC 3986 where needed.  

2. **Where `snyk_org_slug` lives**  
   - **`azure_boards.org_mappings[].snyk_org_slug`**: **required** on each row when using **`org_mappings`**. Reject **`snyk.snyk_org_slug`** and **`azure_boards.snyk_org_slug`** at load.  
   - **Group-only** sync does not configure an org slug; deep links may be incomplete until a future change.  

3. **Validation**  
   - **`sync`** exits non-zero before Snyk calls if any **`org_mappings`** row used for routing lacks a non-empty **`snyk_org_slug`** (loader + validation). Group-only listing does not validate a slug.  

4. **`System.Title` (`target - issue`)**  
   - **`issue`**: `attributes.title`, else primary **`package@version`**, else fallback label.  
   - **`target`**: **`effective_target_label_for_title`** — prefer **`snyk_project_name`** on the normalized record (Snyk scan / monitored project display name), else **`{azure_boards.organization} / {azure_boards.project}`** for the active ADO routing context (same strings as the description header). If neither yields a label, title is **issue only** (no ` - ` prefix).  

5. **Scan target name (`snyk_project_name`)**  
   - Parse JSON:API **`included`** on list and GET issue responses; match **`relationships.scan_item.data`** to **`included`** project **`attributes.name`**.  
   - Store on normalized issue record; enrichment GET may add **`snyk_project_name`** when list omitted **`included`**.  

6. **Remediation body (plain text assembly, then HTML for ADO)**  
   - **Section blocks** joined with blank lines: separate blocks for Azure Boards target line, Snyk target line, severity + issue key, finding (package/paths), how-to-fix (recommended **`upgradeTo`**-style versions + remedy lines), details narrative, classification (type/CVE/CWE; fix availability with **human-readable** labels; **exclude `is_pinnable`** from that summary), link + short note.  
   - **Upgrade hints:** extract from **`coordinates[].remedies`** (`upgradeTo`, **`changes[].upgradeTo`**, etc.) and **`representations[].dependency`** version hints where present.  
   - **Remedies:** prefer **`type: description`** lines over raw JSON for structured remedy dicts.  
   - **`patch_build`:** convert plain assembly to **HTML** for **`System.Description`**: split on `\n\n` into **`<p>...</p>`**, inner `\n` → **`<br />`**, **`html.escape`** text (Azure Boards treats the field as HTML; plain newlines collapse in the UI).  

7. **Extra GET**  
   - When list payload omits **`description`** / **`coordinates[].remedies`** (per **`needs_issue_detail`**), call **`GET`** by **`rest_issue_id`** in the same scope; merge **`issue_attributes`** and copy **`snyk_project_name`** from the GET-normalized record when missing.  

8. **Failure handling**  
   - Per-issue GET failures: log, continue (**`sync-lifecycle`** per-issue semantics). Slug/config failures before loop: global error.  

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **Multi-org group** mis-links | Use **`org_mappings`** with per-row **`snyk_org_slug`**. |
| **ADO description size** limits | Truncate with notice (32k practical limit). |
| **HTML in Description** | Escape user/API text; template **`json_patch`** may still override **`System.Description`** (operator responsibility). |
| **429** from extra GETs | Existing client rate-limit behavior. |
| **Sparse API payloads** | Best-effort sections; Snyk link always present as fallback. |

## Migration Plan

- Operators configure **`org_mappings`** with **`snyk_org_slug`** per row; remove any legacy **`snyk`** / **`azure_boards`** root slug keys.  
- Next **sync** updates titles and descriptions on patched work items.  
- No mapping-store schema migration in this change.

## Open Questions

- Fragment encoding if **`attributes.key`** ever requires it—validate against production payloads.
