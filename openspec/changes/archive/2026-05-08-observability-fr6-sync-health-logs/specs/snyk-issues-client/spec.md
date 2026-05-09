## ADDED Requirements

### Requirement: Terminal HTTP audit logging for Issues API calls

The **`IssuesClient`** SHALL emit **one** Python **`logging`** audit line per **logical** HTTP request to the Snyk Issues REST API at **terminal outcome** (after bounded **429** retry handling or other client-side retries defined for that method), at **`INFO`** for success and **`WARNING`** or **`ERROR`** for failure as appropriate. Each line SHALL satisfy the **safe** URL and **no-credentials** rules in the **`observability`** capability for **P2-FR-6.2**. When the caller supplies **`sync_run_id`** (or equivalent correlation), the client SHALL include it in the audit output.

#### Scenario: 200 response produces audit

- **WHEN** a Issues **`GET`** completes with HTTP **200** after retries
- **THEN** the client SHALL have emitted exactly one terminal audit log for that logical request with status **200**

#### Scenario: 401 is audited

- **WHEN** a Issues request fails with HTTP **401**
- **THEN** the client SHALL emit an audit log with status **401** and **SHALL NOT** log **`SNYK_TOKEN`** or **`Authorization`** contents
