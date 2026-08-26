"""Validation and rendering for auto-create fallback area path templates."""

from __future__ import annotations

from config.errors import ConfigError

DEFAULT_FALLBACK_AREA_PATH_TEMPLATE = "{project}\\Snyk"


def render_fallback_area_path(template: str, project: str) -> str:
    """Substitute ``{project}`` in a fallback area path template."""
    proj = str(project or "").strip()
    return str(template or "").replace("{project}", proj)


def validate_fallback_area_path_template(
    raw: object,
    *,
    field_prefix: str,
) -> str | None:
    """
    Validate and return a trimmed fallback template, or ``None`` when absent.

    Raises :class:`ConfigError` when the value is present but invalid.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ConfigError(f"{field_prefix} must be a string")
    template = raw.strip()
    if not template:
        raise ConfigError(f"{field_prefix} must be a non-empty string")
    if "{project}" not in template:
        raise ConfigError(
            f"{field_prefix} must contain {{project}} placeholder",
        )
    rendered = render_fallback_area_path(template, "PlaceholderProject")
    if "\\" not in rendered:
        raise ConfigError(
            f"{field_prefix} must render to Project\\Area format; got {rendered!r}",
        )
    project, _, remainder = rendered.partition("\\")
    if not project.strip() or not remainder.strip():
        raise ConfigError(
            f"{field_prefix} must render to Project\\Area format; got {rendered!r}",
        )
    return template
