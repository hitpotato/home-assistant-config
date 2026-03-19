from __future__ import annotations

from homeassistant.setup import async_setup_component


async def test_monitored_plug_keeps_bedroom_occupied(
    hass,
    bedroom_timer_config,
    bedroom_template_config,
    bedroom_occupancy_entities,
) -> None:
    """Treat the monitored plug as a positive occupancy signal."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(hass, "template", bedroom_template_config)
    await hass.async_block_till_done()

    # No motion and no active TV, but the plug is on.
    hass.states.async_set(bedroom_occupancy_entities["motion_sensor"], "off")
    hass.states.async_set(bedroom_occupancy_entities["tv"], "off")
    hass.states.async_set(bedroom_occupancy_entities["plug"], "on")
    hass.states.async_set(bedroom_occupancy_entities["door"], "on")
    await hass.async_block_till_done()

    assert hass.states.get(bedroom_occupancy_entities["activity_entity"]).state == "off"
    assert hass.states.get(bedroom_occupancy_entities["occupancy_entity"]).state == "on"


async def test_all_inactive_signals_clear_bedroom_occupancy(
    hass,
    bedroom_timer_config,
    bedroom_template_config,
    bedroom_occupancy_entities,
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
    hass.states.async_set(bedroom_occupancy_entities["motion_sensor"], "off")
    hass.states.async_set(bedroom_occupancy_entities["tv"], "off")
    hass.states.async_set(bedroom_occupancy_entities["plug"], "off")
    hass.states.async_set(bedroom_occupancy_entities["door"], "off")
    await hass.async_block_till_done()

    assert hass.states.get(bedroom_occupancy_entities["hold_timer"]).state == "idle"
    assert hass.states.get(bedroom_occupancy_entities["activity_entity"]).state == "off"
    assert hass.states.get(bedroom_occupancy_entities["occupancy_entity"]).state == "off"


async def test_closed_door_and_active_hold_timer_keep_bedroom_occupied(
    hass,
    bedroom_timer_config,
    bedroom_template_config,
    bedroom_occupancy_entities,
) -> None:
    """Keep bedroom occupancy on while the hold timer is active and the door is closed."""

    assert await async_setup_component(hass, "timer", bedroom_timer_config)
    assert await async_setup_component(hass, "template", bedroom_template_config)
    await hass.async_block_till_done()

    # No direct activity signals remain, so this isolates the hold-timer branch.
    hass.states.async_set(bedroom_occupancy_entities["motion_sensor"], "off")
    hass.states.async_set(bedroom_occupancy_entities["tv"], "off")
    hass.states.async_set(bedroom_occupancy_entities["plug"], "off")
    hass.states.async_set(bedroom_occupancy_entities["door"], "off")
    await hass.async_block_till_done()

    await hass.services.async_call(
        "timer",
        "start",
        {
            "entity_id": bedroom_occupancy_entities["hold_timer"],
            "duration": "00:40:00",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(bedroom_occupancy_entities["hold_timer"]).state == "active"
    assert hass.states.get(bedroom_occupancy_entities["activity_entity"]).state == "off"
    assert hass.states.get(bedroom_occupancy_entities["occupancy_entity"]).state == "on"
