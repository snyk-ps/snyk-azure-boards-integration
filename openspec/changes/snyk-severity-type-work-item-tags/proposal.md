## Why

Downstream reporting (for example WIQL, dashboards, or Elasticsearch) needs **stable, queryable** severity and finding-type dimensions on Azure Boards work items. Today those attributes appear mainly in **human-readable** description text, which is a poor contract for automation.

## What Changes

- **`sync`** SHALL append **derived** work item tags for **Snyk effective severity** and **Snyk finding type**, using **reserved prefix** names, on every work item **create** and **update** where Azure DevOps mutations already apply.
- **Operator tags** from merged **`work_item_template.tags`** (**P2-FR-10**) SHALL **all** be preserved in the combined tag set sent to Azure DevOps — **no omission** of configured tags in favor of derived tags.
- Derived tags SHALL **replace themselves** when Snyk data changes (for example severity **high** → **medium**): at most **one** managed severity tag and **one** managed type tag per work item after each sync, with values reflecting the **current** issue payload.
- Operators SHALL be directed to **avoid** the reserved prefixes in YAML `tags`; if present, the application SHALL treat them as superseded by canonical managed tags from the issue.

**BREAKING**: None (additive behavior; existing configs without reserved-prefix tags behave as before plus new managed tags when derivable).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- **`sync-lifecycle`**: Combine **P2-FR-10** template tags with **Snyk-derived** severity and type tags; define managed prefix vocabulary and merge order.
- **`application-config`**: Document reserved tag prefixes and interaction with **`work_item_template.tags`** (operator guidance and collision rule).

## Impact

- **`src/sync/`** (patch assembly, sync run): merge tag lists before JSON Patch.
- **Tests**: tag merge, reserved-prefix collision, severity/type normalization edge cases.
- **README** / samples: short note on managed tags and prefixes (per `application-config`).
- **No** new OpenSpec capability directories; deltas only under existing capabilities.
