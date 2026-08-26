from __future__ import annotations

import pytest

from homeassistant.setup import async_setup_component


def _fire_hold_timer_finished(hass) -> None:
    """Fire the same event Home Assistant emits when the hold timer completes."""
    hass.bus.async_fire(
        "timer.finished",
        {
            "entity_id": "timer.bedroom_occupancy_hold",
        },
    )


async def test_grillplats_plug_keeps_bedroom_occupied(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_timer_config,
    bedroom_template_config,
) -> None:
    """Treat grillplats_plug as a positive occupancy signal."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(hass, "template", bedroom_template_config)
    await hass.async_block_till_done()

    # No motion and no active TV, but the plug is on.
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    hass.states.async_set("media_player.sony_xr_65a95l_2", "off")
    hass.states.async_set("switch.grillplats_plug", "on")
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "on")
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.bedroom_activity").state == "off"
    assert hass.states.get("binary_sensor.bedroom_occupancy").state == "on"


async def test_all_inactive_signals_clear_bedroom_occupancy(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_timer_config,
    bedroom_template_config,
) -> None:
    """Turn occupancy off when no positive signal remains."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(hass, "template", bedroom_template_config)
    await hass.async_block_till_done()

    # This leaves every positive branch false:
    # - no motion
    # - inactive TV
    # - plug off
    # - door closed, but the hold timer is still idle
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    hass.states.async_set("media_player.sony_xr_65a95l_2", "off")
    hass.states.async_set("switch.grillplats_plug", "off")
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "off")
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "idle"
    assert hass.states.get("binary_sensor.bedroom_activity").state == "off"
    assert hass.states.get("binary_sensor.bedroom_occupancy").state == "off"


async def test_active_hold_timer_keeps_bedroom_occupied(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_timer_config,
    bedroom_template_config,
) -> None:
    """Keep bedroom occupancy on while the hold timer is active regardless of door state."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(hass, "template", bedroom_template_config)
    await hass.async_block_till_done()

    # No direct activity signals remain, so this isolates the hold-timer branch.
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    hass.states.async_set("media_player.sony_xr_65a95l_2", "off")
    hass.states.async_set("switch.grillplats_plug", "off")
    # Door is open
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "on")
    await hass.async_block_till_done()

    await hass.services.async_call(
        "timer",
        "start",
        {
            "entity_id": "timer.bedroom_occupancy_hold",
            "duration": "01:30:00",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "active"
    assert hass.states.get("binary_sensor.bedroom_activity").state == "off"
    assert hass.states.get("binary_sensor.bedroom_occupancy").state == "on"


async def test_reenabling_automations_with_light_on_restarts_hold_timer(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_timer_config,
    bedroom_hold_timer_automation_config,
) -> None:
    """Restart the hold timer when automations come back while the bedroom light is already on."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(
        hass, "automation", bedroom_hold_timer_automation_config
    )
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.automations_enabled", "off")
    hass.states.async_set("light.bedroom_lights", "on")
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "idle"

    hass.states.async_set("input_boolean.automations_enabled", "on")
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "active"


async def test_hold_timer_finished_restarts_when_raw_motion_is_still_on(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_timer_config,
    bedroom_hold_timer_automation_config,
) -> None:
    """The 50-minute check should keep the hold alive if motion is still present."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(
        hass, "automation", bedroom_hold_timer_automation_config
    )
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    hass.states.async_set("light.bedroom_lights", "on")
    await hass.async_block_till_done()

    _fire_hold_timer_finished(hass)
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "active"

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) == 0


@pytest.mark.freeze_time("2026-05-05 18:30:00-07:00")
async def test_hold_timer_finished_turns_lights_back_on_when_motion_still_present(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_timer_config,
    bedroom_hold_timer_automation_config,
) -> None:
    """If lights somehow turned off, the 50-minute motion check should recover them."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(
        hass, "automation", bedroom_hold_timer_automation_config
    )
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    await hass.async_block_till_done()

    _fire_hold_timer_finished(hass)
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "active"

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) >= 1
    assert "brightness_pct" in turn_on_calls[-1].data
    assert "color_temp_kelvin" in turn_on_calls[-1].data


async def test_hold_timer_finished_does_not_restart_when_raw_motion_is_off(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_timer_config,
    bedroom_hold_timer_automation_config,
) -> None:
    """If no motion remains at the 50-minute check, normal vacancy can proceed."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(
        hass, "automation", bedroom_hold_timer_automation_config
    )
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    await hass.async_block_till_done()

    _fire_hold_timer_finished(hass)
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "idle"

    turn_on_calls = [c for c in light_service_calls if c.domain == "light" and c.service == "turn_on" and "light.bedroom_lights" in c.data.get("entity_id", [])]
    assert len(turn_on_calls) == 0


async def test_reenabling_automations_with_light_off_keeps_hold_timer_idle(
    hass,
    light_service_calls,
    input_boolean_service_calls,
    bedroom_timer_config,
    bedroom_hold_timer_automation_config,
) -> None:
    """Do not restart the hold timer when automations come back and the room light is off."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(
        hass, "automation", bedroom_hold_timer_automation_config
    )
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.automations_enabled", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.automations_enabled", "on")
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "idle"
