"""Exceptions raised by the Snyk REST client."""


class SnykApiError(Exception):
    """Base class for Snyk REST API failures."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class MissingTokenError(SnykApiError):
    """Raised when ``SNYK_TOKEN`` is required but missing or empty."""


class SnykAuthError(SnykApiError):
    """Raised for HTTP 401 / 403 responses."""


class SnykClientError(SnykApiError):
    """Raised for HTTP 4xx responses other than auth failures."""


class SnykRateLimitError(SnykClientError):
    """Raised when HTTP 429 persists after bounded retries (rate limit)."""


class SnykServerError(SnykApiError):
    """Raised for HTTP 5xx responses."""


class SnykTransportError(SnykApiError):
    """Raised for network-level failures (timeouts, connection errors)."""
