"""Context-local sync run id for correlating integration HTTP audit logs."""

from __future__ import annotations

from contextvars import ContextVar

_SYNC_RUN_ID: ContextVar[str | None] = ContextVar("sync_run_id", default=None)


def get_sync_run_id() -> str | None:
    """Return the active ``sync_run_id`` for this context, or ``None``."""
    return _SYNC_RUN_ID.get()


def set_sync_run_id(sync_run_id: str) -> object:
    """Bind ``sync_run_id`` for the current context; return token for :func:`reset_sync_run_id`."""
    return _SYNC_RUN_ID.set(sync_run_id)


def reset_sync_run_id(token: object) -> None:
    """Restore the previous ``sync_run_id`` binding."""
    _SYNC_RUN_ID.reset(token)
