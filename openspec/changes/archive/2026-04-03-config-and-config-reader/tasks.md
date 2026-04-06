## 1. Dependencies and packaging

- [x] 1.1 Add a YAML library dependency (e.g. `pyyaml`) via **uv**, update `uv.lock`, and run **Snyk Open Source** (and **Snyk Code** on new code) before merge per project guidelines.
- [x] 1.2 Extend `pyproject.toml` / hatch **`packages`** (and sdist/wheel includes if needed) so `src/config/` is part of the built package.

## 2. Configuration module (`src/config/`)

- [x] 2.1 Implement YAML loading from a filesystem path with clear errors for missing file, permission errors, and invalid YAML (no secrets in messages).
- [x] 2.2 Define the documented schema: `azure_boards.create_new_work_items` (bool, default `true`), `work_item_template` (mapping, default empty), `snyk.group_id` (str), `snyk.severity_threshold` (ordered levels, default `high`); allow forward-compatible handling of extra `snyk` keys per design.
- [x] 2.3 Implement defaults and merge order **defaults → YAML file → environment → CLI** for documented keys (path + selected fields such as `snyk.group_id`); **CLI wins** on conflict; document supported override env vars in README.
- [x] 2.4 Add **unit tests** for public/protected helpers: defaults, parsing, invalid YAML, full precedence chain (file vs env vs CLI), boolean/severity edge cases, and **missing `group_id`** when resolving for a command that requires it.

## 3. CLI wiring (`src/commands/`, `src/main.py`)

- [x] 3.1 Add **`--config`** (path) to the argparse surface in `src/commands/` and plumb **merged** config (defaults + file + env + CLI) into command handlers; for **`fetch`**, resolve **`group_id`** per precedence and **fail clearly** if empty; ensure **`--help`** does not require config or `group_id`.
- [x] 3.2 Ensure `src/main.py` remains the entry point and help text documents the config option and override behavior where relevant.

## 4. Documentation and sample file

- [x] 4.1 Add a **sample YAML** under **`data/`** (e.g. `data/sample-config.yaml`) with placeholder non-secret values matching the schema; **commit** it and confirm **`.gitignore`** does **not** ignore this path (the sample must stay tracked).
- [x] 4.2 Fill **`README.md`** `Configuration` and **`Parameter Descriptions`**: YAML sections, optional omissions and defaults, **precedence** (**defaults → file → env → CLI**), IaC vs local CLI overrides, **`group_id`** required for Snyk fetch, CLI flags, env vars, reference to the **`data/`** sample path, example snippet or pointer to the sample file (no secrets), and pointer to non-secret policy.

## 5. Verification

- [x] 5.1 Run **`uv run pytest`** and fix any regressions; ensure new code paths are covered by tests.
