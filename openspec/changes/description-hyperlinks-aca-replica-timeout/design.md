## Context

Plain-text **`System.Description`** assembly lives in **`issue_content.build_system_description()`** (including optional **`work_item_description_appendix`**). **`patch_build._ado_system_description_html()`** converts blocks to **`<p>`** / **`<br />`** HTML with **`html.escape`** on non-special blocks. Only the **Open in Snyk** two-line block gets an **`<a>`** tag today.

Production **`sync`** runs as a **scheduled Azure Container Apps Job**. Job **`replicaTimeout`** (default **1800** seconds) terminates replicas that run longer, independent of application exit handling.

## Goals / Non-Goals

**Goals:**

- Clickable **`http(s)`** links throughout generated **`System.Description`** (appendix, CVE/NVD URLs in **`CVE-… (https://…)`** lines, other Snyk narrative URLs).
- Preserve existing **Open in Snyk** UX (**`view in Snyk`** anchor text).
- Maintain HTML injection safety (escape non-URL text; only allow **`http://`** / **`https://`** in **`href`**).
- Document **replica timeout** sizing in **`README.md`** for ACA job operators.

**Non-Goals:**

- Markdown or raw HTML in **`work_item_description_appendix`**.
- Linkifying **CVE id** text without URL (for example making **`CVE-2023-29017`** alone clickable)—only URLs in plain text.
- Auto-tuning **`replicaTimeout`** from code or emitting ACA ARM/Bicep/Terraform.
- Changing **`issue_content`** CVE plain-text format (URL linkification happens at HTML stage).

## Decisions

1. **Single choke point:** Add **`_escape_and_linkify_plain_text(plain: str) -> str`** in **`patch_build.py`**. Scan plain text for **`https?://`** URLs; escape inter-URL segments; wrap matches in **`<a href="…">…</a>`** with **`html.escape(..., quote=True)`** on **`href`** and escaped URL as visible text. Strip trailing punctuation (**. , ; : )**) from URL matches before building **`href`**.
2. **Open in Snyk:** Keep the dedicated branch in **`_ado_system_description_html`** (first line **`Open in Snyk`**, second line **`https://app.snyk.io/…`**) so link text stays **`view in Snyk`**. Do not run generic linkify on that block in a way that replaces the label.
3. **Scheme allowlist:** Linkify only if match starts with **`http://`** or **`https://`**. Do not linkify **`javascript:`**, **`data:`**, or angle-bracket pseudo-URLs unless explicitly scoped in a follow-up.
4. **CVE/NVD:** No **`issue_content`** change required; **`cve_entries`** already emits **`CVE-id (url)`** in plain text—the HTML pass linkifies the URL portion.
5. **Replica timeout docs:** Add to **`README.md`** **Minimum requirements**, **Job details (portal walkthrough)**, and **If something fails** tables. Cross-reference **`sync_summary.sync_duration_seconds`** from **Logs and observability**. Cite Microsoft **`replicaTimeout`** / **`--replica-timeout`** docs. Rough guide: **~60 seconds per 50 work items**; stress-test; set timeout **above** peak observed duration with margin (e.g. **1.5–2×**).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **Open redirect / XSS via `href`** | Allowlist **`http(s)`** only; escape attributes and text. |
| **Over-greedy URL regex** | Conservative pattern; unit tests for punctuation boundaries. |
| **Rough timeout estimate misleads** | Document as starting guess only; emphasize **`sync_duration_seconds`** and stress testing. |
| **Appendix “plain text only” doc drift** | Clarify appendix stays plain text in YAML; URLs become links at HTML conversion (not raw HTML in config). |

## Migration Plan

- Deploy updated image; next **`sync`** updates existing work item descriptions on the normal update path.
- Operators with jobs hitting **30 minutes** increase **`replicaTimeout`** in portal or CLI—no app config change.
- No mapping-store or YAML migration.

## Open Questions

- None.
