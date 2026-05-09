## Context

The integration runs **scheduled `sync`** on **Azure Container Apps**; **Application Insights / Log Analytics** ingests **stdout/stderr** (for example **`ContainerAppConsoleLogs_CL`**). Operators need **correlatable** HTTP audit logs, a **per-run duration** field for **log-based alerts**, and **portal-only** alerting setup—no second job, no web health service, no IaC for Monitor rules in this repo.

## Goals / Non-Goals

**Goals:**

- One **terminal-outcome** audit log per Snyk Issues and Azure DevOps WIT HTTP call (after client retry policy), with UTC timestamps, method, status or transport outcome, duration, safe route, optional **`sync_run_id`**, no secrets.
- **`sync_run_id`** generated at **`sync`** start; echoed on HTTP audits and on **one** end-of-run summary line with **`sync_duration_seconds`** and **`sync_outcome`** (**P2-FR-6.3** via logs, not OTel custom metric in this change).
- Configure **`sync`** logging with **UTC** time in the format string (fix plain **`basicConfig`** without **`asctime`**).
- **`README.md`** runbook: Action Group, log alerts for duration / repeated auth patterns / optional staleness, with **Kusto** samples.

**Non-Goals:**

- OpenTelemetry **custom metric** emission for sync latency.
- Terraform, Bicep, or ARM **checked in** for alerts.
- Second Container Apps Job, **liveness HTTP** endpoint, or Availability Tests.
- Logging full request/response bodies.

## Decisions

| Decision | Rationale |
|----------|-----------|
| **Sync as sole health probe** | Satisfies **P2-FR-6.1** with least infrastructure; staleness query covers missed schedules. |
| **Log `sync_duration_seconds` + log alerts** | No metric pipeline; aligns with **Application Insights** log tables operators already use. |
| **One audit line per logical HTTP call at terminal outcome** | Avoids noise from 429 retry loops; optional **`DEBUG`** per-attempt lines are implementation detail. |
| **Safe URL logging** | Log **host + path pattern** (template or normalized path); never **`Authorization`**, PAT, or **`token`** query params. |
| **`sync_run_id`** UUID per **sync** invocation | Correlates **P2-FR-6.2** lines with the **P2-FR-6.3** summary for triage. |
| **stdlib `logging`** | Matches **guidelines** (prefer stdlib); JSON formatter vs key=value left to implementation—README Kusto must match chosen format. |

**Alternatives considered:** OTel custom metric for duration (deferred); separate probe job (rejected by product choice).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| High-volume lists → many log lines | Acceptable; one line per HTTP still bounded; no body logging. |
| Kusto table/column variance across workspaces | README examples labeled **samples**; operators adapt **`ContainerAppConsoleLogs_CL`** or connected workspace. |
| Auth alert false positives | Align stable log substring/field with existing **`Authentication Failed`** / client error mapping. |

## Migration Plan

1. Ship logging + client audit + sync summary behind normal release.
2. Operators add or update **log-based** alert rules using new fields; no data migration.

## Open Questions

- Final choice of **structured JSON** vs **key=value** log lines (resolve during implementation; document in README).
