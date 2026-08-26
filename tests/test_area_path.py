"""Tests for area path ensure logic."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from integrations.azure_devops.errors import AzureDevOpsAuthError, AzureDevOpsClientError
from sync.area_path import (
    AUTO_DEFAULT_AREA_SEGMENT,
    area_path_exists,
    ensure_area_path_exists,
    render_fallback_area_path,
)


def test_ensure_area_path_exists_skips_when_cached() -> None:
    client = MagicMock()
    cache: dict[tuple[str, str, str], bool] = {("org", "proj", "AppTeam\\Snyk"): True}
    ensure_area_path_exists(client, "org", "proj", "AppTeam\\Snyk", cache)
    client.get_classification_node.assert_not_called()


def test_ensure_area_path_exists_walks_and_creates_missing_segments() -> None:
    client = MagicMock()
    client.get_classification_node.side_effect = [
        {"name": "AppTeam"},
        None,
    ]
    cache: dict[tuple[str, str, str], bool] = {}
    ensure_area_path_exists(client, "org", "proj", "AppTeam\\Snyk", cache)
    client.create_classification_node.assert_called_once_with(
        "org",
        "proj",
        "AppTeam",
        AUTO_DEFAULT_AREA_SEGMENT,
    )
    assert cache[("org", "proj", "AppTeam\\Snyk")] is True


def test_ensure_area_path_exists_strips_project_prefix_and_creates_at_root() -> None:
    client = MagicMock()
    client.get_classification_node.return_value = None
    cache: dict[tuple[str, str, str], bool] = {}
    ensure_area_path_exists(
        client,
        "org",
        "test Project Spaces",
        "test Project Spaces\\Snyk",
        cache,
    )
    client.get_classification_node.assert_called_once_with(
        "org",
        "test Project Spaces",
        "Snyk",
    )
    client.create_classification_node.assert_called_once_with(
        "org",
        "test Project Spaces",
        None,
        AUTO_DEFAULT_AREA_SEGMENT,
    )
    assert cache[("org", "test Project Spaces", "test Project Spaces\\Snyk")] is True


def test_ensure_area_path_exists_creates_missing_top_level_area() -> None:
    client = MagicMock()
    client.get_classification_node.side_effect = [
        None,
        None,
    ]
    cache: dict[tuple[str, str, str], bool] = {}
    ensure_area_path_exists(client, "org", "proj", "AppTeam\\Snyk", cache)
    assert client.create_classification_node.call_args_list == [
        (("org", "proj", None, "AppTeam"),),
        (("org", "proj", "AppTeam", AUTO_DEFAULT_AREA_SEGMENT),),
    ]


def test_ensure_area_path_exists_rejects_path_with_only_project_name() -> None:
    client = MagicMock()
    cache: dict[tuple[str, str, str], bool] = {}
    with pytest.raises(AzureDevOpsClientError, match="at least one area segment"):
        ensure_area_path_exists(client, "org", "proj", "proj", cache)


def test_ensure_area_path_exists_propagates_create_auth_error() -> None:
    client = MagicMock()
    client.get_classification_node.side_effect = [
        {"name": "AppTeam"},
        None,
    ]
    client.create_classification_node.side_effect = AzureDevOpsAuthError(
        "forbidden",
        status_code=403,
    )
    cache: dict[tuple[str, str, str], bool] = {}
    with pytest.raises(AzureDevOpsAuthError):
        ensure_area_path_exists(client, "org", "proj", "AppTeam\\Snyk", cache)


def test_render_fallback_area_path_substitutes_project() -> None:
    assert render_fallback_area_path("{project}\\Security", "AppTeam") == "AppTeam\\Security"


def test_area_path_exists_true_when_full_path_present() -> None:
    client = MagicMock()
    client.get_classification_node.return_value = {"name": "TeamA"}
    cache: dict[tuple[str, str, str], bool] = {}
    assert area_path_exists(client, "org", "proj", "proj\\TeamA", cache) is True
    client.get_classification_node.assert_called_once_with("org", "proj", "TeamA")


def test_area_path_exists_false_when_leaf_missing() -> None:
    client = MagicMock()
    client.get_classification_node.return_value = None
    cache: dict[tuple[str, str, str], bool] = {}
    assert area_path_exists(client, "org", "proj", "proj\\Missing", cache) is False
