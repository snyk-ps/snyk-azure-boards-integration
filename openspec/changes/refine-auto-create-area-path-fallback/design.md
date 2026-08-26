## Context

**`sync`** resolves effective area path per **`repo-area-path-mapping`** precedence (CSV → org override → defaults → fallback → unset). When **`auto_create_area_path: true`**, the shipped implementation ensures the **full effective path** regardless of source — including auto-creating segments from CSV or YAML **`area_path`** values.

Operators want **`auto_create_area_path`** to mean **default + fallback only**: synthesize a dedicated fallback area when none is configured, and substitute that fallback when a configured path is **missing** in Azure DevOps — without auto-provisioning arbitrary configured segments.

Classification Nodes GET (already in **`azure-devops-client`**) can test strict full-path existence. Audit comments for area-path changes follow existing **P2-FR-9** patterns in **`run.py`**.

## Goals / Non-Goals

**Goals:**

- **`auto_create_area_path: true`** = default fallback when unset, substitute fallback when configured path missing (strict full-path check), ensure/create **fallback path only**.
- Configurable fallback template **`auto_create_fallback_area_path`** with **`{project}`** placeholder; settable in **`defaults`**, **`ado_targets[]`**, **`org_mappings[].overrides`**, and env **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH`**.
- INFO logging and **P2-FR-9** audit comments when fallback is assigned (**`auto_default`** or **`auto_fallback`**).
- Clear docs and migration note for intentional behavior change.

**Non-Goals:**

- Auto-create iteration paths; rename/delete/reparent area nodes.
- Auto-create configured CSV/YAML area segments after this change.
- Hot-reload of config mid-run; bulk area-tree sync.
- Additional template placeholders beyond **`{project}`** in v1.
- **`auto_create_area_path`** boolean on **`ado_targets[]`** (defer — boolean remains on **`defaults`** / **`org_mappings` overrides** only).

## Decisions

### 1. Config shape

```yaml
azure_boards:
  defaults:
    auto_create_area_path: true
    auto_create_fallback_area_path: "{project}\\Snyk"  # default when omitted

  ado_targets:
    - organization: "myado"
      project: "PaymentsProject"
      auto_create_fallback_area_path: "{project}\\Security"

  org_mappings:
    - organization: "myado"
      project: "PaymentsProject"
      snyk_org_id: "..."
      snyk_org_slug: "..."
      overrides:
        auto_create_fallback_area_path: "{project}\\Triage"
```

- **`auto_create_fallback_area_path`**: optional string template; load-time validation (non-empty, contains **`{project}`**, renders to valid **`Project\Area`** shape).
- When **`auto_create_area_path`** is **`true`** and template omitted → **`{project}\Snyk`** (backward-compatible default).
- Env **`AZURE_BOARDS_AUTO_CREATE_FALLBACK_AREA_PATH`** overrides **`defaults.auto_create_fallback_area_path`** at load (**defaults → YAML → env → CLI**), same as **`AZURE_BOARDS_ORGANIZATION`**.

**Runtime template precedence** (per issue, effective **`(organization, project)`**):

1. Matching **`ado_targets`** entry
2. **`org_mappings[].overrides`** when org-mapping target matches effective ADO target
3. Merged **`defaults`** (includes env-seeded value)

This mirrors work-item taxonomy precedence (**`ado_targets`** → org override → defaults) but applies only to the fallback template, not configured area paths from CSV.

### 2. Runtime resolution algorithm

When **`auto_create_area_path: true`**:

```
configured_path := CSV → org_override → defaults (may be unset)
fallback_template := ado_targets → org_override → defaults
fallback_path := render(fallback_template, effective_ado_project)

if configured_path is unset:
    effective_path := fallback_path
    area_path_source := "auto_default"
else:
    if classification_get(full configured_path) == 200:
        effective_path := configured_path
        area_path_source := unchanged ("csv" | "org_override" | "defaults")
    else:  # strict full path — 404 or missing leaf
        effective_path := fallback_path
        area_path_source := "auto_fallback"

if area_path_source in ("auto_default", "auto_fallback"):
    ensure_area_path_exists(fallback_path)  # create missing fallback segments only
```

**Existence check:** GET Classification Node for the **complete** configured path. Parent exists but leaf missing → **not found** → fallback.

**Where logic lives:** **`resolve_routing`** continues to resolve configured paths and **`auto_default`** when unset (using template). **`finalize_area_path_for_auto_create(...)`** in **`sync/area_path.py`** (or adjacent module) performs existence check + **`auto_fallback`** substitution at sync time (requires ADO client). Per-sync-run cache: **`(org, project, path) → exists`**.

### 3. Logging and audit (P2-FR-9)

**INFO log** when **`area_path_source`** is **`auto_default`** or **`auto_fallback`**, including configured path when **`auto_fallback`**.

**Audit comment** after successful create/recreate/update that sets fallback area path:

- **`auto_fallback`**: documents configured path not found and fallback applied.
- **`auto_default`**: documents default fallback assigned (no configured path).

**Idempotency:** when work item already at effective fallback path, do **not** add duplicate fallback audit on subsequent runs (same rule as unchanged area-path move comment).

Replace hardcoded **`AUTO_DEFAULT_AREA_SEGMENT = "Snyk"`** with template rendering everywhere.

### 4. Error handling

| Condition | Behavior |
|-----------|----------|
| Configured path exists (full GET) | Use it; no ensure; no fallback audit |
| Configured path missing | Substitute fallback; ensure fallback; log + audit |
| Fallback ensure 403/401/400 | Skip issue; log permissions/diagnostic; continue run |
| **`auto_create_area_path: false`** | No existence check; configured missing path → ADO patch may 400 (unchanged) |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **BREAKING**: operators relied on auto-creating CSV paths | Document migration in **`CONFIGURATION.md`**; pre-create paths or disable flag |
| Extra ADO GET per issue with configured path | Per-run existence cache keyed by **`(org, project, full_path)`** |
| Template typo creates wrong hierarchy | Load-time validation; ensure only on fallback path |
| Audit comment noise on every create with **`auto_default`** | Accept per operator request; idempotent skip when path unchanged |

## Migration Plan

No mapping-store migration. Operators with **`auto_create_area_path: true`** today:

- **Before**: CSV **`Proj\TeamA`** auto-created **`TeamA`** if missing.
- **After**: missing **`TeamA`** → fallback (default **`Proj\Snyk`** or custom template); pre-create **`TeamA`** in ADO if still desired.

Document env var and per-target **`ado_targets`** / **`org_mappings`** override examples.

## Open Questions

- *(None — audit on both **`auto_default`** and **`auto_fallback`** confirmed; strict full-path confirmed; config surfaces confirmed.)*
