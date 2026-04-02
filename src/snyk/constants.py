"""Snyk REST API constants (version and media type).

The Issues API requires a dated ``version`` query parameter and JSON:API-style
headers. Values follow Snyk REST documentation; update when Snyk publishes a
new recommended version string.

See: https://docs.snyk.io/snyk-api/rest-api/getting-started-with-the-rest-api
"""

# Default REST base (no trailing slash) — see openspec/specs/integration-apis/spec.md
DEFAULT_BASE_URL: str = "https://api.snyk.io/rest"

# Recommended API version for REST GET requests (query parameter ``version``).
SNYK_REST_API_VERSION: str = "2025-11-05"

# Maximum page size for group issue list (Snyk REST Issues API).
ISSUES_LIST_LIMIT: int = 100

# Default effective severity filters when the caller does not specify any.
DEFAULT_EFFECTIVE_SEVERITY_LEVELS: tuple[str, ...] = ("high", "critical")

# JSON:API media type for Snyk REST request/response bodies.
SNYK_JSON_API_CONTENT_TYPE: str = "application/vnd.api+json"
