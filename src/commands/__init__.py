"""CLI command wiring (argparse) for the application."""

from .fetch import build_parser, run_fetch

__all__ = ["build_parser", "run_fetch"]
