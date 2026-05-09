## Why

Operators need to control **which Snyk findings drive Azure Boards work items** by Snyk project **origin** (for example include **`github`** but not **`cli`**). Origin is already retrieved via the Snyk Projects API as **`attributes.origin`** and persisted as **`snyk_project_origin`** for work item text. Making that signal **policy inputs** (inclusive allowlist in YAML) closes a gap: findings from unwanted sources should not create or receive Boards updates, while still allowing durable **issues sync persistence** for audit and reporting.

## What Changes

- **Configuration:** Add optional **`sync_included_snyk_origins`** under **`azure_boards.defaults`** — comma-separated **inclusive** list of origin tokens (trimmed after split). Omitted or empty ⇒ **no origin filtering** (backward compatible with past behavior). Same key allowed under **`azure_boards.org_mappings[].overrides`** for per-mapping routing.
- **Validation:** Config loader validates token shape (see design) and membership in the documented allowlist enumerated in **`README.md`** and aligned with [Snyk — Origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin), plus **`github-cloud-app`** and **`github-server-app`** as additional accepted operator tokens (REST may expose them).
- **Sync behavior:** After resolving **`snyk_project_origin`** for an issue (existing project GET / cache path), **`sync`** treats issues as **included** only if the allowlist is inactive **or** the origin equals one configured token. **Excluded** issues MUST NOT create, update, or close Azure Boards work items. If the allowlist later includes the issue but persistence still has **no** **`work_item_id`** (typical after a prior excluded-only row), **`sync`** MUST create a work item for **open** issues when **`create_new_work_items`** and other existing gates permit—same as a missing mapping row.
- **Issues sync persistence:** Reposition the store as **issues sync persistence** (logical name); physical SQLite table **`issue_work_item_map`** remains for migration continuity.
- **New columns:** **`excluded`** (boolean), **`exclusion_reason`** (string) persisted per natural key for reporting and stable classification across runs.
- **Documentation:** **`README.md`** — terminology, column table, config key, full allowlist table with link to Snyk docs. **`data/sample-config.yaml`** — commented example key.

## Capabilities

### New Capabilities

- _(none — deltas extend existing capabilities)_

### Modified Capabilities

- **`application-config`**: New **`sync_included_snyk_origins`** key; **`org_mappings` overrides** allow list; README/sample requirements.
- **`azure-platform`**: Logical **issues sync persistence** naming; schema adds **`excluded`**, **`exclusion_reason`**.
- **`sync-lifecycle`**: Origin allowlist gates Boards mutations; persistence rules for exclusion fields.

## Impact

- **`src/config/`** — parse, merge, validate new key.
- **`src/mapping_store/`** — schema migration, **`MappingRow`**, upsert protocol.
- **`src/sync/`** — classify each issue after origin resolution; skip ADO client when excluded.
- **`README.md`**, **`data/sample-config.yaml`**
- **Tests** for config loader, merge, persistence migration, sync gating.

**BREAKING:** None at the YAML top level for operators who omit the new key. Storage schema gains columns with safe defaults for existing SQLite databases.
