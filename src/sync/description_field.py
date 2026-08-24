"""Resolve Azure DevOps narrative field for Snyk work item body content."""

from __future__ import annotations

from config.errors import ConfigError
from config.field_refs import AUTO_DESCRIPTION_FIELD_ORDER
from config.models import AppConfig
from integrations.azure_devops.client import WorkItemsClient

from sync.effective import boards_for_org_mapping, resolve_effective_work_item_config


class DescriptionFieldResolver:
    """Resolve and cache effective description field reference names per sync run."""

    def __init__(self, client: WorkItemsClient) -> None:
        self._client = client
        self._cache: dict[tuple[str, str, str, str | None], str] = {}

    def resolve(
        self,
        organization: str,
        project: str,
        work_item_type: str,
        configured: str | None,
    ) -> str:
        """
        Resolve the Azure DevOps field reference name for narrative body content.

        When ``configured`` is ``None``, prefer ``System.Description`` then
        ``Microsoft.VSTS.TCM.ReproSteps`` on the effective work item type.
        """
        org = organization.strip()
        proj = project.strip()
        wit = work_item_type.strip()
        key = (org, proj, wit, configured)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        field_names = self._client.list_work_item_type_field_names(org, proj, wit)
        field_set = frozenset(field_names)
        if configured:
            if configured not in field_set:
                raise ConfigError(
                    "work_item_description_field "
                    f"{configured!r} is not defined on work item type {wit!r} "
                    f"in Azure DevOps organization {org!r} project {proj!r}",
                )
            resolved = configured
        else:
            resolved = _pick_auto_description_field(field_set, org, proj, wit)

        self._cache[key] = resolved
        return resolved


def _pick_auto_description_field(
    field_set: frozenset[str],
    organization: str,
    project: str,
    work_item_type: str,
) -> str:
    """Choose the first auto candidate present on the work item type."""
    for candidate in AUTO_DESCRIPTION_FIELD_ORDER:
        if candidate in field_set:
            return candidate
    attempted = ", ".join(AUTO_DESCRIPTION_FIELD_ORDER)
    raise ConfigError(
        "No supported work item description field found for work item type "
        f"{work_item_type!r} in Azure DevOps organization {organization!r} "
        f"project {project!r}; attempted {attempted}. "
        "Set azure_boards.defaults.work_item_description_field explicitly.",
    )


def _warm_profile_description_field(
    config: AppConfig,
    resolver: DescriptionFieldResolver,
    *,
    organization: str,
    project: str,
    work_item_type: str,
    description_field: str | None,
) -> None:
    resolver.resolve(
        organization,
        project,
        work_item_type,
        description_field,
    )


def warm_description_fields_for_sync(
    config: AppConfig,
    resolver: DescriptionFieldResolver,
) -> None:
    """Resolve description fields for every routing context before the issue loop."""
    ab = config.azure_boards
    defaults = ab.defaults

    for profile in ab.ado_targets:
        wit_type = profile.work_item_type or defaults.work_item_type
        desc_field = (
            profile.work_item_description_field
            if profile.work_item_description_field is not None
            else defaults.work_item_description_field
        )
        _warm_profile_description_field(
            config,
            resolver,
            organization=profile.organization,
            project=profile.project,
            work_item_type=wit_type,
            description_field=desc_field,
        )

    if ab.org_mappings:
        for mapping in ab.org_mappings:
            boards = boards_for_org_mapping(config, mapping)
            effective = resolve_effective_work_item_config(
                app=config,
                boards=boards,
                org_mapping=mapping,
                ado_target_index=ab.ado_target_index,
                effective_organization=boards.organization,
                effective_project=boards.project,
                csv_match=None,
            )
            _warm_profile_description_field(
                config,
                resolver,
                organization=boards.organization,
                project=boards.project,
                work_item_type=effective.work_item_type,
                description_field=effective.work_item_description_field,
            )
        return

    effective = resolve_effective_work_item_config(
        app=config,
        boards=ab,
        org_mapping=None,
        ado_target_index=ab.ado_target_index,
        effective_organization=ab.organization,
        effective_project=ab.project,
        csv_match=None,
    )
    _warm_profile_description_field(
        config,
        resolver,
        organization=ab.organization,
        project=ab.project,
        work_item_type=effective.work_item_type,
        description_field=effective.work_item_description_field,
    )
