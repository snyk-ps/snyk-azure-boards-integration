## 1. Example inputs

- [x] 1.1 Add **`data/sample-orgs.csv`** with required headers and placeholder rows (no secrets; document in **CONFIGURATION.md** that **`snyk_org_name`** values must match live Snyk org display names).

## 2. Workflow

- [x] 2.1 Add **`.github/workflows/sample-generate-org-mapping-config.yml`** with:
  - **`workflow_dispatch`** (manual, no run-time inputs); job **`env`** from **`vars.SNYK_GROUP_ID`**, **`vars.ORG_MAPPING_CSV_PATH`**, **`vars.SNYK_API_BASE_URL`**, and **`secrets.SNYK_TOKEN`**.
  - **`permissions: contents: read`**.
  - Steps: checkout → setup Python 3.12 → setup uv → **`uv sync`** → preflight **`SNYK_TOKEN`** check → run generator → upload artifact.
  - Map optional **`snyk_api_base_url`** to **`SNYK_API_BASE_URL`** when set.
  - Use **`--output`** under **`${{ runner.temp }}/`**, not tracked **`data/config.yaml`**.

## 3. Documentation

- [x] 3.1 Extend **CONFIGURATION.md** § *Generating org_mappings from a CSV* with a **GitHub Actions (sample)** subsection: secrets, inputs, artifact download, review checklist.
- [x] 3.2 Add **README.md** cross-link to that subsection.

## 4. Verification

- [x] 4.1 Validate workflow YAML syntax (local **`actionlint`** if available, or manual review).
- [x] 4.2 Confirm **`data/sample-orgs.csv`** parses via CLI CSV validation (org resolution may fail with placeholders—that is expected).

## 5. Final (OpenSpec)

- [x] Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/sample-gha-org-mapping-config-generator/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive sample-gha-org-mapping-config-generator`** (or project equivalent) to fold deltas into canonical specs.
