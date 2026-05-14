## 1. NDJSON formatter and CLI wiring

- [x] 1.1 Implement NDJSON **`logging`** output (stdlib **`json`**, one compact object + newline per record) to **`sys.stdout`** with **`timestamp`** (UTC RFC 3339 **`Z`**), **`level`**, **`logger`**, optional **`message`**, and optional **`record`** (object).
- [x] 1.2 Replace plain-text **`UtcFormatter`** / default **`stderr`** **`StreamHandler`** in **`configure_cli_logging()`** with the NDJSON path; document behavior in module docstring.
- [x] 1.3 After setup, set **`logging.getLogger("azure").setLevel(logging.WARNING)`** by default; implement a **documented** env-based override for verbose **`azure`** logging.

## 2. `integration_audit` and tests

- [x] 2.1 Update **`integration_audit`** so **`integration_http`** and **`sync_summary`** payloads are emitted under the envelope’s **`record`** key (**P2-FR-6.2** / **P2-FR-6.3** field names unchanged inside **`record`**).
- [x] 2.2 Update **`tests/test_observability_cli_logging.py`** and other tests that assert log line shape (**`caplog`** / captured output): parse JSON lines and assert **`level`**, **`logger`**, **`record.event`** as applicable.
- [x] 2.3 Add or extend unit tests for any **new public** helpers introduced for formatting or record construction.

## 3. Documentation and policy

- [x] 3.1 Update **`README.md`** runbook: **Kusto** examples using **`parse_json`** on the log body column, filters on **`level`** and **`record.*`**; note **stdout** NDJSON and optional **`PYTHONUNBUFFERED=1`** for ACA; document the **`azure`** verbose env override.
- [ ] 3.2 Run **Snyk Code** and **Snyk Open Source** on touched code and dependencies before merge.

## Final (archive only)

- [ ] Merge **`openspec/specs/`** only when archiving: do **not** manually copy **`openspec/changes/ndjson-stdout-logging/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive ndjson-stdout-logging`** (or project equivalent) to promote deltas into canonical specs.
