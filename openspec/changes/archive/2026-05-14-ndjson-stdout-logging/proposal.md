## Why

**Log Analytics** ingestion of **Azure Container Apps** console output is **unfilterable by severity** when logs are plain text on **`stderr`**, and **Azure SDK** **INFO** lines (**`HttpLoggingPolicy`**, Data Tables client) dominate **`ContainerAppConsoleLogs`**. Operators cannot reliably query **`INFO` / `WARNING` / `ERROR`** for the application itself. Emitting **NDJSON** (**one JSON object per line**) to **stdout** with explicit **`level`**, **`logger`**, and **`timestamp`**, and nesting **`integration_audit`** payloads under **`record`**, restores **P2-FR-6.x** operational usability without shipping **Application Insights SDK** telemetry in this change.

## What Changes

- **CLI logging** emits **NDJSON** to **standard output**: each line is one **JSON object** with **`timestamp`** (UTC RFC 3339 **`Z`**), **`level`**, **`logger`**, and (for **`integration_audit`**) a **`record`** object containing existing **`integration_http`** / **`sync_summary`** fields (`event`, durations, safe targets, outcomes—no secrets).
- **Third-party noise:** after configuring CLI logging, **`azure`** loggers default to **WARNING** (or higher) so SDK HTTP **INFO** spam does not hide application logs; optional **documented** env override for deep SDK debugging.
- **`README.md`**: **Kusto** examples updated to **`parse_json`** on the log line column and filter **`level`**, **`record.event`**, **`record.sync_duration_seconds`**, etc.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- **`observability`**: NDJSON stdout contract; **`record`** nesting for audit logs; Azure SDK logger defaults; README alert/query examples aligned with **P2-FR-6.2** / **P2-FR-6.3**.

## Impact

- **`src/observability/cli_logging.py`**, **`src/observability/integration_audit.py`**, tests under **`tests/test_observability_*.py`** and any suites asserting log text, **`README.md`**.

## Non-goals

- **OpenTelemetry** / **Application Insights** exporter libraries (separate change).
- **IaC** for alert rules in-repo.
- Multi-line or pretty-printed JSON per log event.
