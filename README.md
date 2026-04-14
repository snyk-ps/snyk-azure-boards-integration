# Project Name (Replace with your project's name)

## Description

**Note:** In the template repository, this file is a **README scaffold**. When you build a custom application from the template, replace the title and sections below with that application’s real name, setup, and documentation.

This section provides a high-level overview of the project. It should clearly and concisely explain the project's purpose, functionality, and the problem it aims to solve.

## Table of Contents

- [Description](#description)
- [Using this template](#using-this-template)
  - [General setup](#general-setup)
  - [AI Coding Assistant Setup](#ai-coding-assistant-setup)
  - [Documentation cleanup](#documentation-cleanup)
- [Source layout (src)](#source-layout-src)
- [Tests layout (tests)](#tests-layout-tests)
- [Data layout (data)](#data-layout-data)
- [Scripts layout (scripts)](#scripts-layout-scripts)
- [Template version (TEMPLATE_VERSION)](#template-version-template_version)
- [Automation](#automation)
  - [Dockerfile](#dockerfile)
  - [GitHub Actions](#github-actions)
- [Installation and Setup](#installation-and-setup)
  - [Prerequisites](#prerequisites)
  - [Environment Setup](#environment-setup)
  - [Installation Methods](#installation-methods)
  - [Verification](#verification)
- [Usage](#usage)
- [Features](#features)
- [Configuration](#configuration)
  - [Azure DevOps personal access token (PAT)](#azure-devops-personal-access-token-pat)
  - [Parameter Descriptions](#parameter-descriptions)
- [Output Sample + Description](#output-sample--description)
- [Testing](#testing)
- [Error Handling/Logging](#error-handlinglogging)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)

## Using this template

### General setup

1. **Create a repository** from this template (or fork and clone) into your own org or account.
2. **Rename and describe the project** in this file: replace the title, this description, and the sections below with your application’s real name and documentation. Keep `TEMPLATE_VERSION` (or record it in your docs) so you always know which template revision you started from. When you want **Release Please** and **Docker publishing** for your app, delete `.github/template` (that file keeps automation off for the template repository itself) and add a root `VERSION` file with one semver line (for example `0.1.0`). Release Please `release-type: simple` reads `VERSION`; that file is for **your application**, not the template. The template does not ship `VERSION`.
3. **Python 3.12+** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)** for dependencies. Declare packages in `pyproject.toml` and commit `uv.lock` so installs are reproducible (`uv lock` / `uv sync`). **Scan dependencies with Snyk** (or your team’s process) before merging; do not ship high- or critical-severity issues from those dependencies.
4. **Implement** under `src/` and add **unit tests** under `tests/` as you go. Use `data/` for local fixtures and artifacts and `scripts/` for one-off tooling (see below). The layout here is a starting point; change it to match your package structure.

### AI Coding Assistant Setup

This template assumes you use **[Cursor](https://cursor.com/)** as your IDE. `.cursor/rules/` encodes project conventions (including the OpenSpec workflow), and those rules are written for Cursor’s agent. You can work in another editor, but you will need to apply the same conventions yourself.

**OpenSpec** drives spec-first changes in this repo. After you clone or create your app from the template:

- **Install** the OpenSpec CLI as described in the **[OpenSpec repository on GitHub](https://github.com/Fission-AI/OpenSpec)**.
- **Initialize** from the **repository root**:

  ```bash
  openspec init
  ```

  That initializes OpenSpec in your project (directories such as `openspec/`, project metadata, and editor integration as documented upstream).

- **Read** `openspec/config.yaml` (project context), **`SPEC.md`** (capability → spec paths), `openspec/AGENTS.md`, and the workflow in `.cursor/rules/openspec.mdc` before you implement features.

For background, issues, and releases, use the **[OpenSpec GitHub project](https://github.com/Fission-AI/OpenSpec)**.

Also load **secrets from environment variables** (for example `SNYK_TOKEN`) and follow `.cursor/rules/` for Python and API conventions beyond OpenSpec.

### Documentation cleanup

When your README is ready for readers of your application (not the template scaffold), delete the entire **Using this template** section from this file, including **General setup**, **AI Coding Assistant Setup**, and **Documentation cleanup**. Remove its entries from the [Table of Contents](#table-of-contents) above. Keep or modify **Source layout (src)**, **Tests layout (tests)**, **Data layout (data)**, **Scripts layout (scripts)**, **Template version (TEMPLATE_VERSION)**, and **Automation** if they still apply.

## Source layout (src)


| Directory       | Purpose                                                                                                              |
| --------------- | -------------------------------------------------------------------------------------------------------------------- |
| `commands/`     | CLI commands and `argparse` entry points that wire user input to application logic.                                  |
| `common/`       | Shared helpers, types, and utilities used across packages (not tied to Snyk or a single integration).                |
| `config/`       | Configuration loading, defaults, and environment-driven settings.                                                    |
| `integrations/` | Third-party systems outside Snyk (for example GitHub): API clients, auth, and adapters that call external HTTP APIs. |
| `snyk/`         | Snyk-specific code: the Snyk REST or v1 APIs, Snyk CLI usage, and anything that speaks Snyk’s own surfaces.          |


The project entry point is `src/main.py`.

## Tests layout (tests)

`tests/` (repo root) holds **unit tests** for `src/`. Mirror `src/` when it helps (for example `tests/snyk/` next to `src/snyk/`); otherwise use whatever your runner and team prefer.

## Data layout (data)

`data/` (repo root) is for **local data** the application or tests use: fixtures, sample inputs, small reference files, or generated exports you choose to keep in git. **Do not commit secrets**; use environment variables or secret stores for credentials, and **gitignore** large generated blobs or machine-specific paths. Prefer resolving paths via `config/` or env vars rather than hardcoding absolute locations. The template includes an empty `data/` (via `.gitkeep`) so the path exists; add files as your project needs them.

## Scripts layout (scripts)

`scripts/` (repo root) is for **executable helpers** that live in the repository but are **not** the shipped Python package: one-off migrations, data import/export, local dev wrappers, or operational tasks you run from a shell or `uv run`. Keep **product code** and libraries in `src/`; use `scripts/` for tooling that developers and operators invoke explicitly. The template includes an empty `scripts/` (via `.gitkeep`); add scripts as your workflows need them.

## Template version (TEMPLATE_VERSION)

The root `TEMPLATE_VERSION` file holds a single **semver line** for **this project template** (not your application’s release). When someone creates an app from the template, that value records **which template revision** they started from, which helps with support, upgrades, and comparing to newer template releases.

`VERSION` (which you add for Release Please) is your **app’s** version. `TEMPLATE_VERSION` is **lineage metadata** only; it does not drive Release Please or Docker tags. Template maintainers bump `TEMPLATE_VERSION` when they publish meaningful template changes; app teams may keep the file as-is or update it after merging template updates.

## Automation

`.github/workflows/` wires releases and container publishing. Adjust or remove workflows if your process differs.

**Template marker:** The file `.github/template` exists in this repository so **GitHub Actions do not run** Release Please or Docker publish here. That avoids versioning this project as a shipped template artifact. When someone creates **an application** from the template, they delete `.github/template`, add `VERSION` at the repo root (single semver line), and workflows then run as usual.

### Dockerfile

The root `Dockerfile` uses a **multi-stage** build: dependencies are installed with **uv** in a builder stage, then the app runs in a slim final image without the uv binary.


| Item          | Detail                                                                                                                                                                           |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Builder       | `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` runs `uv sync --locked` using `pyproject.toml` and `uv.lock` (bytecode compile and cache mounts as in the file). |
| Runtime       | `python:3.12-slim-bookworm`; `PATH` includes `/app/.venv/bin`. The process runs as a non-root user (`nonroot`, uid/gid 999).                                     |
| App layout    | Full project is copied into `/app`; the default command is `python src/main.py`.                                                                                         |
| Build context | `.dockerignore` keeps unnecessary paths out of the image build (see that file for the exact list).                                                                           |


**Local build and run** (from the repository root):

```bash
docker build -t myapp:local .
docker run --rm myapp:local
```

Pass env vars and flags your CLI expects with `docker run -e ...` or your orchestrator’s equivalent.

### GitHub Actions

Two workflows cooperate with `Dockerfile` at the repo root:

1. **`tag.yml` (Release Please)**  
   Runs on **push to `main`** only when `.github/template` is absent (so **not** on the upstream template repo). It uses [release-please](https://github.com/googleapis/release-please-action) with `release-type: simple`, which reads the root `VERSION` file (one line, semver). Conventional commits drive proposed bumps; merge the release PR to publish a tag and GitHub release. Tune `release-type` and branch names if you do not use `main` or “simple” versioning.  
   The workflow sets `permissions: contents: write` and `pull-requests: write` so `GITHUB_TOKEN` can manage PRs and releases. If you still see **Resource not accessible by integration**, open **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions** (or ask an org admin if the org enforces read-only workflows).
2. **`release.yml` (Docker publish)**  
   Runs when you **push a tag** matching `v*.*.*` (for example `v1.2.3`), and only when `.github/template` is absent. It checks out the repo, logs in to **GitHub Container Registry** (`ghcr.io`) with `GITHUB_TOKEN`, builds `Dockerfile`, and **pushes** the image as:

   `ghcr.io/<owner>/<repository>:<tag>`

   using the **git tag name** as the image tag (for example `ghcr.io/my-org/my-repo:v1.2.3`; GHCR uses the repository’s lowercase name). It also **creates a GitHub Release** for that tag. Mark tags with a hyphen as prereleases (see the workflow). Ensure the repository allows **GitHub Packages** and that consumers authenticate to `ghcr.io` when pulling private images.

**Typical flow (after you delete `.github/template` and add `VERSION`):** merge work to `main` → Release Please proposes a release PR → merge it → a version tag appears → `release.yml` builds and pushes the Docker image to GHCR.

## Installation and Setup

Replace this section with real install steps for your application.

### Prerequisites

List required tools and versions (for example Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/)).

### Environment Setup

Create a local environment with `uv sync` (uses `pyproject.toml` and `uv.lock`). Document environment variables, optional database or services, and how to obtain API keys.

### Installation Methods

Install from source with uv, use the **Dockerfile**, or scripts; note OS-specific quirks if any.

### Verification

Commands that prove the install works (for example `uv run python src/main.py --help` or `uv run pytest`).

## Usage

Replace with how to run and use the application. From the repository root, after `uv sync`, the scaffold entry point is:

```bash
uv run python src/main.py --help
```

Adjust after you add arguments or package the app.

## Features

Replace with a concise list of what the project does.

## Configuration

Operator settings use a **YAML** file (non-secret policy only). **Secrets** (`SNYK_TOKEN`, Azure DevOps PAT, etc.) **must** come from environment variables or your secret store — **never** commit them in YAML.

### Precedence

When the same logical setting exists in more than one place, the effective value is resolved in this order (**later wins**):

1. Built-in defaults  
2. YAML configuration file  
3. Environment variables (documented overrides below)  
4. **CLI arguments** (highest precedence — useful for local smoke tests without editing files)

For **deployments and IaC**, keep authoritative values in **YAML** (or platform-injected environment). Use **CLI overrides** mainly for **local development** and one-off commands.

### Configuration file layout

Top-level keys:

| Key | Purpose |
| --- | --- |
| `azure_boards` | Azure Boards behavior, including `create_new_work_items` (boolean, default `true`) — global enable/disable for **new** work items (**P2-FR-11**). Also `organization` and `project` (non-secret strings) for Azure DevOps REST routing used by **`azure-devops-smoke`** and future sync. |
| `work_item_template` | Placeholder mapping for future work item defaults (may be `{}`). |
| `snyk` | `group_id` (string), `severity_threshold` (`low` \| `medium` \| `high` \| `critical`, default `high`), plus optional future keys. |
| `mapping_store` | Where Snyk↔work-item mappings are persisted: `sqlite` (local dev/tests) or reserved `azure_table` (production-style; not implemented in this repo yet). Default: `sqlite`. |
| `sqlite_path` | Filesystem path to the SQLite file when `mapping_store` is `sqlite`. Default: `data/mapping_store.sqlite`. **Do not put secrets** (tokens, PATs) in this path or database file — use environment / Key Vault only. |

Sections may be omitted where **defaults** apply; a full example is in **`data/sample-config.yaml`** (tracked in git).

**Local SQLite schema (optional):** from the repository root, run `uv run python scripts/init_mapping_store.py --config data/sample-config.yaml` (or pass `--mapping-store-sqlite-path /path/to/file.sqlite`). The script is idempotent and uses the same `sqlite_path` resolution as the app (**defaults → YAML → env → CLI**).

### Environment variables

| Variable | Role |
| -------- | ---- |
| `SNYK_APP_CONFIG` | Path to the YAML file if you do not pass `--config` (CLI `--config` wins when both are set). |
| `SNYK_GROUP_ID` | Overrides `snyk.group_id` from the file (CLI group arguments override this in turn). |
| `AZURE_BOARDS_CREATE_NEW_WORK_ITEMS` | Overrides `azure_boards.create_new_work_items` (`true` / `false` / `1` / `0`). |
| `AZURE_BOARDS_ORGANIZATION` | Overrides `azure_boards.organization` when set to a non-empty value (non-secret Azure DevOps org name). |
| `AZURE_BOARDS_PROJECT` | Overrides `azure_boards.project` when set to a non-empty value (non-secret Azure DevOps project name or id). |
| `AZURE_DEVOPS_PAT` | **Secret:** Azure DevOps personal access token (not read from YAML or CLI flags). |
| `MAPPING_STORE` | Overrides `mapping_store` (`sqlite` or `azure_table`). |
| `MAPPING_STORE_SQLITE_PATH` | Overrides `sqlite_path` for the SQLite mapping database (CLI `--mapping-store-sqlite-path` wins when set). |
| `SNYK_TOKEN` | **Secret:** Snyk API token (not read from YAML). |

### Azure DevOps personal access token (PAT)

The integration calls Azure DevOps REST APIs using a **personal access token (PAT)**. **Do not** commit a PAT to version control or store it in YAML; set it only via the **`AZURE_DEVOPS_PAT`** environment variable. For production, inject the value from your secret store into the process environment (for example Azure Key Vault backing app settings); high-level runtime and deployment notes are in [Deployment](#deployment).

**Create a PAT**

1. Open **[Azure DevOps](https://dev.azure.com)** and sign in to the organization you use with this project.
2. Open **User settings** from your profile menu (avatar or initials in the upper-right corner).
3. Select **Personal access tokens**.
4. Choose **+ New Token** (or **New Token**).
5. Enter a name, pick the organization (or **All accessible organizations** if your policy allows), set an expiration, then under **Scopes** choose the **Work Items** permissions below.

**Scopes**

| What you are doing | Work Items permission in Azure DevOps |
| --- | --- |
| **`azure-devops-smoke`** and other **read-only** validation | **Read** — often labeled **Work Items: Read** or **Work items (read)** in the PAT dialog |
| **Create**, **update**, and **comment** on work items (sync and similar flows) | **Read & write** — often **Work Items: Read & write** or **Work items (read & write)** |

Labels can vary slightly by Azure DevOps version; if yours differs, match the intent (read-only vs. changing work items) and confirm against Microsoft’s PAT documentation.

Official documentation: [Use personal access tokens to authenticate](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate?view=azure-devops) (Microsoft Learn).

### `azure-devops-smoke` command

The **`azure-devops-smoke`** command performs a **single read-only** `get_work_item` call to validate connectivity, authentication, and response parsing. It reads **`azure_boards.organization`** and **`azure_boards.project`** from merged configuration (YAML and/or `AZURE_BOARDS_ORGANIZATION` / `AZURE_BOARDS_PROJECT`) and requires **`AZURE_DEVOPS_PAT`** in the environment (**do not** pass the PAT on the command line).

Example:

```bash
export AZURE_DEVOPS_PAT="***"
uv run python src/main.py azure-devops-smoke --config data/sample-config.yaml --work-item-id 12345
```

Run **`uv run python src/main.py azure-devops-smoke --help`** for flags. This command does **not** create, update, or add comments by default.

### `fetch` command and Snyk group id

The **`fetch`** smoke command calls the **group-scoped** Snyk Issues API. A **non-empty group id** is **required** after merging file, environment, and CLI layers. Provide it via:

- `snyk.group_id` in YAML, and/or  
- `SNYK_GROUP_ID`, and/or  
- **`fetch list`** positional group id or **`fetch get`** two-argument form (`group_id issue_id`), and/or  
- **`--group-id`**

If the resolved group id is empty, `fetch` exits with an error before calling the API. Run **`uv run python src/main.py fetch --help`** for the current argument layout.

**`fetch`** also accepts **`--mapping-store-sqlite-path`** so you can override the SQLite mapping file path for that process without editing YAML (same precedence layer as other CLI overrides for `sqlite_path`).

### Parameter Descriptions

| Setting | Default | Notes |
| ------- | ------- | ----- |
| `azure_boards.create_new_work_items` | `true` | When `false`, sync logic must not create **new** work items (policy surface for **P2-FR-11**). |
| `azure_boards.organization` | `""` | Azure DevOps organization name for REST paths (non-secret). Required (non-empty) for **`azure-devops-smoke`**. |
| `azure_boards.project` | `""` | Azure DevOps project name or id for REST paths (non-secret). Required (non-empty) for **`azure-devops-smoke`**. |
| `work_item_template` | `{}` | Reserved for future work item type / routing fields. |
| `snyk.group_id` | `""` | **Required** for `fetch` (and group-scoped API use) once merged with env/CLI — use a real Snyk group UUID in production. |
| `snyk.severity_threshold` | `high` | Minimum severity for policy; aligns with **P2-FR-1** when set to `high` or `critical`. |
| `mapping_store` | `sqlite` | Use `sqlite` for local mapping persistence. `azure_table` is reserved; selecting it without a working adapter causes a clear error (no silent fallback to SQLite). |
| `sqlite_path` | `data/mapping_store.sqlite` | SQLite file path for mappings (non-secret). Do not store tokens or PATs here. |

Example file (see also **`data/sample-config.yaml`**):

```yaml
azure_boards:
  create_new_work_items: true
  organization: "your-azure-devops-org"
  project: "your-azure-devops-project"
work_item_template: {}
snyk:
  group_id: "00000000-0000-0000-0000-000000000001"
  severity_threshold: high
mapping_store: sqlite
sqlite_path: data/mapping_store.sqlite
```

## Output Sample + Description

Replace with sample output and what each field means (text, JSON, etc.).

## Testing

How to run tests (for example `uv run pytest`). Add test runners and tools as dev dependencies in `pyproject.toml` and sync with uv. Point to `tests/` and any coverage expectations.

## Error Handling/Logging

How errors and logs behave, where logs go, and JSON log format if applicable.

## Troubleshooting

Common errors, known issues, FAQ, and debugging tips.

## Deployment

Where and how you deploy in production: environment variables, secrets, and runtime config. For containers, images built by `release.yml` are published to `ghcr.io` (GitHub Container Registry); pull and run that image in your environment or wire the registry into Kubernetes, ECS, or another orchestrator. Document any registry auth and image tag policy your operators should follow.