"""One sync run: Snyk list → lifecycle → Azure DevOps + mapping store."""

from __future__ import annotations

import logging
from typing import Any, Mapping
from urllib.parse import quote

from config.models import REOPEN_POLICY_REOPEN_EXISTING, AppConfig, AzureBoardsConfig
from integrations.azure_devops.client import WorkItemsClient
from integrations.azure_devops.errors import AzureDevOpsClientError
from mapping_store.protocol import MappingRow, MappingStore
from snyk.client import GroupIssueListParams, IssuesClient

from sync.azure_batch import batch_get_work_items
from sync.effective import (
    boards_for_org_mapping,
    effective_snyk_org_slug,
    effective_work_item_template,
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
) -> int:
    """
    Execute one synchronization loop.

    Returns:
        ``0`` when the loop completes (per-issue failures are logged only).

    Raises:
        config.errors.ConfigError: When startup validation fails (environment or merged YAML).

    """
    log = logger or LOGGER
    validate_sync_environment()
    validate_sync_config(config)
    ab = config.azure_boards

    if ab.org_mappings:
        for m in ab.org_mappings:
            boards = boards_for_org_mapping(config, m)
            levels = effective_severity_levels_from_threshold(boards.severity_threshold)
            list_params = GroupIssueListParams(effective_severity_levels=levels)
            template = effective_work_item_template(config, m.overrides, boards=boards)
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
                template=template,
                wit_client=wit_client,
                store=store,
                log=log,
                issues_client=issues_client,
                snyk_org_slug=slug,
                use_org_scope_for_detail=True,
                snyk_org_id_for_detail=m.snyk_org_id.strip(),
                snyk_group_id_for_detail=config.snyk.group_id.strip()
                or m.snyk_org_id.strip(),
            )
        log.info("sync run finished (org_mappings mode)")
        return 0

    group_id = config.snyk.group_id.strip()
    boards_flat = ab
    levels = effective_severity_levels_from_threshold(boards_flat.severity_threshold)
    list_params = GroupIssueListParams(effective_severity_levels=levels)
    template = effective_work_item_template(config, None, boards=boards_flat)
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
        template=template,
        wit_client=wit_client,
        store=store,
        log=log,
        issues_client=issues_client,
        snyk_org_slug=slug,
        use_org_scope_for_detail=False,
        snyk_org_id_for_detail=None,
        snyk_group_id_for_detail=group_id,
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
    template: dict[str, Any],
    wit_client: WorkItemsClient,
    store: MappingStore,
    log: logging.Logger,
    issues_client: IssuesClient,
    snyk_org_slug: str,
    use_org_scope_for_detail: bool,
    snyk_org_id_for_detail: str | None,
    snyk_group_id_for_detail: str,
) -> None:
    wids: list[str] = []
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
        if row and str(row.work_item_id).strip():
            wids.append(str(row.work_item_id).strip())
        planned.append((rec, nk, row))

    cache = batch_get_work_items(wit_client, ado_org, ado_proj, wids)

    for rec, nk, row in planned:
        _gid, _oid, pid, iid = nk
        try:
            _sync_one_issue(
                rec=rec,
                natural_key=nk,
                row=row,
                cache=cache,
                group_id=_gid,
                ado_org=ado_org,
                ado_proj=ado_proj,
                boards=boards,
                template=template,
                wit_client=wit_client,
                store=store,
                log=log,
                issues_client=issues_client,
                snyk_org_slug=snyk_org_slug,
                use_org_scope_for_detail=use_org_scope_for_detail,
                snyk_org_id_for_detail=snyk_org_id_for_detail,
                snyk_group_id_for_detail=snyk_group_id_for_detail,
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
    ado_org: str,
    ado_proj: str,
    boards: AzureBoardsConfig,
    template: dict[str, Any],
    wit_client: WorkItemsClient,
    store: MappingStore,
    log: logging.Logger,
    issues_client: IssuesClient,
    snyk_org_slug: str,
    use_org_scope_for_detail: bool,
    snyk_org_id_for_detail: str | None,
    snyk_group_id_for_detail: str,
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
            organization=ado_org,
            project=ado_proj,
            work_item_id=wid_keep,
            work_item_status=wst_keep,
            snyk_project_name=snyk_pn,
            snyk_project_origin=snyk_po,
            excluded=True,
            exclusion_reason=exclusion_reason,
        )
        return

    target_label = effective_target_label_for_title(
        snyk_project_name=snyk_pn,
        ado_organization=ado_org,
        ado_project=ado_proj,
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
    )

    prev_snyk = row.snyk_status if row is not None else None
    prev_wid = str(row.work_item_id) if row is not None else ""
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
        patches = build_create_patch(
            title=title,
            description=description,
            active_state=ab.work_item_state_active,
            template=template,
        )
        created = wit_client.create_work_item(
            ado_org,
            ado_proj,
            ab.work_item_type,
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
            organization=ado_org,
            project=ado_proj,
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
                wit_client.get_work_item(ado_org, ado_proj, prev_wid.strip())
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
                target_state = ab.work_item_state_active
                patches = build_update_patch(
                    title=title,
                    description=description,
                    state=target_state,
                    template=template,
                )
                updated = wit_client.update_work_item(
                    ado_org,
                    ado_proj,
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
                    organization=ado_org,
                    project=ado_proj,
                    work_item_id=prev_wid.strip(),
                    work_item_status=wst,
                    snyk_project_name=snyk_pn,
                    snyk_project_origin=snyk_po,
                    excluded=False,
                    exclusion_reason="",
                )
                if prev_snyk is not None and prev_snyk != new_status:
                    text = _format_audit_comment(
                        old_status=prev_snyk,
                        new_status=new_status,
                        issue_key=issue_key,
                        prior_work_item_id=None,
                    )
                    wit_client.add_work_item_comment(
                        ado_org,
                        ado_proj,
                        prev_wid.strip(),
                        text,
                    )
                return

        if ab.create_only_when_fix_available and not attrs_indicate_fix_available(attrs):
            log.debug("sync skip reopen create (no fix available) issue=%s", issue_key)
            return

        patches = build_create_patch(
            title=title,
            description=description,
            active_state=ab.work_item_state_active,
            template=template,
        )
        created = wit_client.create_work_item(
            ado_org,
            ado_proj,
            ab.work_item_type,
            patches,
        )
        new_wid = str(created.get("work_item_id", ""))
        wst = str(created.get("work_item_status") or "")
        prior_url = (
            _ado_work_item_edit_url(
                organization=ado_org,
                project=ado_proj,
                work_item_id=prev_wid,
            )
            if prev_wid.strip()
            else None
        )
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
        if prev_snyk is not None and prev_snyk != new_status:
            text = _format_audit_comment(
                old_status=prev_snyk,
                new_status=new_status,
                issue_key=issue_key,
                prior_work_item_id=prev_wid or None,
                prior_work_item_url=prior_url,
            )
            wit_client.add_work_item_comment(ado_org, ado_proj, new_wid, text)
        return

    wid = str(row.work_item_id).strip()
    if not wid:
        log.error("sync skip issue=%s has empty work_item_id in mapping", issue_key)
        return

    wi = cache.get(wid)
    if wi is None:
        log.error(
            "sync skip Azure work item %s not found for issue=%s",
            wid,
            issue_key,
        )
        return

    target_state = (
        ab.work_item_state_closed
        if new_status in (DERIVED_RESOLVED, DERIVED_IGNORED)
        else ab.work_item_state_active
    )
    patches = build_update_patch(
        title=title,
        description=description,
        state=target_state,
        template=template,
    )
    updated = wit_client.update_work_item(ado_org, ado_proj, wid, patches)
    wst = str(updated.get("work_item_status") or "")

    store.upsert(
        group_id=gid,
        org_id=oid,
        project_id=pid,
        issue_id=iid,
        snyk_status=new_status,
        organization=ado_org,
        project=ado_proj,
        work_item_id=wid,
        work_item_status=wst,
        snyk_project_name=snyk_pn,
        snyk_project_origin=snyk_po,
        excluded=False,
        exclusion_reason="",
    )

    if prev_snyk is not None and prev_snyk != new_status:
        text = _format_audit_comment(
            old_status=prev_snyk,
            new_status=new_status,
            issue_key=issue_key,
            prior_work_item_id=None,
        )
        wit_client.add_work_item_comment(ado_org, ado_proj, wid, text)
