"""Tests for ``config`` loading, defaults, and precedence."""

from __future__ import annotations

from pathlib import Path

import pytest

from config import ConfigError, load_app_config, load_yaml_file, parse_yaml_bytes


def test_parse_yaml_bytes_invalid() -> None:
    with pytest.raises(ConfigError, match="Invalid"):
        parse_yaml_bytes(b"[", source="test")


def test_parse_yaml_bytes_root_not_mapping() -> None:
    with pytest.raises(ConfigError, match="mapping"):
        parse_yaml_bytes(b"[]", source="test")


def test_load_yaml_file_missing(tmp_path: Path) -> None:
    p = tmp_path / "nope.yaml"
    with pytest.raises(ConfigError, match="not found"):
        load_yaml_file(p)


def test_load_yaml_file_rejects_null_byte() -> None:
    with pytest.raises(ConfigError, match="Invalid"):
        load_yaml_file("foo\x00bar")


def test_load_app_config_defaults_no_file() -> None:
    c = load_app_config(config_path=None, cli_group_id=None)
    assert c.azure_boards.create_new_work_items is True
    assert c.snyk.severity_threshold == "high"
    assert c.snyk.group_id == ""
    assert c.work_item_template == {}


def test_load_app_config_from_yaml_file(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        "snyk:\n  group_id: g-from-file\n  severity_threshold: critical\n",
        encoding="utf-8",
    )
    c = load_app_config(config_path=str(p), cli_group_id=None)
    assert c.snyk.group_id == "g-from-file"
    assert c.snyk.severity_threshold == "critical"


def test_cli_group_id_overrides_file(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text("snyk:\n  group_id: from-file\n", encoding="utf-8")
    c = load_app_config(config_path=str(p), cli_group_id="from-cli")
    assert c.snyk.group_id == "from-cli"


def test_env_group_id_overrides_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = tmp_path / "c.yaml"
    p.write_text("snyk:\n  group_id: from-file\n", encoding="utf-8")
    monkeypatch.setenv("SNYK_GROUP_ID", "from-env")
    c = load_app_config(config_path=str(p), cli_group_id=None)
    assert c.snyk.group_id == "from-env"


def test_cli_overrides_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = tmp_path / "c.yaml"
    p.write_text("snyk:\n  group_id: from-file\n", encoding="utf-8")
    monkeypatch.setenv("SNYK_GROUP_ID", "from-env")
    c = load_app_config(config_path=str(p), cli_group_id="from-cli")
    assert c.snyk.group_id == "from-cli"


def test_resolve_config_path_cli_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from config.loader import resolve_config_path

    monkeypatch.setenv("SNYK_APP_CONFIG", "/env/path.yaml")
    assert resolve_config_path("/cli/path.yaml") == "/cli/path.yaml"


def test_resolve_config_path_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from config.loader import resolve_config_path

    monkeypatch.setenv("SNYK_APP_CONFIG", "/env/path.yaml")
    assert resolve_config_path(None) == "/env/path.yaml"


def test_snyk_extra_keys_preserved(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        "snyk:\n  group_id: g\n  future_key: 42\n",
        encoding="utf-8",
    )
    c = load_app_config(config_path=str(p), cli_group_id=None)
    assert c.snyk.extra.get("future_key") == 42


def test_invalid_severity_in_yaml(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text("snyk:\n  group_id: g\n  severity_threshold: bogus\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="severity_threshold"):
        load_app_config(config_path=str(p), cli_group_id=None)


def test_azure_boards_create_new_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_BOARDS_CREATE_NEW_WORK_ITEMS", "false")
    c = load_app_config(config_path=None, cli_group_id=None)
    assert c.azure_boards.create_new_work_items is False


def test_load_app_config_config_path_env_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When CLI passes config path, SNYK_APP_CONFIG file is not loaded."""
    env_file = tmp_path / "env.yaml"
    env_file.write_text("snyk:\n  group_id: wrong\n", encoding="utf-8")
    cli_file = tmp_path / "cli.yaml"
    cli_file.write_text("snyk:\n  group_id: right\n", encoding="utf-8")
    monkeypatch.setenv("SNYK_APP_CONFIG", str(env_file))
    c = load_app_config(config_path=str(cli_file), cli_group_id=None)
    assert c.snyk.group_id == "right"


def test_mapping_store_defaults_no_file() -> None:
    c = load_app_config(config_path=None, cli_group_id=None)
    assert c.mapping_store == "sqlite"
    assert c.sqlite_path == "data/mapping_store.sqlite"


def test_mapping_store_from_yaml(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        "mapping_store: sqlite\nsqlite_path: custom/db.sqlite\n",
        encoding="utf-8",
    )
    c = load_app_config(config_path=str(p), cli_group_id=None)
    assert c.mapping_store == "sqlite"
    assert c.sqlite_path == "custom/db.sqlite"


def test_mapping_store_env_overrides_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        "mapping_store: sqlite\nsqlite_path: from-yaml.sqlite\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MAPPING_STORE", "sqlite")
    monkeypatch.setenv("MAPPING_STORE_SQLITE_PATH", "from-env.sqlite")
    c = load_app_config(config_path=str(p), cli_group_id=None)
    assert c.sqlite_path == "from-env.sqlite"


def test_sqlite_path_cli_overrides_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = tmp_path / "c.yaml"
    p.write_text("sqlite_path: from-yaml.sqlite\n", encoding="utf-8")
    monkeypatch.setenv("MAPPING_STORE_SQLITE_PATH", "from-env.sqlite")
    c = load_app_config(
        config_path=str(p),
        cli_group_id=None,
        cli_sqlite_path="from-cli.sqlite",
    )
    assert c.sqlite_path == "from-cli.sqlite"


def test_empty_sqlite_path_in_yaml_uses_default(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text("sqlite_path: \"\"\n", encoding="utf-8")
    c = load_app_config(config_path=str(p), cli_group_id=None)
    assert c.sqlite_path == "data/mapping_store.sqlite"


def test_invalid_mapping_store_in_yaml(tmp_path: Path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text("mapping_store: cosmos\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping_store"):
        load_app_config(config_path=str(p), cli_group_id=None)
