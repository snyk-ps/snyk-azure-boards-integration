## 1. Description URL hyperlinks

- [ ] 1.1 Add **`_escape_and_linkify_plain_text`** (or equivalent) in **`src/sync/patch_build.py`**: **`http(s)`** allowlist, HTML escaping, trailing-punctuation trim, **`<a href="…">…</a>`** output.
- [ ] 1.2 Wire into **`_ado_system_description_html`**: generic blocks use linkify; preserve **Open in Snyk** special-case anchor label **`view in Snyk`**.
- [ ] 1.3 Unit tests in **`tests/test_sync_patch_build.py`**: appendix URL; CVE/NVD URL in parens; **Open in Snyk** label unchanged; **`&` / `<` / `>`** still escaped in non-URL text; **`javascript:`** not linkified; trailing-period URL boundary.
- [ ] 1.4 Update **`test_build_create_patch_escapes_special_chars_in_description`** in **`tests/test_sync_issue_content.py`** if behavior for angle-bracket URLs is clarified in tests.

## 2. Documentation (replica timeout)

- [ ] 2.1 **`README.md`**: add **Replica timeout** to **Minimum requirements (Azure Container Apps)** table.
- [ ] 2.2 **`README.md`**: add **Replica timeout** bullet under **Job details** in portal walkthrough (**C**).
- [ ] 2.3 **`README.md`**: add **`DeadlineExceeded` / ~30 minute** row to **If something fails** (**H**); cross-link **`sync_duration_seconds`**.

## 3. Verification

- [ ] 3.1 Run **`pytest`** for affected tests.
- [ ] 3.2 Run **Snyk Code** / Open Source checks per repo guidelines.

## 4. Archive (human)

- [ ] 4.1 Merge **`openspec/specs/`** only when archiving: do **not** copy **`openspec/changes/description-hyperlinks-aca-replica-timeout/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive description-hyperlinks-aca-replica-timeout`** (or project equivalent) to fold deltas into canonical specs.
