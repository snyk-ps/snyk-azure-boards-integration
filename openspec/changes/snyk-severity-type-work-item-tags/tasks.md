## 1. Tag derivation and assembly

- [ ] 1.1 Add a documented helper that maps normalized Snyk severity (`low`/`medium`/`high`/`critical`) to at most one tag `Snyk-Severity-{level}`; returns `None` when input missing or unrecognized.
- [ ] 1.2 Add a documented helper that maps Snyk issue **`attributes.type`** (or normalized record equivalent) to at most one of `Snyk-Type-open_source`, `Snyk-Type-code`, `Snyk-Type-container`, `Snyk-Type-iac`; returns `None` when unmapped or missing (align with **P2-FR-5.2** taxonomy).
- [ ] 1.3 Add **`combine_tags_for_work_item(template_tags: list[str], managed_severity_tag, managed_type_tag) -> list[str]`** (or equivalent) that strips operator strings starting with `Snyk-Severity-` or `Snyk-Type-`, preserves remaining operator tags in order, appends managed tags in order severity then type, and dedupes consecutive duplicates without reordering unrelated tags.
- [ ] 1.4 Extend **`patch_build.build_create_patch`** and **`patch_build.build_update_patch`** (or callers) so **`System.Tags`** uses the combined list when non-empty; when combined is empty, omit **`System.Tags`** operations as today.
- [ ] 1.5 Wire **`sync`** create/update paths to pass current issue severity and type into tag assembly for every ADO mutation that already runs patch build.

## 2. Tests

- [ ] 2.1 Unit tests for severity and type mapping helpers (known values, missing, unknown type, case-insensitive severity).
- [ ] 2.2 Unit tests for combine helper: operator-only, managed-only, union order, collision with reserved prefixes (operator `Snyk-Severity-critical` stripped when derived says `high`).
- [ ] 2.3 Tests asserting JSON Patch **`System.Tags`** value matches semicolon-separated combined list when both operator and managed tags exist; omitted when neither apply.

## 3. Documentation

- [ ] 3.1 Update **`README.md`** (configuration / template tags section): reserved **`Snyk-Severity-*`** and **`Snyk-Type-*`**, union behavior with **`work_item_template.tags`**, and that managed tags refresh each sync.
