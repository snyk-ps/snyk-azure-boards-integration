## MODIFIED Requirements

### Requirement: P2-FR-5.4 direct Snyk web UI issue URL

The application SHALL construct exactly **one** canonical HTTPS URL per work item that satisfies **P2-FR-5.4** using this structure:

`{app_base_url}/org/{snyk_org_slug}/project/{project_id}#issue-{issue_key}`

where:

- **`{app_base_url}`** is the effective Snyk **web app origin** from **`application-config`** (default **`https://app.snyk.io`**, override via **`snyk.app_base_url`**, **`SNYK_APP_BASE_URL`**, or **`--snyk-app-base-url`** on **`sync`**).
- **`{snyk_org_slug}`** is the effective organization slug from **`application-config`** for the routing context processing the issue (**`org_mappings`** rows supply it; group-only sync MAY leave it empty until configuration exists).
- **`{project_id}`** is **`relationships.scan_item.data.id`** from the issue resource.
- **`{issue_key}`** is **`attributes.key`** from the issue resource.

The fragment SHALL be **`#issue-`** immediately followed by **`attributes.key`** verbatim; URL-encoding SHALL be applied only as required for a valid HTTP URL.

The application SHALL NOT emit **`https://app.snyk.io/group/{group_id}/issues/{id}`** or other deprecated **best-effort** link patterns as the primary **P2-FR-5.4** link line.

When the URL is rendered inside **`System.Description`**, it SHALL appear as an HTML **hyperlink** (**`<a href="...">...</a>`**) with **href** set to the canonical URL and link text that identifies the issue in Snyk, subject to the same HTML entity escaping rules as other dynamic description content (**HTML-safe** assembly). The **"Open in Snyk"** description block SHALL receive the same hyperlink treatment regardless of the configured **`app_base_url`** origin.

#### Scenario: Link uses config slug and API identifiers

- **WHEN** sync composes the **P2-FR-5.4** link for an issue with known **`snyk_org_slug`**, **`scan_item`**, and **`attributes.key`**
- **THEN** the URL SHALL match the canonical template above with those substitutions

#### Scenario: Regional app base URL in link

- **WHEN** merged configuration sets **`snyk.app_base_url`** to **`https://app.eu.snyk.io`** and sync composes the **P2-FR-5.4** link for an issue with known slug, project id, and issue key
- **THEN** the URL origin SHALL be **`https://app.eu.snyk.io`** and the path and fragment SHALL match the canonical template

#### Scenario: Fragment uses issue key

- **WHEN** **`attributes.key`** is `SNYK-PYTHON-H11-10293728`
- **THEN** the URL fragment SHALL end with `#issue-SNYK-PYTHON-H11-10293728`

#### Scenario: Description renders link as HTML anchor

- **WHEN** the **P2-FR-5.4** URL is written into **`System.Description`**
- **THEN** the stored HTML SHALL include a single **`a`** element with **`href`** equal to the canonical HTTPS URL (escaped as required)
