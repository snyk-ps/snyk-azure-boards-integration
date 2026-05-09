## ADDED Requirements

### Requirement: Terminal HTTP audit logging for WIT API calls

The **`WorkItemsClient`** SHALL emit **one** Python **`logging`** audit line per **logical** HTTP request to Azure DevOps WIT (including work item comments) at **terminal outcome** (after bounded **429** retry and any **GET** recovery retries defined for that method), at **`INFO`** for success and **`WARNING`** or **`ERROR`** for failure as appropriate. Each line SHALL satisfy the **safe** URL and **no-credentials** rules in the **`observability`** capability for **P2-FR-6.2**. When the caller supplies **`sync_run_id`** (or equivalent correlation), the client SHALL include it in the audit output.

#### Scenario: Work item GET succeeds and is audited

- **WHEN** a **`GET`** work item call completes with HTTP **200**
- **THEN** the client SHALL have emitted exactly one terminal audit log for that logical request with status **200**

#### Scenario: 403 is audited without PAT

- **WHEN** a WIT request fails with HTTP **403**
- **THEN** the client SHALL emit an audit log with status **403** and **SHALL NOT** log **`AZURE_DEVOPS_PAT`** or Basic auth material
