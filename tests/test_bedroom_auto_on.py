from __future__ import annotations

import pytest

from homeassistant.setup import async_setup_component


def _brightness_setting(call_data: dict[str, object], key: str) -> int:
    """Templates render as strings in tests, so normalize settings to ints."""
    return int(str(call_data[key]).strip())


@pytest.mark.freeze_time("2026-05-05 12:00:00-07:00")
async def test_dark_motion_turns_on_bedroom_light(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
    adaptive_lighting_change_switch_settings_calls,
) -> None:
    """Turn on bedroom lights when motion happens in a dark room."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    # These states satisfy the top-level automation guards.
    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
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

    assert len(adaptive_lighting_change_switch_settings_calls) == 1
    assert (
        adaptive_lighting_change_switch_settings_calls[0].data["entity_id"]
        == "switch.adaptive_lighting_adaptive_lighting"
    )
    assert adaptive_lighting_change_switch_settings_calls[0].data["use_defaults"] == "current"
    assert _brightness_setting(adaptive_lighting_change_switch_settings_calls[0].data, "min_brightness") == 5
    assert _brightness_setting(adaptive_lighting_change_switch_settings_calls[0].data, "max_brightness") == 10

    assert len(adaptive_lighting_calls) == 1
    assert adaptive_lighting_calls[0].data["lights"] == "light.bedroom_lights"
    assert adaptive_lighting_calls[0].data["turn_on_lights"] is True


async def test_sleeping_mode_blocks_bedroom_auto_on(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
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

    assert adaptive_lighting_calls == []


@pytest.mark.freeze_time("2026-05-05 14:00:00-07:00")
async def test_door_open_in_dark_room_turns_on_bedroom_light(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
    adaptive_lighting_change_switch_settings_calls,
) -> None:
    """Opening the bedroom door should recover lights when motion is slow."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "on")
    await hass.async_block_till_done()

    assert len(adaptive_lighting_change_switch_settings_calls) == 1
    assert _brightness_setting(adaptive_lighting_change_switch_settings_calls[0].data, "min_brightness") == 15
    assert _brightness_setting(adaptive_lighting_change_switch_settings_calls[0].data, "max_brightness") == 25

    assert len(adaptive_lighting_calls) == 1
    assert adaptive_lighting_calls[0].data["lights"] == "light.bedroom_lights"
    assert adaptive_lighting_calls[0].data["turn_on_lights"] is True


async def test_door_open_auto_on_is_blocked_during_sleep(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
) -> None:
    """Door-open recovery should not steal lighting ownership from Sleep."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "on")
    await hass.async_block_till_done()

    assert adaptive_lighting_calls == []


async def test_main_adaptive_lighting_switch_blocks_door_open_auto_on(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
) -> None:
    """Door-open recovery should respect the main Adaptive Lighting opt-out."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "on")
    await hass.async_block_till_done()

    assert adaptive_lighting_calls == []


@pytest.mark.freeze_time("2026-05-05 18:30:00-07:00")
async def test_manual_light_on_in_dark_room_applies_adaptive_lighting(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
    adaptive_lighting_change_switch_settings_calls,
) -> None:
    """Apply adaptive lighting when the bedroom light is turned on manually in a dark room."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    # These states satisfy the top-level automation guards.
    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")

    # The manual-on branch only needs darkness and an off -> on light transition.
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("light.bedroom_lights", "off")
    await hass.async_block_till_done()

    hass.states.async_set("light.bedroom_lights", "on")
    await hass.async_block_till_done()

    assert len(adaptive_lighting_change_switch_settings_calls) == 1
    assert _brightness_setting(adaptive_lighting_change_switch_settings_calls[0].data, "min_brightness") == 100
    assert _brightness_setting(adaptive_lighting_change_switch_settings_calls[0].data, "max_brightness") == 100

    assert len(adaptive_lighting_calls) == 1
    assert adaptive_lighting_calls[0].data["lights"] == "light.bedroom_lights"
    assert adaptive_lighting_calls[0].data["turn_on_lights"] is True


@pytest.mark.freeze_time("2026-05-05 14:00:00-07:00")
async def test_restart_reapplies_lux_brightness_settings(
    hass,
    adaptive_lighting_lux_brightness_restore_config,
    adaptive_lighting_calls,
    adaptive_lighting_change_switch_settings_calls,
) -> None:
    """Runtime AL setting changes reset on restart, so HA start should reapply them."""

    assert await async_setup_component(
        hass,
        "automation",
        adaptive_lighting_lux_brightness_restore_config,
    )

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "on")
    # In this room, 49 lx can already mean "all bedroom lights are bright".
    # Keep that calibrated reading in the low-brightness bucket.
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "49")
    await hass.async_block_till_done()

    await hass.services.async_call(
        "automation",
        "trigger",
        {
            "entity_id": "automation.bedroom_adaptive_lighting_lux_brightness_restore",
            "skip_condition": False,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert len(adaptive_lighting_change_switch_settings_calls) == 1
    assert _brightness_setting(adaptive_lighting_change_switch_settings_calls[0].data, "min_brightness") == 5
    assert _brightness_setting(adaptive_lighting_change_switch_settings_calls[0].data, "max_brightness") == 10

    assert len(adaptive_lighting_calls) == 1
    assert adaptive_lighting_calls[0].data["lights"] == "light.bedroom_lights"
    assert adaptive_lighting_calls[0].data["turn_on_lights"] is False


async def test_master_toggle_blocks_bedroom_auto_on(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
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

    assert adaptive_lighting_calls == []


async def test_main_adaptive_lighting_switch_blocks_bedroom_auto_on(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
) -> None:
    """Block normal bedroom AL when the main Adaptive Lighting switch is off."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    await hass.async_block_till_done()

    assert adaptive_lighting_calls == []
