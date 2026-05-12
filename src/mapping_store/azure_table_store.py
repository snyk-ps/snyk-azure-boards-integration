"""Azure Table Storage implementation of ``MappingStore``."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from azure.core.credentials import TokenCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import DefaultAzureCredential

from mapping_store.errors import AzureTableMappingStoreUnavailableError
from mapping_store.protocol import MappingRow
from mapping_store.table_keys import table_row_key


def _utc_now_iso_z() -> str:
    """Current UTC time as ISO 8601 with milliseconds and ``Z`` suffix."""
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _bool_to_text(flag: bool) -> str:
    return "true" if flag else "false"


def _text_to_bool(raw: object) -> bool:
    s = str(raw or "").strip().lower()
    return s in ("true", "1", "yes")


def _entity_to_row(entity: Mapping[str, Any]) -> MappingRow:
    """Build :class:`MappingRow` from a Table entity mapping."""
    return MappingRow(
        group_id=str(entity.get("group_id") or ""),
        org_id=str(entity.get("org_id") or ""),
        project_id=str(entity.get("project_id") or ""),
        issue_id=str(entity.get("issue_id") or ""),
        snyk_status=str(entity.get("snyk_status") or ""),
        organization=str(entity.get("organization") or ""),
        project=str(entity.get("project") or ""),
        work_item_id=str(entity.get("work_item_id") or ""),
        work_item_status=str(entity.get("work_item_status") or ""),
        snyk_project_name=str(entity.get("snyk_project_name") or ""),
        snyk_project_origin=str(entity.get("snyk_project_origin") or ""),
        excluded=_text_to_bool(entity.get("excluded")),
        exclusion_reason=str(entity.get("exclusion_reason") or ""),
        created_at=str(entity.get("created_at") or ""),
        updated_at=str(entity.get("updated_at") or ""),
    )


class AzureTableMappingStore:
    """Persist mappings in Azure Table Storage using Entra ID credentials."""

    def __init__(
        self,
        endpoint: str,
        table_name: str,
        *,
        credential: TokenCredential | None = None,
    ) -> None:
        """
        Create the store and ensure the table exists (idempotent).

        ``endpoint`` is the HTTPS Table service URL (non-secret). Authentication
        uses ``DefaultAzureCredential`` when ``credential`` is omitted.
        """
        ep = endpoint.strip()
        tn = table_name.strip()
        cred = credential or DefaultAzureCredential()
        try:
            service = TableServiceClient(endpoint=ep, credential=cred)
            service.create_table_if_not_exists(table_name=tn)
            self._client = service.get_table_client(table_name=tn)
        except Exception as exc:
            raise AzureTableMappingStoreUnavailableError(
                "mapping_store is 'azure_table' but the Azure Table Storage client "
                f"could not be initialized ({type(exc).__name__}). "
                "Check MAPPING_STORE_AZURE_TABLE_ENDPOINT, "
                "MAPPING_STORE_AZURE_TABLE_NAME, network reachability, and that "
                "managed identity or developer credentials have Table data plane "
                "access.",
            ) from exc

    def get_by_natural_key(
        self,
        *,
        group_id: str,
        org_id: str,
        project_id: str,
        issue_id: str,
    ) -> MappingRow | None:
        pk = group_id
        rk = table_row_key(org_id, project_id, issue_id)
        try:
            ent = self._client.get_entity(pk, rk)
        except ResourceNotFoundError:
            return None
        return _entity_to_row(ent)

    def upsert(
        self,
        *,
        group_id: str,
        org_id: str,
        project_id: str,
        issue_id: str,
        snyk_status: str,
        organization: str,
        project: str,
        work_item_id: str,
        work_item_status: str,
        snyk_project_name: str = "",
        snyk_project_origin: str = "",
        excluded: bool = False,
        exclusion_reason: str = "",
    ) -> MappingRow:
        pk = group_id
        rk = table_row_key(org_id, project_id, issue_id)
        now = _utc_now_iso_z()
        created_at = now
        try:
            existing = self._client.get_entity(pk, rk)
            prev = str(existing.get("created_at") or "").strip()
            if prev:
                created_at = prev
        except ResourceNotFoundError:
            pass

        pn = str(snyk_project_name or "")
        po = str(snyk_project_origin or "")
        ex = bool(excluded)
        reason = str(exclusion_reason or "") if ex else ""

        entity: dict[str, Any] = {
            "PartitionKey": pk,
            "RowKey": rk,
            "group_id": group_id,
            "org_id": org_id,
            "project_id": project_id,
            "issue_id": issue_id,
            "snyk_status": snyk_status,
            "organization": organization,
            "project": project,
            "work_item_id": work_item_id,
            "work_item_status": work_item_status,
            "snyk_project_name": pn,
            "snyk_project_origin": po,
            "excluded": _bool_to_text(ex),
            "exclusion_reason": reason,
            "created_at": created_at,
            "updated_at": now,
        }
        self._client.upsert_entity(entity=entity, mode=UpdateMode.REPLACE)
        out = self.get_by_natural_key(
            group_id=group_id,
            org_id=org_id,
            project_id=project_id,
            issue_id=issue_id,
        )
        assert out is not None
        return out

    def delete_by_natural_key(
        self,
        *,
        group_id: str,
        org_id: str,
        project_id: str,
        issue_id: str,
    ) -> bool:
        pk = group_id
        rk = table_row_key(org_id, project_id, issue_id)
        try:
            self._client.delete_entity(pk, rk)
        except ResourceNotFoundError:
            return False
        return True
