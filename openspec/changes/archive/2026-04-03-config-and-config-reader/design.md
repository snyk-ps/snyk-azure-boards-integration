## Context

The product loads **non-secret operator YAML** from a file path (local dev or Azure Files/Blob mount at runtime per `openspec/specs/azure-platform/spec.md`). The codebase today has CLI wiring under `src/commands/` and `src/main.py` but no shared configuration module. **P2-FR-11** requires a configurable global switch for creating **new** Azure Boards work items; **P2-FR-1** and operator docs reference severity and Snyk **group** scoping.

## Goals / Non-Goals

**Goals:**

- Define a **stable top-level YAML shape** with sections: `azure_boards` (including `create_new_work_items`), `work_item_template` (placeholder mapping for future work item type / field defaults), and `snyk` (`group_id`, `severity_threshold`, extensible). Sections or keys **MAY be omitted** in the file where **defaults** apply (see spec); the **full** shape appears in README and the **`data/`** sample so operators can copy an explicit document.
- Implement **load → defaults → environment overrides → CLI overrides → validated / resolved values** in `src/config/` (or a single resolution step used by commands), with clear errors for missing required fields or invalid values when a command runs (no secret material in error paths). **Help-only** invocations (e.g. `--help`) SHALL NOT require a full config load or a present `group_id`.
- Expose config to commands via **argparse** (e.g. `--config` path) from `src/commands/`; keep **`src/main.py`** as the entrypoint that dispatches subcommands.
- Update **README** configuration documentation to match the implementation.
- Ship a **sample configuration file** under **`data/`** (filename TBD in implementation, e.g. `data/sample-config.yaml`) containing only **placeholder** policy values (no secrets). The file SHALL be **version-controlled** and SHALL **not** be listed in **`.gitignore`** (or any ignore rule that would exclude it), so clones always include a copy-paste starting point for local runs (`--config data/sample-config.yaml` or similar).

**Non-Goals:**

- **Hot-reload** of YAML after process start (out of scope per `azure-platform`; restart/revision reloads config).
- **Azure Blob download** or **Key Vault** secret retrieval for config body (secrets stay in env/Key Vault; config file path may still be passed via env).
- **Full work item template semantics** (only structural placeholder keys / empty object allowed until a later change).
- **Persisting** config to Table Storage or merging with Azure DevOps process metadata beyond what YAML provides.

## Decisions

1. **YAML parsing dependency**  
   Python’s standard library does not parse YAML. **Decision:** Add **`PyYAML`** (package name `pyyaml` on PyPI) as a direct dependency, install via **uv**, and run **Snyk Open Source** before merge.  
   **Alternatives:** `ruamel.yaml` (heavier API); hand-rolled subset (unsafe and out of scope).

2. **Top-level YAML keys**  
   Use **`azure_boards`**, **`work_item_template`**, and **`snyk`** as documented sections. **`azure_boards.create_new_work_items`** SHALL be a boolean defaulting to `true` unless overridden (when `false`, creation of **new** work items is disabled—**P2-FR-11**).  
   **Alternatives:** Flat root keys—rejected to keep namespaces clear for future Azure vs Snyk settings.

3. **Snyk section**  
   - **`group_id`**: string (Snyk group UUID as used by the Issues API). **Required** for any code path that calls the **group-scoped** Snyk Issues API (list/get by group), including the **`fetch`** command—after merging file, env, and CLI, the resolved value MUST be non-empty or the command SHALL fail with a clear error.  
   - **`severity_threshold`**: ordered enum (e.g. `low` < `medium` < `high` < `critical`) representing the **minimum** severity for policy; default **`high`** to align with **P2-FR-1** (High/Critical). Exact string set and comparison rules belong in the spec; implementation uses one canonical ordering.  
   **Alternatives:** Free-form string without validation—rejected for predictable behavior.

4. **`work_item_template` section**  
   Represent as a **mapping** (YAML dict). MAY be empty `{}`. Reserved for future keys (e.g. work item type, area path). No required inner keys in this change.

5. **Environment overrides**  
   Support a small, documented set of env vars that override YAML for CI/ops (e.g. path to config file, optional boolean override for `create_new_work_items`, optional `SNYK_GROUP_ID` if aligned with common env naming). **Secrets** (`SNYK_TOKEN`, PAT) remain **only** in environment variables, never in YAML.  
   **Alternatives:** Env-only config with no file—rejected; `azure-platform` expects Azure-hosted YAML.

6. **Precedence: defaults, file, env, CLI**  
   **Decision:** For settings that can appear in more than one layer, resolve in order: **built-in defaults → YAML file → environment variables → CLI arguments**; **CLI wins** when the same key is set at multiple layers (explicit override for the current process). **Operational intent:** operators manage **YAML** (and platform env) as **IaC** / runtime policy; **CLI** is for **local development and smoke testing** (quick overrides without editing files). Document this in README.  
   **Alternatives:** Config always overrides CLI—rejected for local ergonomics; CLI-only production—rejected for Azure-mounted YAML.

7. **Package layout**  
   - `src/config/`: loader, defaults, merge with env and CLI, validation helpers.  
   - `src/commands/`: argparse definitions that accept `--config` and pass resolved values into command handlers.  
   - `src/main.py`: builds parser, dispatches.

8. **Build packaging**  
   Extend **`pyproject.toml`** / hatch **`packages`** to include `src/config` when implementing (so wheels include the new package).

9. **Sample config location**  
   **Decision:** Add the reference sample under **`data/`** alongside other local fixtures per README layout; keep it tracked in git. **Alternatives:** `examples/` at repo root—rejected in favor of the documented `data/` convention for sample inputs.

## Risks / Trade-offs

- **[Risk]** Adding `PyYAML` increases supply-chain surface → **Mitigation:** Pin in `uv.lock`, scan with Snyk, keep version current.  
- **[Risk]** Env and CLI overrides duplicate YAML keys and confuse operators → **Mitigation:** Document the full **defaults → file → env → CLI** chain in README; state that **YAML is the long-term source** for deployments and CLI is primarily for local overrides.  
- **[Risk]** `severity_threshold` vs **P2-FR-1** mismatch if misconfigured → **Mitigation:** Default to `high`; document that lower thresholds may create items below historical High/Critical-only behavior when sync logic honors the threshold.

## Migration Plan

- **Deploy:** Ship new YAML schema and loader; operators add or generate config files alongside existing env secrets; no database migration.  
- **Rollback:** Revert application revision; keep prior YAML compatible by accepting omitted optional sections with defaults.

## Resolved decisions

- **`group_id`:** Not required to **parse** YAML or to show **`--help`**. **Required** when executing a command that performs **group-scoped Snyk Issues** HTTP calls (e.g. **`fetch`**): the merged value from file, env, and CLI MUST be non-empty; otherwise fail fast with a clear error.
