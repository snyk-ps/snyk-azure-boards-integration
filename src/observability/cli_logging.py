"""UTC logging configuration for CLI entrypoints."""

from __future__ import annotations

import logging
import time


class UtcFormatter(logging.Formatter):
    """Formatter that emits ``asctime`` in UTC (GMT)."""

    converter = time.gmtime


def configure_cli_logging(*, level: int = logging.INFO) -> None:
    """
    Configure the root logger with UTC timestamps and level.

    Log lines look like::
        2026-05-08T12:00:00 INFO integration_audit {\"event\": \"sync_summary\", ...}
    """
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%SZ"
    handler = logging.StreamHandler()
    handler.setFormatter(UtcFormatter(fmt, datefmt=datefmt))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
