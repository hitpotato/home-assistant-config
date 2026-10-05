from __future__ import annotations

from typing import Any
import pytest


def test_yaml_defined_input_booleans(configuration_yaml: dict[str, Any]) -> None:
    """Verify input_boolean helpers are properly defined in configuration.yaml."""
    input_booleans = configuration_yaml.get("input_boolean", {})

    # Newly migrated YAML-defined mode flags
    assert "sleeping_mode" in input_booleans
    assert input_booleans["sleeping_mode"].get("name") == "Sleeping Mode"
    # Ensure no initial: so HA state restore works across restarts
    assert "initial" not in input_booleans["sleeping_mode"]

    assert "focus_mode" in input_booleans
    assert input_booleans["focus_mode"].get("name") == "Focus Mode"
    assert "initial" not in input_booleans["focus_mode"]

    # Preserved existing helpers
    assert "automations_enabled" in input_booleans
    assert "bedroom_auto_on_restore_state" in input_booleans
    assert "bedroom_sleep_override_active" in input_booleans
    assert "bedroom_focus_override_active" in input_booleans
    assert "bedroom_auto_on_enabled" in input_booleans
    assert input_booleans["bedroom_auto_on_enabled"].get("initial") is True


def test_bedroom_occupancy_template_uses_sony_tv(configuration_yaml: dict[str, Any]) -> None:
    """Verify Bedroom Occupancy template references media_player.sony_tv."""
    templates = configuration_yaml.get("template", [])
    binary_sensors = []
    for item in templates:
        if "binary_sensor" in item:
            binary_sensors.extend(item["binary_sensor"])

    occupancy_sensor = next(
        (s for s in binary_sensors if s.get("unique_id") == "bedroom_occupancy_logic_lock"),
        None,
    )
    assert occupancy_sensor is not None
    state_template = occupancy_sensor.get("state", "")

    assert "media_player.sony_tv" in state_template
    assert "media_player.sony_xr_65a95l_2" not in state_template
