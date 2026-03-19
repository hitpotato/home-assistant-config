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
- Run `uv run python scripts/sanitize_yaml.py` to refresh the tracked public-safe root files from the ignored local real files.
- The same real ID is mapped to the same fake ID across both YAML files within one sanitize run.

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
