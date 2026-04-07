## Context

The product persists a **stable Snyk↔work-item mapping** for **P2-FR-7** / **P2-FR-8** (see `openspec/specs/sync-lifecycle/spec.md`). Production targets **Azure Table Storage** (`openspec/specs/azure-platform/spec.md`). Today, developers and CI lack a **local durable store** without Azure. This change adds **SQLite** as a **logical stand-in** (same columns and uniqueness rules) plus **shared `src/`** access and a **committed init** path under **`scripts/`**.

## Goals / Non-Goals

**Goals:**

- **Idempotent schema creation** via a **git-tracked** script under **`scripts/`** using `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` as needed.
- **Normative mapping row shape**: snake_case columns, all **TEXT**, **UNIQUE (`group_id`, `org_id`, `project_id`, `issue_id`)**, **Snyk status** vs **work item status**, **`created_at` / `updated_at`** as **UTC ISO 8601** strings (e.g. `2026-04-07T14:30:00.000Z`).
- **Explicit `mapping_store`** with allowed value **`sqlite`** now; **`azure_table`** reserved — when selected and the adapter or credentials are missing, **exit non-zero** with a **clear message** (**no fallback** to SQLite).
- **Config resolution** for store and path: **built-in defaults → YAML → environment → CLI**; **later overrides earlier** for the same logical setting.
- **Same path resolution** for the init script and runtime opens the **same file**.
- **Small mapping-store abstraction** in **`src/`** (protocol + SQLite implementation, CRUD) so sync/CLI can depend on one interface; **Azure Table adapter** is a later swap-in.
- **Documentation**: README / sample YAML state that **secrets do not belong** in the SQLite path or mapping DB; tokens/PATs remain env/Key Vault only.

**Non-Goals:**

- **Sync orchestration**: calling Snyk, applying business rules, calling Azure DevOps, or driving the store from a full sync loop.
- **Implementing** the **Azure Table Storage** adapter (beyond **fail-fast** when `mapping_store` is `azure_table`).
- **Hot-reload** of mapping path or backend at runtime.

## Decisions

| Decision | Rationale | Alternatives considered |
|----------|-----------|-------------------------|
| **stdlib `sqlite3`** | Matches project preference; no extra dependency to vet. | SQLAlchemy / aiosqlite — heavier for a dev/test stand-in. |
| **Default `mapping_store` = `sqlite`** | Predictable local/CI behavior without extra YAML. | Require explicit store — more friction for new contributors. |
| **Default `sqlite_path` = `data/mapping_store.sqlite`** (relative path) | Single documented location under `data/`; aligns with existing sample/config layout. | In-memory only — loses persistence across runs; absolute-only — hurts portability. |
| **Init script invokes shared path + schema helpers from `src/`** | Guarantees init and app use **identical** resolution and DDL. | Duplicate DDL only in `.sql` — risk of drift vs Python DDL. |
| **Committed `.sql` file optional** | User asked for script under `scripts/`; a `.sql` beside a thin Python runner keeps DDL reviewable in git while resolution stays in code. | Pure shell + `sqlite3` CLI — path rules duplicated. |
| **Table name `issue_work_item_map`** (or equivalent single name in tasks) | Short, descriptive; one table for this change. | Multiple tables — unnecessary. |
| **UNIQUE on four Snyk scope columns** | Enforces one “current” mapping row per issue in scope (**P2-FR-7**). | Surrogate key only — weaker constraint for duplicates. |
| **ISO 8601 `Z` UTC strings in TEXT** | Human-readable, JSON-friendly, matches user request. | INTEGER epoch — smaller but less inspectable in sqlite CLI. |
| **Fail-fast for `azure_table`** | Avoids silent wrong backend in production-like settings. | Fallback to SQLite — masks misconfiguration. |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **Relative `sqlite_path`** depends on process CWD | Document in README that CLI should be run from repo root (or use absolute paths in CI); optional later improvement: resolve relative to config file location. |
| **SQLite not suitable for multi-writer cloud scale** | Explicitly scoped to **local dev and tests**; production path remains Table Storage in architecture docs. |
| **Drift between script DDL and repository code** | Single source of DDL (shared module or one `.sql` loaded by both script and tests). |

## Migration Plan

- **Developers**: run the new **`scripts/`** init once (or rely on first-run create-if-missing if tasks specify it — prefer explicit init for clarity).
- **CI**: ensure `data/` exists or use a temp path via **`MAPPING_STORE_SQLITE_PATH`** / CLI.
- **Rollback**: revert change; delete local SQLite file if desired (no server migration).

## Open Questions

- Whether **relative `sqlite_path`** should be resolved relative to the **config file directory** vs **cwd** — pick one in implementation and document in README (default proposal: **current working directory** for simplicity unless existing config loader already anchors paths).
