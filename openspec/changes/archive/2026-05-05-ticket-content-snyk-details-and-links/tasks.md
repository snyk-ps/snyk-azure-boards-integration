## 1. Configuration and validation

- [x] 1.1 Extend merged configuration model with **`azure_boards.org_mappings[].snyk_org_slug`** only per **`application-config`** delta (reject **`snyk.snyk_org_slug`** and **`azure_boards.snyk_org_slug`**; required per-row slug for **`org_mappings`**).
- [x] 1.2 Implement **`sync`** startup validation: resolve effective **`snyk_org_slug`** per routing context; exit non-zero before any Snyk Issues request when missing on **`org_mappings`** rows (**`sync-lifecycle`**).
- [x] 1.3 Update **`data/`** sample YAML and **`README.md`** configuration tables with **`snyk_org_slug`** fields and operator guidance (slug source: Snyk org settings / browser URL).

## 2. Snyk issue enrichment and normalization

- [x] 2.1 In **`sync`** orchestration, after receiving a list issue record, detect missing **`description`** / **`coordinates[].remedies`** (per **`design.md`**) and call **`IssuesClient.get_group_issue`** or **`get_org_issue`** with the correct scope and **`rest_issue_id`**; merge GET **`attributes`** / **`coordinates`** into the working record before **`issue_content`** runs.
- [x] 2.2 Ensure GET failures follow per-issue skip semantics (**`sync-lifecycle`**) unless classified as global failures.
- [x] 2.3 Parse JSON:API **`included`** on list/GET issue documents; set **`snyk_project_name`** on normalized records from scan item project **`attributes.name`** when **`included`** is present; merge **`snyk_project_name`** from GET enrichment when the list record lacked it.

## 3. Work item text, title, and URL

- [x] 3.1 Replace **`best_effort_snyk_issue_url`** with **`snyk_ui_issue_url`** implementing **`https://app.snyk.io/org/{slug}/project/{project_id}#issue-{issue_key}`**; remove group-based URL patterns from **`issue_content`**.
- [x] 3.2 Extend **`build_system_description`** with sectioned context (Azure Boards target, Snyk target, severity, issue key, package, paths, **how to fix** / upgrade hints, details, classification, link); human-readable fix signals (**omit `is_pinnable`**); remedy and upgrade field extraction per **`design.md`**.
- [x] 3.3 Implement **`work_item_title`** as **`{target} - {issue}`** with **`effective_target_label_for_title`** (Snyk target name preferred, else **`organization / project`**); thread **`snyk_org_slug`** and routing context from **`sync`** into **`issue_content`**.
- [x] 3.4 Wrap **`System.Description`** for Azure Boards as HTML in **`patch_build`** (`<p>` / `<br />`, **`html.escape`**) so section spacing renders in the web UI.

## 4. Tests

- [x] 4.1 Unit tests for URL builder (slug, project UUID, issue key, encoding edge cases).
- [x] 4.2 Unit tests for description/title assembly, HTML patch output, **`included`** → **`snyk_project_name`**, and upgrade/remedy formatting.
- [x] 4.3 Unit tests for config merge and **`sync`** startup validation (**org_mappings** slug paths).
- [x] 4.4 Tests for conditional GET enrichment (list-only vs list+GET merge) using mocks.
