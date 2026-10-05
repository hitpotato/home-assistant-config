from __future__ import annotations

from datetime import timedelta
from typing import Any
import pytest
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed


def test_late_night_dim_light_config_brightness_pct_10(
    late_night_dim_light_config: dict[str, Any],
) -> None:
    """Verify Late-Night Dim Light Mode specifies brightness_pct: 10 and 2200K."""
    actions = late_night_dim_light_config["automation"][0]["actions"]
    repeat_seq = actions[0]["repeat"]["sequence"]
    turn_on_action = repeat_seq[0]
    assert turn_on_action["action"] == "light.turn_on"
    assert turn_on_action["data"]["brightness_pct"] == 10
    assert turn_on_action["data"]["color_temp_kelvin"] == 2200
    assert turn_on_action["data"]["transition"] == 2
    assert turn_on_action["target"]["entity_id"] == "light.window_light"


async def test_late_night_dim_light_executes_service_call(
    hass,
    late_night_dim_light_config,
    light_service_calls,
) -> None:
    """Turn on window light at 10% brightness and 2200K during sleep when motion is detected."""

    assert await async_setup_component(hass, "automation", late_night_dim_light_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    await hass.async_block_till_done()

    # Trigger motion during sleep: repeat while loop enters because occupancy is on
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    import asyncio
    await asyncio.sleep(0)

    # Now set occupancy off so wait_for_trigger and while loop terminate cleanly
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()

    turn_on_calls = [
        c
        for c in light_service_calls
        if c.domain == "light"
        and c.service == "turn_on"
        and "light.window_light" in c.data.get("entity_id", [])
    ]
    assert len(turn_on_calls) >= 1
    assert turn_on_calls[0].data.get("brightness_pct") == 10
    assert turn_on_calls[0].data.get("color_temp_kelvin") == 2200
    assert turn_on_calls[0].data.get("transition") == 2


async def test_late_night_dim_light_blocked_when_sleeping_mode_off(
    hass,
    late_night_dim_light_config,
    light_service_calls,
) -> None:
    """Do not trigger late-night dim light mode when sleeping mode is off."""

    assert await async_setup_component(hass, "automation", late_night_dim_light_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    await hass.async_block_till_done()

    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    await hass.async_block_till_done()

    turn_on_calls = [
        c
        for c in light_service_calls
        if c.domain == "light"
        and c.service == "turn_on"
        and "light.window_light" in c.data.get("entity_id", [])
    ]
    assert len(turn_on_calls) == 0
