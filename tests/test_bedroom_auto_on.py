from __future__ import annotations

from homeassistant.setup import async_setup_component


async def test_dark_motion_turns_on_bedroom_light(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
) -> None:
    """Turn on bedroom lights when motion happens in a dark room."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    # These states satisfy the top-level automation guards.
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
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    await hass.async_block_till_done()

    assert adaptive_lighting_calls == []


async def test_manual_light_on_in_dark_room_applies_adaptive_lighting(
    hass,
    bedroom_auto_on_config,
    adaptive_lighting_calls,
) -> None:
    """Apply adaptive lighting when the bedroom light is turned on manually in a dark room."""

    assert await async_setup_component(hass, "automation", bedroom_auto_on_config)

    # These states satisfy the top-level automation guards.
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")

    # The manual-on branch only needs darkness and an off -> on light transition.
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("light.bedroom_lights", "off")
    await hass.async_block_till_done()

    hass.states.async_set("light.bedroom_lights", "on")
    await hass.async_block_till_done()

    assert len(adaptive_lighting_calls) == 1
    assert adaptive_lighting_calls[0].data["lights"] == "light.bedroom_lights"
    assert adaptive_lighting_calls[0].data["turn_on_lights"] is True
