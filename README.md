# Home Assistant Config

This repo contains a public-safe Home Assistant configuration focused on bedroom occupancy and lighting automations, plus a pytest-based scenario test harness.

## Main Files

- `configuration.yaml`
  - root Home Assistant config for this repo
  - defines `Bedroom Activity`
  - defines `Bedroom Occupancy`
  - defines the occupancy hold timer

- `automations.yaml`
  - bedroom lighting automations
  - occupancy hold timer automation
  - air-quality alert automations

- `tests/`
  - pytest-based Home Assistant scenario tests
  - reads the tracked public-safe repo YAML instead of duplicating config in Python

- `pyproject.toml`
  - Python test project config

- `.python-version`
  - pins the repo to Python 3.14 for the local `uv` workflow

- `uv.lock`
  - lockfile for reproducible Python test dependencies

- `scripts/sanitize_yaml.py`
  - refreshes the tracked public-safe YAML from the ignored local real YAML

## Bedroom Architecture

The bedroom logic uses a two-layer occupancy model:

1. `Bedroom Activity`
   - immediate activity signal
   - currently driven by the raw motion sensor

2. `Bedroom Occupancy`
   - retained room-level occupancy state
   - becomes `on` when there is fresh activity, active TV, `grillplats_plug` on, or an active hold timer while the door is closed

This split helps avoid false light-off behavior while still allowing fast light-on behavior.

## Public And Local Config Workflow

- The repo root `configuration.yaml` and `automations.yaml` are the tracked public-safe copies.
- The real local Home Assistant files live under `.local/real/` and are ignored by git.
- Before editing `.local/real/configuration.yaml` or `.local/real/automations.yaml`,
  run `uv run python scripts/backup_real_yaml.py` to snapshot them into
  `.local/backups/<timestamp>/`.
- Run `uv run python scripts/sanitize_yaml.py` to refresh the tracked public-safe root files from the ignored local real files.
- After sanitizing, review the tracked changes with `git diff -- configuration.yaml automations.yaml`
  and then run `uv run pytest`.
- The same real ID is mapped to the same fake ID across both YAML files within one sanitize run.

## Private Repo YAML Workflow

This repo now also has a helper flow for a paired private YAML repo:

- The private repo is expected at the sibling path `../home-assistant-config-private` by default.
- You can override that location with `HA_PRIVATE_YAML_REPO=/path/to/private-repo`.
- The private repo is expected to track the real root `configuration.yaml` and `automations.yaml`.

Use the workflow helper like this:

```bash
uv run python scripts/yaml_flow.py start
uv run python scripts/yaml_flow.py refresh
```

- `start`
  - reads the current public branch name
  - switches or creates the matching private branch
  - creates a new private branch from private `origin/main` if needed
  - refreshes the tracked public-safe YAML from the private repo

- `refresh`
  - reads the current private working tree, including uncommitted YAML edits
  - rewrites the tracked public-safe YAML in this repo
  - refuses to run if tracked public `configuration.yaml` or `automations.yaml` already have local edits

This keeps the private repo as the source of truth for real YAML while the public repo stays safe for tests and review.

## YAML Parity CI

The repo also includes a parity workflow at `.github/workflows/yaml-parity.yml`.

- It only runs for trusted same-repo pull requests.
- It checks that the matching private branch exists.
- It sanitizes the private repo YAML and compares it against the tracked public YAML.
- The comparison canonicalizes random mask values first, so CI stays stable without making public masks stable across history.

Repository configuration needed for that workflow:

- repository variables
  - `PRIVATE_YAML_REPO_OWNER`
  - `PRIVATE_YAML_REPO_NAME`
- repository secrets
  - `PRIVATE_YAML_APP_ID`
  - `PRIVATE_YAML_APP_PRIVATE_KEY`

If parity fails because the public mirror is stale, run:

```bash
uv run python scripts/yaml_flow.py refresh
```

Then commit the updated public YAML and push again.

## Test Setup

The repo uses:

- `uv` for Python/runtime and environment management
- Python 3.14
- `pytest`
- `pytest-homeassistant-custom-component`

The tests are closer to mocked integration tests than tiny unit tests:
- they boot the relevant Home Assistant components
- load tracked public-safe config from the repo YAML
- fake entity states and service calls
- assert behavior

## Running Tests

```bash
uv sync --group dev
uv run python scripts/sanitize_yaml.py
uv run pytest
```
