"""Tests for CLI NDJSON logging and UTC timestamps."""

from __future__ import annotations

import io
import json
import logging
import sys

import pytest

from observability.cli_logging import (
    INTEGRATION_VERBOSE_AZURE_LOGS,
    NdjsonFormatter,
    configure_cli_logging,
    utc_rfc3339_ms_z,
)


def test_utc_rfc3339_ms_z_uses_z_suffix() -> None:
    """Timestamps are RFC 3339 UTC with millisecond field and **Z**."""
    s = utc_rfc3339_ms_z(1_000_000_000.0)
    assert s == "2001-09-09T01:46:40.000Z"
    assert s.endswith("Z")


def test_ndjson_formatter_emits_parseable_object() -> None:
    """Formatter produces one JSON object per line with required keys."""
    logger = logging.getLogger("test_ndjson_fmt")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    h = logging.StreamHandler(stream)
    h.setFormatter(NdjsonFormatter())
    logger.addHandler(h)
    try:
        logger.info("hello world")
    finally:
        logger.removeHandler(h)
    line = stream.getvalue().strip()
    obj = json.loads(line)
    assert obj["level"] == "INFO"
    assert obj["logger"] == "test_ndjson_fmt"
    assert obj["message"] == "hello world"
    assert "timestamp" in obj
    assert obj["timestamp"].endswith("Z")


def test_ndjson_formatter_includes_record_object() -> None:
    """Structured audit payloads appear under ``record``."""
    logger = logging.getLogger("test_ndjson_rec")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    h = logging.StreamHandler(stream)
    h.setFormatter(NdjsonFormatter())
    logger.addHandler(h)
    try:
        logger.info("-", extra={"record": {"event": "integration_http", "method": "GET"}})
    finally:
        logger.removeHandler(h)
    obj = json.loads(stream.getvalue().strip())
    assert "message" not in obj
    assert obj["record"]["event"] == "integration_http"


def test_configure_cli_logging_stdout_ndjson_and_azure_default_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Root uses stdout, ``NdjsonFormatter``, and **azure** at WARNING by default."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    try:
        monkeypatch.delenv(INTEGRATION_VERBOSE_AZURE_LOGS, raising=False)
        configure_cli_logging(level=logging.DEBUG)
        assert len(root.handlers) == 1
        handler = root.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stdout
        assert isinstance(handler.formatter, NdjsonFormatter)
        assert logging.getLogger("azure").level == logging.WARNING
    finally:
        root.handlers.clear()
        for h in saved_handlers:
            root.addHandler(h)
        root.setLevel(saved_level)


def test_configure_cli_logging_verbose_azure_env_sets_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Truth-y **INTEGRATION_VERBOSE_AZURE_LOGS** sets **azure** to INFO."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    try:
        monkeypatch.setenv(INTEGRATION_VERBOSE_AZURE_LOGS, "1")
        configure_cli_logging()
        assert logging.getLogger("azure").level == logging.INFO
    finally:
        root.handlers.clear()
        for h in saved_handlers:
            root.addHandler(h)
        root.setLevel(saved_level)

