## Why

Operators who bulk-build **`azure_boards.org_mappings`** already use **`scripts/generate_org_mapping_config.py`** locally (documented in **CONFIGURATION.md**). A **sample GitHub Actions workflow** shows how to run the same CLI in CI with **`SNYK_TOKEN`** from repository secrets, **`uv`**, and artifact upload—without requiring every operator to invent workflow YAML from scratch. This is **documentation-by-example**, not production sync automation.

## What Changes

- Add **`.github/workflows/sample-generate-org-mapping-config.yml`**: a **manual** (`workflow_dispatch`) workflow that:
  - Checks out the repo, installs **Python 3.12+** and **`uv`**, runs **`uv sync`**, and invokes **`scripts/generate_org_mapping_config.py`**.
  - Reads **`SNYK_TOKEN`** from GitHub Actions **secrets** (never from workflow inputs or logs).
  - Accepts configuration from GitHub **repository variables** and **`SNYK_TOKEN`** secret (mapped to job environment variables).
  - Uploads the generated YAML as a **workflow artifact**; does **not** commit config to the branch.
- Add a **committed example CSV** at **`data/sample-orgs.csv`** (placeholder ADO/Snyk org names only—no secrets). Other **`data/*.csv`** files remain gitignored for operator-local use.
- Document the workflow in **CONFIGURATION.md** (and a short **README** cross-link): required secrets, inputs, artifact download, and review-before-deploy reminder.

## Capabilities

### New Capabilities

- _(None.)_

### Modified Capabilities

- **`csv-snyk-org-config-generator`**: Add requirements for the sample GitHub Actions workflow (trigger, secrets, inputs, artifact output, non-goals).

## Impact

- **New files**: `.github/workflows/sample-generate-org-mapping-config.yml`, `data/sample-orgs.csv`.
- **Docs**: **CONFIGURATION.md**, **README.md** (one bullet).
- **No runtime changes**: **`sync`**, config loader, and the generator CLI behavior stay unchanged unless a bug is found during implementation.
- **Secrets**: Operators configure **`SNYK_TOKEN`** (and optionally regional **`SNYK_API_BASE_URL`**) as repo/org secrets; workflow MUST NOT echo tokens or write secrets into YAML output (existing CLI guarantee).

## Non-Goals

- CI on every push/PR (requires live Snyk credentials and group-specific CSV data).
- Auto-committing generated **`config.yaml`** to the repository.
- Validating generated YAML against Azure DevOps or running **`sync`** in the same workflow.
- Replacing local **`uv run python scripts/generate_org_mapping_config.py ...`** for day-to-day development.
