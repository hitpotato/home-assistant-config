from __future__ import annotations

from datetime import timedelta
import pytest
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util


async def test_pm25_alert_triggers_notification_when_above_threshold(
    hass,
    pm25_alert_config,
    notify_service_calls,
) -> None:
    """Send a critical notification when PM2.5 exceeds 40 for 20 seconds."""

    assert await async_setup_component(hass, "automation", pm25_alert_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("sensor.alpstuga_air_quality_monitor_pm2_5", "10")
    await hass.async_block_till_done()

    # Transition to high PM2.5 level
    hass.states.async_set("sensor.alpstuga_air_quality_monitor_pm2_5", "45")
    await hass.async_block_till_done()

    # Before the 20-second duration elapses, no notification should be sent
    assert len(notify_service_calls) == 0

    # Advance time by 21 seconds to satisfy the `for: 20s` condition
    future = dt_util.utcnow() + timedelta(seconds=21)
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    assert len(notify_service_calls) == 1
    call = notify_service_calls[0]
    assert call.domain == "notify"
    assert "PM2.5 is high" in call.data.get("message", "")
    assert call.data.get("data", {}).get("push", {}).get("sound", {}).get("critical") == 1


async def test_pm25_alert_blocked_when_automations_disabled(
    hass,
    pm25_alert_config,
    notify_service_calls,
) -> None:
    """Do not send PM2.5 alert when automations_enabled is off."""

    assert await async_setup_component(hass, "automation", pm25_alert_config)

    hass.states.async_set("input_boolean.automations_enabled", "off")
    hass.states.async_set("sensor.alpstuga_air_quality_monitor_pm2_5", "10")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.alpstuga_air_quality_monitor_pm2_5", "50")
    await hass.async_block_till_done()

    future = dt_util.utcnow() + timedelta(seconds=25)
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    assert len(notify_service_calls) == 0


async def test_co2_alert_triggers_notification_when_above_threshold(
    hass,
    co2_alert_config,
    notify_service_calls,
) -> None:
    """Send a critical notification when CO2 exceeds 1000 for 1 minute."""

    assert await async_setup_component(hass, "automation", co2_alert_config)

    hass.states.async_set("input_boolean.automations_enabled", "on")
    hass.states.async_set("sensor.alpstuga_air_quality_monitor_carbon_dioxide", "600")
    await hass.async_block_till_done()

    # Transition to high CO2 level
    hass.states.async_set("sensor.alpstuga_air_quality_monitor_carbon_dioxide", "1200")
    await hass.async_block_till_done()

    assert len(notify_service_calls) == 0

    # Advance time by 61 seconds to satisfy the `for: 1m` condition
    future = dt_util.utcnow() + timedelta(seconds=61)
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    assert len(notify_service_calls) == 1
    call = notify_service_calls[0]
    assert call.domain == "notify"
    assert "CO2 is high" in call.data.get("message", "")
    assert call.data.get("data", {}).get("push", {}).get("sound", {}).get("critical") == 1


async def test_co2_alert_blocked_when_automations_disabled(
    hass,
    co2_alert_config,
    notify_service_calls,
) -> None:
    """Do not send CO2 alert when automations_enabled is off."""

    assert await async_setup_component(hass, "automation", co2_alert_config)

    hass.states.async_set("input_boolean.automations_enabled", "off")
    hass.states.async_set("sensor.alpstuga_air_quality_monitor_carbon_dioxide", "600")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.alpstuga_air_quality_monitor_carbon_dioxide", "1200")
    await hass.async_block_till_done()

    future = dt_util.utcnow() + timedelta(seconds=65)
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    assert len(notify_service_calls) == 0
