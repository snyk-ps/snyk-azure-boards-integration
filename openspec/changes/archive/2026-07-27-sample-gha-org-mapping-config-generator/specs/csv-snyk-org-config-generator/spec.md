## ADDED Requirements

### Requirement: Sample GitHub Actions workflow

The repository SHALL ship a **sample** GitHub Actions workflow file under **`.github/workflows/`** that demonstrates running **`scripts/generate_org_mapping_config.py`** with the same CLI contract as this capability (**`--input`**, **`--group-id`**, optional **`--output`**, optional regional API base via environment). The workflow SHALL be triggered only by **`workflow_dispatch`** (manual), not on every push or pull request.

Authentication SHALL use **`SNYK_TOKEN`** from GitHub Actions **secrets** only. The workflow MUST NOT accept the token as a workflow input, MUST NOT log the token, and MUST NOT write secrets into the generated YAML.

The workflow SHALL install **Python 3.12+** and **`uv`**, run **`uv sync`** from the repository root, execute the generator CLI, and upload the generated YAML file as a **workflow artifact** using a standard GitHub **`upload-artifact`** action. The workflow SHALL NOT commit generated configuration to the repository.

The repository SHALL include a **committed example CSV** at **`data/sample-orgs.csv`** (tracked via **`.gitignore`** exception) with the required headers **`ado_organization`**, **`ado_project`**, **`snyk_org_name`** and placeholder cell values suitable for documentation only.

**CONFIGURATION.md** SHALL document: workflow file name, required secret **`SNYK_TOKEN`**, required and optional **repository variables** (**`SNYK_GROUP_ID`**, **`ORG_MAPPING_CSV_PATH`**, **`SNYK_API_BASE_URL`**), how to download the artifact, and that operators must replace placeholder CSV values and review **`defaults`** / **`mapping_store`** comments before deploy.

#### Scenario: Manual run with valid secrets and inputs

- **WHEN** an operator triggers the workflow with a valid **`SNYK_TOKEN`** secret, a configured **`SNYK_GROUP_ID`** repository variable, and a CSV path (from **`ORG_MAPPING_CSV_PATH`** or default) whose rows resolve to unique Snyk org display names in that group
- **THEN** the job SHALL exit zero, and the workflow SHALL publish an artifact containing the generated YAML with populated **`azure_boards.org_mappings`**

#### Scenario: Missing token

- **WHEN** **`SNYK_TOKEN`** is not configured in the repository secrets
- **THEN** the workflow SHALL fail before or during the generator invocation with a clear, non-secret error

#### Scenario: No auto-commit

- **WHEN** the workflow completes successfully
- **THEN** the repository working tree on the runner SHALL NOT be pushed or committed with the generated file

### Requirement: Sample workflow documentation discoverability

**README.md** SHALL include a brief pointer (one bullet or sentence) to the sample GitHub Actions workflow and **CONFIGURATION.md** section for operators who prefer CI over local **`uv run`**.

#### Scenario: Operator finds CI path from README

- **WHEN** an operator reads the configuration / org_mappings section of **README.md**
- **THEN** they SHALL find a reference to the sample workflow and **CONFIGURATION.md** instructions
