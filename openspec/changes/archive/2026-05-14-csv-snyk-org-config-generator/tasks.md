## 1. Spec and scaffolding

- [x] 1.1 Confirm script entrypoint name and location (`scripts/generate_org_mapping_config.py` or equivalent) and add module docstring covering auth, API version, and match rules.
- [x] 1.2 Add `--help` text documenting defaults (`data/config.yaml`), overwrite, **`SNYK_TOKEN`**, and API reference link.

## 2. Core implementation

- [x] 2.1 Implement CSV parsing and validation for **`ado_organization`**, **`ado_project`**, **`snyk_org_name`**.
- [x] 2.2 Implement Snyk **`GET /groups/{group_id}/orgs`** client using **`urllib`**, **`Authorization: token`**, JSON:API headers, **`version`** and **`limit=100`**, and **`links.next`** pagination with safe URL joining (no duplicated **`rest`** segment).
- [x] 2.3 Implement org aggregation, **`snyk_org_name`** → **`id`** / **`slug`** resolution, duplicate detection, and missing-org errors (prefer atomic write to **`--output`**).
- [x] 2.4 Emit YAML per **`openspec/changes/csv-snyk-org-config-generator/specs/csv-snyk-org-config-generator/spec.md`**: commented **`defaults`**, populated **`org_mappings`**, **`snyk.group_id`**, commented **`azure_table`** mapping store lines (optional commented sqlite lines).

## 3. Tests and docs

- [x] 3.1 Add unit tests with mocked HTTP and CSV fixtures for all public functions and error paths (pagination, no match, ambiguous name, bad CSV).
- [x] 3.2 Run **`uv run`** test suite; run Snyk Open Source / Snyk Code if any new dependency is introduced (prefer none).
- [x] 3.3 Add a short README or **CONFIGURATION** cross-reference for the new script (one subsection or bullet) so operators discover the workflow.

## 4. Final (OpenSpec)

- [x] Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/csv-snyk-org-config-generator/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive csv-snyk-org-config-generator`** (or project equivalent) to fold deltas into canonical specs.
