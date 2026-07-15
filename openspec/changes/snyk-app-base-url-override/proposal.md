## Why

Operators in non-**SNYK-US-01** regions must use regional Snyk **web app** URLs to open issues in the product UI (for example `https://app.us.snyk.io`, `https://app.eu.snyk.io`). This integration already supports overriding the **API** origin via `SNYK_API_BASE_URL` / `snyk.api_base_url`, but work item **"Open in Snyk"** links are still hard-coded to **`https://app.snyk.io`**. That produces broken or wrong-region deep links in Azure Boards descriptions for EU, US-02, AU, Gov, and other tenants.

## What Changes

- Introduce a configurable **Snyk web app origin** (default **`https://app.snyk.io`**, region **SNYK-US-01**). Work item issue links SHALL use:
  - **`{app_base_url}/org/{snyk_org_slug}/project/{project_id}#issue-{issue_key}`**
- Support override via (same precedence as other settings):
  1. **`SNYK_APP_BASE_URL`** environment variable (**recommended for Azure Container App Job deployments**)
  2. **`snyk.app_base_url`** in operator YAML
  3. CLI flag **`--snyk-app-base-url`** on **`sync`**
- Wire merged configuration into **`snyk_ui_issue_url`**, description assembly, and the **"Open in Snyk"** HTML branch in **`patch_build`** (today it checks for a hard-coded `https://app.snyk.io/` prefix).
- Update **`README.md`**, **`CONFIGURATION.md`**, and **`data/sample-config.yaml`** with the new setting, defaults, regional lookup link, and note that **`SNYK_APP_BASE_URL`** is independent of but should align with **`SNYK_API_BASE_URL`** for regional tenants.

**Non-goals**

- Auto-deriving **`app_base_url`** from **`api_base_url`** (operators set both explicitly when needed).
- Changing link **path** or **fragment** shape (still org / project / `#issue-{key}` per **P2-FR-5.4**).
- Adding the override to **`fetch`** (no work item link composition).
- Hot-reload of operator YAML on Azure Files.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- **`application-config`**: New **`snyk.app_base_url`**, **`SNYK_APP_BASE_URL`**, CLI override on **`sync`**, precedence, validation, README/CONFIGURATION/sample requirements.
- **`sync-lifecycle`**: **P2-FR-5.4** canonical URL uses configurable app origin instead of a fixed **`app.snyk.io`** host; **"Open in Snyk"** HTML behavior preserved for the configured host.

## Impact

- **Code:** `src/snyk/constants.py` or `src/snyk/urls.py` (default app origin helper), `src/config/` (model + loader + env), `src/commands/sync.py`, `src/sync/issue_content.py`, `src/sync/patch_build.py`, `src/sync/run.py`, tests.
- **Docs:** `README.md`, `CONFIGURATION.md`, `data/sample-config.yaml`, optional one-line note in `openspec/config.yaml` context.
- **Deploy:** Operators in non-US-01 regions set **`SNYK_APP_BASE_URL`** alongside **`SNYK_API_BASE_URL`** on the Container App Job (both non-secret).
