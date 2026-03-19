from __future__ import annotations

from homeassistant.setup import async_setup_component


async def test_grillplats_plug_keeps_bedroom_occupied(
    hass,
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


async def test_closed_door_and_active_hold_timer_keep_bedroom_occupied(
    hass,
    bedroom_timer_config,
    bedroom_template_config,
) -> None:
    """Keep bedroom occupancy on while the hold timer is active and the door is closed."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(hass, "template", bedroom_template_config)
    await hass.async_block_till_done()

    # No direct activity signals remain, so this isolates the hold-timer branch.
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "off")
    hass.states.async_set("media_player.sony_xr_65a95l_2", "off")
    hass.states.async_set("switch.grillplats_plug", "off")
    hass.states.async_set("binary_sensor.myggbett_door_window_sensor_door", "off")
    await hass.async_block_till_done()

    await hass.services.async_call(
        "timer",
        "start",
        {
            "entity_id": "timer.bedroom_occupancy_hold",
            "duration": "00:40:00",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get("timer.bedroom_occupancy_hold").state == "active"
    assert hass.states.get("binary_sensor.bedroom_activity").state == "off"
    assert hass.states.get("binary_sensor.bedroom_occupancy").state == "on"
