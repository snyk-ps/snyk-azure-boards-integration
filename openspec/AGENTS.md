# OpenSpec agents — this repository

1. Read **`openspec/config.yaml`** (`context`, then `rules`) for product summary, Azure reference, API pointers, Python constraints, and per-artifact hints.
2. Read **`openspec/specs/<capability>/spec.md`** for the capability you are changing; use **P2-FR-*** IDs when citing requirements.
3. Follow **`.cursor/rules/openspec.mdc`** for propose → review → apply → archive; do not implement without an approved change under **`openspec/changes/`**.
4. Follow **`.cursor/rules/guidelines.mdc`** for Python 3.12+, uv, argparse, secrets via environment variables, tests, and Snyk policy.

Capabilities: **`sync-lifecycle`**, **`azure-platform`**, **`observability`**, **`integration-apis`**, **`snyk-issues-client`**. See **`SPEC.md`** for paths into `openspec/specs/`.
