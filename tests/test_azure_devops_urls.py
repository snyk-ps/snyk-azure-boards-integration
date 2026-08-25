"""Tests for Azure DevOps URL builders."""

from integrations.azure_devops.urls import (
    classification_node_url,
    normalize_devops_base_url,
    work_item_comment_url,
    work_item_create_url,
    work_item_get_url,
    work_item_type_fields_url,
    work_items_list_url,
    work_item_update_url,
)


def test_normalize_devops_base_url_strips_slash() -> None:
    assert normalize_devops_base_url("https://dev.azure.com/") == "https://dev.azure.com"


def test_work_item_create_url_includes_type_and_api_version() -> None:
    url = work_item_create_url(
        "https://dev.azure.com",
        "my org",
        "my project",
        "Bug",
        api_version="7.1",
    )
    assert url.startswith("https://dev.azure.com/")
    assert "%24Bug" in url or "$Bug" in url
    assert "api-version=7.1" in url


def test_work_item_get_url_encodes_segments() -> None:
    url = work_item_get_url(
        "https://dev.azure.com",
        "org",
        "proj",
        42,
        api_version="7.1",
    )
    assert "/_apis/wit/workitems/42" in url
    assert "api-version=7.1" in url


def test_work_items_list_url_query() -> None:
    url = work_items_list_url(
        "https://dev.azure.com",
        "org",
        "proj",
        [1, 2, 3],
        api_version="7.1",
    )
    assert "ids=1%2C2%2C3" in url or "ids=1,2,3" in url
    assert "errorPolicy=Omit" in url
    assert "api-version=7.1" in url


def test_work_item_type_fields_url() -> None:
    url = work_item_type_fields_url(
        "https://dev.azure.com",
        "org",
        "proj",
        "Bug",
        api_version="7.1",
    )
    assert "/_apis/wit/workitemtypes/Bug/fields" in url
    assert "api-version=7.1" in url


def test_work_item_comment_url_uses_work_items_casing() -> None:
    url = work_item_comment_url(
        "https://dev.azure.com",
        "org",
        "proj",
        9,
        api_version="7.0-preview.3",
    )
    assert "/_apis/wit/workItems/9/comments" in url
    assert "api-version=7.0-preview.3" in url


def test_classification_node_url_root_and_nested() -> None:
    root = classification_node_url(
        "https://dev.azure.com",
        "org",
        "proj",
        "Areas",
        None,
        api_version="7.1",
    )
    assert root.endswith("/_apis/wit/classificationnodes/Areas?api-version=7.1")
    nested = classification_node_url(
        "https://dev.azure.com",
        "org",
        "proj",
        "Areas",
        r"AppTeam\Snyk",
        api_version="7.1",
    )
    assert "/_apis/wit/classificationnodes/Areas/AppTeam/Snyk" in nested
    assert "api-version=7.1" in nested
