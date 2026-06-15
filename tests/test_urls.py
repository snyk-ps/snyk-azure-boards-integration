"""Tests for Snyk REST URL resolution (``links.next``)."""

import pytest

from snyk.constants import DEFAULT_API_ORIGIN, DEFAULT_BASE_URL
from snyk.urls import (
    normalize_api_origin,
    normalize_base_url,
    resolve_api_origin,
    resolve_next_url,
    resolve_snyk_rest_base,
    rest_base_from_origin,
    v1_base_from_origin,
)


def test_normalize_base_url_strips_trailing_slash() -> None:
    assert normalize_base_url("https://api.snyk.io/rest/") == "https://api.snyk.io/rest"


def test_default_api_origin_is_snyk_us_01() -> None:
    assert DEFAULT_API_ORIGIN == "https://api.snyk.io"
    assert DEFAULT_BASE_URL == "https://api.snyk.io/rest"


def test_normalize_api_origin_strips_trailing_slash() -> None:
    assert normalize_api_origin("https://api.us.snyk.io/") == "https://api.us.snyk.io"


def test_rest_base_from_origin() -> None:
    assert rest_base_from_origin("https://api.eu.snyk.io") == "https://api.eu.snyk.io/rest"


def test_v1_base_from_origin() -> None:
    assert v1_base_from_origin("https://api.au.snyk.io") == "https://api.au.snyk.io/v1"


def test_resolve_api_origin_from_rest_suffix() -> None:
    assert resolve_api_origin("https://api.us.snyk.io/rest") == "https://api.us.snyk.io"
    assert resolve_api_origin("https://api.us.snyk.io/rest/") == "https://api.us.snyk.io"


def test_resolve_snyk_rest_base_accepts_origin_or_rest() -> None:
    assert resolve_snyk_rest_base("https://api.eu.snyk.io") == "https://api.eu.snyk.io/rest"
    assert resolve_snyk_rest_base("https://api.eu.snyk.io/rest") == "https://api.eu.snyk.io/rest"


def test_resolve_next_url_none_or_empty() -> None:
    assert resolve_next_url("https://api.snyk.io/rest", None) is None
    assert resolve_next_url("https://api.snyk.io/rest", "") is None
    assert resolve_next_url("https://api.snyk.io/rest", "   ") is None


def test_resolve_next_url_absolute_https() -> None:
    u = "https://api.snyk.io/rest/orgs/x/issues?page=2"
    assert resolve_next_url("https://api.snyk.io/rest", u) == u


def test_resolve_next_url_rest_prefix_no_double_rest() -> None:
    base = "https://api.snyk.io/rest"
    nxt = "rest/orgs/11111111-1111-1111-1111-111111111111/issues?page=2"
    out = resolve_next_url(base, nxt)
    assert out is not None
    assert "rest/rest/" not in out
    assert out.endswith("/orgs/11111111-1111-1111-1111-111111111111/issues?page=2")


def test_resolve_next_url_base_with_trailing_slash_still_no_double_rest() -> None:
    base = "https://api.snyk.io/rest/"
    nxt = "rest/orgs/x/issues?page=2"
    out = resolve_next_url(base, nxt)
    assert out is not None
    assert "rest/rest/" not in out


def test_resolve_next_url_orgs_path_without_rest_prefix() -> None:
    base = "https://api.snyk.io/rest"
    nxt = "orgs/x/issues?page=2"
    out = resolve_next_url(base, nxt)
    assert out == "https://api.snyk.io/rest/orgs/x/issues?page=2"


def test_resolve_next_url_absolute_path_rest() -> None:
    base = "https://api.snyk.io/rest"
    nxt = "/rest/orgs/x/issues?page=2"
    out = resolve_next_url(base, nxt)
    assert out is not None
    assert "rest/rest/" not in out
    assert "/rest/orgs/x/issues" in out


def test_resolve_next_url_absolute_path_orgs() -> None:
    base = "https://api.snyk.io/rest"
    nxt = "/orgs/x/issues?page=2"
    out = resolve_next_url(base, nxt)
    assert out == "https://api.snyk.io/rest/orgs/x/issues?page=2"


@pytest.mark.parametrize(
    ("base", "nxt", "expect_substring"),
    [
        (
            "https://example.test/rest",
            "rest/groups/g/issues?page=2",
            "example.test/rest/groups/g/issues",
        ),
    ],
)
def test_resolve_next_url_param_group_style(
    base: str,
    nxt: str,
    expect_substring: str,
) -> None:
    out = resolve_next_url(base, nxt)
    assert out is not None
    assert expect_substring in out
    assert "rest/rest/" not in out
