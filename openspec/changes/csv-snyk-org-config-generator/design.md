## Context

The product already uses **Snyk REST** (`https://api.snyk.io/rest`) with **`SNYK_TOKEN`**, JSON:API headers, a dated **`version`** query parameter, and **cursor pagination via `links.next`** (see `src/snyk/client.py` and `openspec/specs/integration-apis/spec.md`). [List organizations in a group](https://apidocs.snyk.io/?version=2024-03-12#get-/groups/-group_id-/orgs) for API version **`2024-03-12`** is the normative contract for this script’s org listing.

Operators maintain **`azure_boards.org_mappings`** rows that pair ADO **`organization`** / **`project`** with **`snyk_org_id`** and **`snyk_org_slug`** (see `data/config.local.org.yaml` and `data/sample-config.yaml`). This script automates resolving the last two fields from a CSV that only carries human-meaningful **`snyk_org_name`** values.

## Goals / Non-Goals

**Goals:**

- Implement a **stdlib-first** CLI under **`scripts/`** that reads the CSV, pages through **`GET /groups/{group_id}/orgs`** with **`limit=100`** (and **`version=2024-03-12`** unless overridden for testing), matches each row’s **`snyk_org_name`** to one Snyk org, and writes **`config.yaml`** with **`org_mappings`** populated and template-style commented sections per the change proposal.
- Reuse established **auth and URL** patterns (`Authorization: token …`, base URL normalization, safe handling of **`links.next`** relative to base — avoid **`rest/rest`** duplication as documented in archived fetch-issues design).
- Provide **unit tests** with HTTP mocking for pagination, matching, and error paths.

**Non-Goals:**

- No changes to **`sync`**, config loader, or runtime defaults semantics.
- No ADO validation, no writes to Azure Table or SQLite.
- No embedding **`SNYK_TOKEN`** or other secrets in the output YAML.
- No requirement to use the same **`version`** string as the Issues client (`SNYK_REST_API_VERSION`); this tool pins **`2024-03-12`** for the orgs list operation as requested (optional CLI override for future-proofing is acceptable).

## Decisions

1. **HTTP stack**  
   **Decision:** Prefer **`urllib.request`** (and existing patterns from `IssuesClient`) to stay dependency-free unless maintainers later accept a vetted third-party client.  
   **Alternatives:** `requests` (adds dependency, needs Snyk Open Source gate).

2. **Org name matching**  
   **Decision:** After stripping **leading/trailing whitespace** on CSV **`snyk_org_name`**, match against the **display name** field exposed in the JSON:API org resource for **`2024-03-12`** (implementation derives the exact attribute path from the OpenAPI document; tests freeze representative payloads). Matching is **case-sensitive** unless we discover the API guarantees case-folding; if ambiguous, **document exact rule** in module docstring.  
   **Alternatives:** Case-insensitive match (risk of false positives); fuzzy match (out of scope).

3. **Duplicate or missing names**  
   **Decision:** If **more than one** org in the aggregated group list shares the same display name as a CSV row, the script SHALL **exit non-zero** with a clear message (no silent pick). If **no** org matches, **exit non-zero** listing the row identifier (e.g. row number + **`snyk_org_name`**).  
   **Alternatives:** Pick first (unsafe).

4. **Pagination**  
   **Decision:** Loop until **`links.next`** is absent or empty, aggregating org resources across pages; always send **`limit=100`**.  
   **Rationale:** Aligns with existing Issues client behavior and Snyk JSON:API pagination.

5. **Output YAML shape**  
   **Decision:**  
   - **`azure_boards.defaults`:** A **present key** with **no uncommented policy values**; only **commented** lines illustrating keys from **`data/sample-config.yaml`** (organization, project, severity, work item fields, template, etc.).  
   - **`azure_boards.org_mappings`:** One list item per CSV row with **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`**; **no `overrides`** unless a future change adds CSV columns (out of scope).  
   - **`snyk.group_id`:** Set from **`--group-id`**.  
   - **`mapping_store`:** Emit **commented** **`azure_table`** example (`mapping_store`, endpoint, table name) so operators uncomment when deploying; **do not** rely on this file alone for a production-complete mapping-store block without human edits. Optional: commented SQLite dev lines mirroring **`data/sample-config.yaml`** for symmetry (spec clarifies).  
   **Rationale:** Matches operator request for a deliberate “fill in defaults / storage” workflow; loader defaults still apply at runtime if keys are omitted, but the generated file is a **starter** template.

6. **Module placement**  
   **Decision:** New entrypoint **`scripts/generate_org_mapping_config.py`** (name adjustable in tasks) that bootstraps `sys.path` like **`init_mapping_store.py`**. Core logic MAY live under **`src/`** only if tasks prefer testability packaging; otherwise **`scripts/`** package with tests importing the module path is acceptable for repo conventions—**prefer minimal surface**: implement under `scripts/` with testable functions, or `src/tools/` if duplication becomes painful.

7. **Overwrite policy**  
   **Decision:** Writing to **`--output`** **overwrites** if the path exists; document in **`--help`** (optional **`-n/--dry-run`** is a stretch goal, not required for proposal approval).

## Risks / Trade-offs

- **[Risk]** Default **`data/config.yaml`** may **clobber** an existing file.  
  **→ Mitigation:** Document prominently in **`--help`** and README touchpoint added in tasks.

- **[Risk]** Snyk org **display name** may not be unique globally; duplicate handling is strict failure.  
  **→ Mitigation:** Error message instructs operator to fix CSV or rename orgs in Snyk.

- **[Risk]** API **`2024-03-12`** response shape drift vs OpenAPI.  
  **→ Mitigation:** Pin version in code; integration smoke optional; unit tests use fixtures.

## Migration Plan

Not applicable: **operator-run** dev tool; no deployment migration.

## Open Questions

- Whether to emit a **`work_item_template`** top-level stub (empty) for parity with broader schema—resolve during implementation against `application-config` sample shape (likely **omit** if not required for valid starter YAML).
