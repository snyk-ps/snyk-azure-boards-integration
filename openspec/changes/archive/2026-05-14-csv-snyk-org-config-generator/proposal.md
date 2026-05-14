## Why

Operators who use **org-scoped sync** (`azure_boards.org_mappings`) need accurate **`snyk_org_id`** and **`snyk_org_slug`** per Azure DevOps org/project row. Looking these up manually in the Snyk UI or by paging through APIs is slow and error-prone. A small CLI script that reads a CSV of ADO targets plus Snyk org **names**, calls the [Snyk REST API list orgs for a group](https://apidocs.snyk.io/?version=2024-03-12#get-/groups/-group_id-/orgs) (version `2024-03-12`), and emits a starter **`config.yaml`** reduces onboarding friction and keeps generated files aligned with `data/sample-config.yaml` / `data/config.local.org.yaml` shapes.

## What Changes

- Add a **Python CLI** under **`scripts/`** (per project Python guidelines: `argparse`, **Python 3.12+**, **`SNYK_TOKEN`** from environment only, no token logging).
- **Input**: path via **`--input`** to a CSV with headers **`ado_organization`**, **`ado_project`**, **`snyk_org_name`**.
- **Snyk**: **`--group-id`** (UUID) passed on CLI; script calls `GET {base}/groups/{group_id}/orgs` with **`limit=100`**, follows **pagination** until all orgs for the group are retrieved (per API contract for that version).
- **Resolution**: Match each CSV row’s **`snyk_org_name`** to an org in the aggregated API response to fill **`snyk_org_id`** and **`snyk_org_slug`** for **`azure_boards.org_mappings`**.
- **Output**: write **`config.yaml`** (default path **`data/config.yaml`**), overridable via **`--output`**, with:
  - **`azure_boards.org_mappings`** populated from CSV + resolved Snyk fields.
  - **`azure_boards.defaults`**: **present but empty of applied values**; include **commented sample lines** mirroring `data/sample-config.yaml` style so operators fill policy deliberately.
  - **`snyk.group_id`**: set from the user-supplied **`--group-id`**.
  - **`mapping_store`**: emit **`azure_table`** as the documented choice with **related keys commented** (or commented block) so SQLite remains the obvious dev default until uncommented—matching the request to use Azure Table **commented out** for the mapping store section.

## Capabilities

### New Capabilities

- **`csv-snyk-org-config-generator`**: Requirements and scenarios for the CSV-driven config generator CLI (inputs, API usage, pagination, matching rules, output YAML shape, errors, testing expectations).

### Modified Capabilities

- _(None.)_ Generated YAML must remain valid per existing **`application-config`**; this change does not alter loader or runtime behavior.

## Impact

- **New files**: `scripts/` module(s) and tests for public surfaces; no change to sync runtime unless documented separately.
- **Dependencies**: Prefer **stdlib**; any HTTP client dependency must pass Snyk Open Source / Snyk Code policy before merge.
- **Secrets**: **`SNYK_TOKEN`** only via environment; script documents required scope for group org listing.
- **Non-goals**: No integration with **`sync`** command; no hot-reload; no writing secrets into YAML; no automatic ADO validation.
