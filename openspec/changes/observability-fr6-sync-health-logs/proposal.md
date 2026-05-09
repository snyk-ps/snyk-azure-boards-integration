## Why

**P2-FR-6** through **P2-FR-6.3** require automated monitoring, integration transaction logging, and latency visibility. Each scheduled **`sync`** already exercises Snyk and Azure DevOps, but logs do not yet **uniformly** record every outbound HTTP attempt with UTC timestamps and safe error detail, nor emit a **per-run** **`sync_duration_seconds`** summary for **log-based** threshold alerts. Operators need a **README runbook** for Azure Monitor and Action Groups **without** checking in Terraform, Bicep, or ARM for alerts.

## What Changes

- **P2-FR-6.1:** **`sync`** remains the **sole health probe** for API connectivity and authentication—**no** second Container Apps Job and **no** HTTP-only health service.
- **P2-FR-6.2:** One **audit** log record per **terminal outcome** of each Snyk Issues and Azure DevOps WIT HTTP call (after client retry policy), with UTC time, method, status or transport outcome, duration, safe target (no secrets), optional **`sync_run_id`**, and non-secret error detail on failure.
- **CLI logging:** At minimum the **`sync`** command SHALL configure logging with **UTC** timestamps (not `basicConfig` without `asctime`).
- **P2-FR-6.3:** One **summary** log line per **`sync`** run with **`sync_duration_seconds`** and **`sync_outcome`** so operators can create **log search / scheduled query alerts** (example threshold **300** seconds documented in README). **Custom OpenTelemetry metrics** for sync latency are **out of scope** for this change in favor of **log-based** detection.
- **P2-FR-6:** **`README.md`** SHALL document portal steps: Action Group, **log-based** alert rules, and **copy-paste Kusto** (or equivalent) for duration, repeated auth failures, and optional **staleness** (no successful sync within **N**× schedule). **No** IaC for alerts in this repository.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- **`observability`**: Normative requirements for HTTP audit logs, sync duration summary, sync-as-probe for **P2-FR-6.1**, README-only alerting guidance; **P2-FR-6.3** satisfied via structured summary log (not OTel metric in this change).
- **`sync-lifecycle`**: **`sync_run_id`** correlation; end-of-run **`sync_duration_seconds`** / **`sync_outcome`** summary log.
- **`snyk-issues-client`**: Per-request audit logging requirement.
- **`azure-devops-client`**: Per-request audit logging requirement.

## Impact

- **`src/commands/sync.py`**, **`src/sync/run.py`**, **`src/snyk/client.py`**, **`src/integrations/azure_devops/client.py`**, tests, **`README.md`**.

## Non-goals

- Second job, web health endpoint, or Application Insights availability tests.
- OpenTelemetry custom metric for sync duration (may be a future change).
- Terraform / Bicep / ARM alert definitions in-repo.
