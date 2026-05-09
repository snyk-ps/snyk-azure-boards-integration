"""Tests for CLI logging and UTC formatter."""

from __future__ import annotations

import logging
import time

from observability.cli_logging import UtcFormatter, configure_cli_logging


def test_utc_formatter_uses_gmtime_converter() -> None:
    """Formatter converts record time with UTC (``gmtime``)."""
    fmt = UtcFormatter("%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
    assert fmt.converter is time.gmtime


def test_configure_cli_logging_sets_root_handler_with_formatter() -> None:
    """Root logger gets one StreamHandler whose formatter uses UTC ``converter``."""
    configure_cli_logging(level=logging.DEBUG)
    root = logging.getLogger()
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    f = handler.formatter
    assert isinstance(f, UtcFormatter)
    assert f.converter is time.gmtime
