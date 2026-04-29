## 1. Configuration and validation

- [x] 1.1 Extend merged configuration model with **`azure_boards.org_mappings[].snyk_org_slug`** only per **`application-config`** delta (reject **`snyk.snyk_org_slug`** and **`azure_boards.snyk_org_slug`**; required per-row slug for **`org_mappings`**).
- [x] 1.2 Implement **`sync`** startup validation: resolve effective **`snyk_org_slug`** per routing context; exit non-zero before any Snyk Issues request when missing (**`sync-lifecycle`** ADDED requirement).
- [x] 1.3 Update **`data/`** sample YAML and **`README.md`** configuration tables with **`snyk_org_slug`** fields and operator guidance (slug source: Snyk org settings / browser URL).

## 2. Snyk issue enrichment

- [x] 2.1 In **`sync`** orchestration, after receiving a list issue record, detect missing **`description`** / **`coordinates[].remedies`** (per **`design.md`**) and call **`IssuesClient.get_group_issue`** or **`get_org_issue`** with the correct scope and **`rest_issue_id`**; merge GET **`attributes`** / **`coordinates`** into the working record before **`issue_content`** runs.
- [x] 2.2 Ensure GET failures follow per-issue skip semantics (**`sync-lifecycle`**) unless classified as global failures.

## 3. Work item text and URL

- [x] 3.1 Replace **`best_effort_snyk_issue_url`** with **`snyk_ui_issue_url`** (or equivalent) implementing **`https://app.snyk.io/org/{slug}/project/{project_id}#issue-{issue_key}`**; remove group-based URL and disclaimer lines from **`issue_content`**.
- [x] 3.2 Extend **`build_system_description`** (or successor) to include **`attributes.description`**, formatted **`coordinates[].remedies`**, existing CVE/CWE/type/flags/package lines, and the canonical link; define sensible ordering and plain-text formatting for Azure DevOps HTML constraints per **`design.md`**.
- [x] 3.3 Thread effective **`snyk_org_slug`** from **`sync`** into **`issue_content`** alongside **`group_id`** / org scope context.

## 4. Tests

- [x] 4.1 Unit tests for URL builder (slug, project UUID, issue key, encoding edge cases).
- [x] 4.2 Unit tests for description assembly with mocked **`issue_attributes`** including **`description`**, **`remedies`**, and absent-field cases.
- [x] 4.3 Unit tests for config merge and **`sync`** startup validation (**missing slug** paths).
- [x] 4.4 Tests for conditional GET enrichment (list-only vs list+GET merge) using mocks.
