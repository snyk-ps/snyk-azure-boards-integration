"""Azure DevOps REST defaults aligned with ``integration-apis``."""

from __future__ import annotations

# Default cloud host for Azure DevOps Services (see openspec/specs/integration-apis).
DEFAULT_AZURE_DEVOPS_BASE_URL: str = "https://dev.azure.com"

# Work Item Tracking (non-comment) operations use api-version 7.1 per integration-apis.
AZURE_DEVOPS_WIT_API_VERSION: str = "7.1"

# Comments API is preview-documented in integration-apis; keep in sync when that spec changes.
AZURE_DEVOPS_COMMENT_API_VERSION: str = "7.0-preview.3"

AZURE_DEVOPS_PAT_ENV: str = "AZURE_DEVOPS_PAT"

JSON_PATCH_CONTENT_TYPE: str = "application/json-patch+json"
