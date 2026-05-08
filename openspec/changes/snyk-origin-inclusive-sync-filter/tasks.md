## 1. Configuration and validation

- [ ] 1.1 Add **`ACCEPTABLE_SNYK_ORIGIN_TOKENS`** (or equivalent) as the canonical set matching **`README.md`** / [Snyk Origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin) plus **`github-cloud-app`** and **`github-server-app`**; expose for loader and tests.
- [ ] 1.2 Parse **`azure_boards.defaults.sync_included_snyk_origins`** and **`org_mappings[].overrides.sync_included_snyk_origins`**; merge into effective routing context (same precedence as other **`overrides`**).
- [ ] 1.3 Validate non-string rejection, comma split + strip, empty ⇒ no filter, and unknown token rejection with README-pointer error (**`application-config`** delta).

## 2. Issues sync persistence schema

- [ ] 2.1 Add SQLite **`ALTER TABLE`** for **`excluded`** and **`exclusion_reason`** (`schema.py` + idempotent migration script path **`init_mapping_store`**).
- [ ] 2.2 Extend **`MappingRow`**, **`MappingStore.upsert`**, and **`sqlite_store`** row mapping with defaults **`excluded=false`**, **`exclusion_reason=""`** (**`azure-platform`** delta).

## 3. Sync orchestration

- [ ] 3.1 After **`snyk_project_origin`** is resolved for an issue, compute **origin-included** vs **origin-excluded** against effective allowlist (handles **`origin_unknown`** when empty under active allowlist).
- [ ] 3.2 Skip Azure DevOps create/update/close/comment when **origin-excluded**; persist **`excluded`** and **`exclusion_reason`** (`origin_not_in_allowlist` | `origin_unknown`) on upsert paths that touch the store (**`sync-lifecycle`** delta).
- [ ] 3.3 When allowlist inactive or issue **origin-included**, clear **`excluded`** / **`exclusion_reason`** to non-excluded state on upsert; preserve existing **P2-FR-*** behavior for **`create_new_work_items`** interaction (document in code comments per design).

## 4. Documentation and samples

- [ ] 4.1 Update **`README.md`**: **issues sync persistence** terminology; column table (**`excluded`**, **`exclusion_reason`**); **`sync_included_snyk_origins`**; full allowlist + link to [Snyk — Origin](https://docs.snyk.io/snyk-platform-administration/snyk-projects#origin).
- [ ] 4.2 Update tracked **`data/sample-config.yaml`** with commented example **`sync_included_snyk_origins`** under **`defaults`** (and optional commented **`overrides`** example if sample **`org_mappings`** exists).

## 5. Tests

- [ ] 5.1 Unit tests: allowlist parsing, merge, invalid tokens, empty allowlist semantics.
- [ ] 5.2 Unit tests: SQLite migration applies once; **`MappingRow`** round-trip.
- [ ] 5.3 Unit or integration tests: sync classifies **`cli`** vs **`github`** under stubbed client/fixtures; ADO client not called when excluded.
