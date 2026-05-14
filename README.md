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
  - [Azure Container Apps: portal walkthrough (scheduled job)](#azure-container-apps-portal-walkthrough-scheduled-job)
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

1. **Image:** use a build from this repo’s **`Dockerfile`**, or pull a release image from **[GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)** (**`ghcr.io`**). **Tags**, digests, and pull/copy hints: **[snyk-azure-boards-integration package on GitHub](https://github.com/snyk-ps/snyk-azure-boards-integration/pkgs/container/snyk-azure-boards-integration)**. Authenticate to the registry for private images; pin **tags** or **digests**. The image **ENTRYPOINT** is **`python src/main.py`**; **default args** are **`sync --config /config/config.yaml`** (mount policy there unless your platform overrides **command** / **args**).

2. **Secrets:** inject **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** via your platform (for example Key Vault references on **Azure Container Apps**), not in the image or YAML.

3. **Policy:** supply non-secret config as a mounted file at **`/config/config.yaml`** (recommended, matches the default **`CMD`**), or set **`SNYK_APP_CONFIG`** / override **`--config`** per **[CONFIGURATION.md](CONFIGURATION.md)**. Prefer a **single test Snyk org** for the first production runs until behavior matches expectations.

4. **Job model:** run **`sync`** on a **schedule** (for example Container Apps **cron** or an external scheduler). **Recommended:** trigger **`sync` every 24 hours** so Boards stays aligned with Snyk without excessive API load. If you use the image defaults, the job only needs to **start the container** with secrets and the config mount. One revision at a time is usually enough; see [Deployment](#deployment) for sizing, networking, **Azure Table** + managed identity, and log locations.

**`docker run` example** (replace image tag; use a real config file path on the host):

```bash
docker run --rm \
  -e SNYK_TOKEN \
  -e AZURE_DEVOPS_PAT \
  -v /path/on/host/config.yaml:/config/config.yaml:ro \
  ghcr.io/snyk-ps/snyk-azure-boards-integration:<tag>
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

This section is the **Azure-oriented runbook** for production: sizing, **Azure Table**, identity, and the **[portal walkthrough](#azure-container-apps-portal-walkthrough-scheduled-job)** for a **scheduled Container App Job**.

Production is commonly a **scheduled container** on **[Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview)** using images from **`ghcr.io`** ([**container package on GitHub**](https://github.com/snyk-ps/snyk-azure-boards-integration/pkgs/container/snyk-azure-boards-integration)). **No Bicep/Terraform** is required in this repo. **Schedule `sync` every 24 hours** unless your risk or change cadence needs a different interval.

### Minimum requirements (Azure Container Apps)

| Area | Recommendation |
| ---- | -------------- |
| **`sync` schedule** | **Every 24 hours** (daily) is recommended; adjust if you need fresher work items or must throttle API usage. |
| **CPU / memory** | Start around **0.5 vCPU** and **1 GiB** for typical **`sync`** batch work; increase if runs are slow or OOM. |
| **Replicas** | **1** is usually enough if jobs do not overlap. |
| **Networking** | Outbound **HTTPS** to Snyk, **`dev.azure.com`**, and your Table endpoint if using **`azure_table`**. |
| **Secrets** | **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** via Key Vault references / Container Apps secrets, not the image. |
| **Identity** | Managed identity on the app when using **Azure Table** with **`DefaultAzureCredential`**. |

### Azure Container Apps: portal walkthrough (scheduled job)

Use a **Container App Job** with a **Schedule** trigger (cron), not a regular HTTP Container App. The steps below follow the [Create a job in the Azure portal](https://learn.microsoft.com/en-us/azure/container-apps/jobs-get-started-portal) flow and this repo’s image default **`sync --config /config/config.yaml`**.

#### A. Prepare config in Azure Storage (do this first)

1. In the portal, open **Storage accounts** → **+ Create**.
2. **Basics:** pick subscription, resource group, region, a **globally unique** name, **Performance** Standard, **Redundancy** LRS (or per policy). **Kind** StorageV2 is fine.
3. **Advanced:** ensure **Allow storage account key access** stays **enabled** if you will use the **account key** for the ACA file share link (common for SMB).
4. Create the account, then open it.
5. Under **Data storage** → **File shares** → **+ File share:** create a share (e.g. `snyk-boards-config`).
6. Open the share → **Upload** your **`config.yaml`** (non-secret policy only).  
   The object in the share must end up as **`config.yaml`** at the **root** of the share so the mounted path **`/config/config.yaml`** is correct.
7. Under **Security + networking** → **Access keys:** copy **key1** (or **key2**) — you’ll paste it when wiring the environment **Volume mount**.

**Networking:** If the storage account uses a **restricted firewall** or **public network access** disabled, SMB mounts from Container Apps can fail (for example **`VolumeMountFailure`** / **`mount error(13): Permission denied`**). The account must be **reachable** from your Container Apps environment for that file share. See [Use storage mounts in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts).

#### B. Create the Container Apps environment (with file share link)

You can either create the environment **inside** the job wizard (**Basics**) or create it **first** as its own resource. Either way you need one **Container Apps** environment.

1. Portal search: **Container Apps environments** → open your environment (or create it from the job wizard via **Create new**, as in the [portal quickstart](https://learn.microsoft.com/en-us/azure/container-apps/jobs-get-started-portal)).
2. Open the environment → **Settings** → **Volume mounts** (or **Storage** / **Azure Files**, depending on portal wording).
3. **Add** a volume mount:
   - **Protocol:** SMB (default for standard Azure Files).
   - **Name:** a short logical name you will reuse on the job (e.g. `configshare`). This is the **`storageName` / environment storage name**, not the Azure share name.
   - **Storage account:** select the account from step **A**.
   - **File share:** select the share that contains **`config.yaml`**.
   - **Access key:** paste the key from step **A** (if the UI asks).
   - **Access mode:** **Read only** is enough if the job only reads config.
4. **Save** so the environment now lists this Azure Files mount.

#### C. Create the Container App Job (scheduled)

1. Portal top search: **Container App Jobs** → **Create**.

**Basics**

- Subscription, **Resource group**
- **Container job name:** e.g. `snyk-boards-sync` (must follow ACA naming rules; short name).
- **Region:** same as the environment (and typically the same as the storage account region).
- **Container Apps environment:** select the environment from **B** (or **Create new** and match the quickstart: **Workload profiles** / **Consumption** per your org’s standard).

**Job details** (or equivalent step)

- **Trigger type:** **Scheduled**
- **Cron expression:** use a **five-field** schedule in **UTC** (examples: `0 2 * * *` = daily 02:00 UTC). Adjust to your cadence.

**Container** (main step)

- **Container name:** e.g. `main`
- **Image source:** **Docker Hub or other registries** (or **Azure Container Registry** if you use ACR).
- For **`ghcr.io`:** set **registry** to **`ghcr.io`**, image **`snyk-ps/snyk-azure-boards-integration:<tag>`** (pin a real **tag** or **digest**). If the package is **private**, set **registry credentials** / **secret** per portal prompts.
- **Workload profile:** **Consumption** is usually fine for this sync.
- **CPU and memory:** e.g. **0.5 CPU**, **1.0 Gi** (matches [minimum requirements](#minimum-requirements-azure-container-apps) above).

**Do not** override **ENTRYPOINT** / **command** unless you know you need to; the image default is already **`sync --config /config/config.yaml`**.

#### D. Secrets and environment variables (portal)

On the job’s container / configuration (wording varies by blade version). The **create** wizard may not expose **Secrets**; if not, open the deployed **Container App Job** → **Settings** → **Secrets**, then reference those secrets from **Environment variables** on the container / template (same idea as [Manage secrets in Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets?tabs=azure-portal)).

**Secrets** (job-level): add at least:

| Secret name | Value |
| ----------- | ----- |
| `snyk-token` | Snyk API token |
| `azure-devops-pat` | Azure DevOps PAT |

**Environment variables** for the container:

| Variable | Source |
| -------- | ------ |
| `SNYK_TOKEN` | Reference secret `snyk-token` |
| `AZURE_DEVOPS_PAT` | Reference secret `azure-devops-pat` |

**Key Vault:** if your org requires it, use the portal options for **Key Vault references** on Container Apps secrets instead of pasting values — same net result: env vars backed by secrets.

#### E. Mount the file share on the job at `/config`

The environment link exists from **B**; the job still needs a **volume + mount** so the file appears as **`/config/config.yaml`**.

1. In the **Container** step (or **Volumes** / **Advanced** on the same wizard), **add a volume:**
   - **Type:** **Azure Files** (backed by the environment mount you named, e.g. `configshare`).
2. **Mount** that volume on the main container:
   - **Mount path:** **`/config`**
   - No **`subPath`** needed if **`config.yaml`** is at the **root** of the share.

If the **create** wizard does not offer volumes, finish **Create**, then open the job resource → find **Containers** / **Revision** / **Edit** (same idea as **Revisions and replicas** on a normal Container App), add the **Azure Files** volume and **`/config`** mount, then **save** so a new revision applies.

#### F. Optional: Azure Table + managed identity (if YAML uses `azure_table`)

1. On the **Container App Job** resource: **Identity** → turn on **System assigned** (or user-assigned per policy).
2. On the **Table** storage account: **Access Control (IAM)** → **Add role assignment** → **Storage Table Data Contributor** → assign to the job’s identity.
3. Ensure **Table endpoint** and **table name** are set in YAML or env as documented (see [Azure Table Storage](#azure-table-storage) below).

#### G. Deploy, test, logs

1. **Review + create** on the job.
2. Open the job → **Execution history** (or **Executions**) → **Run now** / manual start if offered, to test before waiting for cron.
3. Open **Log stream** or **Logs** for the latest execution; confirm **`sync_summary`** / **`integration_audit`** lines (see [Logs and observability](#logs-and-observability)).

**Where to click:** **Execution history** → select a run → **View logs**; for longer retention and queries, use **Monitoring** → **Logs** on the **Container Apps environment** or **Log Analytics** (`ContainerAppConsoleLogs_CL`). Details: [Where to view logs](#where-to-view-logs).

**Exit reason:** **`ProcessExited`** with **exit code `0`** means the main process finished successfully — expected for **`sync`** when the run succeeds.

#### H. If something fails

| Issue | What to check |
| ----- | ------------- |
| **Missing config** | The share contains **`config.yaml`** and the mount path is exactly **`/config`**. |
| **Volume mount / Permission denied** | Storage account **firewall** / **public network access**, wrong **access key** on the environment volume, or share path; see **A** (**Networking**) and [Use storage mounts in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts). |
| **Auth errors** | Secrets and PAT scopes (**Work items: Read & write**). |
| **Pull image failed** | **`ghcr.io`** visibility and any **registry credentials** on the job. |

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

The image **defaults to** **`sync --config /config/config.yaml`** (see [Deployment / production installation](#deployment-production-installation)). Images are published to **`ghcr.io`**; see the [**container package page**](https://github.com/snyk-ps/snyk-azure-boards-integration/pkgs/container/snyk-azure-boards-integration) for tags and digests. Authenticate your runtime to **`ghcr.io`**; pin **tags** or **digests**. [Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

## Logs and observability

The **`sync`** command configures the root logger to emit **NDJSON** (one **JSON object per line**) on **standard output**. Each line includes **`timestamp`** (UTC, RFC 3339 with **`Z`**), **`level`** (`INFO`, `WARNING`, `ERROR`, …), **`logger`**, and optional fields:

| Field | When present |
|--------|----------------|
| **`record`** | Structured payloads for the **`integration_audit`** logger (see below). |
| **`message`** | Plain messages from other loggers (no **`record`**). |
| **`exception`** | Traceback text when a logged exception is attached. |

The **`integration_audit`** **`record`** object uses the same **`event`** values as before:

| `record.event` | Meaning |
|--------|---------|
| **`integration_http`** | One line per terminal Snyk or Azure DevOps HTTP result (after retries). Includes `method`, `http_status`, `duration_ms`, `safe_target` (no secrets); **401/403** may include **`Authentication Failed`**. |
| **`sync_summary`** | One line per **`sync`**: **`sync_duration_seconds`**, **`sync_outcome`** (`success` / `failure`). |

Example line (wrapped for readability; runtime output is a **single** line):

```text
{"level":"INFO","logger":"integration_audit","record":{"duration_ms":12.0,"event":"integration_http","http_status":200,"integration":"snyk","method":"GET","safe_target":"https://api.snyk.io/rest/..."},"timestamp":"2026-05-12T10:15:30.123Z"}
```

**Azure SDK noise:** by default, **`azure.*`** loggers are set to **WARNING** so **`HttpLoggingPolicy`** does not flood **INFO**. To troubleshoot Azure client HTTP logging, set env **`INTEGRATION_VERBOSE_AZURE_LOGS=1`** (or **`true`** / **`yes`** / **`on`**). For line-oriented shipping in containers, **`PYTHONUNBUFFERED=1`** is recommended.

### Log Analytics (Kusto)

Console logs often land in **`ContainerAppConsoleLogs`** / **`ContainerAppConsoleLogs_CL`**; the raw message column name varies (**`Log_s`**, **`LogMessage`**, etc.—inspect your workspace).

Parse one NDJSON line and filter by level and audit event, for example:

```kusto
ContainerAppConsoleLogs_CL
| where Log_s startswith "{"
| extend J = parse_json(Log_s)
| where J.level == "ERROR" or J.level == "WARNING"
| where J.logger == "integration_audit"
| extend evt = J.record.event
| where evt == "sync_summary" and todouble(J.record.sync_duration_seconds) > 300
```

### Alerting (portal)

**Latency:** alert when **`sync_duration_seconds`** in successful runs exceeds your threshold (for example **300**)—after **`parse_json`**, use **`J.record.sync_duration_seconds`** and **`J.record.sync_outcome`**. **Auth failures:** alert on **`integration_http`** records where **`J.record.error`** contains **`Authentication Failed`** (or **`J.record.http_status`** is **`401`** or **`403`**). **`Terraform` / Bicep** for alerts are out of scope for this repo.

| Symptom | What to check |
| ------- | ------------- |
| **Snyk `Authentication Failed`** | **`SNYK_TOKEN`**, expiry, org/group access. |
| **Azure DevOps `Authentication Failed`** | **`AZURE_DEVOPS_PAT`**, **Work items** read/write scope, org/project names vs PAT scope. |
| **`sync` config errors** | **`snyk.group_id`** set; **`azure_boards.defaults`** structure; **`work_item_type`** and states; **`organization`** / **`project`** or **`org_mappings`** rows. |
| **Table store startup failure** | Endpoint, table name, network, managed identity, **Storage Table Data Contributor**. |
| **No new work items** | **`create_new_work_items`**, filters, **`create_only_when_fix_available`**, Snyk data in scope. |
| **Cannot pull image** | **`ghcr.io`** auth and tag/digest; confirm image name on the [**GitHub container package**](https://github.com/snyk-ps/snyk-azure-boards-integration/pkgs/container/snyk-azure-boards-integration). |

## More documentation

| Document | Audience |
| -------- | -------- |
| **[CONFIGURATION.md](CONFIGURATION.md)** | Full YAML keys, env vars, PAT steps, commands, tags, origins list, mapping columns. |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | Layout, tests, OpenSpec, CI/Docker, **`TEMPLATE_VERSION`**. |
