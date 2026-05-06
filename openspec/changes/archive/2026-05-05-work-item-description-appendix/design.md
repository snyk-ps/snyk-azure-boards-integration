## Context

Work item **`System.Description`** is built as plain text in **`issue_content.build_system_description()`**, then converted to HTML in **`patch_build._ado_system_description_html()`** for JSON Patch. Operators need a **config-only** way to append static guidance (links, access requests) without **`json_patch`** on unsupported custom fields or **`System.Description`** overrides.

## Goals / Non-Goals

**Goals:**

- Optional **`azure_boards.defaults.work_item_description_appendix`** string; optional **per-mapping** override via **`org_mappings[].overrides`**.
- Append **after** all built-in sections with blank-line separation so HTML yields an extra paragraph block.
- Same escaping pipeline as the rest of the description body (appendix is operator YAML, not Snyk API JSON, but still escaped for HTML safety).
- Combined plain text subject to existing maximum length / truncation behavior.

**Non-goals:**

- **Templating** with placeholders (`{{issue_id}}`, etc.).
- Hot-reload of config without process restart (unchanged product behavior).

## Decisions

1. **Where to merge**: Extend **`AzureBoardsDefaults`** with **`work_item_description_appendix: str`** default **`""`**. Resolve effective value using the same **`boards_for_org_mapping`** / merged **`AzureBoardsConfig`** path as other per-row **`defaults` + `overrides`** fields.

2. **Where to append**: Prefer extending **`build_system_description(..., description_appendix: str | None = None)`** (or a dedicated helper called from **`run.py`** immediately after) so truncation stays in **`issue_content`**. If appendix is empty after strip, skip append (whitespace-only treats as empty).

3. **HTML**: Do **not** inject raw HTML from YAML. Pass appendix through the same pipeline as other description lines so **`_ado_system_description_html`** performs escaping like other paragraphs.

4. **Loader**: Accept omitted key as **`""`**; reject non-string types with a clear **`ConfigError`**.

## Risks / Trade-offs

- **[Risk]** Operators expect Markdown or HTML in YAML → Boards shows escaped text only → **Mitigation**: Document that appendix is plain text; Boards renders paragraphs from escaped content.

- **[Risk]** Very long appendix pushes finding details out of the 32k window → **Mitigation**: Same truncation notice as today; document in README.

## Migration Plan

No data migration. New optional key; existing configs unchanged.

## Open Questions

None.
