## ADDED Requirements

### Requirement: Integration HTTP audit logs (P2-FR-6.2)

For **P2-FR-6.2**, the application SHALL emit **one** audit log record per **logical** outbound HTTP request to the **Snyk REST Issues API** and **Azure DevOps Work Item Tracking REST API** at **terminal outcome** (after the respective client’s retry policy for that call concludes—success, terminal HTTP error, or transport failure). Each record SHALL include: **UTC** timestamp via the configured log formatter, **HTTP method**, **HTTP status code** or explicit **transport** failure class, **elapsed duration**, an **integration** discriminator identifying **Snyk** vs **Azure DevOps**, a **safe request target** (host and path pattern without secrets—no `Authorization` header values, no PAT, no raw tokens in URLs), optional **`sync_run_id`** when a sync run is active, and **non-secret** error detail when the attempt fails.

#### Scenario: Successful Issues GET is audited

- **WHEN** the Snyk issues client completes a **`GET`** to the Issues API with HTTP **2xx** after retries
- **THEN** logs SHALL contain exactly one terminal audit record for that logical call with method, status, duration, `integration` identifying Snyk, and a safe target

#### Scenario: Azure DevOps auth failure is audited without secrets

- **WHEN** the Azure DevOps client receives **401** or **403** on a WIT request
- **THEN** logs SHALL contain an audit record with that status and **SHALL NOT** include the PAT or `Authorization` material

---

### Requirement: Sync duration summary and UTC CLI logging (P2-FR-6.3)

For **P2-FR-6.3**, at the **end of each `sync` run** (all exit paths, success or failure), the application SHALL emit **one** summary log record that includes numeric **`sync_duration_seconds`** (wall-clock seconds for the full sync invocation) and **`sync_outcome`** with documented values (at minimum **`success`** and **`failure`**). Operators MAY define **Azure Monitor log search or scheduled query alerts** on these fields using a **documented** threshold (for example **300** seconds) as a starting point.

The **`sync`** CLI entrypoint SHALL configure the root logger with a format that includes **UTC** time (for example ISO-8601 **`asctime`**).

**P2-FR-6.3** SHALL be satisfied by this summary log and log-based alerting in this change; a **custom OpenTelemetry metric** for sync latency is **not** required.

#### Scenario: Successful sync logs duration

- **WHEN** **`sync`** completes successfully
- **THEN** logs SHALL include exactly one summary record with **`sync_outcome`** success and **`sync_duration_seconds`** greater than or equal to zero

#### Scenario: Failed sync still logs duration

- **WHEN** **`sync`** exits with failure
- **THEN** logs SHALL still include exactly one summary record with **`sync_outcome`** indicating failure, **`sync_duration_seconds`**, and non-secret error context

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
