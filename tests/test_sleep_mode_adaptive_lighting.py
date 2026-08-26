from __future__ import annotations

from homeassistant.setup import async_setup_component


async def test_sleep_start_records_on_state_cancels_focus_and_disables_main_al(
    hass,
    sleep_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Sleep entry should save the main AL state before taking temporary control."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "on")
    hass.states.async_set("input_boolean.bedroom_auto_on_restore_state", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.focus_mode").state == "off"
    assert hass.states.get("input_boolean.bedroom_auto_on_restore_state").state == "on"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "on"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"
    assert hass.states.get("input_boolean.bedroom_auto_on_enabled").state == "off"
    assert all(
        call.data.get("entity_id") != "switch.adaptive_lighting_sleep_mode_adaptive_lighting"
        for call in switch_service_calls
    )


async def test_sleep_start_does_not_reapply_normal_al_while_cancelling_focus(
    hass,
    sleep_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Sleep entry should suppress the Focus restore path while Sleep takes ownership."""

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "on")
    hass.states.async_set("input_boolean.bedroom_auto_on_restore_state", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "on")
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.focus_mode").state == "off"



async def test_sleep_start_records_off_state_when_main_al_was_already_off(
    hass,
    sleep_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Sleep entry should preserve a prior opt-out instead of forcing restore-on."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_restore_state", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_auto_on_restore_state").state == "off"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "on"
    assert hass.states.get("input_boolean.bedroom_auto_on_enabled").state == "off"


async def test_sleep_end_restores_main_al_and_reapplies_it_when_saved_on(
    hass,
    sleep_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Sleep exit should restore AL ownership when sleep started from normal AL mode."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_restore_state", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "on")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "off")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_auto_on_enabled").state == "on"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "off"


async def test_sleep_end_turns_lights_on_when_room_is_already_active_and_dark(
    hass,
    sleep_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Sleep exit should catch up when motion stayed on while auto-on was blocked."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_restore_state", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "on")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("binary_sensor.myggspray_wrlss_mtn_sensor_occupancy", "on")
    hass.states.async_set("sensor.myggspray_wrlss_mtn_sensor_illuminance", "5")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "off")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_auto_on_enabled").state == "on"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "off"


async def test_sleep_end_keeps_main_al_off_when_saved_off(
    hass,
    sleep_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Sleep exit should respect a previously disabled main AL switch."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_restore_state", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "on")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_auto_on_enabled", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "off")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_auto_on_enabled").state == "off"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "off"






