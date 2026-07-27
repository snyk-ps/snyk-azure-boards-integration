## Context

- **CLI**: `scripts/generate_org_mapping_config.py` — requires **`--input`**, **`--group-id`**, **`SNYK_TOKEN`**, optional **`--output`** (default **`data/config.yaml`**) and **`SNYK_API_BASE_URL`** / **`--base-url`** (see `openspec/specs/csv-snyk-org-config-generator/spec.md`).
- **Repo CI today**: only **`.github/workflows/release.yml`** (Docker release on tags); no Python/uv CI workflow yet.
- **Local CSV policy**: **`data/*.csv`** is gitignored except **`data/sample-orgs.csv`** (committed sample).

## Goals / Non-Goals

**Goals:**

- Provide a **copy-paste-friendly** sample workflow operators can adapt in their own fork or internal repo.
- Mirror local invocation: **`uv sync`** then **`uv run python scripts/generate_org_mapping_config.py ...`** from repo root.
- Fail clearly when **`SNYK_TOKEN`** or required inputs are missing.
- Publish generated config as a **downloadable artifact** for human review before deployment.

**Non-Goals:**

- Scheduled or PR-triggered runs.
- Matrix builds, multi-region fan-out, or Azure Key Vault integration in this sample.
- Storing operator CSVs or generated config in git.

## Decisions

1. **Trigger: `workflow_dispatch` only**  
   **Decision:** Manual run with typed inputs.  
   **Rationale:** Avoids failed PR checks for contributors without Snyk secrets; matches “operator onboarding” use case.  
   **Alternatives:** `push` to `data/*.csv` (blocked by gitignore); `repository_dispatch` (more setup, out of scope for “sample”).

2. **Secrets vs configuration**  
   **Decision:** **`SNYK_TOKEN`** from **`secrets.SNYK_TOKEN`**. **`SNYK_GROUP_ID`**, **`ORG_MAPPING_CSV_PATH`**, and **`SNYK_API_BASE_URL`** from GitHub **repository variables** (`vars.*`), mapped to job **`env`**.  
   **Rationale:** Aligns with CLI auth model and lets operators configure once under **Settings → Secrets and variables → Actions**.  
   **Alternatives:** **`workflow_dispatch` inputs** (re-enter values each run); **`SNYK_GROUP_ID`** as secret (group id is non-secret).

3. **Example CSV location**  
   **Decision:** **`data/sample-orgs.csv`** with placeholder values; document in **CONFIGURATION.md** that operators must replace names with their real Snyk org display names.  
   **Rationale:** Aligns with the repo **`data/`** convention; **`!data/sample-orgs.csv`** in **`.gitignore`** keeps the sample tracked while other CSVs stay local.

4. **Output handling**  
   **Decision:** Write to a path under **`${{ runner.temp }}/`** (e.g. **`generated-config.yaml`**) via **`--output`**, then **`actions/upload-artifact@v4`**.  
   **Rationale:** Avoids overwriting tracked files in the workspace; artifact is the deliverable.  
   **Alternatives:** Default **`data/config.yaml`** in runner (works but confusing in logs).

5. **Python / uv setup**  
   **Decision:** **`actions/setup-python@v5`** with **`python-version: '3.12'`** (match **`pyproject.toml`**), install **`uv`** via **`astral-sh/setup-uv@v5`**, then **`uv sync`** (no **`--dev`** needed for the generator).  
   **Alternatives:** Pin exact uv version in workflow for reproducibility (optional follow-up).

6. **Permissions**  
   **Decision:** **`contents: read`** only (checkout + read repo). No **`packages`**, **`id-token`**, or write permissions.  
   **Rationale:** Workflow does not publish or commit.

7. **Regional Snyk API**  
   **Decision:** Optional workflow input **`snyk_api_base_url`** mapped to env **`SNYK_API_BASE_URL`** when non-empty (same semantics as CLI spec).  
   **Rationale:** Matches archived **`snyk-api-base-url-override`** behavior for EU/AU tenants.

## Risks / Trade-offs

- **[Risk]** Operators run the sample against production group/org names and upload config containing real ADO project names.  
  **→ Mitigation:** Artifact is private to repo collaborators; docs stress review and least-privilege token scope.

- **[Risk]** Example CSV placeholders do not match any real Snyk org → workflow fails with **`OrgResolutionError`**.  
  **→ Mitigation:** Document that the sample CSV is structural only; operators must supply a CSV whose **`snyk_org_name`** values match Snyk display names.

- **[Risk]** **`SNYK_TOKEN`** missing → opaque failure.  
  **→ Mitigation:** Add an early step that checks secret presence (without printing value) and exits with a clear message.

## Migration Plan

Not applicable. Operators opt in by configuring secrets and running the workflow manually.

## Open Questions

- Should **`SNYK_GROUP_ID`** also be offered as an optional **secret** fallback when the workflow input is empty? *(Recommend: input only for simplicity in v1.)*
- Should the workflow include a **dry-run** job that validates CSV headers only (no API)? *(Recommend: non-goal for v1; CLI already validates CSV before API.)*
