## 1. Fix-availability across all coordinates

- [ ] 1.1 Extract the recognized fix-signal key tuple into a single shared constant so the create gate and the description summary cannot drift apart.
- [ ] 1.2 Rewrite **`attrs_indicate_fix_available`** in **`src/sync/issue_filters.py`** to return **`True`** when any **`coordinates[]`** entry has any recognized signal identical to **`True`**; skip non-dict entries; preserve **`False`** for absent, non-list, or empty **`coordinates`**; update the PEP 257 docstring.
- [ ] 1.3 Update **`fix_signal_labels`** in **`src/sync/issue_content.py`** to union true signals across all coordinates in **`_FIX_SIGNAL_LABELS`** declaration order with no duplicate labels; keep **`is_pinnable`** excluded; update the docstring, which currently states first-coordinate behavior.
- [ ] 1.4 Unit tests for **`attrs_indicate_fix_available`**: signal on first coordinate; signal only on a later coordinate; signals on several coordinates; no signal on any coordinate; empty list; non-list value; key absent; non-dict entries mixed with valid ones; truthy-but-not-**`True`** values rejected.
- [ ] 1.5 Unit tests for **`fix_signal_labels`**: labels unioned across coordinates without duplication; stable ordering; label sourced from a later coordinate; **`is_pinnable`**-only yields no upgrade-path implication.
- [ ] 1.6 Assert in a unit test that the shared signal constant matches the **P2-FR-5.5** list exactly, so the constant and the spec cannot silently diverge.

## 2. Sync behavior for the corrected gate

- [ ] 2.1 Sync integration test: with **`create_only_when_fix_available: true`**, an issue whose only fix signal is on a non-first coordinate results in a work item create and a mapping upsert carrying the new **`work_item_id`**.
- [ ] 2.2 Sync integration test: an issue failing the fix-available policy is skipped and writes **no** mapping row.
- [ ] 2.3 Sync integration test: an issue skipped on a first run is created on a second run once the policy is satisfied, with no backfill step.
- [ ] 2.4 Verify the corrected gate applies at the recreate, reopen, and routing-migration create paths, and add coverage for at least one of them.

## 3. Azure DevOps error detail

- [ ] 3.1 Add a total helper under **`src/integrations/azure_devops/`** that turns an error response body into a bounded, redacted diagnostic: parse the envelope, prefer **`message`**, prefix **`typeKey`** when present, truncate at 512 characters with an explicit marker, redact credential-shaped substrings, and return **`None`** on any failure.
- [ ] 3.2 Read the **`HTTPError`** body once in the terminal **4xx**/**5xx** branch of **`_request_json`**, positioned after the **429** and **`GET`** **5xx** recovery **`continue`** paths, and pass the result as **`error=`** to **`log_integration_http`**.
- [ ] 3.3 Extend **`_raise_http`** to append the diagnostic to the exception message when available, preserving the existing error-type selection by status code and the status-only message when no diagnostic is available.
- [ ] 3.4 Confirm no code path logs request bodies, JSON Patch payloads, **`Authorization`** headers, or **`AZURE_DEVOPS_PAT`**.
- [ ] 3.5 Unit tests for the extraction helper: well-formed envelope with **`message`** and **`typeKey`**; envelope without **`typeKey`**; non-JSON body; empty body; body exceeding the bound is truncated with a marker; credential-shaped content is redacted; malformed input returns **`None`** without raising.
- [ ] 3.6 Client tests: terminal **400** emits an audit record whose error field contains the envelope message; the raised error message contains status and diagnostic; **401**/**403** records still exclude credential material; **429** retry-budget-exhausted and transport-failure records keep their existing error values; retry paths do not consume the body.
- [ ] 3.7 Sync test: a work item create rejected with **400** produces a per-issue skip log containing the Azure DevOps diagnostic and does not fail the run.

## 4. Documentation

- [ ] 4.1 **`CONFIGURATION.md`**: correct the **`create_only_when_fix_available`** description to state that the gate evaluates fix signals across **all** coordinates, list the recognized signals, note that **`is_pinnable`** does not qualify, and add an upgrade note about the expected one-time volume increase and automatic pickup of previously skipped findings.
- [ ] 4.2 **`CONFIGURATION.md`**: in the logging and troubleshooting material, document that failed Azure DevOps calls now carry non-secret error detail on the **`integration_http`** audit record and in the per-issue skip log, with a sample Kusto filter.
- [ ] 4.3 **`README.md`**: update the Error Handling/Logging section to point operators at the error detail on failed Azure DevOps audit records as the first place to look when work item mutations are rejected.

## 5. Verification

- [ ] 5.1 Run the full test suite with **`uv`**; confirm no regression in existing fix-signal, description-assembly, or Azure DevOps client tests.
- [ ] 5.2 Run **Snyk Code** and **Snyk Open Source**; confirm no new high or critical issues and no new dependencies.

## 6. Archive prep

- [ ] 6.1 Merge **`openspec/specs/`** only when archiving: do **not** copy or merge **`openspec/changes/sync-fix-signal-and-ado-error-detail/specs/*.md`** into **`openspec/specs/`** during implementation; run **`openspec archive sync-fix-signal-and-ado-error-detail`** to fold the deltas into the canonical specs.
