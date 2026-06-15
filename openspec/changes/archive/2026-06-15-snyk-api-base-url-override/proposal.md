## Why

Snyk is hosted in multiple regions, each with its own API host (for example `https://api.us.snyk.io` for **SNYK-US-02**). This integration currently assumes the **SNYK-US-01** default host (`https://api.snyk.io`) for all Snyk HTTP calls. Tokens scoped to a non-default region often fail with **401** when sent to the wrong host. Production deployments on **Azure Container Apps** need a documented, env-first way to set the correct regional API origin without code changes.

## What Changes

- Introduce a configurable **Snyk API origin** (default **`https://api.snyk.io`**, region **SNYK-US-01**). The application SHALL derive:
  - **REST** base URL: `{origin}/rest` (no trailing slash after normalization)
  - **V1** base URL: `{origin}/v1` (for any V1 client or future use; same origin)
- Support override via:
  1. **`SNYK_API_BASE_URL`** environment variable (**recommended for Azure Container App Job deployments**)
  2. **`snyk.api_base_url`** in operator YAML
  3. CLI flags on commands that call Snyk (`sync`, `fetch`, and alignment with existing `--base-url` on `generate_org_mapping_config.py`)
- Wire merged configuration into **`IssuesClient`** construction for **`sync`** and **`fetch`** (today they always use the hard-coded default).
- Centralize origin → REST/V1 derivation in **`src/snyk/`** (shared with org-config generator).
- Update **`README.md`**, **`CONFIGURATION.md`**, sample YAML, and **`openspec/config.yaml`** context to document defaults, regional lookup link, and troubleshooting for **401** + wrong base URL.

**Non-goals**

- Changing **`app.snyk.io`** UI link composition (remains separate from API host).
- Auto-detecting region from the token.
- Hot-reload of config on Azure Files.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- **`application-config`**: New **`snyk.api_base_url`**, **`SNYK_API_BASE_URL`**, CLI override, precedence, validation, README/CONFIGURATION/sample requirements.
- **`integration-apis`**: Document regional API hosts, default **SNYK-US-01**, and that REST/V1 paths are rooted at the configured origin.
- **`snyk-issues-client`**: Production (not test-only) base URL from merged config; default remains **`https://api.snyk.io/rest`** derived from default origin.
- **`csv-snyk-org-config-generator`**: Use the same origin/REST derivation helper; document env/YAML parity where applicable.

## Impact

- **Code:** `src/snyk/constants.py` or `src/snyk/urls.py` (origin helpers), `src/config/` (model + loader + env), `src/commands/sync.py`, `src/commands/fetch.py`, `src/org_config_generator/core.py`, tests.
- **Docs:** `README.md`, `CONFIGURATION.md`, `data/sample-config.yaml`, `openspec/config.yaml` context line.
- **Deploy:** Operators in non-US-01 regions set **`SNYK_API_BASE_URL`** on the Container App Job (non-secret env var alongside Key Vault **`SNYK_TOKEN`**).
