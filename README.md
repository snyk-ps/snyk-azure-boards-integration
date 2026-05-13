# Azure Boards Integration

## Description

**Azure Boards Integration** syncs **Snyk** security issues into **Azure Boards** (Azure DevOps work items). It discovers issues that match your severity and filtering rules, keeps work items aligned (create, update, close, and comments where needed), and maintains a **mapping** between each Snyk issue and at most one work item. Operators express non-secret policy in YAML; tokens and other secrets live in environment variables or a secret store. Typical deployment is a **scheduled container** (for example **Azure Container Apps**) running **`sync`** on a **daily cadence** (**every 24 hours** is recommended); the same build is also easy to run on a workstation for smoke tests and debugging.

## Table of contents

- [Quick start](#quick-start)
- [Installation and setup](#installation-and-setup)
  - [Development / local installation](#development-local-installation)
  - [Deployment / production installation](#deployment-production-installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Deployment](#deployment)
- [Logs and observability](#logs-and-observability)
- [Troubleshooting](#troubleshooting)
- [More documentation](#more-documentation)

## Quick start

Pick an installation path below. Both use the same **secrets** and **YAML policy** model.

**Development / local**

1. Clone the repo, **`uv sync`**, set **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`**, copy **`data/sample-config.yaml`** and adjust it (see [Development / local installation](#development-local-installation)).
2. Run **`uv run python src/main.py sync --config /path/to/your-config.yaml`**.

**Deployment / production**

1. Run the app from a **container** on your platform (commonly a **scheduled** job on **Azure Container Apps**). The image **defaults to** **`sync --config /config/config.yaml`** (mount your YAML there or override args). Schedule **`sync` every 24 hours** (recommended). Inject **`SNYK_TOKEN`**, **`AZURE_DEVOPS_PAT`**, and mount or supply **`--config`** (see [Deployment / production installation](#deployment-production-installation) and [Deployment](#deployment)).

Full YAML and environment reference: **[CONFIGURATION.md](CONFIGURATION.md)**.

**Rollout:** Start with **one test Snyk org** (and the Azure Boards project you intend to use for it) to validate YAML, credentials, work item fields, and mapping behavior. Expand to more orgs or broader group scope only after runs look correct.

## Installation and setup

### Prerequisites

- **Snyk** API access and **Azure DevOps** access (PAT with **Work items** read and write for `sync`; see [Azure DevOps PAT](#azure-devops-pat)).
- **Development / local:** **Python** 3.12+ and **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (installs from **`pyproject.toml`** / **`uv.lock`**).
- **Deployment / production:** a container runtime and outbound **HTTPS** to Snyk, **`dev.azure.com`**, and (if used) your **Azure Table** endpoint; **Docker** optional for building images locally.
- **Azure Table** storage account only if you set **`mapping_store: azure_table`** in config.

### Secrets and environment (both paths)

| Variable | Required for `sync` | Role |
| -------- | ------------------- | ---- |
| **`SNYK_TOKEN`** | Yes | Snyk API token (**secret**; never commit). |
| **`AZURE_DEVOPS_PAT`** | Yes | Azure DevOps PAT for work items (**secret**). |
| **`SNYK_GROUP_ID`** | If not set in YAML | Overrides **`snyk.group_id`**. |

**Never** put tokens or PATs in YAML; use the process environment or your platform’s secret store (Key Vault, Container Apps secrets, etc.).

All variables and overrides: **[CONFIGURATION.md § Environment variables](CONFIGURATION.md#environment-variables)**.

### Azure DevOps PAT

Use **`AZURE_DEVOPS_PAT`**. Set **Work Items** to **Read & write** in the PAT dialog (labels vary by Azure DevOps version). That covers **`sync`** (read/update/create/comment) and **`azure-devops-smoke`**.

Steps to create a token: **[CONFIGURATION.md § Azure DevOps personal access token](CONFIGURATION.md#azure-devops-personal-access-token-pat)** (and [Microsoft PAT documentation](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate?view=azure-devops)).

### Development / local installation

Use this path to contribute, debug, or smoke-test from your machine.

1. **Clone** the repository and install dependencies:

```bash
uv sync
```

For tests and optional dev dependencies: **`uv sync --dev`** (see **[CONTRIBUTING.md](CONTRIBUTING.md)**).

2. **Configure** policy: copy **`data/sample-config.yaml`**, set **`snyk.group_id`**, **`azure_boards.defaults.organization`**, **`azure_boards.defaults.project`**, and work item fields to match your tenant (full reference: **[CONFIGURATION.md](CONFIGURATION.md)**).

3. **Export secrets** in your shell (or use your IDE’s env):

```bash
export SNYK_TOKEN="***"
export AZURE_DEVOPS_PAT="***"
```

4. **Run** the CLI with **`uv run`**:

```bash
uv run python src/main.py --help
uv run python src/main.py sync --config /path/to/your-config.yaml
```

Optional: build and run the root **`Dockerfile`** locally to mirror production; image notes and CI context are in **[CONTRIBUTING.md](CONTRIBUTING.md)**.

### Deployment / production installation

Use this path for scheduled sync in a cluster or cloud (recommended for ongoing operations).

1. **Image:** use a build from this repo’s **`Dockerfile`**, or pull a release image from **[GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)** (**`ghcr.io`**). Tags and install/copy hints are on this repository’s **Packages** page on GitHub. Authenticate to the registry for private images; pin **tags** or **digests**. The image **ENTRYPOINT** is **`python src/main.py`**; **default args** are **`sync --config /config/config.yaml`** (mount policy there unless your platform overrides **command** / **args**).

2. **Secrets:** inject **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** via your platform (for example Key Vault references on **Azure Container Apps**), not in the image or YAML.

3. **Policy:** supply non-secret config as a mounted file at **`/config/config.yaml`** (recommended, matches the default **`CMD`**), or set **`SNYK_APP_CONFIG`** / override **`--config`** per **[CONFIGURATION.md](CONFIGURATION.md)**. Prefer a **single test Snyk org** for the first production runs until behavior matches expectations.

4. **Job model:** run **`sync`** on a **schedule** (for example Container Apps **cron** or an external scheduler). **Recommended:** trigger **`sync` every 24 hours** so Boards stays aligned with Snyk without excessive API load. If you use the image defaults, the job only needs to **start the container** with secrets and the config mount. One revision at a time is usually enough; see [Deployment](#deployment) for sizing, networking, **Azure Table** + managed identity, and log locations.

**`docker run` example** (replace image tag; use a real config file path on the host):

```bash
docker run --rm \
  -e SNYK_TOKEN \
  -e AZURE_DEVOPS_PAT \
  -v /path/on/host/config.yaml:/config/config.yaml:ro \
  ghcr.io/<owner>/<repo>:<tag>
```

Other CLI subcommands override the default args, for example: **`docker run … <image> fetch list --config /config/config.yaml`**.

## Configuration

- Non-secret **policy** lives in a **YAML** file passed with **`--config`** or **`SNYK_APP_CONFIG`**. **Never** put API tokens or PATs in YAML.
- Precedence: defaults, then YAML, then environment variables, then CLI (see **[CONFIGURATION.md § Precedence](CONFIGURATION.md#precedence)**).
- **Rollout:** It is **recommended** to scope your first **`sync`** runs to **one test Snyk org** so you can confirm configuration end-to-end before adding **`org_mappings`** rows or widening to the full group.
- Start from **`data/sample-config.yaml`**. Full key list, **`azure_boards.org_mappings`**, mapping store, **`fetch`** / **`sync`** details: **[CONFIGURATION.md](CONFIGURATION.md)**.

## Usage

CLI entry point:

```bash
uv run python src/main.py --help
```

| Command | Purpose |
| ------- | ------- |
| **`sync`** | Reconcile Snyk issues with Boards and update the mapping store. Needs **`SNYK_TOKEN`**, **`AZURE_DEVOPS_PAT`**, **`snyk.group_id`**, and routing from config. |
| **`fetch`** | Smoke-test the Snyk Issues API. Prefer the same **`snyk.group_id`** as **`sync`**. |
| **`azure-devops-smoke`** | One read-only **`get_work_item`** against Azure DevOps. |

Examples:

```bash
uv run python src/main.py sync --config data/sample-config.yaml
uv run python src/main.py fetch list --config data/sample-config.yaml
```

Command-level behavior: **[CONFIGURATION.md](CONFIGURATION.md)** (`sync`, `fetch`, `azure-devops-smoke` sections).

## Features

- One-way sync from Snyk issues to Azure Boards with configurable type, states, severity, and filters.
- Mapping store: **SQLite** or **Azure Table Storage** (Entra ID / **`DefaultAzureCredential`** for Table).
- Optional **multi-org** routing via **`azure_boards.org_mappings`**.
- Work item **tags** and **JSON Patch** templates; structured **`integration_audit`** logging.

## Deployment

This section is the **Azure-oriented runbook** for production: sizing, **Azure Table**, identity, and day-two operations. For the install surface (image, secrets, config, scheduler entrypoint), start with **[Deployment / production installation](#deployment-production-installation)** above.

Production is commonly a **scheduled container** on **[Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview)** using images from **`ghcr.io`** (published by this repo’s workflows and listed on the repository **Packages** page). **No Bicep/Terraform** is required in this repo. **Schedule `sync` every 24 hours** unless your risk or change cadence needs a different interval.

### Minimum requirements (Azure Container Apps)

| Area | Recommendation |
| ---- | -------------- |
| **`sync` schedule** | **Every 24 hours** (daily) is recommended; adjust if you need fresher work items or must throttle API usage. |
| **CPU / memory** | Start around **0.5 vCPU** and **1 GiB** for typical **`sync`** batch work; increase if runs are slow or OOM. |
| **Replicas** | **1** is usually enough if jobs do not overlap. |
| **Networking** | Outbound **HTTPS** to Snyk, **`dev.azure.com`**, and your Table endpoint if using **`azure_table`**. |
| **Secrets** | **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** via Key Vault references / Container Apps secrets, not the image. |
| **Identity** | Managed identity on the app when using **Azure Table** with **`DefaultAzureCredential`**. |

### Azure Table Storage

1. Create a storage account with the **Table** API.
2. Set **`mapping_store: azure_table`**, **`mapping_store_azure_table_endpoint`** (for example `https://<account>.table.core.windows.net`), and **`mapping_store_azure_table_name`** (YAML and/or **`MAPPING_STORE_AZURE_TABLE_*`** env vars).
3. The app calls **`create_table_if_not_exists`** on startup if needed.
4. **Partition key** is **`snyk.group_id`**; **row key** is derived from **`org_id`**, **`project_id`**, **`issue_id`**. Details: **[CONFIGURATION.md § Mapping row columns](CONFIGURATION.md#mapping-row-columns-issue_work_item_map)**.

### DefaultAzureCredential and Table RBAC

The Table client uses **`DefaultAzureCredential`**. On **Azure Container Apps**, assign a **managed identity** and grant **Storage Table Data Contributor** on the storage account (built-in role id **`0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3`**). For local dev, **`az login`** or a service principal with the same data-plane role. Boards access still requires **`AZURE_DEVOPS_PAT`**.

Extended notes: **[CONFIGURATION.md](CONFIGURATION.md)** aligns with deployment; see also [DefaultAzureCredential (Python)](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential).

### Azure-aligned checklist

| Concern | Typical approach |
| --- | --- |
| **Policy YAML** | Mount from **Azure Files** (for example **`/config/config.yaml`**) and pass **`--config`** (or rely on the image default **`CMD`**). Restart revision after changes. |
| **Secrets** | Key Vault references → Container Apps secrets → env vars. |
| **Mapping store** | **`azure_table`** + endpoint/name; non-secret; auth via Entra ID. |

### Where to view logs

- **Log stream:** [Container App log streaming](https://learn.microsoft.com/en-us/azure/container-apps/log-streaming).
- **Log Analytics:** query workspace linked to the ACA environment; structured lines often appear in **`ContainerAppConsoleLogs_CL`**. See [Logs and observability](#logs-and-observability).

### Container registry

The image **defaults to** **`sync --config /config/config.yaml`** (see [Deployment / production installation](#deployment-production-installation)). Images are published to **`ghcr.io`** and appear on this repository’s **Packages** page. Authenticate your runtime to **`ghcr.io`**; pin **tags** or **digests**. [Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

## Logs and observability

The **`sync`** command logs in **UTC**. The **`integration_audit`** logger emits **JSON** lines for operators and Azure Monitor:

| `event` | Meaning |
|--------|---------|
| **`integration_http`** | One line per terminal Snyk or Azure DevOps HTTP result (after retries). Includes `method`, `http_status`, `duration_ms`, `safe_target` (no secrets); **401/403** may include **`Authentication Failed`**. |
| **`sync_summary`** | One line per **`sync`**: duration, **`sync_outcome`** (`success` / `failure`). |

Example shape:

```text
2026-05-12T10:15:30.123Z INFO integration_audit {"event":"integration_http","integration":"snyk","method":"GET","http_status":200,...}
2026-05-12T10:15:45.456Z INFO integration_audit {"event":"sync_summary","sync_duration_seconds":12.3,"sync_outcome":"success",...}
```

In **Log Analytics**, parse trailing JSON from **`ContainerAppConsoleLogs_CL`** as needed.

### Alerting (portal)

**Latency:** alert when **`sync_duration_seconds`** in successful runs exceeds your threshold (for example **300**). **Auth failures:** alert on repeated **`Authentication Failed`** in **`integration_http`**. Example Kusto patterns and stale-run ideas previously lived in the README; you can copy them from git history or adapt to your workspace schema. **`Terraform` / Bicep** for alerts are out of scope for this repo.

## Troubleshooting

| Symptom | What to check |
| ------- | ------------- |
| **Snyk `Authentication Failed`** | **`SNYK_TOKEN`**, expiry, org/group access. |
| **Azure DevOps `Authentication Failed`** | **`AZURE_DEVOPS_PAT`**, **Work items** read/write scope, org/project names vs PAT scope. |
| **`sync` config errors** | **`snyk.group_id`** set; **`azure_boards.defaults`** structure; **`work_item_type`** and states; **`organization`** / **`project`** or **`org_mappings`** rows. |
| **Table store startup failure** | Endpoint, table name, network, managed identity, **Storage Table Data Contributor**. |
| **No new work items** | **`create_new_work_items`**, filters, **`create_only_when_fix_available`**, Snyk data in scope. |
| **Cannot pull image** | **`ghcr.io`** auth and tag/digest. |

## More documentation

| Document | Audience |
| -------- | -------- |
| **[CONFIGURATION.md](CONFIGURATION.md)** | Full YAML keys, env vars, PAT steps, commands, tags, origins list, mapping columns. |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | Layout, tests, OpenSpec, CI/Docker, **`TEMPLATE_VERSION`**. |
