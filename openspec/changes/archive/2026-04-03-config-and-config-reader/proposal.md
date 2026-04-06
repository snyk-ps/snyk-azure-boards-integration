## Why

The integration needs a single, documented operator contract for non-secret YAML configuration (aligned with `azure-platform` runtime config) and Python code that loads it with sensible defaults and environment overrides. Without this, **P2-FR-11** (global enable/disable for creating new work items) and Snyk-scoped settings (group, severity policy) cannot be implemented consistently or explained in the README.

## What Changes

- Introduce a **YAML configuration file** format with explicit sections: **Azure Boards** (including a global toggle for creating new work items), **work item template** (structural placeholder for future fields), and **Snyk** (severity threshold, group ID; extensible for more keys later).
- Add **`src/config/`** modules to load YAML from a configurable path, apply defaults, merge environment-driven overrides where specified, and expose a typed or structured object for the rest of the application.
- Wire **`argparse`** in **`src/commands/`** (and **`src/main.py`**) so users can pass a config file path (and related flags as needed) without embedding secrets; secrets remain environment-only per project guidelines.
- Document **precedence** for overlapping settings: **`defaults → YAML file → environment variables → CLI arguments`** (CLI wins when the same setting is supplied in multiple places). **Managed YAML** is the intended source of truth for deployed / IaC workflows; **CLI flags** are primarily for **local testing and smoke commands** (explicit one-off overrides).
- Require a resolved **Snyk `group_id`** (non-empty after merge of file, env, and CLI) **before** issuing group-scoped Snyk Issues API calls (including the **`fetch`** smoke command); fetching issues without a group ID is not supported.
- **Fill out the README `Configuration` section** (and parameter descriptions): file format, CLI flags, relevant environment variables, defaults, and examples—without documenting secret values.
- Add a **sample YAML configuration** under **`data/`** (e.g. `data/sample-config.yaml`) with placeholder non-secret values, **committed to git** so developers can copy or point `--config` at it; the repo SHALL **not** gitignore this file (contrast with operator-specific or generated files under `data/` that may stay local-only in future—this sample is intentionally tracked).

## Capabilities

### New Capabilities

- `application-config`: Normative requirements for the YAML shape, loading behavior, defaults, env overrides, and integration with the CLI; maps the global “create new work items” setting to **P2-FR-11** and Snyk section fields to `azure-platform` / Snyk Issues usage.

### Modified Capabilities

- *(none)* — Baseline **P2-FR-*** requirements in `sync-lifecycle` and `azure-platform` already describe operator YAML and **P2-FR-11**; this change specifies the concrete application-level schema and loader behavior without altering those requirement statements.

## Impact

- **Code:** New package under `src/config/`; updates to `src/commands/` and `src/main.py`; `pyproject.toml` / `uv.lock` if a YAML parser dependency is added (YAML is not in the Python standard library).
- **Docs:** README `Configuration` and `Parameter Descriptions` subsections; tracked **`data/`** sample config file.
- **Tests:** New unit tests under `tests/` for public config APIs.
- **Dependencies:** Likely `PyYAML` (or equivalent) subject to Snyk Open Source policy; no secrets in config files.
