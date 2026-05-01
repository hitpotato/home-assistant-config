from __future__ import annotations

from homeassistant.setup import async_setup_component


async def test_manual_control_event_turns_off_main_adaptive_lighting_switch(
    hass,
    adaptive_lighting_manual_opt_out_config,
    switch_service_calls,
) -> None:
    """Manual changes should visibly disable the main AL switch in normal mode."""

    assert await async_setup_component(
        hass,
        "automation",
        adaptive_lighting_manual_opt_out_config,
    )

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    # This event is what Adaptive Lighting emits after it detects a manual
    # brightness/color change.
    hass.bus.async_fire(
        "adaptive_lighting.manual_control",
        {
            "entity_id": "light.bedroom_lights",
            "switch": "switch.adaptive_lighting_adaptive_lighting",
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"


async def test_manual_control_event_from_other_switch_is_ignored(
    hass,
    adaptive_lighting_manual_opt_out_config,
    switch_service_calls,
) -> None:
    """Only the bedroom AL switch should drive the bedroom opt-out bridge."""

    assert await async_setup_component(
        hass,
        "automation",
        adaptive_lighting_manual_opt_out_config,
    )

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    hass.bus.async_fire(
        "adaptive_lighting.manual_control",
        {
            "entity_id": "light.other_room",
            "switch": "switch.adaptive_lighting_other_room",
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "on"


async def test_turning_main_switch_on_clears_manual_control_and_reapplies_al(
    hass,
    adaptive_lighting_resume_bridge_config,
    adaptive_lighting_calls,
    adaptive_lighting_set_manual_control_calls,
) -> None:
    """Turning the main switch back on should immediately restore normal AL."""

    assert await async_setup_component(
        hass,
        "automation",
        adaptive_lighting_resume_bridge_config,
    )

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("light.bedroom_lights", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert len(adaptive_lighting_set_manual_control_calls) == 1
    assert (
        adaptive_lighting_set_manual_control_calls[0].data["entity_id"]
        == "switch.adaptive_lighting_adaptive_lighting"
    )
    assert adaptive_lighting_set_manual_control_calls[0].data["manual_control"] is False

    assert len(adaptive_lighting_calls) == 1
    assert adaptive_lighting_calls[0].data["entity_id"] == "switch.adaptive_lighting_adaptive_lighting"
    assert adaptive_lighting_calls[0].data["lights"] == "light.bedroom_lights"
    assert adaptive_lighting_calls[0].data["turn_on_lights"] is False
    assert hass.states.get("light.bedroom_lights").state == "off"


async def test_turning_main_switch_on_during_sleep_saves_restore_on_but_keeps_al_disabled(
    hass,
    adaptive_lighting_resume_bridge_config,
    adaptive_lighting_calls,
    adaptive_lighting_set_manual_control_calls,
    input_boolean_service_calls,
    switch_service_calls,
) -> None:
    """Sleep should save restore-on intent without letting AL take live ownership."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "on")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        "automation",
        adaptive_lighting_resume_bridge_config,
    )

    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert adaptive_lighting_set_manual_control_calls == []
    assert adaptive_lighting_calls == []
    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"
    assert input_boolean_service_calls[-1].service == "turn_on"
    assert switch_service_calls[-1].service == "turn_off"


async def test_turning_main_switch_on_during_focus_saves_restore_on_but_keeps_al_disabled(
    hass,
    adaptive_lighting_resume_bridge_config,
    adaptive_lighting_calls,
    adaptive_lighting_set_manual_control_calls,
    input_boolean_service_calls,
    switch_service_calls,
) -> None:
    """Focus should save restore-on intent without letting AL take live ownership."""

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "on")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("input_boolean.bedroom_sleep_override_active", "off")
    hass.states.async_set("input_boolean.bedroom_focus_override_active", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        "automation",
        adaptive_lighting_resume_bridge_config,
    )

    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "on")
    await hass.async_block_till_done()

    assert adaptive_lighting_set_manual_control_calls == []
    assert adaptive_lighting_calls == []
    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"
    assert hass.states.get("switch.adaptive_lighting_adaptive_lighting").state == "off"
    assert input_boolean_service_calls[-1].service == "turn_on"
    assert switch_service_calls[-1].service == "turn_off"


async def test_manual_control_event_during_sleep_does_not_rewrite_restore_state(
    hass,
    adaptive_lighting_manual_opt_out_config,
    switch_service_calls,
) -> None:
    """Sleep should ignore manual-control bridge events and preserve the saved restore state."""

    assert await async_setup_component(
        hass,
        "automation",
        adaptive_lighting_manual_opt_out_config,
    )

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "on")
    hass.states.async_set("input_boolean.focus_mode", "off")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "on")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    hass.bus.async_fire(
        "adaptive_lighting.manual_control",
        {
            "entity_id": "light.bedroom_lights",
            "switch": "switch.adaptive_lighting_adaptive_lighting",
        },
    )
    await hass.async_block_till_done()

    assert switch_service_calls == []
    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "on"


async def test_manual_control_event_during_focus_does_not_rewrite_restore_state(
    hass,
    adaptive_lighting_manual_opt_out_config,
    switch_service_calls,
) -> None:
    """Focus should ignore manual-control bridge events and preserve the saved restore state."""

    assert await async_setup_component(
        hass,
        "automation",
        adaptive_lighting_manual_opt_out_config,
    )

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("input_boolean.sleeping_mode", "off")
    hass.states.async_set("input_boolean.focus_mode", "on")
    hass.states.async_set("input_boolean.bedroom_override_restore_adaptive_lighting", "off")
    hass.states.async_set("switch.adaptive_lighting_adaptive_lighting", "off")
    await hass.async_block_till_done()

    hass.bus.async_fire(
        "adaptive_lighting.manual_control",
        {
            "entity_id": "light.bedroom_lights",
            "switch": "switch.adaptive_lighting_adaptive_lighting",
        },
    )
    await hass.async_block_till_done()

    assert switch_service_calls == []
    assert hass.states.get("input_boolean.bedroom_override_restore_adaptive_lighting").state == "off"
