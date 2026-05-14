## Context

CLI entrypoints use **`configure_cli_logging()`** in **`src/observability/cli_logging.py`**, which today attaches a **`StreamHandler`** (default **`stderr`**) and a **`UtcFormatter`** producing human-readable lines. **`integration_audit`** in **`src/observability/integration_audit.py`** logs JSON **strings** for **`integration_http`** and **`sync_summary`**. **Azure** client libraries register INFO loggers (**`azure.core.pipeline.policies.http_logging_policy`**, etc.) that propagate to the root logger and flood **ContainerAppConsoleLogs** when the root level is **INFO**.

## Goals / Non-Goals

**Goals:**

- **NDJSON** on **stdout**: exactly **one** compact **JSON object** per **`print`/write**, terminated by **`\n`**, no literal newlines inside the JSON object.
- **Queryable fields:** **`timestamp`** (RFC 3339, UTC, **`Z`**), **`level`** (**`DEBUG`** / **`INFO`** / **`WARNING`** / **`ERROR`** / **`CRITICAL`**), **`logger`** (name).
- **`integration_audit`:** same semantic payload as today, exposed as a **JSON object** under **`record`** so Kusto can use **`parse_json(Log_s).record.event`** without double-parsing a string field.
- **Default quiet Azure SDK:** **`logging.getLogger("azure").setLevel(logging.WARNING)`** after CLI logging setup; optional **environment variable** (e.g. truthy **`INTEGRATION_VERBOSE_AZURE_LOGS`**) to set **`azure`** to **INFO** or **DEBUG** for troubleshooting—**documented in README**.

**Non-Goals:**

- New PyPI dependencies solely for JSON logging (stdlib **`json`** only).
- Replacing **`integration_audit`** inner field names (`event`, `sync_run_id`, …).
- Changing Azure Container Apps diagnostic settings.

## Decisions

| Decision | Rationale | Alternatives considered |
|----------|-----------|-------------------------|
| **Stdout** for configured app logging | Matches common “data/logs on stdout, errors on stderr” split; ACA ingests both; operators can still query a single table | Stay on stderr: keeps conflating with Python defaults but worsens “all stderr” confusion |
| **Envelope key `record`** for audit payloads | Clear separation from **`message`** / framework fields; stable KQL path **`record.event`** | Nest only under **`message`**: often a string elsewhere—ambiguous |
| **`logging.Formatter` + `json.dumps`** | Fits existing `configure_cli_logging` pattern; minimal churn | Custom **`QueueHandler`/structlog: extra deps or complexity |
| **Suppress `azure` at WARNING** | Removes **`HttpLoggingPolicy`** INFO noise in one place | Per-client pipeline customization: more code, SDK-version sensitive |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Existing **Kusto** alerts use **`contains "sync_summary"`** on raw text | Serialized NDJSON still contains those substrings; README documents **`parse_json`**-based queries for new rules |
| Log agents split on newlines | **Forbidden:** multi-line JSON records; tracebacks escaped into a **single string** field (**`exception`** or **`message`**) |
| **Buffering** in containers | Document **`PYTHONUNBUFFERED=1`** for ACA in README |

## Migration Plan

1. Ship application change; redeploy Container App (job) revision.
2. Operators add or update **log search** alerts using **`parse_json`**; keep legacy **`contains`** rules until verified, then retire.

## Open Questions

- Exact name of the **verbose Azure logs** env var (**`INTEGRATION_VERBOSE_AZURE_LOGS`** vs shorter)—finalize in implementation and README.
