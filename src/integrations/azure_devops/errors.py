"""Errors raised by the Azure DevOps client."""

from __future__ import annotations


class AzureDevOpsApiError(Exception):
    """Base error for Azure DevOps REST failures."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class MissingPatError(AzureDevOpsApiError):
    """Raised when ``AZURE_DEVOPS_PAT`` is unset or empty."""


class AzureDevOpsAuthError(AzureDevOpsApiError):
    """Raised for HTTP 401/403 responses."""


class AzureDevOpsRateLimitError(AzureDevOpsApiError):
    """Raised when rate limiting (HTTP 429) cannot be resolved within the retry budget."""


class AzureDevOpsClientError(AzureDevOpsApiError):
    """Raised for other 4xx responses (validation, not found, etc.)."""


class AzureDevOpsServerError(AzureDevOpsApiError):
    """Raised for 5xx responses."""


class AzureDevOpsTransportError(AzureDevOpsApiError):
    """Raised for connection/DNS/TLS failures and similar transport issues."""
