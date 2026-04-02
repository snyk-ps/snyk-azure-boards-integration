# Azure platform — runtime, state, secrets, operator config

Recommended Azure services and runtime behavior for the Snyk–Azure Boards integration. Cross-reference **P2-FR-*** in `../sync-lifecycle/spec.md` where cited.

## Major components

| Component | Recommended Azure service | Purpose |
|-----------|---------------------------|---------|
| Synchronization middleware | Azure Container Apps (ACA) | Runs the containerized application that implements Snyk–Azure Boards synchronization logic. |
| State & mapping | Azure Table Storage | Persists the relationship between Snyk finding identifiers and Azure Boards work item IDs to support stable mapping and reopen handling. |
| Secrets | Azure Key Vault | Stores sensitive credentials (`SNYK_TOKEN`, Azure DevOps PAT); ACA references these as environment variables without embedding values in code or config artifacts. |
| Cloud identity | System-assigned managed identity | Authenticates the app to Azure APIs (Key Vault, Table Storage, and other Azure resources that support Microsoft Entra ID) without client secrets in the workload. |
| Logging & observability | ACA OpenTelemetry agent + Application Insights / Log Analytics | Ships logs and telemetry for operations, transaction visibility, and sync latency measurement (supports P2-FR-6, P2-FR-6.2, P2-FR-6.3). |
| Alerting | Azure Monitor (metric alerts, log search alerts) + Action Groups | Notifies operators when health, authentication, or latency thresholds are breached (supports P2-FR-6). |
| Operator configuration | **Azure-only:** YAML on an **Azure Files** share (mounted into the container) and/or **Azure Blob Storage** (downloaded at startup); managed identity grants access | End-user tunables live **only in Azure** (no Git or repo as the required source of truth): severity filters, work item type and template defaults, tags, and related options without rebuilding the container image. |

## Synchronization middleware (Azure Container Apps)

The integration runs as a container on **Azure Container Apps**. It runs on a **scheduled sync** model (for example ACA **cron** or an equivalent periodic job): each run calls the **Snyk Issues API** to list current issues for configured orgs/projects, reconciles them with **Azure Table Storage** mappings, then calls **Azure DevOps** Work Item Tracking APIs to create, update, or close work items per the functional requirements.

## Durable state & mapping (Azure Table Storage)

**Azure Table Storage** holds application state needed for a **stable, unique mapping** between Snyk issues and work items (**P2-FR-7**). The same store supports **re-opened findings** (**P2-FR-8**): when a previously fixed or closed finding becomes open again, the stored history allows the solution to open a **new** work item while retaining traceability to past mappings as required by policy.

**Minimum attributes persisted per mapping row** (exact partition/row key design is implementation detail; together these fields identify the Snyk issue and its Azure Boards counterpart):

| Source | Field | Role |
|--------|-------|------|
| Snyk | **Group ID** | Locates the issue in Snyk’s hierarchy (with org and project). |
| Snyk | **Org ID** | Organization that owns the project and issue. |
| Snyk | **Project ID** | Snyk project containing the issue. |
| Snyk | **Issue ID** | Stable identifier for the Snyk issue (primary logical key with org + project). |
| Snyk | **Status** | Issue lifecycle from Snyk: **open**, **closed**, or **ignored** (drives close-on-fix, close-on-ignore, and reopen behavior). |
| Azure DevOps | **Organization** | Azure DevOps organization name (or id) for REST calls. |
| Azure DevOps | **Project** | Team project containing the work item. |
| Azure DevOps | **Work item ID** | Boards work item linked to this Snyk issue. |

Additional columns (for example last sync time, prior work item ids for **P2-FR-8** audit, or issue severity snapshot) may be added by the implementation but are not required by this minimum contract.

## Secrets (Azure Key Vault)

**Azure Key Vault** stores **`SNYK_TOKEN`** and the **Azure DevOps personal access token (PAT)**. **Azure Container Apps** can integrate with Key Vault so secrets are **referenced directly** and exposed to the container as **environment variables**, avoiding plaintext secrets in source control or container images.

## Identity (managed identity & DefaultAzureCredential)

A **system-assigned managed identity** on the Container App satisfies the need to monitor and rely on **authentication health** for Azure-backed dependencies (**P2-FR-6.1**). Application code (e.g. Python) uses **`DefaultAzureCredential`** from the **Azure Identity SDK**, which detects the ACA runtime and acquires tokens for **Key Vault**, **Table Storage**, **Azure Files** / **Blob** (for operator YAML), and other Entra-protected Azure endpoints **without embedding client secrets** in code or shell scripts.

## Runtime configuration (external YAML, Azure-only)

Behavior that must be adjustable **without code changes** is defined in a **YAML file stored in Azure** (reference format: YAML). It is **not** baked into the container image, and **source control is not required**: operators maintain the file **directly in Azure** (for example Azure portal, Storage Explorer, Azure CLI, or scripts using the Storage APIs).

**Preferred delivery to the app:**

- **Azure Files** — mount a file share so the container reads a path such as `/config/app.yaml`.
- **Azure Blob Storage** — alternative: store the YAML in a private container and **download at startup** using the managed identity.

Either pattern uses **DefaultAzureCredential** (or equivalent) for access; permissions are granted via **RBAC on the storage account** to the Container App’s managed identity.

**Typical settings** include (non-exhaustive):

- **Create enablement** — a **global on/off** for creating **new** work items (**P2-FR-11**).
- **Finding filters** — e.g. which **severities** create work items (aligned with **P2-FR-1**), and optional scopes (projects, targets, types).
- **Severity downgrade** — optional **close_on_severity_downgrade**: when enabled, **close** the mapped work item if Snyk severity falls **below** the configured threshold while the issue is still open; when severity returns to policy, the **same** work item is **reopened** (distinct from P2-FR-8 new work item on Snyk fix/reopen).
- **Work item defaults** — work item **type**, **template** or field layout, and default **state** such as Unassigned (**P2-FR-2**).
- **Tags and labels** — default **tags** on created or updated items (**P2-FR-10**).
- **Azure DevOps routing** — organization, project, and team / area path as needed for work item creation.

**Secrets** (tokens, PATs) stay in **Key Vault**; the YAML holds only **non-secret** policy and routing.

**Applying changes:** After the file is updated in **Azure Files** or **Blob**, operators **restart** the Container App or roll a **new revision** so the process **loads configuration at startup**. Hot-reload is out of scope unless added later. For safer rollback without Git, enable **Azure Files share snapshots** and/or **Blob versioning** as an operational practice.
