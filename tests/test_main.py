"""Tests for CLI entrypoint."""

import pytest

from main import main


def test_fetch_without_token_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("SNYK_TOKEN", raising=False)
    code = main(["fetch", "list", "11111111-1111-1111-1111-111111111111"])
    assert code == 1
    err = capsys.readouterr().err
    assert "SNYK_TOKEN" in err


def test_fetch_get_without_issue_id_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SNYK_TOKEN", "x")
    code = main(["fetch", "get", "11111111-1111-1111-1111-111111111111"])
    assert code == 2
    err = capsys.readouterr().err
    assert "issue_id" in err.lower() or "requires" in err.lower()
