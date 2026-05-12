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
  - [The `sync` command](#the-sync-command)
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
| `sync/`         | Synchronization orchestration: Snyk issue lifecycle → Azure Boards work items and SQLite (or future) mapping store.   |
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

From the repository root, after `uv sync`, the CLI entry point is:

```bash
uv run python src/main.py --help
```

Subcommands:

| Command | Purpose |
| ------- | ------- |
| **`sync`** | List Snyk issues (by severity threshold), reconcile Azure Boards work items, and update the mapping store. Requires **`SNYK_TOKEN`**, **`AZURE_DEVOPS_PAT`**, and routing fields per configuration mode; **`org_mappings[].snyk_org_slug`** supplies Snyk UI links when using **`org_mappings`**. See [The `sync` command](#the-sync-command) under Configuration. |
| **`fetch`** | Smoke-test the Snyk Issues API (`list` / `get`); requires **`SNYK_TOKEN`** and a non-empty group id. See [The `fetch` command and Snyk group id](#fetch-command-and-snyk-group-id). |
| **`azure-devops-smoke`** | Single read-only `get_work_item` against Azure DevOps; requires **`AZURE_DEVOPS_PAT`** and routing from config. |

Examples:

```bash
uv run python src/main.py sync --config data/sample-config.yaml
uv run python src/main.py fetch list --config data/sample-config.yaml
```

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
| `azure_boards` | **`defaults`** holds routing (`organization`, `project`), **`create_new_work_items`** (boolean, default `true` — **P2-FR-11**), **`severity_threshold`** (`low` \| `medium` \| `high` \| `critical`), optional **`sync_included_snyk_origins`** (comma-separated **inclusive** list of Snyk project [origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin) tokens — omit or leave empty to sync all origins; see **Acceptable `sync_included_snyk_origins` values** below), **`issues_sync_from`** (`historical` or an ISO-8601 timestamp), **`create_only_when_fix_available`**, **`reopen_work_item_policy`** (`new_work_item` \| `reopen_existing`), **`work_item_type`**, **`work_item_state_*`**, optional **`work_item_description_appendix`** (plain text appended after the auto-generated **`System.Description`** body; multiline YAML `|` supported), and optional **`work_item_template`**. Do **not** set routing, severity, or `work_item_*` keys as direct children of **`azure_boards`** — the loader rejects legacy flat keys. **`org_mappings`** is an optional list of `{ organization, project, snyk_org_id, snyk_org_slug, overrides? }` for multi-target sync; each row **`snyk_org_slug`** identifies that Snyk org in **`app.snyk.io`** URLs (**required** per row). Optional **`overrides`** partially replace **`defaults`** (including **`work_item_description_appendix`** and **`sync_included_snyk_origins`** per mapping). After load, merged values are also available on **`azure_boards`** top-level fields for convenience in code paths that expect a flat view. |
| `work_item_template` | Optional `tags` (list of strings) and `json_patch` (JSON Patch ops) applied on **`sync`** create/update; may be `{}`. Merged with `azure_boards.defaults.work_item_template`, then per-mapping `overrides.work_item_template` (`json_patch` lists concatenate in that order). Assignee: use `json_patch` with path `/fields/System.AssignedTo` (Azure DevOps identity format). **Managed tags:** on each Boards create/update, **`sync`** also sets severity and finding-type tags from the current issue (see **Work item tags** below); your configured tags remain in the union. |
| `snyk` | `group_id` (string; required for group-scoped **`fetch`** / **`sync`** unless **`azure_boards.org_mappings`** defines at least one mapping). **`snyk.severity_threshold` is not supported** — use **`azure_boards.defaults.severity_threshold`**. Do **not** put **`snyk_org_slug`** here — use **`azure_boards.org_mappings[].snyk_org_slug`** only. |
| `mapping_store` | Where **issues sync persistence** (Snyk issue state and optional Azure Boards work item link) is stored: **`sqlite`** (local dev/tests) or **`azure_table`** (Azure Table Storage using **`DefaultAzureCredential`**). Default: **`sqlite`**. |
| `sqlite_path` | Filesystem path to the SQLite file when **`mapping_store`** is **`sqlite`**. Ignored for **`azure_table`**. Default: `data/mapping_store.sqlite`. **Do not put secrets** (tokens, PATs) in this path or database file — use environment / Key Vault only. |
| `mapping_store_azure_table_endpoint` | HTTPS Table service URL (for example `https://<account>.table.core.windows.net`). Required when **`mapping_store`** is **`azure_table`** (YAML or **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`**). Non-secret. |
| `mapping_store_azure_table_name` | Azure Table name (3–63 alphanumeric characters starting with a letter). Required when **`mapping_store`** is **`azure_table`** (YAML or **`MAPPING_STORE_AZURE_TABLE_NAME`**). Non-secret. |

Sections may be omitted where **defaults** apply; a full example is in **`data/sample-config.yaml`** (tracked in git).

**Work item tags (`System.Tags`, P2-FR-10 plus managed labels):**

- **`work_item_template.tags`** supply **operator** strings. They appear **first**, in merged-template order (**defaults** → **`overrides`**, deduped as documented for templates).
- **`sync`** adds up to **two managed** tags from the **current** Snyk issue payload on **every** work item **create** and **update** (when Boards is mutated): **`Snyk-Severity-{low|medium|high|critical}`** from **`effective_severity_level`** (case-insensitive), and a **`Snyk-Type-{suffix}`** from **`attributes.type`**. Supported REST **`type`** values **`package_vulnerability`**, **`license`**, **`cloud`**, **`code`**, **`custom`**, and **`config`** map as: **`license`** → **`Snyk-Type-license`**; **`custom`** → **`Snyk-Type-custom`**; **`package_vulnerability`** → **`Snyk-Type-open_source`** (and common OSS synonyms); **`cloud`** and **`config`** → **`Snyk-Type-iac`**; **`code`** → **`Snyk-Type-code`** (plus synonyms such as **`sast`**); other synonyms (e.g. **`container`**) are documented in code. Unknown **`type`** values omit the managed type tag until the integration adds them.
- **Reserved prefixes:** do **not** use **`Snyk-Severity-*`** or **`Snyk-Type-*`** in YAML `tags`. If present, **`sync`** **omits** them from the operator list and applies canonical values from Snyk so reporting stays truthful.
- If there are **no** operator tags and **nothing** derivable from the issue, **`sync`** does **not** send a **`System.Tags`** patch (so it does **not** clear existing tags solely for absence of YAML tags).

**Local SQLite (issues sync persistence):** from the repository root, run `uv run python scripts/init_mapping_store.py --config data/sample-config.yaml` (or pass `--mapping-store-sqlite-path /path/to/file.sqlite`). The script is idempotent and uses the same `sqlite_path` resolution as the app (**defaults → YAML → env → CLI**). The physical table is **`issue_work_item_map`**; it stores one row per Snyk issue in scope (see columns below). Text fields may be empty until **`sync`** fills them.

**Acceptable `sync_included_snyk_origins` values** (tokens must match exactly; catalog aligns with [Snyk — Origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin) plus `github-cloud-app` and `github-server-app`):

`acr`, `api`, `artifactory-cr`, `aws-config`, `aws-lambda`, `azure-functions`, `azure-repos`, `bitbucket-cloud`, `bitbucket-server`, `cli`, `cloud-foundry`, `digitalocean-cr`, `docker-hub`, `ecr`, `gcr`, `github`, `github-cloud-app`, `github-cr`, `github-enterprise`, `github-server-app`, `gitlab`, `gitlab-cr`, `google-artifact-cr`, `harbor-cr`, `heroku`, `ibm-cloud`, `kubernetes`, `nexus-cr`, `pivotal`, `quay-cr`, `terraform-cloud`

| Column | Meaning |
| ------ | ------- |
| `group_id` | Storage namespace (Snyk group id or org id used for this row). |
| `org_id` | Snyk organization id for the issue. |
| `project_id` | Snyk project id for the issue. |
| `issue_id` | Snyk issue id (natural key with the three ids above). |
| `snyk_status` | Last-seen derived Snyk status stored for the mapping. |
| `organization` | Azure DevOps organization for the work item. |
| `project` | Azure DevOps project for the work item. |
| `work_item_id` | Azure Boards work item id. |
| `work_item_status` | Last-seen work item status snapshot. |
| `snyk_project_name` | Snyk project display name (filled when **`sync`** resolves project metadata). |
| `snyk_project_origin` | Snyk project **origin** token from project metadata (**`attributes.origin`**) when **`sync`** resolves it. |
| `excluded` | When `true`, **`sync`** treats the issue as **origin-excluded** ( **`sync_included_snyk_origins`** allowlist): no Azure Boards create/update/close/comment for that run. |
| `exclusion_reason` | When **`excluded`** is `true`, a stable reason (for example **`origin_unknown`**, **`origin_not_in_allowlist`**); otherwise empty. |
| `created_at` | UTC timestamp when the mapping row was created. |
| `updated_at` | UTC timestamp when the mapping row was last updated. |

### Environment variables

| Variable | Role |
| -------- | ---- |
| `SNYK_APP_CONFIG` | Path to the YAML file if you do not pass `--config` (CLI `--config` wins when both are set). |
| `SNYK_GROUP_ID` | Overrides `snyk.group_id` from the file (CLI group arguments override this in turn). |
| `AZURE_BOARDS_CREATE_NEW_WORK_ITEMS` | Overrides `azure_boards.defaults.create_new_work_items` (`true` / `false` / `1` / `0`). |
| `AZURE_BOARDS_ORGANIZATION` | Overrides `azure_boards.defaults.organization` when set to a non-empty value (non-secret Azure DevOps org name). |
| `AZURE_BOARDS_PROJECT` | Overrides `azure_boards.defaults.project` when set to a non-empty value (non-secret Azure DevOps project name or id). |
| `AZURE_DEVOPS_PAT` | **Secret:** Azure DevOps personal access token (not read from YAML or CLI flags). |
| `MAPPING_STORE` | Overrides `mapping_store` (`sqlite` or `azure_table`). |
| `MAPPING_STORE_SQLITE_PATH` | Overrides `sqlite_path` for the SQLite mapping database (CLI `--mapping-store-sqlite-path` wins when set). |
| `MAPPING_STORE_AZURE_TABLE_ENDPOINT` | Overrides **`mapping_store_azure_table_endpoint`** when **`mapping_store`** is **`azure_table`** (HTTPS Table service URL; non-secret). |
| `MAPPING_STORE_AZURE_TABLE_NAME` | Overrides **`mapping_store_azure_table_name`** when **`mapping_store`** is **`azure_table`** (non-secret). |
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

### The `sync` command

The **`sync`** command runs one reconciliation pass: it lists issues from the Snyk Issues API using **`snyk.group_id`** (**group** scope) when **`azure_boards.org_mappings`** is absent or empty; when **`org_mappings`** is non-empty, it lists issues per configured **`snyk_org_id`** (**org** scope) and routes Azure DevOps calls to each row’s **`organization`** / **`project`** with **`defaults`** merged with that row’s **`overrides`**. List calls use **`effective_severity_level`** derived from **`azure_boards.defaults.severity_threshold`** (comma-separated levels in the query string). When **`sync_included_snyk_origins`** is set (merged per mapping), only issues whose Snyk project **origin** is in that **inclusive** list receive Boards mutations; other issues are still written to **issues sync persistence** with **`excluded`** / **`exclusion_reason`**. It reads or writes rows in the mapping store and creates, updates, or closes Azure Boards work items via **`AZURE_DEVOPS_PAT`** (create/update/comment scope) for **non-excluded** issues. If you widen the allowlist (or an issue becomes eligible) and a row already exists with **no** Azure **`work_item_id`** (for example it was only ever persisted as excluded), **`sync`** **creates** a work item for **open** issues under the same rules as when no row exists (**`create_new_work_items`** and related gates still apply).

**Secrets** (`SNYK_TOKEN`, `AZURE_DEVOPS_PAT`) must be set in the environment — not in YAML. After merge, **`sync`** requires non-empty **`azure_boards.defaults.work_item_type`** (mirrored on **`azure_boards.work_item_type`**), **`work_item_state_active`**, and **`work_item_state_closed`** (defaults apply when omitted). When **`org_mappings`** is **not** used, **`sync`** also requires a non-empty **`snyk.group_id`**, **`azure_boards.defaults.organization`**, and **`azure_boards.defaults.project`** (effective values are mirrored on **`azure_boards.organization`** / **`project`**). When **`org_mappings`** **is** used, **`snyk.group_id`** is optional for listing (mapping rows may use **`snyk_org_id`** as the storage namespace when **`group_id`** is unset); each row **must** include **`snyk_org_slug`** (non-empty) so work items get valid Snyk UI links.

When **`azure_boards.defaults.create_new_work_items`** is **`false`** (mirrored on **`azure_boards.create_new_work_items`**), **`sync`** does **not** create new work items or insert new mapping rows for **eligible** (non-origin-excluded) unmapped issues (**no row** or **empty** **`work_item_id`**); it still updates or closes work items that already have a mapping. Origin-excluded issues may still receive a persistence row with **`excluded`** set for reporting.

```bash
export SNYK_TOKEN="***"
export AZURE_DEVOPS_PAT="***"
uv run python src/main.py sync --config data/sample-config.yaml
```

Use **`--group-id`** to override `snyk.group_id` for one invocation. **`--mapping-store-sqlite-path`** overrides the SQLite mapping database path (same precedence as **`fetch`**). Run **`uv run python src/main.py sync --help`** for the full flag list.

### `azure-devops-smoke` command

The **`azure-devops-smoke`** command performs a **single read-only** `get_work_item` call to validate connectivity, authentication, and response parsing. It reads **`azure_boards.defaults.organization`** and **`azure_boards.defaults.project`** from merged configuration (YAML and/or `AZURE_BOARDS_ORGANIZATION` / `AZURE_BOARDS_PROJECT`) and requires **`AZURE_DEVOPS_PAT`** in the environment (**do not** pass the PAT on the command line).

Example:

```bash
export AZURE_DEVOPS_PAT="***"
uv run python src/main.py azure-devops-smoke --config data/sample-config.yaml --work-item-id 12345
```

Run **`uv run python src/main.py azure-devops-smoke --help`** for flags. This command does **not** create, update, or add comments by default.

### `fetch` command and Snyk group or org id

The **`fetch`** smoke command calls the Snyk Issues API (**group** or **org** scope). You must supply **either** a non-empty **group id** (after merging file, env, and CLI) **or** **`--org-id`** for **org-scoped** list/get:

- **Group scope:** `snyk.group_id` in YAML, `SNYK_GROUP_ID`, **`fetch list`** positional group id, **`fetch get`** two-argument form (`group_id issue_id`), or **`--group-id`**.  
- **Org scope:** **`--org-id`** (`fetch list --org-id <uuid>`, **`fetch get --org-id <uuid> <issue_id>`**) — **group id is not required**.

If both group id and **`--org-id`** are missing after merge, **`fetch`** exits with an error before calling the API. Run **`uv run python src/main.py fetch --help`** for the full layout.

**`fetch`** also accepts **`--mapping-store-sqlite-path`** so you can override the SQLite mapping file path for that process without editing YAML (same precedence layer as other CLI overrides for `sqlite_path`).

### Parameter Descriptions

| Setting | Default | Notes |
| ------- | ------- | ----- |
| `azure_boards.defaults.create_new_work_items` | `true` | When `false`, **`sync`** must not create **new** work items or mapping rows (**P2-FR-11**); it may still update/close mapped items. |
| `azure_boards.defaults.organization` | `""` | Azure DevOps organization name for REST paths (non-secret). Required (non-empty) for **`azure-devops-smoke`** and for **`sync`** when **`org_mappings`** is not used. |
| `azure_boards.defaults.project` | `""` | Azure DevOps project name or id for REST paths (non-secret). Required (non-empty) for **`azure-devops-smoke`** and for **`sync`** when **`org_mappings`** is not used. |
| `azure_boards.defaults.severity_threshold` | `high` | Minimum severity for issue listing; **`fetch`** / **`sync`** map this to Snyk **`effective_severity_level`** (comma-separated). Not valid under **`snyk`**. |
| `azure_boards.defaults.issues_sync_from` | `historical` | `historical` or an ISO-8601 timestamp — controls which issues are in scope for sync (see design docs). |
| `azure_boards.defaults.create_only_when_fix_available` | `false` | When `true`, skip creating work items unless the issue indicates a fix is available. |
| `azure_boards.defaults.reopen_work_item_policy` | `new_work_item` | `new_work_item` or `reopen_existing` when a mapped work item is missing in ADO. |
| `azure_boards.defaults` | (nested) | Also holds **`work_item_type`**, **`work_item_state_*`**, and **`work_item_template`** — do not set **`work_item_*`** as direct children of **`azure_boards`**. |
| `azure_boards.org_mappings` | `[]` | Optional list of **`organization`**, **`project`**, **`snyk_org_id`**, **`snyk_org_slug`** (required per row), **`overrides`** for multi-target **`sync`**. |
| `azure_boards.defaults.work_item_type` | `Task` | WIT name for **`sync`** create (`$type`); must exist in your process. |
| `azure_boards.defaults.work_item_state_active` | `New` | Boards **`System.State`** for active findings; must exist in your process. |
| `azure_boards.defaults.work_item_state_closed` | `Closed` | Boards **`System.State`** when **`sync`** closes on resolved/ignored. |
| `work_item_template` | `{}` | Optional **`tags`** and **`json_patch`** for **`sync`** (see **`data/sample-config.yaml`**). |
| `snyk.group_id` | `""` | **Required** for group-scoped **`fetch`** / **`sync`** when **`org_mappings`** is empty — use a real Snyk group UUID. Optional when **`org_mappings`** drives **`sync`**. |
| `mapping_store` | `sqlite` | Use **`sqlite`** for local mapping persistence or **`azure_table`** for Azure Table Storage (requires endpoint + table name). There is **no** silent fallback to SQLite when **`azure_table`** is selected. |
| `sqlite_path` | `data/mapping_store.sqlite` | SQLite file path for mappings when **`mapping_store`** is **`sqlite`** (non-secret). Do not store tokens or PATs here. |
| `mapping_store_azure_table_endpoint` | `""` | HTTPS Table service URL when **`mapping_store`** is **`azure_table`**. Set via YAML or **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`**. |
| `mapping_store_azure_table_name` | `""` | Table name when **`mapping_store`** is **`azure_table`**. Set via YAML or **`MAPPING_STORE_AZURE_TABLE_NAME`**. |

Example file (see also **`data/sample-config.yaml`**):

```yaml
azure_boards:
  defaults:
    organization: "your-azure-devops-org"
    project: "your-azure-devops-project"
    create_new_work_items: true
    severity_threshold: high
    issues_sync_from: historical
    create_only_when_fix_available: false
    reopen_work_item_policy: new_work_item
    work_item_type: Task
    work_item_state_active: New
    work_item_state_closed: Closed
    work_item_template:
      tags:
        - Snyk
snyk:
  group_id: "00000000-0000-0000-0000-000000000001"
mapping_store: sqlite
sqlite_path: data/mapping_store.sqlite
```

## Output Sample + Description

Replace with sample output and what each field means (text, JSON, etc.).

## Testing

Run **`uv run pytest`** from the repository root (tests live under **`tests/`**; **`pythonpath`** includes **`src`** via **`pyproject.toml`**).

## Error Handling/Logging

The **`sync`** command configures the root logger with **UTC** timestamps (ISO-8601 `asctime`, `Z` suffix).

Structured **JSON** audit events are emitted on the logger named **`integration_audit`**:

| `event` | Meaning |
|--------|---------|
| **`integration_http`** | One line per terminal Snyk or Azure DevOps HTTP outcome after client retry policy. Fields include `integration` (`snyk` or `azure_devops`), `method`, `http_status`, `duration_ms`, `safe_target` (scheme/host/path only—no `Authorization`), optional `sync_run_id`, and on **401**/**403** an `error` containing **`Authentication Failed`**. |
| **`sync_summary`** | One line per **`sync`** invocation: `sync_run_id`, `sync_duration_seconds`, `sync_outcome` (`success` or `failure`), and `error` only on failure. |

In **Azure Monitor** / **Log Analytics**, container stdout often lands in **`ContainerAppConsoleLogs_CL`** (exact table names depend on the workspace and data collection rule). Each stdout line looks like ``UTC-timestamp LEVEL logger-name {JSON}`` — the trailing **`{JSON}`** is a single object with fields such as **`event`**, **`sync_duration_seconds`**, **`integration_http`**, etc. Use **`Log_s` contains** filters on stable substrings, or extract the JSON object before **`parse_json`** if your pipeline stores only structured JSON per row.

### Alerting runbook (portal; no IaC in this repo)

1. **Action Group** — In Azure Portal, create an [Action Group](https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/action-groups) with email, SMS, or webhook for on-call.
2. **Log-based alert** — Create a **scheduled query** or **log search** alert on the workspace receiving container logs.
3. **Latency (starting threshold 300 seconds)** — Alert when a sync run is slow, for example when `sync_duration_seconds` exceeds **300** (tune for your schedule and data volume). Example Kusto pattern (adapt table/column names to your workspace):

```kusto
ContainerAppConsoleLogs_CL
| where Log_s has "sync_summary" and Log_s has "\"sync_outcome\":\"success\""
| extend j = parse_json(tostring(split(Log_s, "integration_audit ")[1]))
| where todouble(j.sync_duration_seconds) > 300
| project TimeGenerated, j.sync_run_id, j.sync_duration_seconds
```

If `split`/`parse_json` is awkward for your exact `Log_s` shape, use **`Log_s contains "sync_duration_seconds"`** with a **regular expression** or a **workspace transform** to promote JSON fields.

4. **Repeated authentication failures** — Alert when **`Authentication Failed`** appears in `integration_http` events (for example more than **3** times in **10** minutes):

```kusto
ContainerAppConsoleLogs_CL
| where Log_s has "integration_http" and Log_s has "Authentication Failed"
| summarize cnt=count() by bin(TimeGenerated, 10m)
| where cnt > 3
```

5. **Stale sync (optional)** — If you expect a run at least every interval **T**, alert when there is **no** successful `sync_summary` within **N×T** (for example **N = 2**). Replace the time window and `ContainerAppConsoleLogs_CL` filter to match your deployment.

**Terraform / Bicep / ARM** for alert definitions are **not** required artifacts of this repository; operators may add them externally if desired.

## Troubleshooting

Common errors, known issues, FAQ, and debugging tips.

## Deployment

Production often runs this integration as a **scheduled container** on **[Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview)** (ACA), using the same **`ghcr.io`** images produced by CI (see `.github/workflows/`). **No Bicep/Terraform** artifacts are required in this repository—provision resources with your preferred tooling.

### Azure-aligned checklist

| Concern | Typical approach |
| --- | --- |
| **Operator YAML** | Store non-secret policy YAML on an **[Azure Files](https://learn.microsoft.com/en-us/azure/storage/files/storage-files-introduction)** share and mount it into the container (for example **`/config/app.yaml`**). Pass **`--config`** to that path. **Restart** the revision after YAML edits (hot-reload is not supported). |
| **Secrets** | **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** via **[Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)** references as Container Apps **secrets** mapped into **environment variables** — never bake secrets into the image or YAML. |
| **Managed identity** | Enable a **[managed identity](https://learn.microsoft.com/en-us/azure/container-apps/security-managed-identity)** on the Container App for Azure Table Storage and Files access (**`DefaultAzureCredential`** in the workload). Grant **Table Data Contributor** (or equivalent RBAC) on the storage account used for mappings. |
| **Mapping store** | Set **`mapping_store: azure_table`** and supply **`mapping_store_azure_table_endpoint`** plus **`mapping_store_azure_table_name`** (YAML and/or **`MAPPING_STORE_AZURE_TABLE_*`** env vars). Values are **non-secret**; authentication uses Entra ID, **not** storage account keys. |

### Where to view logs

The app logs to **stdout/stderr** only; no extra logging configuration is required inside the process.

- **[Log stream](https://learn.microsoft.com/en-us/azure/container-apps/log-streaming)** — In the Azure Portal, open your **Container App → Monitoring → Log stream** for a live tail of container console output when debugging a revision.
- **Log Analytics / Logs** — Use **Container App → Monitoring → Logs** (or **Azure Monitor → Logs**) against the workspace linked to your ACA environment. Structured **`integration_audit`** lines often appear in tables such as **`ContainerAppConsoleLogs_CL`** (exact names depend on workspace / data collection rules). See **Error Handling/Logging** above for **`sync_summary`** / **`integration_http`** fields and sample Kusto queries.

### Container registry

Authenticate ACA (or another orchestrator) to **`ghcr.io`** so it can pull the package; pin **tags** or **digests** according to your release policy.