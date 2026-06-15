## MODIFIED Requirements

### Requirement: CLI flags and defaults

The tool SHALL expose:

- **`--input`**: path to the CSV (required).
- **`--group-id`**: Snyk **group** UUID (required).
- **`--output`**: path for the generated YAML; default **`data/config.yaml`** relative to the current working directory unless an absolute path is given.
- Optional **`--base-url`**: Snyk REST base URL or API origin; default derived from **`https://api.snyk.io`** (**SNYK-US-01**) as **`https://api.snyk.io/rest`** (no trailing slash), consistent with **`integration-apis`** and **`application-config`**. When **`SNYK_API_BASE_URL`** is set in the environment, the tool SHALL use the same origin/REST derivation as the main application unless **`--base-url`** overrides it for that invocation.
- Optional **`--api-version`**: query parameter **`version`** for the org list; default **`2024-03-12`** as specified in [Snyk REST API — List orgs in a group](https://apidocs.snyk.io/?version=2024-03-12#get-/groups/-group_id-/orgs).

Authentication SHALL use **`SNYK_TOKEN`** from the **environment** only (never read from CLI flags or YAML). The tool MUST NOT log the token or any credential material.

#### Scenario: Missing token

- **WHEN** **`SNYK_TOKEN`** is unset or empty at runtime
- **THEN** the tool SHALL exit non-zero with a clear error before or upon the first API call

#### Scenario: Default output path

- **WHEN** the user omits **`--output`**
- **THEN** the tool SHALL write to **`data/config.yaml`**

#### Scenario: Org list uses regional base from environment

- **WHEN** the operator sets **`SNYK_API_BASE_URL=https://api.eu.snyk.io`** and does not pass **`--base-url`**
- **THEN** org list HTTP calls SHALL target **`https://api.eu.snyk.io/rest`**

---

### Requirement: Snyk group org listing and pagination

For the given **`group_id`**, the tool SHALL retrieve all organizations by calling **`GET /groups/{group_id}/orgs`** against the configured REST base URL (derived from origin per **`application-config`**), including query parameters **`version`** (see **`--api-version`**) and **`limit=100`**. The tool SHALL follow **JSON:API pagination** using **`links.next`** until no further page exists, aggregating org resources from all pages into a single in-memory collection before resolving CSV rows.

#### Scenario: Multiple pages

- **WHEN** the API returns a **`links.next`** link and a non-empty **`data`** array with **`limit=100`**
- **THEN** the tool SHALL request subsequent pages until **`links.next`** is absent and SHALL include orgs from every page in the aggregated set
