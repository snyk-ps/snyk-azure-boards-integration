## 1. Logging configuration

- [x] 1.1 Update **`sync`** (and align other subcommands that call **`logging.basicConfig`**) so the root logger format includes **UTC** **`asctime`** (ISO-8601 style) and level.
- [x] 1.2 Add tests that logging configuration includes a timestamp field (for example **`caplog`** or **`LogRecord`** inspection).

## 2. Snyk client HTTP audit (**`snyk-issues-client`**)

- [x] 2.1 Implement terminal-outcome audit logging in **`IssuesClient`** for each logical HTTP request: **`integration`** (Snyk), method, status or transport outcome, duration, safe target, optional **`sync_run_id`**, no secrets.
- [x] 2.2 Unit tests with injectable **`opener`**: success (**2xx**), **401/403**, transport error—verify audit emission and no token leakage.

## 3. Azure DevOps client HTTP audit (**`azure-devops-client`**)

- [x] 3.1 Implement the same for **`WorkItemsClient`** with **`integration`** discriminating Azure DevOps.
- [x] 3.2 Unit tests parallel to **2.2** (including **403**, no PAT in logs).

## 4. Sync correlation and summary (**`sync-lifecycle`**)

- [x] 4.1 Generate **`sync_run_id`** at **`sync`** start; thread through orchestration so clients receive correlation (constructor param, context, or equivalent per **`design.md`**).
- [x] 4.2 Wrap **`run_sync`** (or entrypoint) so **every** exit path emits **one** summary log: **`sync_duration_seconds`**, **`sync_outcome`**, **`sync_run_id`**, non-secret failure context.
- [x] 4.3 Tests: stubbed clients; assert exactly one summary and bounded **`sync_duration_seconds`**; assert **`sync_run_id`** appears on audit logs when applicable.

## 5. Documentation (**`observability` / operators**)

- [x] 5.1 Extend **`README.md`** with an **Alerting runbook**: Action Group; **log-based** rules; sample **Kusto** for **`sync_duration_seconds`** &gt; threshold (document **300s** as starting point); repeated auth/connectivity pattern matching implementation; optional **staleness** (no **`sync_outcome`=`success`** within **N**× schedule). State that **IaC for alerts is not** in this repo.
- [x] 5.2 Match Kusto examples to the **actual** log line format chosen in implementation (JSON vs key=value).

## 6. Spec merge (at archive)

- [x] 6.1 Merge **`openspec/changes/observability-fr6-sync-health-logs/specs/**`** into **`openspec/specs/**`** and update **`openspec/config.yaml`** context as part of **`openspec archive change`**.
