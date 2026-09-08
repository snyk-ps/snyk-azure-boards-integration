## MODIFIED Requirements

### Requirement: Integration HTTP audit logs (P2-FR-6.2)

For **P2-FR-6.2**, the application SHALL emit **one** audit log record per **logical** outbound HTTP request to the **Snyk REST Issues API** and **Azure DevOps Work Item Tracking REST API** at **terminal outcome** (after the respective client’s retry policy for that call concludes—success, terminal HTTP error, or transport failure). Each record SHALL include: **UTC** timestamp, **HTTP method**, **HTTP status code** or explicit **transport** failure class, **elapsed duration**, an **integration** discriminator identifying **Snyk** vs **Azure DevOps**, a **safe request target** (host and path pattern without secrets—no `Authorization` header values, no PAT, no raw tokens in URLs), optional **`sync_run_id`** when a sync run is active, and **non-secret** error detail when the attempt fails.

For **Azure DevOps** terminal **4xx** and **5xx** outcomes, the **error** field SHALL carry the bounded, redacted diagnostic derived from the Azure DevOps error envelope per **`azure-devops-client`** whenever such a diagnostic can be derived. When no diagnostic can be derived, the record SHALL still be emitted with the status code and MAY omit the error field. Records for **`429`** retry-budget exhaustion and transport failures SHALL retain their existing error detail.

The **`integration_audit`** logger SHALL emit each audit record as part of the **NDJSON** contract (**Requirement: NDJSON structured CLI logging (P2-FR-6.x operator usability)**): the fields listed above (including **`event`:** **`integration_http`**) SHALL appear as a **JSON object** under the **`record`** key of a **single-line** JSON log entry written to **standard output**, with **UTC** wall time in the envelope’s **`timestamp`** field (RFC 3339 with **`Z`**).

#### Scenario: Successful Issues GET is audited

- **WHEN** the Snyk issues client completes a **`GET`** to the Issues API with HTTP **2xx** after retries
- **THEN** logs SHALL contain exactly one terminal audit record for that logical call with method, status, duration, `integration` identifying Snyk, and a safe target

#### Scenario: Azure DevOps auth failure is audited without secrets

- **WHEN** the Azure DevOps client receives **401** or **403** on a WIT request
- **THEN** logs SHALL contain an audit record with that status and **SHALL NOT** include the PAT or `Authorization` material

#### Scenario: Failed Azure DevOps mutation is audited with cause

- **WHEN** an Azure DevOps work item create or update concludes with a terminal **400** carrying an error envelope
- **THEN** the **`integration_http`** record SHALL include the **400** status and a non-secret error value naming the Azure DevOps cause

#### Scenario: Operator filters failed Boards calls by cause

- **WHEN** an operator queries **`integration_http`** records where the **integration** discriminator identifies Azure DevOps and the status is **400**
- **THEN** the returned records SHALL expose an error field sufficient to group failures by cause without reproducing the request

#### Scenario: Undeterminable cause still audits the failure

- **WHEN** an Azure DevOps request concludes with a terminal **4xx** whose body yields no derivable diagnostic
- **THEN** exactly one **`integration_http`** record SHALL still be emitted with method, status, duration, and safe target
