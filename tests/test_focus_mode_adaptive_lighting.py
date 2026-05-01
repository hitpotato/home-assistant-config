from __future__ import annotations

from homeassistant.setup import async_setup_component


async def test_focus_start_records_on_state_and_disables_main_al(
    hass,
    focus_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
    adaptive_lighting_calls,
) -> None:
    """Focus entry should save AL ownership before it applies a custom desk-light scene."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", focus_mode_lighting_config)

    hass.states.async_set("input_boolean.focus_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "on"
    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"
    assert hass.states.get("light.desk_light").state == "on"
    assert adaptive_lighting_calls == []


async def test_focus_cannot_stay_on_while_sleep_is_active(
    hass,
    focus_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
    adaptive_lighting_calls,
) -> None:
    """Sleep mode should immediately reject Focus taking ownership."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "on")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", focus_mode_lighting_config)

    hass.states.async_set("input_boolean.focus_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.focus_mode").state == "off"
    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"
    assert adaptive_lighting_calls == []


async def test_focus_start_records_off_state_when_main_al_was_already_off(
    hass,
    focus_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Focus entry should preserve a prior AL opt-out instead of forcing restore-on."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", focus_mode_lighting_config)

    hass.states.async_set("input_boolean.focus_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "off"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "on"
    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"


async def test_focus_end_restores_main_al_and_reapplies_it_when_saved_on(
    hass,
    focus_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
    adaptive_lighting_calls,
) -> None:
    """Focus exit should restore AL ownership when Focus started from normal AL mode."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "on")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", focus_mode_lighting_config)

    hass.states.async_set("input_boolean.focus_mode", "off")
    await hass.async_block_till_done()

    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"
    assert len(adaptive_lighting_calls) == 1
    assert adaptive_lighting_calls[0].data["entity_id"] == "switch.adaptive_lighting_adaptive_lighting"
    assert adaptive_lighting_calls[0].data["lights"] == "light.bedroom_lights"
    assert adaptive_lighting_calls[0].data["turn_on_lights"] is False


async def test_focus_end_keeps_main_al_off_when_saved_off(
    hass,
    focus_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
    adaptive_lighting_calls,
) -> None:
    """Focus exit should respect a previously disabled main AL switch."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "on")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", focus_mode_lighting_config)

    hass.states.async_set("input_boolean.focus_mode", "off")
    await hass.async_block_till_done()

    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"
    assert adaptive_lighting_calls == []


async def test_focus_start_keeps_saved_on_state_when_bridge_is_loaded(
    hass,
    focus_with_resume_bridge_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Focus entry should keep its saved restore state even with the bridge loaded."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", focus_with_resume_bridge_config)

    hass.states.async_set("input_boolean.focus_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "on"


async def test_rejected_focus_during_sleep_does_not_turn_off_desk_light(
    hass,
    focus_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Rejected Focus should not run desk-light cleanup if Focus never took ownership."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "on")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    hass.states.async_set("light.desk_light", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", focus_mode_lighting_config)

    hass.states.async_set("input_boolean.focus_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.focus_mode").state == "off"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"
    assert hass.states.get("light.desk_light").state == "on"
