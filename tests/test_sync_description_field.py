"""Tests for work item description field resolution."""

from __future__ import annotations

import json

import pytest
from urllib.request import Request

from config.errors import ConfigError
from config.field_refs import (
    DESCRIPTION_FIELD_REPRO_STEPS,
    DESCRIPTION_FIELD_SYSTEM,
)
from config.models import (
    AppConfig,
    AzureBoardsConfig,
    AzureBoardsDefaults,
    OrgMapping,
    SnykConfig,
)
from integrations.azure_devops.client import WorkItemsClient
from sync.description_field import DescriptionFieldResolver, warm_description_fields_for_sync


class _FakeResp:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _fields_json(*reference_names: str) -> bytes:
    value = [{"referenceName": name} for name in reference_names]
    return json.dumps({"count": len(value), "value": value}).encode("utf-8")


def test_resolver_auto_prefers_description_when_both_exist() -> None:
    captured: list[str] = []

    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        captured.append(req.full_url)
        return _FakeResp(_fields_json(DESCRIPTION_FIELD_SYSTEM, DESCRIPTION_FIELD_REPRO_STEPS))

    client = WorkItemsClient(pat="x", opener=opener)
    resolver = DescriptionFieldResolver(client)
    assert resolver.resolve("org", "proj", "Bug", None) == DESCRIPTION_FIELD_SYSTEM
    assert resolver.resolve("org", "proj", "Bug", None) == DESCRIPTION_FIELD_SYSTEM
    assert len(captured) == 1


def test_resolver_auto_falls_back_to_repro_steps() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        return _FakeResp(_fields_json(DESCRIPTION_FIELD_REPRO_STEPS))

    client = WorkItemsClient(pat="x", opener=opener)
    resolver = DescriptionFieldResolver(client)
    assert resolver.resolve("org", "proj", "Bug", None) == DESCRIPTION_FIELD_REPRO_STEPS


def test_resolver_explicit_skips_fallback() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        return _FakeResp(_fields_json(DESCRIPTION_FIELD_SYSTEM, DESCRIPTION_FIELD_REPRO_STEPS))

    client = WorkItemsClient(pat="x", opener=opener)
    resolver = DescriptionFieldResolver(client)
    assert (
        resolver.resolve("org", "proj", "Bug", DESCRIPTION_FIELD_REPRO_STEPS)
        == DESCRIPTION_FIELD_REPRO_STEPS
    )


def test_resolver_explicit_missing_field_raises() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        return _FakeResp(_fields_json(DESCRIPTION_FIELD_SYSTEM))

    client = WorkItemsClient(pat="x", opener=opener)
    resolver = DescriptionFieldResolver(client)
    with pytest.raises(ConfigError, match="not defined"):
        resolver.resolve("org", "proj", "Bug", DESCRIPTION_FIELD_REPRO_STEPS)


def test_resolver_auto_failure_when_no_supported_fields() -> None:
    def opener(req: Request, timeout: float = 0) -> _FakeResp:
        return _FakeResp(_fields_json("System.Title"))

    client = WorkItemsClient(pat="x", opener=opener)
    resolver = DescriptionFieldResolver(client)
    with pytest.raises(ConfigError, match="No supported work item description field"):
        resolver.resolve("org", "proj", "Custom", None)


def test_warm_description_fields_for_org_mappings() -> None:
    calls: list[tuple[str, str, str, str | None]] = []

    class _StubResolver:
        def resolve(
            self,
            organization: str,
            project: str,
            work_item_type: str,
            configured: str | None,
        ) -> str:
            calls.append((organization, project, work_item_type, configured))
            return DESCRIPTION_FIELD_SYSTEM

    app = AppConfig(
        azure_boards=AzureBoardsConfig(
            defaults=AzureBoardsDefaults(work_item_type="Task"),
            org_mappings=[
                OrgMapping(
                    organization="o1",
                    project="p1",
                    snyk_org_id="id1",
                    snyk_org_slug="slug1",
                ),
            ],
        ),
        work_item_template={},
        snyk=SnykConfig(),
    )
    warm_description_fields_for_sync(app, _StubResolver())  # type: ignore[arg-type]
    assert calls == [("o1", "p1", "Task", None)]
