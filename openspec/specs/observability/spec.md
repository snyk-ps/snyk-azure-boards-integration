# Observability — health, logging, alerting

Normative requirements for monitoring, transaction logging, and latency detection. Complements Azure platform deployment details in `../azure-platform/spec.md`.

## Functional requirements

| ID | Requirement |
|----|-------------|
| **P2-FR-6** | Provide **automated health monitoring** and **alerting**. |
| **P2-FR-6.1** | Monitor **API connectivity** and **authentication** health for integrated systems (Snyk, Azure DevOps/Boards as applicable). |
| **P2-FR-6.2** | **Log all integration transaction attempts**, including **timestamps**, **HTTP/status codes**, and **error details**. |
| **P2-FR-6.3** | **Detect and report** when **synchronization latency** exceeds **predefined thresholds** (thresholds configurable or documented). |

## Logging & observability (Application Insights, Log Analytics)

As of 2026, ACA often ships an **OpenTelemetry-based monitoring agent**. **Application Insights** (backed by **Log Analytics**) receives **container stdout and stderr**, which appear in tables such as **`ContainerAppConsoleLogs_CL`** — supporting operational review and correlation with **P2-FR-6.2** (timestamps, status codes, errors in structured logs).

The **`sync`** CLI SHALL configure logging so application output is **NDJSON** on **standard output**: one JSON object per line with **`timestamp`**, **`level`**, **`logger`**, optional **`record`**, optional **`message`**, optional **`exception`**, per the normative requirements below.

The application SHALL emit structured audit events on the Python logger named **`integration_audit`** (see normative requirements below): **`event=integration_http`** for each terminal Snyk and Azure DevOps HTTP outcome, and **`event=sync_summary`** once per **`sync`** run with **`sync_duration_seconds`** and **`sync_outcome`**; **`integration_audit`** payloads appear under the NDJSON **`record`** object. Operators use **log-based alerts** to satisfy **P2-FR-6.3** (for example when **`sync_duration_seconds`** exceeds a documented threshold such as **300** seconds). A **custom OpenTelemetry metric** for sync latency is optional and **not** required when this log summary is implemented.

## Alerting (Azure Monitor & Action Groups)

**Azure Monitor Action Groups** (email, SMS, webhook, etc.) fulfill **P2-FR-6** by routing alerts to operators. This repository documents **portal** setup and sample **Kusto** in **`README.md`**; **Terraform / Bicep / ARM** for alert rules are **not** required in-repo.

- **Latency alert:** A **log search / scheduled query** alert on **`sync_summary`** records where **`sync_duration_seconds`** exceeds the operator-chosen threshold (starting point **300** seconds).
- **Availability / authentication alert:** A **log search alert** on **`integration_http`** records whose **`error`** contains **`Authentication Failed`** (or equivalent **401**/**403** handling), e.g. more than **three** matches in **ten** minutes.

---

## Normative requirements (P2-FR-6.x)

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

**P2-FR-6.3** SHALL be satisfied by this summary log and log-based alerting; a **custom OpenTelemetry metric** for sync latency is **not** required.

The **`sync_summary`** fields (`event`, **`sync_duration_seconds`**, **`sync_outcome`**, and non-secret error context) SHALL appear under the NDJSON **`record`** object on the **`integration_audit`** logger in the same manner as **`integration_http`** audit records.

#### Scenario: Successful sync logs duration

- **WHEN** **`sync`** completes successfully
- **THEN** logs SHALL include exactly one summary record with **`sync_outcome`** success and **`sync_duration_seconds`** greater than or equal to zero

#### Scenario: Failed sync still logs duration

- **WHEN** **`sync`** exits with failure
- **THEN** logs SHALL still include exactly one summary record with **`sync_outcome`** indicating failure, **`sync_duration_seconds`**, and non-secret error context

---

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

---

### Requirement: Health via scheduled sync (P2-FR-6.1) and alerting runbook (P2-FR-6)

**P2-FR-6.1** SHALL be satisfied by **scheduled `sync` runs** that perform real Snyk and Azure DevOps calls; the product SHALL **not** require a separate always-on probe workload (no additional Container Apps Job only for health, no HTTP-only health service) to meet this requirement.

**P2-FR-6** SHALL be satisfied by operators configuring **Azure Monitor** alert rules with **Action Groups**. This repository SHALL document the steps in **`README.md`** (**runbook**): create an Action Group, create **log-based** alert rules, and paste or adapt example **Kusto** for (a) **`sync_duration_seconds`** over a chosen threshold, (b) repeated authentication or connectivity failures using stable log fields or substrings produced by the application (aligned with patterns such as **`Authentication Failed`** where applicable), and (c) optional **staleness** (no successful **`sync_outcome`** within **N** times the expected schedule—**N** documented as an operator tuning parameter). **Terraform, Bicep, and ARM templates** for alerts SHALL **not** be required artifacts of this repository.

#### Scenario: Operator follows README for alerts

- **WHEN** an operator configures monitoring using **`README.md`** only
- **THEN** they SHALL be able to attach Action Groups and log-based rules without using IaC from this repo

#### Scenario: Long gap between syncs is detectable via logs

- **WHEN** the operator deploys a staleness alert per the README
- **THEN** absence of successful sync summary logs beyond **N**× the schedule SHALL be detectable via the documented query pattern
