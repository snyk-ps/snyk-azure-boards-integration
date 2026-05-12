"""Tests for Azure Table row key encoding."""

from __future__ import annotations

import base64

from mapping_store.table_keys import table_row_key


def test_table_row_key_delimiter_form() -> None:
    assert table_row_key("o", "p", "i") == "o|p|i"
    assert (
        table_row_key("550e8400-e29b-41d4-a716-446655440000", "proj", "SNYK-JS-1")
        == "550e8400-e29b-41d4-a716-446655440000|proj|SNYK-JS-1"
    )


def test_table_row_key_base64url_when_slash() -> None:
    rk = table_row_key("o/x", "p", "i")
    assert "|" not in rk
    parts = rk.split("_")
    assert len(parts) == 3
    for p in parts:
        _decoded = base64.urlsafe_b64decode(p + "==")
        assert isinstance(_decoded, bytes)


def test_table_row_key_base64url_when_hash() -> None:
    rk = table_row_key("org", "proj", "issue#1")
    assert "_" in rk


def test_table_row_key_base64url_when_question() -> None:
    rk = table_row_key("org", "proj", "what?")
    assert "_" in rk


def test_table_row_key_base64url_backslash() -> None:
    rk = table_row_key("org\\id", "p", "i")
    parts = rk.split("_")
    assert len(parts) == 3


def test_table_row_key_unicode_without_forbidden_uses_delimiter() -> None:
    assert table_row_key("org", "proj", "café") == "org|proj|café"
