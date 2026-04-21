## Why

The product needs a **first end-to-end sync run** that turns existing clients, configuration, and `MappingStore` into governed Boards behavior: normative Snyk lifecycle from Issues API attributes, durable derived `snyk_status` for transitions and mapping, and Azure work item create/update/close aligned with **P2-FR-1** through **P2-FR-11**. Today the specs and platform text still mix legacy “closed” wording with Snyk’s **`resolved`** / **`ignored`** model and lack a single orchestrated command; this change closes that gap without introducing a separate “sync engine” capability.

## What Changes

- Add a **sync subcommand** (argparse under `src/commands/`, `main.py` delegates) that runs one reconciliation loop via orchestration under **`src/sync/`**: merged config, `SNYK_TOKEN`, `AZURE_DEVOPS_PAT`, Snyk client, Azure DevOps client, and `MappingStore` injected; **no new secret sources**.
- **Normative lifecycle** from `data[].attributes.status` and `data[].attributes.ignored` only; `coordinates[].state` is **not** authoritative for open/close/reopen decisions.
- **Lifecycle rules**: `ignored == true` → ignored bucket (**P2-FR-4**); else `status == "resolved"` → fixed/closed path (**P2-FR-3**); else `status == "open"` and `ignored == false` → active open (**P2-FR-1** / updates); any other `status` → skip issue, **error log** with unexpected value (no secrets).
- **Derived `snyk_status`** persisted as one string: `open` \| `resolved` \| `ignored` (precedence: ignored → resolved → open for storage and transition identity; same close path for ignored and resolved).
- **Contract**: Normalized Snyk issue records (and **snyk-issues-client** spec) **must** include `status` and `ignored` from attributes; docs must **not** imply a literal API `closed` — use **`resolved`** + **`ignored`** as above.
- **MappingStore** as source of truth for **P2-FR-7**; upsert on create/update; natural key `(group_id, org_id, project_id, issue_id)`; refresh stored fields when sync observes new Snyk/Azure state; **P2-FR-8** reopen = **new** work item, previous stays closed; mapping row **upsert** replaces `work_item_id` (and related fields) for same natural key; optional audit comment may mention prior WI id.
- **P2-FR-11** (`create_new_work_items: false`): still close/update **existing** mapped work items; **never** create new work items; **never** insert new mapping rows — findings with no row are **untouched**.
- **P2-FR-2**: “Unassigned” = **default assignee** (do not set `System.AssignedTo` on create unless `work_item_template` supplies it).
- **P2-FR-9 (v1)**: Audit comment when **derived** `snyk_status` changes (compare stored vs newly derived); text includes old → new, Snyk issue key, safe ids; no secrets or full API bodies; max length/truncation in design.
- **P2-FR-10 (v1)**: Config-driven tags from **`work_item_template`** (structure defined in design/spec), applied on create/update.
- **P2-FR-5.x**: Description/title+primary package, type verbatim, CWE/CVE rules, best-effort Snyk URL without org slug (full UI parity deferred), fix flags summary — per user bullets.
- **Azure**: create/update/close and optional comment via **azure-devops-client**; use get / list-by-ids (≤200) when reconciling WI state vs mapping.
- **Config**: `azure_boards.work_item_type` (default `Task`), `work_item_state_active` (default `New`), `work_item_state_closed` (default `Closed`); **README** and **`data/sample-config.yaml`** SHALL document defaults and that values MUST exist for the target process.
- **Run policy**: Per-issue errors → log, skip, continue; exit **0** when loop completes (skips counted); **non-zero** for config/auth/client failures that prevent starting or invalidate the whole run (**not** fail-fast on per-issue errors).

## Capabilities

### New Capabilities

- _(none — orchestration extends **`sync-lifecycle`**; no new top-level “sync engine” capability.)_

### Modified Capabilities

- **`sync-lifecycle`**: Normative lifecycle from Snyk attributes; derived `snyk_status`; create/update/close paths; P2-FR-8 new ticket on reopen; P2-FR-9 audit comments; P2-FR-10 tags from template; P2-FR-5.1–5.5 v1 content rules; per-issue error policy and exit codes; list filters aligned with P2-FR-1 + client defaults.
- **`snyk-issues-client`**: Normalized records **shall** include `status` and `ignored`; spec text aligned with lifecycle contract (no `coordinates[].state` as authority for open/close).
- **`application-config`**: New `azure_boards` keys with defaults, merge precedence, validation (non-empty when sync runs vs documented defaults — resolved in delta spec); README/sample requirements for new keys.
- **`azure-platform`**: Mapping row `snyk_status` semantics updated to **`open` \| `resolved` \| `ignored`** (not open/closed/ignored); align **P2-FR-2** prose with assignee-based “Unassigned”; remove implication of literal Snyk/API `closed` where it conflicts with Issues API.

## Impact

- **`src/commands/`**: new sync subcommand wiring; **`src/main.py`** dispatches to it.
- **`src/sync/`**: sync run orchestration (lifecycle, patch assembly, per-issue loop); reuses **`src/snyk/`**, **`src/integrations/azure_devops/`**, mapping abstraction, config loader — no new secret sources.
- **`MappingStore` / SQLite schema**: may need column or migration for derived `snyk_status` and any additional snapshot fields per design (if not already present).
- **Tests**: unit tests for derived status, lifecycle branches, P2-FR-11 guardrails, per-issue skip behavior, and public/protected surfaces touched by implementation.
- **Documentation**: README, `data/sample-config.yaml`; possible non-normative clarifications in **`azure-devops-client`** only if REST/patch behavior needs explicit sync reference (minimal).
