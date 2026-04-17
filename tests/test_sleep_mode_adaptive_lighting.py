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
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.focus_mode").state == "off"
    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "on"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"
    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"
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
    adaptive_lighting_calls,
) -> None:
    """Sleep entry should suppress the Focus restore path while Sleep takes ownership."""

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "on")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.focus_mode").state == "off"
    assert adaptive_lighting_calls == []


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
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "off"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "on"
    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"


async def test_sleep_end_restores_main_al_and_reapplies_it_when_saved_on(
    hass,
    sleep_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
    adaptive_lighting_calls,
) -> None:
    """Sleep exit should restore AL ownership when sleep started from normal AL mode."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "on")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "on")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "off")
    await hass.async_block_till_done()

    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "off"
    assert len(adaptive_lighting_calls) == 1
    assert adaptive_lighting_calls[0].data["entity_id"] == "switch.adaptive_lighting_adaptive_lighting"
    assert adaptive_lighting_calls[0].data["lights"] == "light.bedroom_lights"
    assert adaptive_lighting_calls[0].data["turn_on_lights"] is False


async def test_sleep_end_keeps_main_al_off_when_saved_off(
    hass,
    sleep_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
    adaptive_lighting_calls,
) -> None:
    """Sleep exit should respect a previously disabled main AL switch."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "on")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_mode_lighting_config)

    hass.states.async_set("input_boolean.sleeping_mode", "off")
    await hass.async_block_till_done()

    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "off"
    assert adaptive_lighting_calls == []


async def test_sleep_start_keeps_saved_on_state_when_bridge_is_loaded(
    hass,
    sleep_with_resume_bridge_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Sleep entry should keep its saved restore state even with the bridge loaded."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(hass, "automation", sleep_with_resume_bridge_config)

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "on"


async def test_sleep_from_focus_turns_off_desk_light_before_focus_clears(
    hass,
    sleep_with_resume_bridge_config,
    focus_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
) -> None:
    """Sleep should let Focus clean up the desk lamp before Focus deactivates."""

    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                sleep_with_resume_bridge_config["automation"][0],
                sleep_with_resume_bridge_config["automation"][1],
                focus_mode_lighting_config["automation"][0],
            ]
        },
    )

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "on")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    hass.states.async_set("light.desk_light", "on")
    await hass.async_block_till_done()

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.focus_mode").state == "off"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"
    assert hass.states.get("light.desk_light").state == "off"


async def test_sleep_from_real_focus_session_restores_original_al_state(
    hass,
    sleep_with_resume_bridge_config,
    focus_mode_lighting_config,
    switch_service_calls,
    input_boolean_service_calls,
    light_service_calls,
    adaptive_lighting_calls,
    adaptive_lighting_set_manual_control_calls,
) -> None:
    """Sleep should inherit Focus's saved AL state instead of re-saving the temporary off state."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                sleep_with_resume_bridge_config["automation"][0],
                sleep_with_resume_bridge_config["automation"][1],
                focus_mode_lighting_config["automation"][0],
            ]
        },
    )

    hass.states.async_set("input_boolean.focus_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "on"
    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"

    hass.states.async_set("input_boolean.sleeping_mode", "on")
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.focus_mode").state == "off"
    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "on"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"

    hass.states.async_set("input_boolean.sleeping_mode", "off")
    await hass.async_block_till_done()

    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "on"
    assert hass.states.get("input_boolean.bedroom_sleep_override_active").state == "off"
    assert hass.states.get("input_boolean.bedroom_focus_override_active").state == "off"
    assert adaptive_lighting_calls
    assert adaptive_lighting_calls[-1].data["turn_on_lights"] is False
