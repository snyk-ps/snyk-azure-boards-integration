## Context

**`attrs_indicate_fix_available`** in **`src/sync/issue_filters.py`** gates work item creation when **`create_only_when_fix_available`** is enabled. It selects **`coordinates[0]`** and tests five boolean flags on that single object. **`fix_signal_labels`** in **`src/sync/issue_content.py`** does the same for the description summary. **`sync-lifecycle`** **P2-FR-5.5** already specifies reading signals from **each** **`coordinates[]`** object, so both call sites are non-conformant.

The Snyk REST Issues API returns one **`coordinates[]`** entry per introduction path or representation. A transitive dependency reachable by several paths commonly carries the actionable signal on a path other than the first, and API ordering is not guaranteed to place a fixable coordinate first. The gate runs against the **enriched** issue view (after the **`GET /…/issues/{issue_id}`** merge), so coordinates added by enrichment are already in scope.

Separately, **`WorkItemsClient._request_json`** catches **`HTTPError`**, calls **`log_integration_http`** without an **`error`** argument, and then **`_raise_http`** builds the exception message from **`_status_message(code)`** alone. The **`429`**-exhausted, **`URLError`**, and **`OSError`** branches already pass **`error=`**, so the field exists in the audit contract and only the terminal 4xx/5xx branch omits it. Azure DevOps returns a JSON error envelope on these responses containing **`message`**, **`typeKey`**, **`typeName`**, and **`errorCode`**.

## Goals / Non-Goals

**Goals:**

- Fix-availability determination that matches the existing **P2-FR-5.5** wording: signals read from **all** coordinates.
- Operator-visible, non-secret cause for every failed Azure DevOps mutation, in both the **`integration_http`** audit record and the per-issue skip log.
- No configuration surface change; no behavior change when **`create_only_when_fix_available`** is **`false`**.

**Non-Goals:**

- Changing the recognized fix-signal set, including whether **`is_pinnable`** should count. Deliberately deferred — that decision changes which Snyk filter the gate targets and warrants its own change with reconciliation evidence.
- Aligning the gate with a specific Snyk report column (**Computed Fixability** vs **"Fixed in" Available**). The Snyk REST Issues API exposes no single equivalent boolean; parity work belongs with the Export API and is out of scope.
- Logging full Azure DevOps response bodies, request bodies, or JSON Patch payloads.
- Retry, backoff, or recovery behavior changes for any status class.
- Closing work items for findings no longer present in Snyk.

## Decisions

### 1. Fix-signal evaluation

```
FIX_SIGNAL_KEYS = (
    "is_upgradeable", "is_patchable",
    "is_fixable_manually", "is_fixable_snyk", "is_fixable_upstream",
)

attrs_indicate_fix_available(attrs):
    coords := attrs["coordinates"]
    if coords is not a non-empty list: return False
    return any(
        c.get(k) is True
        for c in coords if isinstance(c, dict)
        for k in FIX_SIGNAL_KEYS
    )
```

Identity comparison against **`True`** is retained (rather than truthiness) so string or numeric values in a partial payload do not satisfy the gate. Non-dict entries are skipped rather than raising, matching current tolerance for partial payloads. Absent, non-list, or empty **`coordinates`** remains **`False`** — no fix signal means the gate stays closed.

**Alternative considered:** short-circuit on the first coordinate that has *any* key present, on the theory that later coordinates are duplicates. Rejected — coordinates represent distinct introduction paths with independently populated flags, so presence of a key on one coordinate says nothing about the others.

**`fix_signal_labels`** applies the same traversal, unioning true signals across coordinates and preserving the declaration order of **`_FIX_SIGNAL_LABELS`** so description output is stable across runs for the same input. **`is_pinnable`** stays excluded per the existing **P2-FR-5.5** scenario.

The signal key tuple is currently duplicated between the two modules. It moves to a single shared constant so the gate and the summary cannot drift apart.

Enrichment is unaffected: **`needs_issue_detail`** and remedy extraction already evaluate all coordinates, so no GET-enrichment change is required.

### 2. Recovery of previously skipped issues

No backfill or migration path is needed, because a skipped issue leaves no persisted decision:

- Snyk list filtering sends only **`version`**, **`limit`**, **`effective_severity_level`**, **`type`**, and **`status`**. There is **no** server-side fix predicate, so the issue is returned on every run regardless of prior skips.
- The gate returns **before** any **`store.upsert`** call. Mapping rows are written only for origin-excluded issues and after a successful Azure DevOps mutation, so a skipped issue has no row and remains **unmapped** on the next run.
- Work item create and the mapping upsert occur in the same branch, so the row and the work item id appear together.

The corrected gate therefore applies on the next scheduled run through the ordinary unmapped-create path. The same gate guards the recreate-when-mapped-id-missing, reopen, and routing-migration paths, which recover identically. Work items created this way carry the run's timestamp, not the original Snyk discovery date; no retroactive dating is attempted.

### 3. Azure DevOps error detail

Azure DevOps error envelope (WIT REST):

```json
{ "message": "...", "typeKey": "...", "typeName": "...", "errorCode": 0 }
```

Extraction lives in **`src/integrations/azure_devops/`** as a total helper:

- Read the body from the **`HTTPError`** once, decode as UTF-8 with replacement, parse JSON.
- Use the envelope **`message`** only. When the body is not the documented envelope, or carries no usable **`message`**, return nothing rather than echoing arbitrary response content into logs.
- Prepend **`typeKey`** when present, producing search-friendly detail such as **`TF401320: <message>`**.
- **Truncate** to a documented maximum of **480** characters with an explicit truncation marker. The bound sits below the existing **500**-character clamp that **`log_integration_http`** applies to **`error`** values, so the marker survives into the emitted record.
- **Redact** credential-shaped content before emission, reusing the patterns already applied for safe-target construction.
- On any decoding, parsing, or shape failure, return **`None`** and degrade to the current status-only message. Extraction SHALL NOT raise and SHALL NOT change which exception class the status code selects.

Wiring:

| Site | Change |
|------|--------|
| Terminal **4xx**/**5xx** **`log_integration_http`** | pass **`error=<detail>`** |
| **`_raise_http`** | message becomes **`Azure DevOps API HTTP error {code}: {detail}`** when detail is available; unchanged when not |
| **`429`** exhausted, **`URLError`**, **`OSError`** | unchanged (already carry **`error=`**) |

**`401`**/**`403`** keep their existing audit **`error`** value of **`Authentication Failed (HTTP {code})`**, which **`log_integration_http`** substitutes unconditionally and on which operators already alert. The redacted diagnostic still reaches the raised exception message for those statuses, so triage gains the Azure DevOps text without disturbing the alerting contract.

The body is read only in the terminal branch, after the **429** and **5xx** GET-recovery paths have already taken their **`continue`**, so no retry path consumes a stream it still needs.

Because per-issue handling in **`run.py`** logs the caught exception, the detail reaches the per-issue skip line with no change in **`run.py`**.

### 4. Why a bounded excerpt rather than the full body

**`azure-devops-client`** currently states diagnostics SHALL NOT log full response bodies by default. That rule exists to avoid echoing field values, identities, and payload fragments into logs. The envelope **`message`** is a server-authored diagnostic naming the failing field or type, not a copy of the request, so a bounded excerpt preserves the rule's intent while satisfying the **P2-FR-6.2** error-detail obligation. The spec delta narrows the prohibition rather than removing it.

**Alternative considered:** emit the full body behind a debug-only flag. Rejected — it adds a configuration surface for a diagnostic that should be available by default on the failures operators actually need to triage, and a debug flag is rarely enabled at the moment a production failure occurs.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Work item volume rises where **`create_only_when_fix_available: true`** | Documented in **`CONFIGURATION.md`** as an intended correction; operators can narrow scope via **`severity_threshold`**, origin allowlist, or **`issues_sync_from`** |
| Azure DevOps error message echoes a submitted field value into logs | Bounded excerpt, credential redaction, no request body or JSON Patch logged; **`message`** is server-authored, not a payload copy |
| Reading the error body consumes an **`HTTPError`** stream needed by a retry path | Read exactly once in the terminal branch, after all retry branches have taken **`continue`** |
| Detail extraction raises and masks the original error | Extraction is total; every failure mode returns **`None`** and falls back to status-only |
| Larger log records in Log Analytics | 512-character cap, emitted only on failure |
| Shared signal constant drifts from spec wording | Constant is referenced by both call sites and asserted in unit tests against the **P2-FR-5.5** list |

## Migration Plan

No mapping-store migration, no configuration migration, no operator action required. Deployment is a normal revision rollout; rollback is a revision revert with no persisted state to unwind.

Operators running **`create_only_when_fix_available: true`** SHOULD expect a one-time increase in created work items on the first run after upgrade, as previously skipped findings qualify. Because those findings were never persisted, recovery is automatic and needs no replay command. Operators who want the prior volume must narrow scope through existing keys; the first-coordinate behavior is not preserved behind a flag.

## Open Questions

- *(None — signal set unchanged by decision; excerpt bound set at 512 characters; **`is_pinnable`** deferred to a separate change.)*
