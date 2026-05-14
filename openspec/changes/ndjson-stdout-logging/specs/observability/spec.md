## MODIFIED Requirements

### Requirement: Integration HTTP audit logs (P2-FR-6.2)

For **P2-FR-6.2**, the application SHALL emit **one** audit log record per **logical** outbound HTTP request to the **Snyk REST Issues API** and **Azure DevOps Work Item Tracking REST API** at **terminal outcome** (after the respective client’s retry policy for that call concludes—success, terminal HTTP error, or transport failure). Each record SHALL include: **UTC** timestamp, **HTTP method**, **HTTP status code** or explicit **transport** failure class, **elapsed duration**, an **integration** discriminator identifying **Snyk** vs **Azure DevOps**, a **safe request target** (host and path pattern without secrets—no `Authorization` header values, no PAT, no raw tokens in URLs), optional **`sync_run_id`** when a sync run is active, and **non-secret** error detail when the attempt fails.

The **`integration_audit`** logger SHALL emit each audit record as part of the **NDJSON** contract (**Requirement: NDJSON structured CLI logging (P2-FR-6.x operator usability)**): the fields listed above (including **`event`:** **`integration_http`**) SHALL appear as a **JSON object** under the **`record`** key of a **single-line** JSON log entry written to **standard output**, with **UTC** wall time in the envelope’s **`timestamp`** field (RFC 3339 with **`Z`**).

#### Scenario: Successful Issues GET is audited

- **WHEN** the Snyk issues client completes a **`GET`** to the Issues API with HTTP **2xx** after retries
- **THEN** logs SHALL contain exactly one terminal audit record for that logical call with method, status, duration, `integration` identifying Snyk, and a safe target

#### Scenario: Azure DevOps auth failure is audited without secrets

- **WHEN** the Azure DevOps client receives **401** or **403** on a WIT request
- **THEN** logs SHALL contain an audit record with that status and **SHALL NOT** include the PAT or `Authorization` material

---

### Requirement: Sync duration summary and UTC CLI logging (P2-FR-6.3)

For **P2-FR-6.3**, at the **end of each `sync` run** (all exit paths, success or failure), the application SHALL emit **one** summary log record that includes numeric **`sync_duration_seconds`** (wall-clock seconds for the full sync invocation) and **`sync_outcome`** with documented values (at minimum **`success`** and **`failure`**). Operators MAY define **Azure Monitor log search or scheduled query alerts** on these fields using a **documented** threshold (for example **300** seconds) as a starting point.

The **`sync`** CLI entrypoint SHALL configure the root logger so each log line is **NDJSON** to **standard output** with a **`timestamp`** field that encodes **UTC** wall time in **RFC 3339** form with **`Z`**, satisfying UTC visibility for operators (superseding a plain-text-only **`asctime`** line format).

**P2-FR-6.3** SHALL be satisfied by this summary log and log-based alerting in this change; a **custom OpenTelemetry metric** for sync latency is **not** required.

The **`sync_summary`** fields (`event`, **`sync_duration_seconds`**, **`sync_outcome`**, and non-secret error context) SHALL appear under the NDJSON **`record`** object on the **`integration_audit`** logger in the same manner as **`integration_http`** audit records.

#### Scenario: Successful sync logs duration

- **WHEN** **`sync`** completes successfully
- **THEN** logs SHALL include exactly one summary record with **`sync_outcome`** success and **`sync_duration_seconds`** greater than or equal to zero

#### Scenario: Failed sync still logs duration

- **WHEN** **`sync`** exits with failure
- **THEN** logs SHALL still include exactly one summary record with **`sync_outcome`** indicating failure, **`sync_duration_seconds`**, and non-secret error context

---

## ADDED Requirements

### Requirement: NDJSON structured CLI logging (P2-FR-6.x operator usability)

In addition to audit content required by **P2-FR-6.2** and **P2-FR-6.3**, the application SHALL emit **CLI / runtime** logs to **standard output** as **NDJSON** (**exactly one JSON object per line**, with **no embedded literal newlines** inside the object). Each line SHALL be parseable as JSON and SHALL include at minimum:

- **`timestamp`**: **UTC** wall time (**RFC 3339** with **`Z`** offset).
- **`level`**: The Python log level name in **uppercase** (**`DEBUG`**, **`INFO`**, **`WARNING`**, **`ERROR`**, **`CRITICAL`**).
- **`logger`**: The **`logging`** logger name (e.g. **`integration_audit`**).

For **`integration_audit`** records carrying **`event`:** **`integration_http`** or **`sync_summary`**, the application SHALL include those audit fields as a **JSON object** under **`record`** so operators can filter using **`parse_json(<log column>).record.event`** without parsing a nested stringified JSON blob.

The **`sync`** CLI entrypoint SHALL configure logging to use this NDJSON stdout contract.

#### Scenario: Operator filters by severity in Log Analytics

- **WHEN** logs are ingested into **Log Analytics** from **Container Apps** console output
- **THEN** operators SHALL be able to filter on **`level == "ERROR"`** or **`WARNING`** or **`INFO`** after **`parse_json`** of the log line body without relying solely on unstructured substrings for the envelope

#### Scenario: Sync summary remains queryable on nested fields

- **WHEN** a **`sync`** run completes
- **THEN** the NDJSON line for the summary SHALL expose **`record.event`**, **`record.sync_outcome`**, and **`record.sync_duration_seconds`** for use in **log-based alerts**

---

### Requirement: Azure SDK logging shall not overwhelm application INFO logs

After **CLI logging** is configured, the application SHALL set the **`azure`** parent logger (and thus typical **`azure.*`** child loggers) to **WARNING** or higher **by default**, so routine **Azure SDK** HTTP **INFO** traffic does not obscure **`integration_audit`** records. A **documented** environment-variable override MAY lower **`azure`** verbosity for troubleshooting.

#### Scenario: Default Container Apps deployment is not flooded by SDK HTTP INFO lines

- **WHEN** the workload runs with default logging configuration
- **THEN** **`azure.core.pipeline.policies.http_logging_policy`** SHALL not emit routine per-request **INFO** lines that dominate application logs
