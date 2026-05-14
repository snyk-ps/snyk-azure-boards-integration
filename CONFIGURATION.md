# Configuration reference

Operator reference for YAML policy, environment variables, and CLI commands. For installation, container images, and Azure deployment, see the [README](README.md). Release images and tags: **[snyk-azure-boards-integration on GitHub Packages](https://github.com/snyk-ps/snyk-azure-boards-integration/pkgs/container/snyk-azure-boards-integration)**.


Operator settings use a **YAML** file (non-secret policy only). **Secrets** (`SNYK_TOKEN`, Azure DevOps PAT, etc.) **must** come from environment variables or your secret store. **Never** commit them in YAML. The shipped container image **defaults** to **`sync --config /config/config.yaml`**; **`SNYK_APP_CONFIG`** or CLI **`--config`** still follow the precedence below.

## Precedence

When the same logical setting exists in more than one place, the effective value is resolved in this order (**later wins**):

1. Built-in defaults  
2. YAML configuration file  
3. Environment variables (documented below)  
4. **CLI arguments** (highest precedence; useful for local smoke tests without editing files)

For **deployments and IaC**, keep authoritative values in **YAML** (or platform-injected environment). Use **CLI overrides** mainly for **local development** and one-off commands.

## Configuration file: top-level keys

| Key | Purpose |
| --- | ------- |
| `azure_boards` | **`defaults`** holds your main Boards and sync policy: Azure DevOps **organization** and **project**, work item type and states, severity and origin filters, and related options. Use this when everything goes to one Boards project, or as the shared baseline for multi-target sync. **`org_mappings`** is optional: a list where each entry links one **Snyk org** to a specific Azure DevOps org/project and can supply **overrides** (partial **`defaults`** for that row only), so one **`sync`** can push different Snyk orgs to different Boards targets. |
| `work_item_template` | Optional global template (merged with **`defaults.work_item_template`** and per-mapping overrides). |
| `snyk` | Snyk **`group_id`** (Snyk Group UUID). **Always set**; see **[snyk](#snyk)**. |
| `mapping_store` | `sqlite` or `azure_table`. |
| `sqlite_path` | SQLite file path when **`mapping_store`** is **`sqlite`**. |
| `mapping_store_azure_table_endpoint` | HTTPS Table endpoint when **`mapping_store`** is **`azure_table`**. |
| `mapping_store_azure_table_name` | Table name when **`mapping_store`** is **`azure_table`**. |

Sections may be omitted where defaults apply. A full example is in **`data/sample-config.yaml`**.

## azure_boards.defaults

| Subkey | Type / values | Default (if any) | Notes |
| ------ | ------------- | ---------------- | ----- |
| `organization` | string | `""` | Azure DevOps organization (non-secret). Required for **`azure-devops-smoke`** and **`sync`** when **`org_mappings`** is empty. |
| `project` | string | `""` | Azure DevOps project name or id. Same requirements as **`organization`**. |
| `create_new_work_items` | boolean | `true` | When `false`, **`sync`** does not create new work items or new mapping rows for eligible unmapped issues; updates/closes still apply for existing mappings. |
| `severity_threshold` | `low` \| `medium` \| `high` \| `critical` | `high` | Maps to Snyk **`effective_severity_level`** filtering. Not valid under **`snyk`**. |
| `sync_included_snyk_origins` | string (comma-separated tokens) | (omit = all) | Inclusive allowlist of Snyk project [origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin) values. |
| `issues_sync_from` | `historical` or ISO-8601 timestamp | `historical` | Which issues are in scope for sync. |
| `create_only_when_fix_available` | boolean | `false` | When `true`, skip creating work items unless a fix is indicated. |
| `reopen_work_item_policy` | `new_work_item` \| `reopen_existing` | `new_work_item` | When a Snyk issue **reopens** (resolved or ignored back to **open**). **`new_work_item`** always creates a **new** Azure Boards work item, updates the mapping to that id, and adds an audit comment that references the previous work item when one existed. **`reopen_existing`** transitions the **existing** mapped work item back to the active state when Azure DevOps still returns it; if that work item no longer exists (**404**), **`sync`** creates a new work item and updates the mapping (same as **`new_work_item`** for that case). |
| `work_item_type` | string | `Task` | Work item type name for creates; must exist in your process. |
| `work_item_state_active` | string | `New` | **`System.State`** for active findings. |
| `work_item_state_closed` | string | `Closed` | **`System.State`** when **`sync`** closes on resolved/ignored. |
| `work_item_description_appendix` | string | `""` | Optional **appendix**: your own plain text, added **at the end** of the work item description **after** the auto-generated Snyk content (finding info and links). **`sync`** turns the full description into HTML for Azure DevOps; this text is **escaped** as plain text, not treated as HTML. If you omit the key or the value is only whitespace after trim, nothing extra is added. You can set a different appendix per **`org_mappings`** row via **`overrides`**. Use for runbooks or notes, **not** secrets. |
| `work_item_template` | object | (see below) | **`tags`**, optional **`json_patch`**; see **`work_item_template`**. |

## `azure_boards.org_mappings` (each entry)

| Subkey | Required | Notes |
| ------ | -------- | ----- |
| `organization` | yes | Azure DevOps org for this row. |
| `project` | yes | Azure DevOps project for this row. |
| `snyk_org_id` | yes (for org-scoped listing) | Snyk organization UUID for this target. |
| `snyk_org_slug` | yes | Non-empty slug for **`app.snyk.io`** links in work items. |
| `overrides` | no | Partial **`defaults`** override (severity, origins, **`work_item_*`**, **`work_item_template`**, etc.). |

When **`org_mappings`** is non-empty, **`sync`** lists issues with the **org**-scoped Snyk API using each row’s **`snyk_org_id`**. Always set **`snyk.group_id`** to your Snyk **Group** UUID: it is the **mapping store namespace** for every row (Azure Table **`PartitionKey`** / SQLite **`group_id`** column). Issue **detail** GETs in this mode use the org API.

### Generating `org_mappings` from a CSV

For many Snyk orgs, you can start from a CSV with columns **`ado_organization`**, **`ado_project`**, and **`snyk_org_name`** (human-readable Snyk org name), then resolve **`snyk_org_id`** and **`snyk_org_slug`** via the Snyk REST [list orgs in group](https://apidocs.snyk.io/?version=2024-03-12#get-/groups/-group_id-/orgs) API. Run (from the repo root, with **`SNYK_TOKEN`** set):

`uv run python scripts/generate_org_mapping_config.py --input path/to/mappings.csv --group-id <your-group-uuid>`

The default output is **`data/config.yaml`** (overwritten if present); use **`--output`** to choose another path. Review the generated **`azure_boards.defaults`** and **`mapping_store`** comments before deploying. Details: **`python scripts/generate_org_mapping_config.py --help`**.

## work_item_template

Applies at **root** `work_item_template`, under **`azure_boards.defaults.work_item_template`**, and under **`org_mappings[].overrides.work_item_template`**. Merge order: defaults, root template, per-mapping overrides (**`json_patch`** lists concatenate).

| Subkey | Purpose |
| ------ | ------- |
| `tags` | List of operator-defined tag strings (managed Snyk tags are added separately; see [Work item tags](#work-item-tags)). |
| `json_patch` | JSON Patch operations applied on **`sync`** create/update (for example **`/fields/System.AssignedTo`** in Azure DevOps identity format). May be `[]` or omitted. |

## snyk

| Subkey | Purpose |
| ------ | ------- |
| `group_id` | Snyk **Group** UUID for the group that contains your organizations. **Always configure** **`snyk.group_id`** (YAML, env **`SNYK_GROUP_ID`**, or **`--group-id`** on **`sync`** / **`fetch`**). It is required for **`sync`** and group-scoped **`fetch`**, and it is the **mapping store partition** (**`PartitionKey`** / **`group_id`** column) for every issue. With **`org_mappings`**, **listing** uses each row’s **`snyk_org_id`**, but **`snyk.group_id`** is still **always** set for storage and for group-scoped API use. **`snyk.severity_threshold` is not supported** (use **`azure_boards.defaults.severity_threshold`**). Do **not** put **`snyk_org_slug`** here. |

## Mapping store (`mapping_store`, SQLite, Azure Table)

| Key / setting | Values | Notes |
| ------------- | ------ | ----- |
| `mapping_store` | `sqlite` (default) \| `azure_table` | Where issue-to-work-item state is stored. No silent fallback if **`azure_table`** is selected. |
| `sqlite_path` | filesystem path | Default `data/mapping_store.sqlite`. Ignored when **`azure_table`**. |
| `mapping_store_azure_table_endpoint` | HTTPS URL | Example: `https://<account>.table.core.windows.net`. Required for **`azure_table`** (YAML or **`MAPPING_STORE_AZURE_TABLE_ENDPOINT`**). |
| `mapping_store_azure_table_name` | string | 3 to 63 alphanumeric characters, starts with a letter. Required for **`azure_table`** (YAML or **`MAPPING_STORE_AZURE_TABLE_NAME`**). |

## Work item tags

- **`work_item_template.tags`** supply **operator** strings. They appear **first**, in merged-template order (**defaults** → **`overrides`**, deduped as documented for templates).
- **`sync`** also writes up to **two managed tags** on each work item **create** and **update** (when Boards is changed), using the current issue: **severity** as **`Snyk-Severity-*`** from **`effective_severity_level`**, and **finding type** as **`Snyk-Type-*`** from **`attributes.type`**. If Snyk’s type is not one the integration maps, there is no managed type tag for that issue.
- **Reserved prefixes:** do **not** use **`Snyk-Severity-*`** or **`Snyk-Type-*`** in YAML `tags`. If present, **`sync`** **omits** them from the operator list and applies canonical values from Snyk so reporting stays truthful.
- If there are **no** operator tags and **nothing** derivable from the issue, **`sync`** does **not** send a **`System.Tags`** patch (so it does **not** clear existing tags solely for absence of YAML tags).

## Local SQLite (init script)

From the repository root:

```bash
uv run python scripts/init_mapping_store.py --config data/sample-config.yaml
```

(or pass `--mapping-store-sqlite-path /path/to/file.sqlite`). The script is idempotent and uses the same `sqlite_path` resolution as the app (**defaults → YAML → env → CLI**). The physical table is **`issue_work_item_map`**.

## Acceptable `sync_included_snyk_origins` values

Tokens must match exactly; the catalog aligns with [Snyk Origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin) plus `github-cloud-app` and `github-server-app`:

`acr`, `api`, `artifactory-cr`, `aws-config`, `aws-lambda`, `azure-functions`, `azure-repos`, `bitbucket-cloud`, `bitbucket-server`, `cli`, `cloud-foundry`, `digitalocean-cr`, `docker-hub`, `ecr`, `gcr`, `github`, `github-cloud-app`, `github-cr`, `github-enterprise`, `github-server-app`, `gitlab`, `gitlab-cr`, `google-artifact-cr`, `harbor-cr`, `heroku`, `ibm-cloud`, `kubernetes`, `nexus-cr`, `pivotal`, `quay-cr`, `terraform-cloud`

## Mapping row columns (`issue_work_item_map`)

| Column | Meaning |
| ------ | ------- |
| `group_id` | Snyk **Group** id from **`snyk.group_id`** (always set in configuration); same value as Azure Table **`PartitionKey`**. |
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
| `excluded` | When `true`, **`sync`** treats the issue as **origin-excluded** (**`sync_included_snyk_origins`** allowlist): no Azure Boards create/update/close/comment for that run. |
| `exclusion_reason` | When **`excluded`** is `true`, a stable reason (for example **`origin_unknown`**, **`origin_not_in_allowlist`**); otherwise empty. |
| `created_at` | UTC timestamp when the mapping row was created. |
| `updated_at` | UTC timestamp when the mapping row was last updated. |

## Environment variables

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

## Azure DevOps personal access token (PAT)

The integration calls Azure DevOps REST APIs using a **personal access token (PAT)**. **Do not** commit a PAT to version control or store it in YAML; set it only via the **`AZURE_DEVOPS_PAT`** environment variable. For production, inject the value from your secret store into the process environment (for example Azure Key Vault backing app settings); see [Deployment](README.md#deployment).

**Create a PAT**

1. Open **[Azure DevOps](https://dev.azure.com)** and sign in to the organization you use with this project.
2. Open **User settings** from your profile menu (avatar or initials in the upper-right corner).
3. Select **Personal access tokens**.
4. Choose **+ New Token** (or **New Token**).
5. Enter a name, pick the organization (or **All accessible organizations** if your policy allows), set an expiration, then under **Scopes** grant the **Work Items** permission listed below.

**Required scope**

Set **Work Items** to **Read & write** (Azure DevOps may label this **Work Items: Read & write**, **Work items (read & write)**, or similar; wording varies by portal version).

That one scope covers everything in this repository:

- **`sync`**: reads work items when reconciling state; **creates** and **updates** work items (fields, state, tags); **adds comments** on status changes where applicable.
- **`azure-devops-smoke`**: **reads** a single work item to verify connectivity and auth (read is included in **Read & write**).

If your dialog uses different labels, pick the option that allows both reading and changing work items, and confirm against [Microsoft’s PAT documentation](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate?view=azure-devops) (Microsoft Learn).

## The `sync` command

The **`sync`** command runs one reconciliation pass: it lists issues from the Snyk Issues API using **`snyk.group_id`** (**group** scope) when **`azure_boards.org_mappings`** is absent or empty; when **`org_mappings`** is non-empty, it lists issues per configured **`snyk_org_id`** (**org** scope) and routes Azure DevOps calls to each row’s **`organization`** / **`project`** with **`defaults`** merged with that row’s **`overrides`**. List calls use **`effective_severity_level`** derived from **`azure_boards.defaults.severity_threshold`**. When **`sync_included_snyk_origins`** is set (merged per mapping), only issues whose Snyk project **origin** is in that **inclusive** list receive Boards mutations; other issues are still written to the mapping store with **`excluded`** / **`exclusion_reason`**. It reads or writes rows in the mapping store and creates, updates, or closes Azure Boards work items via **`AZURE_DEVOPS_PAT`** (create/update/comment scope) for **non-excluded** issues. If you widen the allowlist (or an issue becomes eligible) and a row already exists with **no** Azure **`work_item_id`** (for example it was only ever persisted as excluded), **`sync`** **creates** a work item for **open** issues under the same rules as when no row exists (**`create_new_work_items`** and related gates still apply).

**Secrets** (`SNYK_TOKEN`, `AZURE_DEVOPS_PAT`) must be set in the environment, not in YAML. After merge, **`sync`** requires a non-empty **`snyk.group_id`** (always: YAML **`snyk.group_id`**, **`SNYK_GROUP_ID`**, or **`--group-id`**) and non-empty **`azure_boards.defaults.work_item_type`** (mirrored on **`azure_boards.work_item_type`**), **`work_item_state_active`**, and **`work_item_state_closed`** (defaults apply when omitted). **`snyk.group_id`** is the **mapping store partition** (**`PartitionKey`** / **`group_id`** column) for every issue. When **`org_mappings`** is **not** used, **`sync`** also requires **`azure_boards.defaults.organization`** and **`azure_boards.defaults.project`** (effective values are mirrored on **`azure_boards.organization`** / **`project`**). When **`org_mappings`** **is** used, each row **must** include **`snyk_org_slug`** (non-empty) so work items get valid Snyk UI links.

When **`azure_boards.defaults.create_new_work_items`** is **`false`** (mirrored on **`azure_boards.create_new_work_items`**), **`sync`** does **not** create new work items or insert new mapping rows for **eligible** (non-origin-excluded) unmapped issues (**no row** or **empty** **`work_item_id`**); it still updates or closes work items that already have a mapping. Origin-excluded issues may still receive a persistence row with **`excluded`** set for reporting.

```bash
export SNYK_TOKEN="***"
export AZURE_DEVOPS_PAT="***"
uv run python src/main.py sync --config data/sample-config.yaml
```

Use **`--group-id`** to override `snyk.group_id` for one invocation. **`--mapping-store-sqlite-path`** overrides the SQLite mapping database path. Run **`uv run python src/main.py sync --help`** for the full flag list.

## `azure-devops-smoke` command

The **`azure-devops-smoke`** command performs a **single read-only** `get_work_item` call to validate connectivity, authentication, and response parsing. It reads **`azure_boards.defaults.organization`** and **`azure_boards.defaults.project`** from merged configuration (YAML and/or `AZURE_BOARDS_ORGANIZATION` / `AZURE_BOARDS_PROJECT`) and requires **`AZURE_DEVOPS_PAT`** in the environment (**do not** pass the PAT on the command line).

Example:

```bash
export AZURE_DEVOPS_PAT="***"
uv run python src/main.py azure-devops-smoke --config data/sample-config.yaml --work-item-id 12345
```

Run **`uv run python src/main.py azure-devops-smoke --help`** for flags. This command does **not** create, update, or add comments by default.

## `fetch` command and Snyk group or org id

**Configuration for this integration always includes **`snyk.group_id`** (Snyk Group UUID), same as **`sync`**.

The **`fetch`** smoke command calls the Snyk Issues API (**group** or **org** scope). For **group-scoped** list/get, supply a non-empty **group id** after merging YAML, **`SNYK_GROUP_ID`**, and CLI (**`--group-id`**, or **`fetch list`** / **`fetch get`** positional forms as documented in **`fetch --help`**).

For **org-scoped** **`fetch`** only, you may pass **`--org-id`** (`fetch list --org-id <uuid>`, **`fetch get --org-id <uuid> <issue_id>`**) so that command can call the API without a merged group id. **Do not** use that as a pattern for **`sync`**: **`sync`** always requires **`snyk.group_id`**.

If both group id and **`--org-id`** are missing after merge, **`fetch`** exits with an error before calling the API. Run **`uv run python src/main.py fetch --help`** for the full layout.

**`fetch`** also accepts **`--mapping-store-sqlite-path`** so you can override the SQLite mapping file path for that process without editing YAML.

