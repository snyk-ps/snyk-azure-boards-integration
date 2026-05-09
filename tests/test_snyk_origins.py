"""Tests for ``sync_included_snyk_origins`` parsing and ``classify_origin_for_allowlist``."""

from __future__ import annotations

import pytest

from config import ConfigError, load_app_config
from config.snyk_origins import parse_sync_included_snyk_origins
from sync.effective import boards_for_org_mapping
from sync.origin_filter import (
    EXCLUSION_ORIGIN_NOT_IN_ALLOWLIST,
    EXCLUSION_ORIGIN_UNKNOWN,
    classify_origin_for_allowlist,
)


def test_parse_none_and_empty_means_no_filter() -> None:
    assert parse_sync_included_snyk_origins(None, field_prefix="x") is None
    assert parse_sync_included_snyk_origins("", field_prefix="x") is None
    assert parse_sync_included_snyk_origins("  , , ", field_prefix="x") is None


def test_parse_comma_split_strip() -> None:
    assert parse_sync_included_snyk_origins(
        " github , gitlab ",
        field_prefix="t",
    ) == ("github", "gitlab")


def test_parse_rejects_non_string() -> None:
    with pytest.raises(ConfigError, match="must be a string"):
        parse_sync_included_snyk_origins(1, field_prefix="p")  # type: ignore[arg-type]


def test_parse_rejects_unknown_token() -> None:
    with pytest.raises(ConfigError, match="unknown origin"):
        parse_sync_included_snyk_origins("not-a-real-origin-value", field_prefix="p")


def test_parse_rejects_invalid_chars() -> None:
    with pytest.raises(ConfigError, match="invalid origin"):
        parse_sync_included_snyk_origins("github,Foo_Bar", field_prefix="p")


def test_load_app_config_merge_override_origins(tmp_path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        "azure_boards:\n"
        "  defaults:\n"
        "    organization: o\n"
        "    project: p\n"
        "    sync_included_snyk_origins: github,gitlab\n"
        "  org_mappings:\n"
        "    - organization: o2\n"
        "      project: p2\n"
        "      snyk_org_id: oid\n"
        "      snyk_org_slug: slug\n"
        "      overrides:\n"
        "        sync_included_snyk_origins: cli\n"
        "snyk:\n"
        "  group_id: g\n",
        encoding="utf-8",
    )
    c = load_app_config(config_path=str(p), cli_group_id=None)
    assert c.azure_boards.defaults.sync_included_snyk_origins == ("github", "gitlab")
    boards = boards_for_org_mapping(c, c.azure_boards.org_mappings[0])
    assert boards.defaults.sync_included_snyk_origins == ("cli",)


def test_classify_no_allowlist_includes_all() -> None:
    ok, reason = classify_origin_for_allowlist("cli", None)
    assert ok and reason == ""
    ok, reason = classify_origin_for_allowlist("", ())
    assert ok and reason == ""


def test_classify_unknown_origin_under_allowlist() -> None:
    ok, reason = classify_origin_for_allowlist("", ("github",))
    assert not ok
    assert reason == EXCLUSION_ORIGIN_UNKNOWN


def test_classify_not_in_list() -> None:
    ok, reason = classify_origin_for_allowlist("cli", ("github",))
    assert not ok
    assert reason == EXCLUSION_ORIGIN_NOT_IN_ALLOWLIST


def test_classify_match() -> None:
    ok, reason = classify_origin_for_allowlist("github", ("github", "gitlab"))
    assert ok and reason == ""
