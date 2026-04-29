## ADDED Requirements

### Requirement: Sync validates snyk_org_slug for org_mappings before work item patches

Before the **`sync`** run issues **any** Snyk Issues API HTTP requests, **`sync`** SHALL resolve the effective **`snyk_org_slug`** per **`application-config`** for each routing context. When **`org_mappings`** is non-empty, each active mapping row’s **`snyk_org_slug`** SHALL be non-empty (loader-enforced for YAML; validation covers in-memory edge cases) or **`sync`** SHALL exit non-zero with a clear, non-secret error. When **group-only** issue listing is used (no effective **`org_mappings`**), there is no configured org slug; composed Snyk UI links MAY use an empty org path segment until a later product change adds configuration for group mode.

#### Scenario: Org mappings sync fails when effective slug missing for a row

- **WHEN** an **`org_mappings`** row has an empty effective **`snyk_org_slug`** (in-memory misconfiguration)
- **THEN** **`sync`** SHALL exit non-zero before any Snyk Issues API request with an error that does not include secrets

---

## MODIFIED Requirements

### Requirement: P2-FR-5.1 primary package and title or description body

The **primary package** SHALL be taken from the **first** `coordinates[]` element in API order that contains a `representations[]` entry with a **`dependency`** field set.

The human-readable text used for **`System.Title`** on create SHALL combine **`attributes.title`** with that primary package line using the same composition rule for both **P2-FR-5.1** and the **System.Title** requirement.

For **`System.Description`** (work item body text), the application SHALL assemble content so developers can remediate without relying on the Snyk web UI when the API provides sufficient data. That assembly SHALL include at minimum:

1. **`attributes.title`** and the **primary package** line when applicable (consistent with the title composition rule).
2. **`attributes.description`** when present on the issue payload (vulnerability narrative).
3. **`coordinates[].remedies`** formatted as human-readable remediation guidance when present.
4. Content required by **P2-FR-5.2**, **P2-FR-5.3**, and boolean fix signals referenced by **P2-FR-5.5**, when present on the payload.

When the issue record produced by **list** operations omits **`attributes.description`** or **`coordinates[].remedies`** (or other fields needed for the paragraphs above), the application SHALL issue **`GET /groups/{group_id}/issues/{issue_id}`** or **`GET /orgs/{org_id}/issues/{issue_id}`** in the **same** scope as the list operation for that issue’s **`rest_issue_id`** (JSON:API **`data.id`**), merge **`attributes`** and **`coordinates`** from the GET response into the working issue view per the active change **`design.md`**, then assemble **`System.Description`**. The client SHALL use the same **`version`** query parameter as documented for Issues API requests.

If fields remain absent after GET, the description SHALL still include all other available metadata; the run SHALL NOT fail solely because narrative or remedies are missing.

#### Scenario: Primary package from first dependency representation

- **WHEN** multiple coordinates include dependency representations
- **THEN** the sync SHALL select the first such coordinate in API order for the primary package line

#### Scenario: Description includes narrative when attributes.description is present

- **WHEN** the working issue attributes include non-empty **`description`**
- **THEN** **`System.Description`** SHALL include that text in addition to other required sections

#### Scenario: GET issue enriches payload when list omits remedies or description

- **WHEN** the list payload lacks **`description`** or **`remedies`** and GET-by-id returns them for the same issue
- **THEN** **`System.Description`** SHALL incorporate those fields after the GET merge

---

### Requirement: P2-FR-5.4 direct Snyk web UI issue URL

The application SHALL construct exactly **one** canonical HTTPS URL per work item that satisfies **P2-FR-5.4** using this structure:

`https://app.snyk.io/org/{snyk_org_slug}/project/{project_id}#issue-{issue_key}`

where:

- **`{snyk_org_slug}`** is the effective organization slug from **`application-config`** for the routing context processing the issue (**`org_mappings`** rows supply it; group-only sync MAY leave it empty until configuration exists).
- **`{project_id}`** is **`relationships.scan_item.data.id`** from the issue resource.
- **`{issue_key}`** is **`attributes.key`** from the issue resource.

The fragment SHALL be **`#issue-`** immediately followed by **`attributes.key`** verbatim; URL-encoding SHALL be applied only as required for a valid HTTP URL.

The application SHALL NOT emit **`https://app.snyk.io/group/{group_id}/issues/{id}`** or other deprecated **best-effort** link patterns as the primary **P2-FR-5.4** link line.

#### Scenario: Link uses config slug and API identifiers

- **WHEN** sync composes the **P2-FR-5.4** link for an issue with known **`snyk_org_slug`**, **`scan_item`**, and **`attributes.key`**
- **THEN** the URL SHALL match the canonical template above with those substitutions

#### Scenario: Fragment uses issue key

- **WHEN** **`attributes.key`** is `SNYK-PYTHON-H11-10293728`
- **THEN** the URL fragment SHALL end with `#issue-SNYK-PYTHON-H11-10293728`

---

### Requirement: P2-FR-5.5 fix availability and fix guidance

The application SHALL read boolean fix signals from each **`coordinates[]`** object: **`is_upgradeable`**, **`is_patchable`**, **`is_pinnable`**, **`is_fixable_manually`**, **`is_fixable_snyk`**, **`is_fixable_upstream`**.

The work item description SHALL summarize **true** flags together with the issue **title** and the **primary package** line from **P2-FR-5.1**.

When **`coordinates[].remedies`** or other structured fix guidance is present on the issue payload (including after **GET** enrichment per **P2-FR-5.1**), the work item description SHALL include that guidance in human-readable form so developers can remediate without opening the Snyk web UI when the API supplies such data.

#### Scenario: Summary mentions true flags

- **WHEN** at least one of the boolean flags is true
- **THEN** the work item description SHALL include a concise enumeration of which flags are true

#### Scenario: Remedies rendered when coordinates contain remedies

- **WHEN** **`coordinates[].remedies`** is present after list and GET merge
- **THEN** the work item description SHALL include formatted remedy guidance
