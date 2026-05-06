## Why

Operators often need a **fixed block** in each synced work item (for example an internal Snyk access-request link or runbook) without using `json_patch` on custom Azure DevOps fields (fragile field reference names, frequent HTTP 400s) or replacing **`System.Description`** entirely. Today, work item body text is assembled in code; there is no way to append operator-defined copy from YAML.

## What Changes

- Add optional **`azure_boards.defaults.work_item_description_appendix`**: a **string** (default **empty**). When non-empty, **`sync`** appends it to the plain-text assembly for **`System.Description` after all built-in sections, separated by at least one blank line so it becomes a **distinct paragraph block** after HTML conversion.
- **`azure_boards.org_mappings[].overrides`** may set **`work_item_description_appendix`** per mapping row (same merge pattern as other **`defaults`** keys overridden by **`overrides`**).
- **HTML safety**: Appendix text is part of the same description pipeline; it SHALL be subject to the same **HTML entity escaping** rules as the rest of the generated description so characters like `&`, `<`, `>` cannot inject markup.
- **Length**: The appendix is included in the **combined** plain text before the existing maximum-size truncation (with the existing truncation notice) so the field stays within Azure Boards practical limits.
- **Documentation**: Update **`README.md`** (configuration / parameter descriptions). Update tracked **`data/`** sample YAML (commented optional example; no secrets).

## Capabilities

### New Capabilities

- *(None.)*

### Modified Capabilities

- **`application-config`**: Schema and merge rules for **`work_item_description_appendix`** under **`azure_boards.defaults`** and **`org_mappings[].overrides`**; extend documented allowed **`overrides`** keys; README and **`data/`** sample requirements.
- **`sync-lifecycle`**: Normative behavior for optional description appendix in **`System.Description`** assembly; scenarios for empty vs non-empty and per-mapping override.

## Impact

- **`src/config/`** (models, loader), **`src/sync/`** (`issue_content` and/or `run.py`), tests, **`README.md`**, **`data/*.yaml`** samples.
