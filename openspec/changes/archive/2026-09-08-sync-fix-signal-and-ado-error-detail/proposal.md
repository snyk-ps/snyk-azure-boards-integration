## Why

Two defects reduce the accuracy and diagnosability of **`sync`** runs.

**1. Fix-availability gate reads only the first coordinate.** **`sync-lifecycle`** (**P2-FR-5.5**) requires the application to read boolean fix signals from **each** **`coordinates[]`** object. The implementation inspects **`coordinates[0]`** only, both in the **`create_only_when_fix_available`** create gate and in the human-readable fix-availability summary. A Snyk issue whose fix signal appears on a later coordinate is treated as having no fix, so no work item is created and no fix guidance is surfaced. Snyk derives fix availability across all coordinates for an issue, so the current behavior under-counts qualifying findings relative to Snyk.

**2. Azure DevOps error responses are discarded.** **`observability`** (**P2-FR-6.2**) requires **non-secret** error detail on integration HTTP audit records when an attempt fails. For terminal Azure DevOps **4xx**/**5xx** outcomes the client emits the audit record without any error detail, and the raised exception message carries only the status code. Azure DevOps returns a structured error envelope whose **`message`** and **`typeKey`** name the actual cause (invalid field value, missing required field, unknown work item type, invalid area path). Operators see only the status code and cannot determine why work item mutations were rejected without reproducing the call by hand.

Both are conformance defects against requirements already in **`openspec/specs/`**, not gaps in capability.

## What Changes

- **Fix-signal evaluation across all coordinates**: **`attrs_indicate_fix_available`** SHALL return **true** when **any** **`coordinates[]`** entry has **any** recognized fix signal set to **`true`**. The recognized signal set is **unchanged** (**`is_upgradeable`**, **`is_patchable`**, **`is_fixable_manually`**, **`is_fixable_snyk`**, **`is_fixable_upstream`**).
- **Fix-availability summary across all coordinates**: **`fix_signal_labels`** SHALL derive displayed labels from the union of true signals across all coordinates rather than the first coordinate only, aligning the implementation with the existing **P2-FR-5.5** requirement. **`is_pinnable`** remains excluded from the displayed summary and from the create gate.
- **Azure DevOps error detail**: the client SHALL parse the Azure DevOps error envelope on terminal **4xx**/**5xx** outcomes, extract a **bounded, redacted** diagnostic from **`message`** (and **`typeKey`** when present), include it as the **`error`** field on the **`integration_http`** audit record, and append it to the raised exception message so per-issue **`sync`** skip logs name the cause.
- **Docs**: **`CONFIGURATION.md`** and **`README.md`** updated for the corrected **`create_only_when_fix_available`** semantics and for the error detail now available in logs.

**Not breaking, but expect a volume change:** no configuration key changes and no behavior change when **`create_only_when_fix_available`** is **`false`**. Operators running **`create_only_when_fix_available: true`** SHALL expect **more** qualifying findings after this change, because issues previously excluded on a first-coordinate-only reading now qualify. This is a correction toward Snyk parity, not a policy change. Previously skipped issues are picked up on the next scheduled run with no backfill step, because a skipped issue persists no mapping row and Snyk list filtering applies no server-side fix predicate.

## Capabilities

### New Capabilities

- *(None — corrects conformance defects in existing capabilities.)*

### Modified Capabilities

- **`sync-lifecycle`**: add an explicit normative requirement for the **`create_only_when_fix_available`** gate evaluating **all** coordinates (**`application-config`** currently defines the key by deferral to this capability, which has no dedicated requirement for it); amend **P2-FR-5.5** so summary derivation across all coordinates is explicit and testable.
- **`azure-devops-client`**: amend **HTTP errors, logging, and retries** to permit a bounded, redacted excerpt of the Azure DevOps error envelope in diagnostics, narrowing the blanket prohibition on response-body content while preserving the no-secrets and no-full-body rules.
- **`observability`**: amend **Integration HTTP audit logs (P2-FR-6.2)** to make the error-detail obligation explicit and testable for Azure DevOps terminal HTTP failures.

## Impact

- **`src/sync/issue_filters.py`** — **`attrs_indicate_fix_available`** iterates all coordinates
- **`src/sync/issue_content.py`** — **`fix_signal_labels`** unions signals across coordinates
- **`src/integrations/azure_devops/client.py`** — error envelope parsing, redaction, bounded excerpt; wired into **`_raise_http`** and the terminal **`log_integration_http`** call
- **`src/integrations/azure_devops/errors.py`** — optional structured detail on the error types
- **`tests/`** — fix-signal unit tests (later-coordinate, multi-coordinate, none, malformed), error-envelope parsing and redaction, audit record carries **`error`**, exception message carries detail
- **`CONFIGURATION.md`**, **`README.md`**
- **No configuration schema change** — no new keys, no new environment variables
- **No mapping-store migration**
- **No new Python dependencies**
- **Out of scope**: closing work items for findings no longer present in Snyk
