## ADDED Requirements

### Requirement: Sync run correlation and duration summary

The **`sync`** command orchestration SHALL generate a unique **`sync_run_id`** at the start of each **`sync`** invocation and SHALL pass it into **Snyk** and **Azure DevOps** client usage so **P2-FR-6.2** HTTP audit logs can be correlated for that run.

The **`sync`** orchestration SHALL emit exactly **one** summary log record at the end of every **`sync`** invocation (all exit paths) containing **`sync_duration_seconds`**, **`sync_outcome`**, and **`sync_run_id`**, as specified in the **`observability`** capability.

#### Scenario: sync_run_id ties HTTP audits to summary

- **WHEN** **`sync`** runs to completion with logging enabled
- **THEN** HTTP audit logs from Snyk and Azure DevOps for that invocation SHALL carry the same **`sync_run_id`** as the final summary log

#### Scenario: Summary emitted once per invocation

- **WHEN** **`sync`** is invoked once
- **THEN** exactly one summary log with **`sync_duration_seconds`** SHALL be emitted for that invocation
