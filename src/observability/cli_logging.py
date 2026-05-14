"""NDJSON logging configuration for CLI entrypoints (stdout, UTC timestamps)."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime

# When truthy, lowers ``azure.*`` loggers from WARNING to INFO for SDK troubleshooting.
INTEGRATION_VERBOSE_AZURE_LOGS = "INTEGRATION_VERBOSE_AZURE_LOGS"


def utc_rfc3339_ms_z(epoch_seconds: float) -> str:
    """
    Format ``epoch_seconds`` as RFC 3339 UTC with millisecond precision and **Z** suffix.

    Example: ``2026-05-14T12:00:00.000Z``
    """
    dt = datetime.fromtimestamp(epoch_seconds, tz=UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _truthy_env(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in ("1", "true", "yes", "on")


class NdjsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON object (one line) for Log Analytics parsing."""

    def format(self, record: logging.LogRecord) -> str:
        """Return one NDJSON line with ``timestamp``, ``level``, ``logger``, and body fields."""
        payload: dict[str, object] = {
            "timestamp": utc_rfc3339_ms_z(record.created),
            "level": record.levelname,
            "logger": record.name,
        }
        structured = getattr(record, "record", None)
        if structured is not None:
            payload["record"] = structured
        else:
            payload["message"] = record.getMessage()
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info).rstrip()
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def configure_cli_logging(*, level: int = logging.INFO) -> None:
    """
    Configure the root logger: **NDJSON** lines on **stdout**, UTC **timestamp** per record.

    Each line is a JSON object with ``timestamp`` (RFC 3339 UTC **Z**), ``level``,
    ``logger``, optional ``message``, optional ``record`` (structured audit payload),
    and optional ``exception`` for tracebacks.

    After configuration, the **azure** logger namespace defaults to **WARNING** so SDK
    HTTP **INFO** noise does not flood logs. Set environment variable
    **INTEGRATION_VERBOSE_AZURE_LOGS** to ``1`` / ``true`` / ``yes`` / ``on`` to allow
    **INFO** on **azure** loggers for troubleshooting.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(NdjsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    if _truthy_env(INTEGRATION_VERBOSE_AZURE_LOGS):
        logging.getLogger("azure").setLevel(logging.INFO)
    else:
        logging.getLogger("azure").setLevel(logging.WARNING)
