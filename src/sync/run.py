"""One sync run: Snyk list → lifecycle → Azure DevOps + mapping store."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from config.models import AppConfig, AzureBoardsConfig
from integrations.azure_devops.client import WorkItemsClient
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
from sync.lifecycle import (
    DERIVED_IGNORED,
    DERIVED_OPEN,
    DERIVED_RESOLVED,
    derive_snyk_status,
    effective_severity_levels_from_threshold,
)
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


def _format_audit_comment(
    *,
    old_status: str,
    new_status: str,
    issue_key: str,
    prior_work_item_id: str | None,
) -> str:
    parts = [
        f"Snyk derived status: {old_status} → {new_status}",
        f"Snyk issue={issue_key}",
    ]
    if prior_work_item_id:
        parts.append(f"Prior work item id={prior_work_item_id}")
    text = "; ".join(parts)
    if len(text) <= _MAX_COMMENT:
        return text
    return text[: _MAX_COMMENT - len(_TRUNC)] + _TRUNC


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

    levels = effective_severity_levels_from_threshold(config.snyk.severity_threshold)
    list_params = GroupIssueListParams(effective_severity_levels=levels)

    if ab.org_mappings:
        for m in ab.org_mappings:
            boards = boards_for_org_mapping(config, m)
            template = effective_work_item_template(config, m.overrides)
            store_gid = config.snyk.group_id.strip() or m.snyk_org_id.strip()
            slug = effective_snyk_org_slug(config, m)
            issues = list(
                issues_client.iter_org_issues(
                    m.snyk_org_id.strip(),
                    list_params=list_params,
                ),
            )
            _run_sync_batch(
                issues=issues,
                group_id_for_store=store_gid,
                ado_org=m.organization.strip(),
                ado_proj=m.project.strip(),
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
    ado_org = ab.organization.strip()
    ado_proj = ab.project.strip()
    template = effective_work_item_template(config, None)
    slug = effective_snyk_org_slug(config, None)
    issues = list(issues_client.iter_group_issues(group_id, list_params=list_params))
    _run_sync_batch(
        issues=issues,
        group_id_for_store=group_id,
        ado_org=ado_org,
        ado_proj=ado_proj,
        boards=ab,
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
        ado_organization=ado_org,
        ado_project=ado_proj,
        snyk_project_name=snyk_pn or None,
        severity=severity or None,
    )

    prev_snyk = row.snyk_status if row is not None else None
    prev_wid = str(row.work_item_id) if row is not None else ""

    reopen = (
        row is not None
        and new_status == DERIVED_OPEN
        and row.snyk_status in (DERIVED_RESOLVED, DERIVED_IGNORED)
    )

    if row is None and new_status != DERIVED_OPEN:
        log.debug("sync skip unmapped non-open issue=%s status=%s", issue_key, new_status)
        return

    if row is None:
        if not ab.create_new_work_items:
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
        )
        if prev_snyk is not None and prev_snyk != new_status:
            text = _format_audit_comment(
                old_status=prev_snyk,
                new_status=new_status,
                issue_key=issue_key,
                prior_work_item_id=prev_wid or None,
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
    )

    if prev_snyk is not None and prev_snyk != new_status:
        text = _format_audit_comment(
            old_status=prev_snyk,
            new_status=new_status,
            issue_key=issue_key,
            prior_work_item_id=None,
        )
        wit_client.add_work_item_comment(ado_org, ado_proj, wid, text)
