## 1. Specs and contracts

- [x] 1.1 Confirm Snyk OpenAPI for **`GET /orgs/{org_id}/issues`** and **`GET /orgs/{org_id}/issues/{issue_id}`** matches **`integration-apis`** delta (query params, version).
- [x] 1.2 Archive-ready review: delta specs under **`openspec/changes/snyk-org-issues-ado-mappings/specs/`** align with **`proposal.md`** and **`design.md`**.

## 2. Snyk issues client (org scope)

- [x] 2.1 Implement org-scoped issue **list** and **get** in **`src/snyk/`**, reusing pagination (`links.next`), filters, normalized records, 429 handling, and **`version=2025-11-05`** per **`snyk-issues-client`** delta.
- [x] 2.2 Unit tests for org list/get URL construction, pagination, and normalized fields (mirror group-scope tests).

## 3. Configuration loader

- [x] 3.1 Parse **`azure_boards.defaults`** (**`work_item_type`**, **`work_item_state_active`**, **`work_item_state_closed`**, **`work_item_template`**).
- [x] 3.2 Parse **`azure_boards.org_mappings`** with validation per **`application-config`** ADDED requirement.
- [x] 3.3 Reject flat **`azure_boards.work_item_*`** keys; work item policy only under **`defaults`**.
- [x] 3.4 Implement effective **`work_item_template`** merge: top-level → **`defaults.work_item_template`** → **`overrides.work_item_template`** (`json_patch` list concat order per **`design.md`**).
- [x] 3.5 Unit tests for validation, merge precedence, and effective template per row.

## 4. CLI

- [x] 4.1 Extend **`fetch`** (or equivalent) under **`src/commands/`** to support **org-scoped** smoke per **`snyk-issues-client`** delta (document in `--help`).
- [x] 4.2 Unit or integration tests for argparse wiring (no token in argv).

## 5. Sync orchestration

- [x] 5.1 When **`org_mappings`** is non-empty, iterate each row: org-scoped Snyk list, ADO **`organization`**/**`project`**, effective work item strings and template for **`build_create_patch`** / **`build_update_patch`**.
- [x] 5.2 When **`org_mappings`** is empty, preserve current group-scoped **`sync`** behavior and **`snyk.group_id`** validation.
- [x] 5.3 Unit tests for orchestration branches (mock clients / mapping store as existing tests do).

## 6. Documentation and samples

- [x] 6.1 Update **`README.md`** **`Configuration`** (Parameter Descriptions): **`defaults`**, **`org_mappings`**, inheritance, **`group_id`** rules, assignee via **`json_patch`**.
- [x] 6.2 Update **`data/sample-config.yaml`** with **`defaults`** and commented **`org_mappings`** example (placeholders only).

## 7. Quality gates

- [x] 7.1 Run **`uv run`** test suite; fix regressions.
- [x] 7.2 Run Snyk Code / Open Source on touched code per project guidelines before merge.
