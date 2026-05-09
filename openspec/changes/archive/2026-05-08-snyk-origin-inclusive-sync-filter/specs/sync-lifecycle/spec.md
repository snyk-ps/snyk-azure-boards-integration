## ADDED Requirements

### Requirement: Inclusive Snyk origin allowlist gates Azure Boards mutations

When merged configuration yields a **non-empty** effective **`sync_included_snyk_origins`** list per **`application-config`**, **`sync`** SHALL classify each issue **after** resolving **`snyk_project_origin`** (using persisted row values when sufficiently fresh per existing project-metadata rules, otherwise **`GET /orgs/{org_id}/projects/{project_id}`** when org-scoped project fetch applies). An issue SHALL be **origin-included** only if **`strip(snyk_project_origin)`** equals one allowlisted token **exactly**.

For **origin-included** issues, existing **P2-FR-*** work item rules unchanged. For **origin-excluded** issues, **`sync`** SHALL **not** invoke Azure DevOps **create**, **update**, **state transition**, or **comment** operations for that issue on that run.

When **`snyk_project_origin`** cannot be resolved to a non-empty string before classification and a non-empty allowlist is active, the issue SHALL be treated as **origin-excluded** with **`exclusion_reason`** **`origin_unknown`**.

When the origin is known but not in the allowlist, **`exclusion_reason`** SHALL be **`origin_not_in_allowlist`**.

#### Scenario: Allowlist inactive preserves prior Boards behavior

- **WHEN** effective **`sync_included_snyk_origins`** is empty per **`application-config`**
- **THEN** **`sync`** SHALL not exclude issues based on origin and SHALL apply **P2-FR-1** and other gates as before this change

#### Scenario: CLI origin excluded when allowlist omits cli

- **WHEN** effective allowlist is non-empty, **`snyk_project_origin`** is **`cli`**, and **`cli`** is not among the tokens
- **THEN** the issue SHALL be origin-excluded and **`sync`** SHALL skip Azure DevOps mutations for it

#### Scenario: GitHub origin included when listed

- **WHEN** effective allowlist contains **`github`** and **`snyk_project_origin`** after strip is **`github`**
- **THEN** the issue SHALL be origin-included subject to **P2-FR-1** and other requirements

#### Scenario: Re-included open issue with empty work_item_id creates a work item

- **WHEN** issues sync persistence already holds a row for the issue with **empty** **`work_item_id`** (for example the issue was **origin-excluded** on a prior run and Azure Boards was never mutated), the effective allowlist is **non-empty**, the issue is now **origin-included**, **`create_new_work_items`** is **true**, and the derived Snyk status is **open**
- **THEN** **`sync`** SHALL create an Azure Boards work item for that issue (same rules as for a missing row) and SHALL upsert **`work_item_id`** and **`excluded`** **`false`**, except that **reopen** transitions (**resolved** or **ignored** → **open**) SHALL use the existing **reopen** orchestration path (which already **creates** when **`work_item_id`** is empty)

---

### Requirement: Persist exclusion fields on issues sync persistence upserts

On each **`sync`** pass that upserts the **issues sync persistence** row for a natural key, **`sync`** SHALL set **`excluded`** and **`exclusion_reason`** consistent with the **origin classification** for that routing context: **`excluded`** **`false`** and **`exclusion_reason`** empty when origin-included or when no allowlist applies; **`excluded`** **`true`** and non-empty **`exclusion_reason`** when origin-excluded.

#### Scenario: Included issue clears exclusion flags

- **WHEN** an issue is origin-included
- **THEN** the upsert SHALL persist **`excluded`** **`false`** and **`exclusion_reason`** empty

#### Scenario: Excluded issue records reason

- **WHEN** an issue is origin-excluded because **`snyk_project_origin`** is **`cli`** and the allowlist excludes **`cli`**
- **THEN** the upsert SHALL persist **`excluded`** **`true`** and **`exclusion_reason`** **`origin_not_in_allowlist`**

---

## MODIFIED Requirements

### Requirement: One sync run orchestrates Snyk list, mapping, and Azure Boards updates

The application SHALL provide a **`sync`** command (argparse subcommand implemented under **`src/commands/`**, dispatched from **`src/main.py`**) that performs **one** synchronization run by invoking orchestration implemented under **`src/sync/`** (Python package `sync`). That run SHALL load merged configuration, obtain issues from the Snyk Issues API using **group-scoped** list operations **when `azure_boards.org_mappings` is absent or empty**, or using **org-scoped** list operations **for each non-empty `org_mappings` row** when **`org_mappings`** is present and non-empty, with filters aligned to **P2-FR-1**, **`azure_boards.defaults.severity_threshold`**, **`issues_sync_from`**, **`create_only_when_fix_available`** (when enabled), **`effective_severity_level`** encoding per **`snyk-issues-client`**, and **effective `sync_included_snyk_origins`** per **`application-config`**, read and write rows through the **`MappingStore`** abstraction, and invoke the **Azure DevOps** client for work item create, update, close, and optional comments **only for issues that are not origin-excluded** when an origin allowlist applies. For each **`org_mappings`** row, the run SHALL use that row’s effective **`organization`**, **`project`**, and **effective** work item and policy settings (**`defaults`** merged with that row’s **`overrides`**) and **effective** **`work_item_template`** per **`application-config`** merge rules. The sync run SHALL obtain **`SNYK_TOKEN`** and **`AZURE_DEVOPS_PAT`** only via the same environment-variable rules as the respective clients; it SHALL NOT introduce new secret sources.

#### Scenario: Sync entrypoint lives under commands

- **WHEN** a developer inspects CLI wiring for **`sync`**
- **THEN** argparse registration and argument-to-service wiring SHALL reside under **`src/commands/`** and **`src/main.py`** SHALL delegate without embedding subcommand logic

#### Scenario: Sync orchestration lives under src/sync

- **WHEN** a developer inspects implementation of the per-issue loop, lifecycle derivation, and patch assembly for **`sync`**
- **THEN** that logic SHALL reside under **`src/sync/`** (not under **`src/commands/`**)

#### Scenario: Sync uses merged configuration and mapping store

- **WHEN** the operator runs **`sync`** with a valid configuration path and environment secrets set
- **THEN** the run SHALL use merged **`azure_boards`**, **`snyk`**, **`work_item_template`**, and mapping store settings from the **`application-config`** capability before issuing Snyk or Azure DevOps calls

#### Scenario: Multi-mapping sync uses org-scoped Snyk list per row

- **WHEN** merged configuration includes at least one valid **`org_mappings`** entry
- **THEN** the run SHALL list issues from Snyk using **`snyk_org_id`** for each such entry and SHALL route Azure DevOps operations for issues from that list to that entry’s effective **`organization`** and **`project`** when those issues are not origin-excluded

---

### Requirement: Persist Snyk project display metadata on mapping rows

The **`sync`** run SHALL persist **`snyk_project_name`** (from **`GET /orgs/{org_id}/projects/{project_id}`** **`attributes.name`**) and **`snyk_project_origin`** (from **`attributes.origin`**) on the **issues sync persistence** row for the natural key, updating values when refreshed per **`design.md`**, so routine sync loops avoid repeating project GET for unchanged rows.

#### Scenario: Upsert stores project metadata

- **WHEN** sync obtains non-empty project **`name`** and **`origin`** from the Snyk Projects API for an issue’s **`project_id`**
- **THEN** the persistence upsert SHALL persist **`snyk_project_name`** and **`snyk_project_origin`** alongside existing routing fields

---
