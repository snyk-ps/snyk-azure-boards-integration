# Observability — health, logging, alerting

Normative requirements for monitoring, transaction logging, and latency detection. Complements Azure platform deployment details in `../azure-platform/spec.md`.

## Functional requirements

| ID | Requirement |
|----|-------------|
| **P2-FR-6** | Provide **automated health monitoring** and **alerting**. |
| **P2-FR-6.1** | Monitor **API connectivity** and **authentication** health for integrated systems (Snyk, Azure DevOps/Boards as applicable). |
| **P2-FR-6.2** | **Log all integration transaction attempts**, including **timestamps**, **HTTP/status codes**, and **error details**. |
| **P2-FR-6.3** | **Detect and report** when **synchronization latency** exceeds **predefined thresholds** (thresholds configurable or documented). |

## Logging & observability (OpenTelemetry, Application Insights, Log Analytics)

As of 2026, ACA uses an **OpenTelemetry-based monitoring agent**. **Application Insights** (backed by **Log Analytics**) receives **container stdout and stderr**, which appear in the **`ContainerAppConsoleLogs_CL`** table — supporting operational review and correlation with **P2-FR-6.2** (timestamps, status codes, errors in structured or textual logs as implemented by the app).

The application should emit a **custom OpenTelemetry metric** for **sync latency** (e.g. end-to-end duration of a sync cycle or per-finding processing) to support **P2-FR-6.3** (threshold-based detection of slow synchronization).

## Alerting (Azure Monitor & Action Groups)

**Azure Monitor Action Groups** (email, SMS, webhook, etc.) fulfill **P2-FR-6** by routing alerts to operators.

- **Latency alert:** A **metric alert** on the average **“Sync Duration”** (or equivalent emitted OTel metric) that fires when the average exceeds **300 seconds** over the evaluation window.
- **Availability / authentication alert:** A **log search alert** that fires when the string **`Authentication Failed`** appears in logs **more than three times within ten minutes**, indicating repeated auth or connectivity failures worth investigating.
