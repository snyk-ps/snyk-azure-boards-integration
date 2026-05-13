# Contributing

This document is for people who change code or release this repository. Operators should use the [README](README.md): **[Development / local installation](README.md#development-local-installation)** for contributors and smoke tests, **[Deployment / production installation](README.md#deployment-production-installation)** plus **[Deployment](README.md#deployment)** for scheduled containers in Azure (or similar).

## Development setup

- **Python** 3.12 or newer ([`pyproject.toml`](pyproject.toml) `requires-python`).
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** for dependencies (`pyproject.toml`, `uv.lock`).

From the repository root:

```bash
uv sync
```

To include dev dependencies (for example **pytest**):

```bash
uv sync --dev
```

Do not commit secrets. Use environment variables ( **`SNYK_TOKEN`**, **`AZURE_DEVOPS_PAT`**, etc.) when exercising the app locally.

## Running tests

```bash
uv run pytest
```

Tests live under **`tests/`**; **`pythonpath`** includes **`src`** via **`pyproject.toml`**.

## Project layout

| Path | Purpose |
| ---- | ------- |
| `src/commands/` | CLI commands and `argparse` entry points. |
| `src/common/` | Shared helpers (conventions; package may be empty until used). |
| `src/config/` | Configuration loading, defaults, validation. |
| `src/integrations/` | Azure DevOps REST clients and adapters. |
| `src/mapping_store/` | SQLite and Azure Table mapping persistence. |
| `src/observability/` | Logging and structured **`integration_audit`** events. |
| `src/sync/` | Snyk issue lifecycle to Boards and mapping store. |
| `src/snyk/` | Snyk REST usage and parsing. |

Entry point: **`src/main.py`**.

| Path | Purpose |
| ---- | ------- |
| `tests/` | Unit tests; mirror `src/` when helpful. |
| `data/` | Fixtures and sample YAML (for example **`data/sample-config.yaml`**). **Do not commit secrets.** |
| `scripts/` | Helper scripts (for example **`scripts/init_mapping_store.py`**). |

## OpenSpec and specifications

This repo uses **OpenSpec** for spec-driven changes:

1. Read **`openspec/config.yaml`** and **`SPEC.md`** for capability paths.
2. Read **`openspec/AGENTS.md`** for agent workflow.
3. Follow **`.cursor/rules/openspec.mdc`**: propose an approved change under **`openspec/changes/`** before implementation, then apply and archive per project rules.
4. Follow **`.cursor/rules/guidelines.mdc`** for Python 3.12+, uv, secrets via env vars, and tests.

## CI, releases, and containers

**`.github/workflows/`** wires **Release Please** (`tag.yml`) and **Docker publish** to **`ghcr.io`** (`release.yml`) when the repo is configured as a shipping application (root **`VERSION`**, no **`.github/template`** marker blocking workflows).

### Dockerfile

| Item | Detail |
| ---- | ------ |
| Builder | `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` runs `uv sync --locked` from **`pyproject.toml`** / **`uv.lock`**. |
| Runtime | `python:3.12-slim-bookworm`; non-root user **`nonroot`**; `PATH` includes `/app/.venv/bin`. |
| Default command | **ENTRYPOINT** `python src/main.py`; **CMD** `sync --config /config/config.yaml` (mount policy at **`/config/config.yaml`** or override args). |

Local build example:

```bash
docker build -t azure-boards-integration:local .
docker run --rm \
  -e SNYK_TOKEN \
  -e AZURE_DEVOPS_PAT \
  -v "$(pwd)/data/sample-config.yaml:/config/config.yaml:ro" \
  azure-boards-integration:local
```

Use a real config and valid secrets; **`sample-config.yaml`** is illustrative only. Override the default process for other subcommands, for example **`docker run --rm -e SNYK_TOKEN -v "$(pwd)/data/sample-config.yaml:/config/config.yaml:ro" azure-boards-integration:local fetch list --config /config/config.yaml`**.

### GitHub Actions

1. **`tag.yml`**: on push to **`main`** (when workflows are enabled), Release Please proposes version bumps from conventional commits and **`VERSION`** (`release-type: simple`).
2. **`release.yml`**: on tag **`v*.*.*`**, builds **`Dockerfile`**, pushes **`ghcr.io/<owner>/<repo>:<tag>`**, creates a GitHub Release.

If **`.github/template`** is present, those workflows are skipped for template repos. Remove it and add **`VERSION`** for normal product releases.

## Template metadata

The root **`TEMPLATE_VERSION`** file records **upstream template lineage** (semver). **`VERSION`** is the application version for Release Please. They are separate concerns.
