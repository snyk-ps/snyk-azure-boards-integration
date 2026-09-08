## MODIFIED Requirements

### Requirement: HTTP errors, logging, and retries

On non-success HTTP status codes, the client SHALL surface errors that include the **HTTP status** and SHALL allow callers to distinguish **authentication failures (`401`/`403`)**, **other client errors (4xx)**, **rate limiting (`429`)**, and **server errors (`5xx`)** where practical.

On **terminal** **4xx** and **5xx** outcomes (after the bounded **429** retry policy and any **`GET`** recovery retries conclude), the client SHALL attempt to derive a **bounded, non-secret diagnostic** from the Azure DevOps error response envelope and SHALL include it both in the raised error message and as the **error detail** on the audit record required by **`observability`** **P2-FR-6.2**. The diagnostic SHALL:

- Prefer the envelope **`message`** field, prefixed with **`typeKey`** when present.
- Be **truncated** to a documented maximum length with an explicit truncation marker.
- Have credential-shaped content **redacted** before emission.
- Be **omitted** — falling back to a status-only message — when the response body is absent, undecodable, or not the expected envelope, or when extraction would otherwise fail. Extraction SHALL NOT raise and SHALL NOT change which error type the status code selects.

Diagnostic messages and logs SHALL **omit secrets**, SHALL **not** log the **`Authorization`** header or **`AZURE_DEVOPS_PAT`**, SHALL **not** log request bodies or JSON Patch payloads, and SHALL **not** log **full** response bodies. The bounded envelope diagnostic defined above is the only response-derived content permitted in diagnostics.

On **`429`**, for **all** supported HTTP methods, the client SHALL retry the same logical operation with **bounded** attempts, honoring the **`Retry-After`** header when present and otherwise using **capped exponential backoff**.

For **`GET`** operations (**get**, **list-by-ids**), the client MAY apply **limited** retries for **`5xx`** responses or connection-level failures.

For **`POST`** and **`PATCH`** operations (**create**, **update**, **add comment**), the client SHALL retry **`429`** as above and SHALL **not** implement open-ended **`5xx`** retries; failures SHALL be surfaced so higher layers may treat them as retriable without assuming idempotent side effects.

The client does **not** guarantee idempotency for mutating **`POST`**/**`PATCH`** side effects.

#### Scenario: Unauthorized

- **WHEN** the API responds with `401` or `403`
- **THEN** the error surfaced to the caller SHALL indicate authorization failure without including the PAT

#### Scenario: Rate limited with Retry-After

- **WHEN** the API responds with `429` and a `Retry-After` value
- **THEN** the client SHALL wait per that header (within bounded retry limits) before retrying and SHALL not log full response bodies

#### Scenario: Mutating 5xx not endlessly retried

- **WHEN** a create, update, or comment request receives `5xx` from the server
- **THEN** the client SHALL not apply open-ended automatic retries for that response class

#### Scenario: Client error surfaces Azure DevOps diagnostic

- **WHEN** a work item create returns **400** with an error envelope containing a **`message`**
- **THEN** the raised client error message SHALL include the status code and that message, and the audit record SHALL carry the same non-secret detail

#### Scenario: Diagnostic includes typeKey when present

- **WHEN** the error envelope contains both **`typeKey`** and **`message`**
- **THEN** the emitted diagnostic SHALL include the **`typeKey`** value ahead of the message text

#### Scenario: Unparseable error body degrades to status only

- **WHEN** a request returns **400** with an empty or non-JSON body
- **THEN** the client SHALL raise the status-only error without failing, and the audit record SHALL be emitted without error detail

#### Scenario: Oversized diagnostic is truncated

- **WHEN** the error envelope **`message`** exceeds the documented maximum diagnostic length
- **THEN** the emitted diagnostic SHALL be truncated with an explicit truncation marker

#### Scenario: Auth error diagnostic excludes credentials

- **WHEN** a request fails with **401** or **403** and a response body is present
- **THEN** the emitted diagnostic SHALL NOT contain **`AZURE_DEVOPS_PAT`**, Basic auth material, or **`Authorization`** header values

#### Scenario: Retry paths are unaffected by diagnostic extraction

- **WHEN** a **`GET`** receives **`5xx`** and remains within its recovery retry budget, or any method receives **`429`** within its retry budget
- **THEN** the client SHALL retry as before and SHALL NOT consume the response body for diagnostic extraction on that attempt
