"""One sync run: Snyk list → lifecycle → Azure DevOps + mapping store."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Mapping
from urllib.parse import quote

from config.models import (
    REOPEN_POLICY_REOPEN_EXISTING,
    AdoTargetIndex,
    AppConfig,
    AzureBoardsConfig,
    OrgMapping,
)
from integrations.azure_devops.client import WorkItemsClient
from integrations.azure_devops.errors import AzureDevOpsAuthError, AzureDevOpsClientError
from mapping_store.protocol import MappingRow, MappingStore
from observability.integration_audit import log_missing_mapped_work_item, log_sync_summary
from observability.sync_context import get_sync_run_id, reset_sync_run_id, set_sync_run_id
from snyk.client import GroupIssueListParams, IssuesClient

from sync.area_path import AreaPathEnsureCache, ensure_area_path_exists
from sync.azure_batch import batch_get_work_items
from sync.description_field import DescriptionFieldResolver, warm_description_fields_for_sync
from sync.effective import (
    EffectiveWorkItemConfig,
    boards_for_org_mapping,
    effective_snyk_org_slug,
    resolve_effective_work_item_config,
)
from sync.enrichment import enrich_issue_record
from sync.issue_content import (
    build_system_description,
    effective_target_label_for_title,
    work_item_title,
)
from sync.issue_filters import (
    attrs_indicate_fix_available,
    issue_passes_sync_from_filter,
)
from sync.lifecycle import (
    DERIVED_IGNORED,
    DERIVED_OPEN,
    DERIVED_RESOLVED,
    derive_snyk_status,
    effective_severity_levels_from_threshold,
)
from sync.origin_filter import classify_origin_for_allowlist
from sync.patch_build import build_create_patch, build_update_patch
from sync.repo_mapping import RepoMappingIndex, ResolvedRouting, load_repo_mapping_index, resolve_routing
from sync.validate import validate_sync_config, validate_sync_environment

LOGGER = logging.getLogger(__name__)
_MAX_COMMENT = 4000
_TRUNC = "[truncated]"


def _issue_attrs(rec: Mapping[str, Any]) -> dict[str, Any]:
    raw = rec.get("issue_attributes")
    return dict(raw) if isinstance(raw, dict) else {}


def _natural_key(
    rec: Mapping[str, Any],
    *,
    group_id: str,
) -> tuple[str, str, str, str] | None:
    org = rec.get("org_id")
    proj = rec.get("project_id")
    iid = rec.get("issue_id")
    if not org or not proj or not iid:
        return None
    return (group_id.strip(), str(org), str(proj), str(iid))


def _ado_work_item_edit_url(
    *,
    organization: str,
    project: str,
    work_item_id: str,
) -> str:
    org_seg = quote(organization.strip(), safe="")
    proj_seg = quote(project.strip(), safe="")
    return (
        f"https://dev.azure.com/{org_seg}/{proj_seg}/_workitems/edit/{work_item_id.strip()}"
    )


def _format_audit_comment(
    *,
    old_status: str,
    new_status: str,
    issue_key: str,
    prior_work_item_id: str | None,
    prior_work_item_url: str | None = None,
) -> str:
    parts = [
        f"Snyk derived status: {old_status} → {new_status}",
        f"Snyk issue={issue_key}",
    ]
    if prior_work_item_id:
        parts.append(f"Prior work item id={prior_work_item_id}")
    if prior_work_item_url:
        parts.append(f"Prior work item={prior_work_item_url}")
    text = "; ".join(parts)
    if len(text) <= _MAX_COMMENT:
        return text
    return text[: _MAX_COMMENT - len(_TRUNC)] + _TRUNC


def _format_area_path_move_comment(*, previous: str, new: str) -> str:
    prev_display = previous if previous else "(unset)"
    return f"Snyk sync moved work item area path from '{prev_display}' to '{new}'."


def _format_routing_migration_recreate_comment(
    *,
    prior_work_item_id: str,
    old_org: str,
    old_proj: str,
    new_org: str,
    new_proj: str,
) -> str:
    return (
        "Snyk sync recreated this work item due to repo-mapping ADO target change. "
        f"Previous work item {prior_work_item_id.strip()} was in "
        f"{old_org.strip()}/{old_proj.strip()}; "
        f"new target is {new_org.strip()}/{new_proj.strip()}."
    )


def _format_routing_migration_retarget_comment(
    *,
    old_org: str,
    old_proj: str,
    new_org: str,
    new_proj: str,
) -> str:
    return (
        "Snyk sync updated mapping target due to repo-mapping change. "
        f"Future syncs for this issue will use {new_org.strip()}/{new_proj.strip()}. "
        f"This work item remains in {old_org.strip()}/{old_proj.strip()}."
    )


def _routing_target_changed(row: MappingRow, routing: ResolvedRouting) -> bool:
    stored_org = str(row.organization or "").strip()
    stored_proj = str(row.project or "").strip()
    return stored_org != routing.organization.strip() or stored_proj != routing.project.strip()


def _work_item_area_path(wi: Mapping[str, Any] | None) -> str:
    if wi is None:
        return ""
    fields = wi.get("fields")
    if not isinstance(fields, dict):
        return ""
    return str(fields.get("System.AreaPath") or "").strip()


def _ensure_routing_area_path_if_enabled(
    *,
    wit_client: WorkItemsClient,
    boards: AzureBoardsConfig,
    routing: ResolvedRouting,
    ensure_cache: AreaPathEnsureCache,
    log: logging.Logger,
    issue_key: str,
) -> bool:
    """
    Ensure the routing area path exists when ``auto_create_area_path`` is enabled.

    Returns ``False`` when ensure fails and the caller should skip the issue.
    """
    if not boards.defaults.auto_create_area_path:
        return True
    area = str(routing.area_path or "").strip()
    if not area:
        return True
    try:
        ensure_area_path_exists(
            wit_client,
            routing.organization,
            routing.project,
            area,
            ensure_cache,
        )
        return True
    except (AzureDevOpsAuthError, AzureDevOpsClientError) as exc:
        log.warning(
            "sync skip issue=%s (area path ensure failed): %s",
            issue_key,
            exc,
        )
        return False


def _log_issue_routing(
    log: logging.Logger,
    *,
    issue_key: str,
    routing: ResolvedRouting,
    effective_wit: EffectiveWorkItemConfig | None = None,
) -> None:
    if effective_wit is not None:
        log.info(
            "sync routing issue=%s ado_target_source=%s organization=%s project=%s "
            "area_path_source=%s assignee_from_csv=%s work_item_config_source=%s "
            "work_item_type=%s work_item_state_active=%s",
            issue_key,
            routing.ado_target_source,
            routing.organization,
            routing.project,
            routing.area_path_source,
            routing.assignee_from_csv,
            effective_wit.work_item_config_source,
            effective_wit.work_item_type,
            effective_wit.work_item_state_active,
        )
        return
    log.info(
        "sync routing issue=%s ado_target_source=%s organization=%s project=%s "
        "area_path_source=%s assignee_from_csv=%s",
        issue_key,
        routing.ado_target_source,
        routing.organization,
        routing.project,
        routing.area_path_source,
        routing.assignee_from_csv,
    )


def _create_replacement_work_item(
    *,
    gid: str,
    oid: str,
    pid: str,
    iid: str,
    ado_org: str,
    ado_proj: str,
    effective_wit: EffectiveWorkItemConfig,
    description_field: str,
    wit_client: WorkItemsClient,
    store: MappingStore,
    title: str,
    description: str,
    severity_level_for_tags: str | None,
    issue_snyk_type: str | None,
    app_base_url: str,
    new_status: str,
    issue_key: str,
    prior_work_item_id: str,
    snyk_pn: str,
    snyk_po: str,
    prev_snyk: str | None,
    audit_prior_work_item: bool,
    audit_comment: str | None,
    routing: ResolvedRouting,
    boards: AzureBoardsConfig,
    area_path_ensure_cache: AreaPathEnsureCache,
    log: logging.Logger,
) -> str:
    """
    Create a new Azure Boards work item, upsert mapping, optional audit on prior id.

    Returns the new work item id string.
    """
    _log_issue_routing(
        log,
        issue_key=issue_key,
        routing=routing,
        effective_wit=effective_wit,
    )
    if not _ensure_routing_area_path_if_enabled(
        wit_client=wit_client,
        boards=boards,
        routing=routing,
        ensure_cache=area_path_ensure_cache,
        log=log,
        issue_key=issue_key,
    ):
        return ""
    patches = build_create_patch(
        title=title,
        description=description,
        active_state=effective_wit.work_item_state_active,
        template=effective_wit.template,
        issue_effective_severity_level=severity_level_for_tags,
        issue_snyk_type=issue_snyk_type,
        app_base_url=app_base_url,
        description_field=description_field,
        area_path=routing.area_path,
        assigned_to=routing.assignee,
    )
    created = wit_client.create_work_item(
        ado_org,
        ado_proj,
        effective_wit.work_item_type,
        patches,
    )
    new_wid = str(created.get("work_item_id", ""))
    wst = str(created.get("work_item_status") or "")
    store.upsert(
        group_id=gid,
        org_id=oid,
        project_id=pid,
        issue_id=iid,
        snyk_status=new_status,
        organization=ado_org,
        project=ado_proj,
        work_item_id=new_wid,
        work_item_status=wst,
        snyk_project_name=snyk_pn,
        snyk_project_origin=snyk_po,
        excluded=False,
        exclusion_reason="",
    )
    if audit_comment:
        wit_client.add_work_item_comment(ado_org, ado_proj, new_wid, audit_comment)
    elif audit_prior_work_item and prior_work_item_id.strip():
        prior_url = _ado_work_item_edit_url(
            organization=ado_org,
            project=ado_proj,
            work_item_id=prior_work_item_id,
        )
        old_status = prev_snyk if prev_snyk is not None else new_status
        text = _format_audit_comment(
            old_status=old_status,
            new_status=new_status,
            issue_key=issue_key,
            prior_work_item_id=prior_work_item_id,
            prior_work_item_url=prior_url,
        )
        wit_client.add_work_item_comment(ado_org, ado_proj, new_wid, text)
    return new_wid


def _fetch_project_metadata(
    issues_client: IssuesClient,
    org_id: str,
    project_id: str,
    log: logging.Logger,
) -> tuple[str, str]:
    """Return ``(name, origin)`` from Snyk Projects API; empty strings on failure."""
    try:
        doc = issues_client.get_org_project(org_id, project_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("Snyk project metadata fetch failed: %s", exc)
        return "", ""
    return str(doc.get("name") or "").strip(), str(doc.get("origin") or "").strip()


def run_sync(
    *,
    config: AppConfig,
    issues_client: IssuesClient,
    wit_client: WorkItemsClient,
    store: MappingStore,
    logger: logging.Logger | None = None,
    sync_run_id: str | None = None,
) -> int:
    """
    Execute one synchronization loop.

    Returns:
        ``0`` when the loop completes (per-issue failures are logged only).

    Raises:
        config.errors.ConfigError: When startup validation fails (environment or merged YAML).

    """
    log = logger or LOGGER
    rid = sync_run_id if sync_run_id is not None else str(uuid.uuid4())
    token = set_sync_run_id(rid)
    t0 = time.perf_counter()
    outcome = "failure"
    err_short = ""
    try:
        validate_sync_environment()
        validate_sync_config(config)
        rc = _run_sync_body(
            config=config,
            issues_client=issues_client,
            wit_client=wit_client,
            store=store,
            log=log,
        )
        outcome = "success"
        return rc
    except BaseException as exc:
        err_short = f"{type(exc).__name__}: {exc!s}"[:500]
        raise
    finally:
        reset_sync_run_id(token)
        log_sync_summary(
            sync_run_id=rid,
            sync_duration_seconds=time.perf_counter() - t0,
            sync_outcome=outcome,
            error=err_short,
        )


def _run_sync_body(
    *,
    config: AppConfig,
    issues_client: IssuesClient,
    wit_client: WorkItemsClient,
    store: MappingStore,
    log: logging.Logger,
) -> int:
    """Core sync loop after environment validation (no sync_run_id wrapper)."""
    ab = config.azure_boards
    repo_index = load_repo_mapping_index(config)
    global_area_path = ab.defaults.area_path
    area_path_ensure_cache: AreaPathEnsureCache = {}
    description_fields = DescriptionFieldResolver(wit_client)
    warm_description_fields_for_sync(config, description_fields)

    if ab.org_mappings:
        for m in ab.org_mappings:
            boards = boards_for_org_mapping(config, m)
            description_field = description_fields.resolve(
                boards.organization,
                boards.project,
                boards.work_item_type,
                boards.defaults.work_item_description_field,
            )
            _ = description_field  # warmed; per-issue resolve uses description_fields
            levels = effective_severity_levels_from_threshold(boards.severity_threshold)
            list_params = GroupIssueListParams(effective_severity_levels=levels)
            store_gid = config.snyk.group_id.strip() or m.snyk_org_id.strip()
            slug = effective_snyk_org_slug(config, m)
            raw_issues = list(
                issues_client.iter_org_issues(
                    m.snyk_org_id.strip(),
                    list_params=list_params,
                ),
            )
            issues = [
                r
                for r in raw_issues
                if isinstance(r, dict)
                and issue_passes_sync_from_filter(
                    r,
                    issues_sync_from=boards.issues_sync_from,
                )
            ]
            _run_sync_batch(
                issues=issues,
                group_id_for_store=store_gid,
                ado_org=boards.organization.strip(),
                ado_proj=boards.project.strip(),
                boards=boards,
                app=config,
                org_mapping=m,
                ado_target_index=config.azure_boards.ado_target_index,
                description_fields=description_fields,
                wit_client=wit_client,
                store=store,
                log=log,
                issues_client=issues_client,
                snyk_org_slug=slug,
                app_base_url=config.snyk.app_base_url,
                use_org_scope_for_detail=True,
                snyk_org_id_for_detail=m.snyk_org_id.strip(),
                snyk_group_id_for_detail=config.snyk.group_id.strip()
                or m.snyk_org_id.strip(),
                repo_index=repo_index,
                global_defaults_area_path=global_area_path,
                area_path_ensure_cache=area_path_ensure_cache,
            )
        log.info("sync run finished (org_mappings mode)")
        return 0

    group_id = config.snyk.group_id.strip()
    boards_flat = ab
    description_field = description_fields.resolve(
        boards_flat.organization,
        boards_flat.project,
        boards_flat.work_item_type,
        boards_flat.defaults.work_item_description_field,
    )
    _ = description_field  # warmed; per-issue resolve uses description_fields
    levels = effective_severity_levels_from_threshold(boards_flat.severity_threshold)
    list_params = GroupIssueListParams(effective_severity_levels=levels)
    slug = effective_snyk_org_slug(config, None)
    raw_issues = list(issues_client.iter_group_issues(group_id, list_params=list_params))
    issues = [
        r
        for r in raw_issues
        if isinstance(r, dict)
        and issue_passes_sync_from_filter(
            r,
            issues_sync_from=boards_flat.issues_sync_from,
        )
    ]
    _run_sync_batch(
        issues=issues,
        group_id_for_store=group_id,
        ado_org=boards_flat.organization.strip(),
        ado_proj=boards_flat.project.strip(),
        boards=boards_flat,
        app=config,
        org_mapping=None,
        ado_target_index=config.azure_boards.ado_target_index,
        description_fields=description_fields,
        wit_client=wit_client,
        store=store,
        log=log,
        issues_client=issues_client,
        snyk_org_slug=slug,
        app_base_url=config.snyk.app_base_url,
        use_org_scope_for_detail=False,
        snyk_org_id_for_detail=None,
        snyk_group_id_for_detail=group_id,
        repo_index=repo_index,
        global_defaults_area_path=global_area_path,
        area_path_ensure_cache=area_path_ensure_cache,
    )
    log.info("sync run finished for group_id=%s", group_id)
    return 0


def _run_sync_batch(
    *,
    issues: list[dict[str, Any]],
    group_id_for_store: str,
    ado_org: str,
    ado_proj: str,
    boards: AzureBoardsConfig,
    app: AppConfig,
    org_mapping: OrgMapping | None,
    ado_target_index: AdoTargetIndex,
    description_fields: DescriptionFieldResolver,
    wit_client: WorkItemsClient,
    store: MappingStore,
    log: logging.Logger,
    issues_client: IssuesClient,
    snyk_org_slug: str,
    app_base_url: str,
    use_org_scope_for_detail: bool,
    snyk_org_id_for_detail: str | None,
    snyk_group_id_for_detail: str,
    repo_index: RepoMappingIndex,
    global_defaults_area_path: str | None,
    area_path_ensure_cache: AreaPathEnsureCache,
) -> None:
    planned: list[tuple[dict[str, Any], tuple[str, str, str, str], MappingRow | None]] = []
    for rec in issues:
        if not isinstance(rec, dict):
            continue
        nk = _natural_key(rec, group_id=group_id_for_store)
        if nk is None:
            log.error("sync skip: missing org_id, project_id, or issue_id in Snyk record")
            continue
        row = store.get_by_natural_key(
            group_id=nk[0],
            org_id=nk[1],
            project_id=nk[2],
            issue_id=nk[3],
        )
        planned.append((rec, nk, row))

    partitions: dict[tuple[str, str], list[str]] = {}
    for _rec, _nk, row in planned:
        if row is None or not str(row.work_item_id).strip():
            continue
        stored_org = str(row.organization or "").strip() or ado_org
        stored_proj = str(row.project or "").strip() or ado_proj
        partitions.setdefault((stored_org, stored_proj), []).append(
            str(row.work_item_id).strip(),
        )

    cache: dict[str, dict] = {}
    for (part_org, part_proj), wids in partitions.items():
        cache.update(batch_get_work_items(wit_client, part_org, part_proj, wids))

    for rec, nk, row in planned:
        _gid, _oid, pid, iid = nk
        try:
            _sync_one_issue(
                rec=rec,
                natural_key=nk,
                row=row,
                cache=cache,
                group_id=_gid,
                config_ado_org=ado_org,
                config_ado_proj=ado_proj,
                boards=boards,
                app=app,
                org_mapping=org_mapping,
                ado_target_index=ado_target_index,
                description_fields=description_fields,
                wit_client=wit_client,
                store=store,
                log=log,
                issues_client=issues_client,
                snyk_org_slug=snyk_org_slug,
                app_base_url=app_base_url,
                use_org_scope_for_detail=use_org_scope_for_detail,
                snyk_org_id_for_detail=snyk_org_id_for_detail,
                snyk_group_id_for_detail=snyk_group_id_for_detail,
                repo_index=repo_index,
                global_defaults_area_path=global_defaults_area_path,
                area_path_ensure_cache=area_path_ensure_cache,
            )
        except Exception as exc:  # noqa: BLE001 — per-issue isolation
            log.error("sync skip issue_id=%s: %s", iid, exc)


def _sync_one_issue(
    *,
    rec: dict[str, Any],
    natural_key: tuple[str, str, str, str],
    row: MappingRow | None,
    cache: dict[str, dict],
    group_id: str,
    config_ado_org: str,
    config_ado_proj: str,
    boards: AzureBoardsConfig,
    app: AppConfig,
    org_mapping: OrgMapping | None,
    ado_target_index: AdoTargetIndex,
    description_fields: DescriptionFieldResolver,
    wit_client: WorkItemsClient,
    store: MappingStore,
    log: logging.Logger,
    issues_client: IssuesClient,
    snyk_org_slug: str,
    app_base_url: str,
    use_org_scope_for_detail: bool,
    snyk_org_id_for_detail: str | None,
    snyk_group_id_for_detail: str,
    repo_index: RepoMappingIndex,
    global_defaults_area_path: str | None,
    area_path_ensure_cache: AreaPathEnsureCache,
) -> None:
    gid, oid, pid, iid = natural_key
    rec = enrich_issue_record(
        issues_client,
        rec,
        use_org_scope=use_org_scope_for_detail,
        snyk_org_id=snyk_org_id_for_detail,
        snyk_group_id=snyk_group_id_for_detail,
        log=log,
    )
    attrs = _issue_attrs(rec)
    issue_key = str(rec.get("issue_id") or iid)

    derived = derive_snyk_status(status=attrs.get("status"), ignored=attrs.get("ignored"))
    if derived is None:
        log.error(
            "sync skip unexpected Snyk attributes.status=%r issue=%s",
            attrs.get("status"),
            issue_key,
        )
        return

    new_status = derived.status
    ab = boards
    issue_key = str(attrs.get("key") or issue_key)
    proj_for_url = str(rec.get("project_id") or pid or "").strip()
    sev_raw = attrs.get("effective_severity_level") or rec.get("severity")
    severity = str(sev_raw).strip() if sev_raw is not None else ""
    severity_level_for_tags = severity if severity else None
    type_raw = attrs.get("type")
    issue_snyk_type = str(type_raw).strip() if type_raw is not None else None
    if issue_snyk_type == "":
        issue_snyk_type = None
    snyk_pn = str(rec.get("snyk_project_name") or "").strip()
    stored_name = str(row.snyk_project_name if row else "").strip()
    stored_origin = str(row.snyk_project_origin if row else "").strip()

    allowlist = ab.defaults.sync_included_snyk_origins
    active_allowlist = bool(allowlist)
    org_for_project = ""
    if use_org_scope_for_detail and snyk_org_id_for_detail:
        org_for_project = snyk_org_id_for_detail.strip()
    elif active_allowlist and oid:
        org_for_project = str(oid).strip()

    meta_name, meta_origin = "", ""
    if pid and org_for_project:
        want_project_fetch = (not stored_name or not stored_origin) or (
            active_allowlist and not stored_origin
        )
        if want_project_fetch:
            meta_name, meta_origin = _fetch_project_metadata(
                issues_client,
                org_for_project,
                pid,
                log,
            )
    snyk_pn = stored_name or snyk_pn or meta_name
    snyk_po = stored_origin or meta_origin

    included, exclusion_reason = classify_origin_for_allowlist(snyk_po, allowlist)
    if not included:
        # create_new_work_items does not block persisting excluded rows (issues sync
        # persistence for reporting). Azure DevOps is not mutated for origin-excluded issues.
        wid_keep = str(row.work_item_id) if row is not None else ""
        wst_keep = str(row.work_item_status) if row is not None else ""
        store.upsert(
            group_id=gid,
            org_id=oid,
            project_id=pid,
            issue_id=iid,
            snyk_status=new_status,
            organization=config_ado_org,
            project=config_ado_proj,
            work_item_id=wid_keep,
            work_item_status=wst_keep,
            snyk_project_name=snyk_pn,
            snyk_project_origin=snyk_po,
            excluded=True,
            exclusion_reason=exclusion_reason,
        )
        return

    routing = resolve_routing(
        index=repo_index,
        snyk_project_origin=snyk_po,
        snyk_project_name=snyk_pn,
        boards=boards,
        global_defaults_area_path=global_defaults_area_path,
    )
    effective_org = routing.organization
    effective_proj = routing.project
    effective_wit = resolve_effective_work_item_config(
        app=app,
        boards=boards,
        org_mapping=org_mapping,
        ado_target_index=ado_target_index,
        effective_organization=effective_org,
        effective_project=effective_proj,
        csv_match=routing.csv_match,
    )
    description_field = description_fields.resolve(
        effective_org,
        effective_proj,
        effective_wit.work_item_type,
        effective_wit.work_item_description_field,
    )

    target_label = effective_target_label_for_title(
        snyk_project_name=snyk_pn,
        ado_organization=effective_org,
        ado_project=effective_proj,
    )
    title = work_item_title(attrs, target_name=target_label)
    description = build_system_description(
        attrs,
        snyk_org_slug=snyk_org_slug,
        project_id=proj_for_url,
        issue_key=issue_key,
        snyk_project_name=snyk_pn or None,
        snyk_project_origin=snyk_po or None,
        severity=severity or None,
        description_appendix=ab.defaults.work_item_description_appendix,
        app_base_url=app_base_url,
    )

    prev_snyk = row.snyk_status if row is not None else None
    prev_wid = str(row.work_item_id) if row is not None else ""
    stored_org = str(row.organization if row else "").strip() or config_ado_org
    stored_proj = str(row.project if row else "").strip() or config_ado_proj

    if (
        row is not None
        and prev_wid.strip()
        and _routing_target_changed(row, routing)
    ):
        if new_status == DERIVED_OPEN:
            if not ab.create_new_work_items:
                log.warning(
                    "sync skip routing migration recreate (create_new_work_items false) "
                    "issue=%s",
                    issue_key,
                )
                return
            if ab.create_only_when_fix_available and not attrs_indicate_fix_available(
                attrs,
            ):
                log.debug(
                    "sync skip routing migration recreate (no fix available) issue=%s",
                    issue_key,
                )
                return
            migration_comment = _format_routing_migration_recreate_comment(
                prior_work_item_id=prev_wid,
                old_org=stored_org,
                old_proj=stored_proj,
                new_org=effective_org,
                new_proj=effective_proj,
            )
            _create_replacement_work_item(
                gid=gid,
                oid=oid,
                pid=pid,
                iid=iid,
                ado_org=effective_org,
                ado_proj=effective_proj,
                effective_wit=effective_wit,
                description_field=description_field,
                wit_client=wit_client,
                store=store,
                title=title,
                description=description,
                severity_level_for_tags=severity_level_for_tags,
                issue_snyk_type=issue_snyk_type,
                app_base_url=app_base_url,
                new_status=new_status,
                issue_key=issue_key,
                prior_work_item_id=prev_wid,
                snyk_pn=snyk_pn,
                snyk_po=snyk_po,
                prev_snyk=prev_snyk,
                audit_prior_work_item=False,
                audit_comment=migration_comment,
                routing=routing,
                boards=boards,
                area_path_ensure_cache=area_path_ensure_cache,
                log=log,
            )
            return

        if new_status in (DERIVED_RESOLVED, DERIVED_IGNORED):
            try:
                wit_client.get_work_item(stored_org, stored_proj, prev_wid.strip())
            except AzureDevOpsClientError as exc:
                if getattr(exc, "status_code", None) != 404:
                    raise
                log.info(
                    "routing migration retarget: work item %s missing in %s/%s issue=%s",
                    prev_wid,
                    stored_org,
                    stored_proj,
                    issue_key,
                )
            else:
                retarget_comment = _format_routing_migration_retarget_comment(
                    old_org=stored_org,
                    old_proj=stored_proj,
                    new_org=effective_org,
                    new_proj=effective_proj,
                )
                wit_client.add_work_item_comment(
                    stored_org,
                    stored_proj,
                    prev_wid.strip(),
                    retarget_comment,
                )
            store.upsert(
                group_id=gid,
                org_id=oid,
                project_id=pid,
                issue_id=iid,
                snyk_status=new_status,
                organization=effective_org,
                project=effective_proj,
                work_item_id=prev_wid.strip(),
                work_item_status=str(row.work_item_status or ""),
                snyk_project_name=snyk_pn,
                snyk_project_origin=snyk_po,
                excluded=False,
                exclusion_reason="",
            )
            return

    # Rows persisted while origin-excluded often have no work_item_id; if the issue
    # becomes origin-included (allowlist widens / origin resolves), treat like unmapped.
    unmapped_for_ado = row is None or not prev_wid.strip()

    reopen = (
        row is not None
        and new_status == DERIVED_OPEN
        and row.snyk_status in (DERIVED_RESOLVED, DERIVED_IGNORED)
    )

    if unmapped_for_ado and new_status != DERIVED_OPEN:
        log.debug("sync skip unmapped non-open issue=%s status=%s", issue_key, new_status)
        return

    # Reopen transitions (resolved/ignored → open) must use the reopen branch below so
    # policy and audit comments stay consistent—even when work_item_id is still empty.
    if unmapped_for_ado and not reopen:
        if not ab.create_new_work_items:
            return
        if ab.create_only_when_fix_available and not attrs_indicate_fix_available(attrs):
            log.debug("sync skip create (no fix available) issue=%s", issue_key)
            return
        _log_issue_routing(
            log,
            issue_key=issue_key,
            routing=routing,
            effective_wit=effective_wit,
        )
        if not _ensure_routing_area_path_if_enabled(
            wit_client=wit_client,
            boards=boards,
            routing=routing,
            ensure_cache=area_path_ensure_cache,
            log=log,
            issue_key=issue_key,
        ):
            return
        patches = build_create_patch(
            title=title,
            description=description,
            active_state=effective_wit.work_item_state_active,
            template=effective_wit.template,
            issue_effective_severity_level=severity_level_for_tags,
            issue_snyk_type=issue_snyk_type,
            app_base_url=app_base_url,
            description_field=description_field,
            area_path=routing.area_path,
            assigned_to=routing.assignee,
        )
        created = wit_client.create_work_item(
            effective_org,
            effective_proj,
            effective_wit.work_item_type,
            patches,
        )
        wid = str(created.get("work_item_id", ""))
        wst = str(created.get("work_item_status") or "")
        store.upsert(
            group_id=gid,
            org_id=oid,
            project_id=pid,
            issue_id=iid,
            snyk_status=new_status,
            organization=effective_org,
            project=effective_proj,
            work_item_id=wid,
            work_item_status=wst,
            snyk_project_name=snyk_pn,
            snyk_project_origin=snyk_po,
            excluded=False,
            exclusion_reason="",
        )
        return

    assert row is not None
    if reopen:
        if not ab.create_new_work_items:
            log.warning(
                "sync skip reopen (create_new_work_items is false) issue=%s",
                issue_key,
            )
            return

        if (
            ab.reopen_work_item_policy == REOPEN_POLICY_REOPEN_EXISTING
            and prev_wid.strip()
        ):
            try:
                existing = wit_client.get_work_item(
                    stored_org,
                    stored_proj,
                    prev_wid.strip(),
                )
            except AzureDevOpsClientError as exc:
                if getattr(exc, "status_code", None) != 404:
                    raise
                log.info(
                    "reopen_existing: work item %s missing; creating new issue=%s",
                    prev_wid,
                    issue_key,
                )
            else:
                if ab.create_only_when_fix_available and not attrs_indicate_fix_available(
                    attrs,
                ):
                    log.debug(
                        "sync skip reopen transition (no fix available) issue=%s",
                        issue_key,
                    )
                    return
                target_state = effective_wit.work_item_state_active
                current_area = _work_item_area_path(existing)
                effective_area = str(routing.area_path or "").strip()
                patch_area = bool(effective_area and effective_area != current_area)
                _log_issue_routing(
                    log,
                    issue_key=issue_key,
                    routing=routing,
                    effective_wit=effective_wit,
                )
                if patch_area and not _ensure_routing_area_path_if_enabled(
                    wit_client=wit_client,
                    boards=boards,
                    routing=routing,
                    ensure_cache=area_path_ensure_cache,
                    log=log,
                    issue_key=issue_key,
                ):
                    return
                patches = build_update_patch(
                    title=title,
                    description=description,
                    state=target_state,
                    template=effective_wit.template,
                    issue_effective_severity_level=severity_level_for_tags,
                    issue_snyk_type=issue_snyk_type,
                    app_base_url=app_base_url,
                    description_field=description_field,
                    area_path=effective_area or None,
                    patch_area_path=patch_area,
                    assigned_to=routing.assignee,
                )
                updated = wit_client.update_work_item(
                    stored_org,
                    stored_proj,
                    prev_wid.strip(),
                    patches,
                )
                wst = str(updated.get("work_item_status") or "")
                store.upsert(
                    group_id=gid,
                    org_id=oid,
                    project_id=pid,
                    issue_id=iid,
                    snyk_status=new_status,
                    organization=effective_org,
                    project=effective_proj,
                    work_item_id=prev_wid.strip(),
                    work_item_status=wst,
                    snyk_project_name=snyk_pn,
                    snyk_project_origin=snyk_po,
                    excluded=False,
                    exclusion_reason="",
                )
                if patch_area and effective_area:
                    wit_client.add_work_item_comment(
                        stored_org,
                        stored_proj,
                        prev_wid.strip(),
                        _format_area_path_move_comment(
                            previous=current_area,
                            new=effective_area,
                        ),
                    )
                if prev_snyk is not None and prev_snyk != new_status:
                    text = _format_audit_comment(
                        old_status=prev_snyk,
                        new_status=new_status,
                        issue_key=issue_key,
                        prior_work_item_id=None,
                    )
                    wit_client.add_work_item_comment(
                        stored_org,
                        stored_proj,
                        prev_wid.strip(),
                        text,
                    )
                return

        if ab.create_only_when_fix_available and not attrs_indicate_fix_available(attrs):
            log.debug("sync skip reopen create (no fix available) issue=%s", issue_key)
            return

        _create_replacement_work_item(
            gid=gid,
            oid=oid,
            pid=pid,
            iid=iid,
            ado_org=effective_org,
            ado_proj=effective_proj,
            effective_wit=effective_wit,
            description_field=description_field,
            wit_client=wit_client,
            store=store,
            title=title,
            description=description,
            severity_level_for_tags=severity_level_for_tags,
            issue_snyk_type=issue_snyk_type,
            app_base_url=app_base_url,
            new_status=new_status,
            issue_key=issue_key,
            prior_work_item_id=prev_wid,
            snyk_pn=snyk_pn,
            snyk_po=snyk_po,
            prev_snyk=prev_snyk,
            audit_prior_work_item=prev_snyk is not None and prev_snyk != new_status,
            audit_comment=None,
            routing=routing,
            boards=boards,
            area_path_ensure_cache=area_path_ensure_cache,
            log=log,
        )
        return

    wid = str(row.work_item_id).strip()
    if not wid:
        log.error("sync skip issue=%s has empty work_item_id in mapping", issue_key)
        return

    wi = cache.get(wid)
    if wi is None:
        log.info(
            "mapped work item %s missing from Azure DevOps for issue=%s",
            wid,
            issue_key,
        )
        sync_rid = get_sync_run_id()
        if new_status in (DERIVED_RESOLVED, DERIVED_IGNORED):
            log_missing_mapped_work_item(
                prior_work_item_id=wid,
                issue_key=issue_key,
                action="skip",
                sync_run_id=sync_rid,
            )
            return
        if new_status != DERIVED_OPEN:
            log_missing_mapped_work_item(
                prior_work_item_id=wid,
                issue_key=issue_key,
                action="skip",
                sync_run_id=sync_rid,
            )
            return
        if not ab.create_new_work_items:
            log_missing_mapped_work_item(
                prior_work_item_id=wid,
                issue_key=issue_key,
                action="skip",
                sync_run_id=sync_rid,
            )
            log.warning(
                "sync skip recreate (create_new_work_items is false) issue=%s",
                issue_key,
            )
            return
        if ab.create_only_when_fix_available and not attrs_indicate_fix_available(attrs):
            log.debug(
                "sync skip recreate (no fix available) issue=%s",
                issue_key,
            )
            return
        log_missing_mapped_work_item(
            prior_work_item_id=wid,
            issue_key=issue_key,
            action="recreate",
            sync_run_id=sync_rid,
        )
        _create_replacement_work_item(
            gid=gid,
            oid=oid,
            pid=pid,
            iid=iid,
            ado_org=effective_org,
            ado_proj=effective_proj,
            effective_wit=effective_wit,
            description_field=description_field,
            wit_client=wit_client,
            store=store,
            title=title,
            description=description,
            severity_level_for_tags=severity_level_for_tags,
            issue_snyk_type=issue_snyk_type,
            app_base_url=app_base_url,
            new_status=new_status,
            issue_key=issue_key,
            prior_work_item_id=wid,
            snyk_pn=snyk_pn,
            snyk_po=snyk_po,
            prev_snyk=prev_snyk,
            audit_prior_work_item=True,
            audit_comment=None,
            routing=routing,
            boards=boards,
            area_path_ensure_cache=area_path_ensure_cache,
            log=log,
        )
        return

    target_state = (
        effective_wit.work_item_state_closed
        if new_status in (DERIVED_RESOLVED, DERIVED_IGNORED)
        else effective_wit.work_item_state_active
    )
    current_area = _work_item_area_path(wi)
    effective_area = str(routing.area_path or "").strip()
    patch_area = bool(effective_area and effective_area != current_area)
    _log_issue_routing(
        log,
        issue_key=issue_key,
        routing=routing,
        effective_wit=effective_wit,
    )
    if patch_area and not _ensure_routing_area_path_if_enabled(
        wit_client=wit_client,
        boards=boards,
        routing=routing,
        ensure_cache=area_path_ensure_cache,
        log=log,
        issue_key=issue_key,
    ):
        return
    patches = build_update_patch(
        title=title,
        description=description,
        state=target_state,
        template=effective_wit.template,
        issue_effective_severity_level=severity_level_for_tags,
        issue_snyk_type=issue_snyk_type,
        app_base_url=app_base_url,
        description_field=description_field,
        area_path=effective_area or None,
        patch_area_path=patch_area,
        assigned_to=routing.assignee,
    )
    updated = wit_client.update_work_item(stored_org, stored_proj, wid, patches)
    wst = str(updated.get("work_item_status") or "")

    store.upsert(
        group_id=gid,
        org_id=oid,
        project_id=pid,
        issue_id=iid,
        snyk_status=new_status,
        organization=effective_org,
        project=effective_proj,
        work_item_id=wid,
        work_item_status=wst,
        snyk_project_name=snyk_pn,
        snyk_project_origin=snyk_po,
        excluded=False,
        exclusion_reason="",
    )

    if patch_area and effective_area:
        wit_client.add_work_item_comment(
            stored_org,
            stored_proj,
            wid,
            _format_area_path_move_comment(previous=current_area, new=effective_area),
        )

    if prev_snyk is not None and prev_snyk != new_status:
        text = _format_audit_comment(
            old_status=prev_snyk,
            new_status=new_status,
            issue_key=issue_key,
            prior_work_item_id=None,
        )
        wit_client.add_work_item_comment(stored_org, stored_proj, wid, text)
