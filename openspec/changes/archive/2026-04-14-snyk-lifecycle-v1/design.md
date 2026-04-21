## Context

The repository already exposes a **Snyk issues client** (list/get, normalized records, severity filters), an **Azure DevOps client** (JSON Patch create/update, get, list-by-ids ≤200, comments), **application configuration** (YAML merge, `azure_boards`, `work_item_template`, `snyk`, mapping store), and a **mapping store** abstraction with a SQLite backend for local use. **P2-FR-*** requirements exist at a high level in `openspec/specs/sync-lifecycle/spec.md`, but there is no single **testable sync run** that wires these pieces with explicit Snyk **Issues API** lifecycle semantics (`attributes.status`, `attributes.ignored`), a persisted **derived `snyk_status`**, and Boards **state** transitions driven by operator config.

## Goals / Non-Goals

**Goals:**

- One **sync run** entry point (argparse subcommand under `src/commands/`, `main.py` delegates) with **constructor injection** of merged config, `SNYK_TOKEN` / `AZURE_DEVOPS_PAT` (read only by existing client rules), Snyk client, Azure DevOps client, and `MappingStore` — **no new secret sources**.
- **Normative inputs** from Snyk list response: lifecycle from `data[].attributes.status` and `data[].attributes.ignored` only; **`coordinates[].state`** ignored for open/close/reopen policy.
- **Derived `snyk_status`** (single stored string): `ignored` if `ignored == true`; else `resolved` if `status == "resolved"`; else `open` if `status == "open"` and `ignored == false`; else **skip** issue with **error** log including unexpected `status` (no secrets).
- **Work item actions**: create (when allowed), update fields/tags, transition to **active** state (`azure_boards.work_item_state_active`, default `New`) or **closed** state (`work_item_state_closed`, default `Closed`) per close path; use **azure-devops-client**; batch **list-by-ids** in chunks of **≤200** when reconciling remote WI state vs mapping.
- **P2-FR-11**: If `create_new_work_items` is `false`, **never** POST new work items and **never** insert new mapping rows; still PATCH/close **existing** mapped items.
- **P2-FR-8**: If stored derived status was in the **closed** family (`resolved` or `ignored`) and the finding is now **active open** (`open`), **create a new work item**, leave the old WI closed, **upsert** mapping to the new `work_item_id`; optional audit comment may reference the prior WI id.
- **P2-FR-9**: Compare previous stored `snyk_status` to newly derived; on change, **add comment** with `old → new`, Snyk issue **key**, and non-secret ids; **max comment length 4000 characters** (Azure DevOps practical limit — if exceeded, truncate with a single trailing marker `[truncated]` and ensure no secrets in truncated portion).
- **P2-FR-10 (v1)**: Tags from config: under `work_item_template`, key **`tags`** whose value is a **list of strings** (empty list allowed). Applied on create and update via JSON Patch alongside other template-driven operations.
- **P2-FR-5.x (v1)**: **Primary package** = first element of `coordinates[]` (in API order) that has a `representations[]` entry with **`dependency`** set; **description / System.Title** use `attributes.title` plus that primary package line (same rule for both). **Finding type**: `attributes.type` verbatim. **CWE**: from `attributes.classes` where `source == "CWE"`. **CVE**: from `attributes.problems` where `id` matches `CVE-*`, include `url` when present. **Snyk link**: best-effort URL from API ids/key **without** org slug; document deferral of slug-based UI parity. **Fix signal**: booleans on `coordinates[]` as listed in proposal; v1 summary = flags + title + package line.
- **JSON Patch**: **`System.Title`** required on create (title + primary package). **`System.AssignedTo`**: **omit** on create unless `work_item_template` explicitly includes a patch op or field instruction for it (**P2-FR-2** = Unassigned assignee). Additional fields (area, iteration, custom fields) come from **`work_item_template`** using a small internal representation: e.g. list of patch op dicts under key **`json_patch`** or reserved keys mapped to ops — implementation picks one shape and documents it in code + spec; **unknown keys** in `work_item_template` remain forward-compatible per loader rules (ignored unless documented).
- **Create URL type**: `POST .../workitems/$type` uses `azure_boards.work_item_type` (default `Task`).
- **Run policy**: per-issue try/except or error accumulation — **log**, **skip**, continue; exit code **0** if the run completes the loop; **non-zero** for startup failures (missing config, missing tokens, client preflight, unrecoverable API auth errors that abort the whole run). Per-issue skips do **not** force non-zero exit in v1.

**Non-Goals:**

- Hot-reload of YAML; **Azure Table** mapping backend implementation; **WIQL** / **batch** APIs; full **Snyk UI** URL with org slug; long-form human remediation text beyond flags/title/package unless a new API is introduced later; **fail-fast** on first issue error; **coordinates[].state** as authority; treating **`closed`** as a literal Snyk `attributes.status` value for policy (use **`resolved`** + **`ignored`**).

## Decisions

1. **Module layout**  
   - **Decision**: Implement sync orchestration in **`src/sync/`** (Python package `sync` rooted there): one run entry callable from the new subcommand; submodules as needed (e.g. lifecycle derivation, patch builders). **`src/commands/`** holds argparse wiring only; **no** new top-level OpenSpec capability named “sync engine.”  
   - **Rationale**: Keeps `sync-lifecycle` as the normative spec home, matches existing top-level packages under `src/` (`config`, `snyk`, `mapping_store`), and avoids sprawl in `main.py`.

2. **Severity filter alignment (P2-FR-1)**  
   - **Decision**: List issues with `effective_severity_level` derived from merged `snyk.severity_threshold` (minimum level) **and** client defaults (per **snyk-issues-client**: when caller passes none, client uses `high` + `critical`). Sync passes threshold from config so **P2-FR-1** High/Critical baseline remains the default when threshold is `high`.  
   - **Rationale**: Single place for product policy; reuses client HTTP shape.

3. **Mapping row field refresh**  
   - **Decision**: On every successful observation for a mapped issue, update `snyk_status`, `work_item_id` (if changed by reopen), `work_item_status` (latest known Azure state string), `organization`, `project` from merged config if they differ from stored (config wins for routing), and timestamps `updated_at`. Optionally persist last-seen severity/title hash — **non-normative** unless spec demands; v1 **shall** persist at least `snyk_status` and `work_item_status` when obtained from APIs.  
   - **Rationale**: Supports reconciliation and P2-FR-9 transition detection.

4. **Reconciliation with Azure**  
   - **Decision**: Before update/close, optionally **get** or **list-by-ids** the mapped work item if needed to verify existence and current `System.State`; chunk ids in batches of 200. If WI is missing (404), log error, skip issue (mapping row policy: leave row vs delete — **defer to tasks**: default **leave row**, skip updates until operator cleans up).  
   - **Rationale**: Avoids blind PATCH failures; respects client cap.

5. **Closed path**  
   - **Decision**: When derived `snyk_status` is `resolved` **or** `ignored`, apply **same** Boards transition to `work_item_state_closed` (default `Closed`) unless remote already in that state.  
   - **Rationale**: Matches user rule: same close path; stored label distinguishes audit.

6. **`work_item_template` shape for tags and patch**  
   - **Decision**: `work_item_template.tags: [str, ...]` and `work_item_template.json_patch: [ { "op": "add", "path": "/fields/...", "value": ... }, ... ]` (subset of RFC 6902) merged last after built-in Title/Description/State ops so operators can override carefully. Document in **application-config** delta.  
   - **Alternative considered**: Free-form dict of field names — rejected in favor of explicit JSON Patch alignment with Azure DevOps client.

7. **Config validation**  
   - **Decision**: `work_item_type`, `work_item_state_active`, `work_item_state_closed` default to `Task`, `New`, `Closed` when omitted; if present in YAML they **must** be non-empty strings; sync command validates non-empty **after merge** and fails fast **before** loop if invalid.  
   - **Rationale**: Matches “values MUST exist for target process” while keeping samples copy-pasteable.

## Risks / Trade-offs

- **[Risk] Wrong process state names** (e.g. Agile `Active` vs `New`) break transitions → **[Mitigation]** Document in README/sample that operators must set `work_item_state_*` to valid states for their process; validate non-empty only, not membership in a fixed enum.  
- **[Risk] JSON Patch from template could break create** → **[Mitigation]** Unit tests + documented examples; optional schema validation later.  
- **[Risk] list-by-ids volume** → **[Mitigation]** Chunk at 200; single sync run may be N API calls — acceptable for v1.  
- **[Risk] `System.Title` length** → **[Mitigation]** Truncate title+package to Azure limit (typically 255) with ellipsis marker if needed (detail in tasks).

## Migration Plan

- Ship SQLite **DDL migration** (if new columns): idempotent `ALTER TABLE` or recreate per existing project patterns; document one-time run of `scripts/` init for new clones.  
- **Rollback**: revert application revision; mapping DB backward compatibility — if adding columns, keep defaults nullable-safe.

## Open Questions

- Whether to **delete** mapping rows when Azure WI is permanently gone vs retain for audit — v1 default **retain**; confirm in implementation tasks if product prefers delete.  
- Exact **`json_patch`** merge order with built-in fields — finalize in first implementation PR with golden tests.
