## Why

Work item **`System.Description`** is HTML in Azure Boards, but only the built-in **Open in Snyk** block is rendered as a clickable hyperlink today. URLs elsewhere in the description—including **`work_item_description_appendix`** (for example access-request links) and **CVE/NVD** URLs from Snyk **`attributes.problems`**—appear as escaped plain text, which hurts operator usability (**P2-FR-5.3**, appendix intent from **`work-item-description-appendix`**).

Separately, **`sync`** runs on **Azure Container Apps Jobs** with a default **`replicaTimeout`** of **30 minutes**. Large tenants can exceed that limit and fail with **`DeadlineExceeded`** even when **`sync`** is healthy. Operators need documented guidance to size **`replicaTimeout`** from observed **`sync_duration_seconds`** and rough capacity planning.

## What Changes

- **Description hyperlinks:** During HTML conversion for **`System.Description`**, **`sync`** SHALL turn **`http://`** and **`https://`** URLs in plain-text description blocks into safe **`<a href="...">...</a>`** elements (escaped **`href`** and link text). Applies to appendix text, CVE/NVD URLs, narrative/remediation text, and other API-sourced copy. The existing **Open in Snyk** block keeps its dedicated anchor label (**`view in Snyk`**). Non-**`http(s)`** schemes (for example **`javascript:`**) SHALL NOT be linkified.
- **Security:** Non-URL text remains HTML-escaped; operators still cannot inject raw HTML via YAML appendix.
- **Documentation:** **`README.md`** **`Deployment`** section SHALL document **Container App Job replica timeout** sizing: default **30 minutes**, rough estimate **~60 seconds per 50 work items**, recommendation to stress-test and set timeout above observed **`sync_summary.sync_duration_seconds`** with buffer; portal **Configuration** and CLI **`--replica-timeout`** pointers; troubleshooting for **`DeadlineExceeded`**.

## Capabilities

### New Capabilities

- *(None.)*

### Modified Capabilities

- **`sync-lifecycle`**: Extend **HTML-safe `System.Description`** and **P2-FR-5.3** scenarios so **`http(s)`** URLs in description assembly render as hyperlinks; preserve **Open in Snyk** friendly link text.
- **`application-config`**: Extend **README Deployment** documentation requirement with **replica timeout** operator guidance for scheduled Container App Jobs.

## Impact

- **`src/sync/patch_build.py`**: URL linkification helper; wire into **`_ado_system_description_html`**.
- **`tests/test_sync_patch_build.py`** (and related): hyperlink, escaping, Open in Snyk, appendix, CVE URL cases.
- **`README.md`**: minimum requirements table, job walkthrough, troubleshooting.
- **No** config schema changes, mapping-store migration, or API contract changes.
