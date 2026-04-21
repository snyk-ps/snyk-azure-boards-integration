## 1. Configuration and documentation

- [x] 1.1 Extend merged config model and loader defaults for `azure_boards.work_item_type`, `work_item_state_active`, and `work_item_state_closed` (non-empty validation at `sync` startup; defaults `Task` / `New` / `Closed`).
- [x] 1.2 Extend `work_item_template` parsing exposure for `tags` (list of strings) and `json_patch` (list of op dicts), preserving unknown keys per existing forward-compatibility rules.
- [x] 1.3 Update `data/sample-config.yaml` with the new keys, defaults, and brief comments that values MUST exist for the target process; extend `work_item_template` example shape as needed.
- [x] 1.4 Update `README.md` Configuration / parameter descriptions for `sync`, new `azure_boards` keys, template `tags` / `json_patch`, and `sync` vs `fetch` group id requirements.

## 2. Snyk normalized records

- [x] 2.1 Add `status` and `ignored` to normalized issue records in `src/snyk/` (list and get paths), with boolean coercion for `ignored` as needed.
- [x] 2.2 Add or extend unit tests asserting normalized output includes `status` and `ignored` for representative JSON:API payloads.

## 3. Mapping store and schema

- [x] 3.1 Ensure SQLite (and mapping abstraction) persists derived `snyk_status` vocabulary (`open` | `resolved` | `ignored`); add idempotent DDL migration / `ALTER` if columns or constraints are missing vs spec.
- [x] 3.2 Implement or extend `MappingStore` upsert by natural key `(group_id, org_id, project_id, issue_id)` and refresh of `work_item_id`, `work_item_status`, `snyk_status`, routing fields, and timestamps on successful observations.
- [x] 3.3 Unit tests for mapping upsert, uniqueness, and field refresh semantics.

## 4. Sync core (`src/sync/`)

- [x] 4.1 Under **`src/sync/`**, implement pure functions for derived `snyk_status` from `status` + `ignored`, unexpected-status detection, and primary-package extraction (first coordinate with `representations[].dependency`); unit tests for edge cases (ignored precedence, unexpected status, missing coordinates).
- [x] 4.2 Under **`src/sync/`**, implement builders for P2-FR-5.x v1 fields (title + package, verbatim type, CWE/CVE extraction, best-effort link without org slug, fix-flag summary) plus `System.Title` length handling if required by Azure limits.
- [x] 4.3 Under **`src/sync/`**, implement JSON Patch assembly for create/update: required `System.Title`; active/closed state transitions using configured state strings; apply `work_item_template.json_patch` and `tags` with ordering per `design.md` (built-in ops then template); omit `System.AssignedTo` unless template supplies it.
- [x] 4.4 Under **`src/sync/`**, implement per-issue loop with non-fail-fast error handling (log, skip, continue) and process exit code policy (`0` on completed loop; non-zero only for global/startup failures).
- [x] 4.5 Under **`src/sync/`**, implement P2-FR-11 branches (no create, no new mapping insert when `create_new_work_items` is false) and P2-FR-8 reopen flow (new WI, old stays closed, mapping upsert to new id, optional prior-id mention in audit comment).
- [x] 4.6 Under **`src/sync/`**, implement P2-FR-9 audit comments on stored vs derived `snyk_status` change, including truncation rules (4000 chars + `[truncated]`).
- [x] 4.7 Under **`src/sync/`**, integrate Azure DevOps get / list-by-ids in chunks ≤200 when reconciling WI existence/state vs mapping; handle missing WI per design default (retain mapping, skip with log unless superseded by spec).

## 5. CLI wiring

- [x] 5.1 Add `sync` argparse subcommand under `src/commands/`, wire `main.py` delegation, construct dependencies (merged config, clients, mapping store), and invoke the run entrypoint implemented under **`src/sync/`** with `SNYK_TOKEN` / `AZURE_DEVOPS_PAT` unchanged from existing env rules.
- [x] 5.2 CLI or unit tests for argument parsing and startup validation paths (missing token, missing group id, empty state strings) without live network where feasible.

## 6. Verification

- [x] 6.1 Run unit test suite via `uv` / project standard; fix regressions.
- [x] 6.2 Manual smoke checklist in PR description: `fetch` still works; `sync` exercised against mock or non-production tenants if available.
