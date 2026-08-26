from __future__ import annotations

import pytest

from homeassistant.setup import async_setup_component


def _brightness_setting(call_data: dict[str, object], key: str) -> int:
    """Templates render as strings in tests, so normalize settings to ints."""
    return int(str(call_data[key]).strip())


@pytest.mark.freeze_time("2026-05-05 12:00:00-07:00")
async def test_dark_motion_turns_on_bedroom_light(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_auto_on_config,
    switch_service_calls,
) -> None:
    """Turn on bedroom lights when motion happens in a dark room."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    # These states satisfy the top-level automation guards.
    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")

    # These states satisfy the motion branch conditions.
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    await hass.async_block_till_done()

    # The automation only reacts to the off -> on edge, so we create it here.
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    await hass.async_block_till_done()

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) >= 1
    assert "brightness_pct" in turn_on_calls[-1].data
    assert "color_temp_kelvin" in turn_on_calls[-1].data


async def test_sleeping_mode_blocks_bedroom_auto_on(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_auto_on_config,
) -> None:
    """Block auto-on when sleeping mode is enabled."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    # Keep the room dark, but flip the main guard into the blocking state.
    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    await hass.async_block_till_done()

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) == 0


@pytest.mark.freeze_time("2026-05-05 14:00:00-07:00")
async def test_door_open_in_dark_room_turns_on_bedroom_light(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_auto_on_config,
    switch_service_calls,
) -> None:
    """Opening the bedroom door should recover lights when motion is slow."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "on")
    await hass.async_block_till_done()

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) >= 1
    assert "brightness_pct" in turn_on_calls[-1].data
    assert "color_temp_kelvin" in turn_on_calls[-1].data


async def test_door_open_auto_on_is_blocked_during_sleep(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_auto_on_config,
) -> None:
    """Door-open recovery should not steal lighting ownership from Sleep."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "on")
    await hass.async_block_till_done()

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) == 0



async def test_manual_light_on_in_dark_room_applies_adaptive_lighting(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_auto_on_config,
) -> None:
    """Apply adaptive lighting when the bedroom light is turned on manually in a dark room."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    # These states satisfy the top-level automation guards.
    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")

    # The manual-on branch only needs darkness and an off -> on light transition.
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("light.bedroom_lights", "off")
    await hass.async_block_till_done()

    hass.states.async_set("light.bedroom_lights", "on")
    await hass.async_block_till_done()

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) >= 1
    assert "brightness_pct" in turn_on_calls[-1].data
    assert "color_temp_kelvin" in turn_on_calls[-1].data


@pytest.mark.freeze_time("2026-05-05 14:00:00-07:00")

async def test_master_toggle_blocks_bedroom_auto_on(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_auto_on_config,
) -> None:
    """Block auto-on when the repo-wide automation toggle is disabled."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    hass.states.async_set("input_boolean.automations_enabled", "off")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    await hass.async_block_till_done()

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) == 0



