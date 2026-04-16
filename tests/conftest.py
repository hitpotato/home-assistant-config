from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from homeassistant.core import HomeAssistant, ServiceCall


REPO_ROOT = Path(__file__).resolve().parents[1]


class HomeAssistantYamlLoader(yaml.SafeLoader):
    """YAML loader that tolerates Home Assistant tags like !include."""

    # Home Assistant config files often contain custom tags such as !include.
    # PyYAML does not know those tags by default, so we teach it how to keep
    # parsing the file without trying to resolve the include at test-load time.


def _construct_home_assistant_tag(
    loader: HomeAssistantYamlLoader,
    tag_suffix: str,
    node: yaml.Node,
) -> Any:
    """Return the underlying YAML value for any unknown Home Assistant tag."""
    # This keeps values like !include automations.yaml parseable.
    # For our tests we only care about the timer/template sections, so we do not
    # need to actually resolve the include target here.
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)

    raise TypeError(f"Unsupported YAML node for tag !{tag_suffix}: {type(node)!r}")


HomeAssistantYamlLoader.add_multi_constructor("!", _construct_home_assistant_tag)


def load_yaml_file(path: Path) -> Any:
    """Load a YAML file from the repo using the HA-friendly loader."""
    with path.open("r", encoding="utf-8") as file:
        return yaml.load(file, Loader=HomeAssistantYamlLoader)


def find_automation_by_id(
    automations: list[dict[str, Any]],
    automation_id: str,
) -> dict[str, Any]:
    """Return one automation dict by id from automations.yaml."""
    for automation in automations:
        if automation.get("id") == automation_id:
            # Deep-copy so each test gets its own clean config object.
            return deepcopy(automation)

    raise AssertionError(f"Automation {automation_id!r} was not found in automations.yaml")


@pytest.fixture
def configuration_yaml() -> dict[str, Any]:
    """Load the tracked configuration.yaml from this repo."""
    return load_yaml_file(REPO_ROOT / "configuration.yaml")


@pytest.fixture
def automations_yaml() -> list[dict[str, Any]]:
    """Load the tracked automations.yaml from this repo."""
    return load_yaml_file(REPO_ROOT / "automations.yaml")


@pytest.fixture
def bedroom_timer_config(configuration_yaml: dict[str, Any]) -> dict[str, Any]:
    """Extract the timer config used by Bedroom Occupancy."""
    return {"timer": deepcopy(configuration_yaml["timer"])}


@pytest.fixture
def bedroom_template_config(configuration_yaml: dict[str, Any]) -> dict[str, Any]:
    """Extract the tracked template config used by Bedroom Activity/Occupancy."""
    return {"template": deepcopy(configuration_yaml["template"])}


@pytest.fixture
def bedroom_auto_on_config(automations_yaml: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract the tracked bedroom auto-on automation by id."""
    automation = find_automation_by_id(automations_yaml, "1773020624303")
    return {"automation": [automation]}


@pytest.fixture
def adaptive_lighting_manual_opt_out_config(
    automations_yaml: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract the tracked manual opt-out bridge automation by id."""
    automation = find_automation_by_id(automations_yaml, "1775000000001")
    return {"automation": [automation]}


@pytest.fixture
def adaptive_lighting_resume_bridge_config(
    automations_yaml: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract the tracked immediate-resume bridge automation by id."""
    automation = find_automation_by_id(automations_yaml, "1775000000002")
    return {"automation": [automation]}


@pytest.fixture
def sleep_mode_lighting_config(
    automations_yaml: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract the tracked sleep-mode lighting automation by id."""
    automation = find_automation_by_id(automations_yaml, "1773033168449")
    return {"automation": [automation]}


@pytest.fixture
def bedroom_hold_timer_automation_config(
    automations_yaml: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract the tracked occupancy-hold automation by id."""
    automation = find_automation_by_id(automations_yaml, "1774000000000")
    return {"automation": [automation]}


@pytest.fixture
def adaptive_lighting_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Capture calls to adaptive_lighting.apply during a test."""
    calls: list[ServiceCall] = []

    async def handle_service(call: ServiceCall) -> None:
        calls.append(call)

    # Register a fake service so the real Adaptive Lighting integration is not
    # required for these tests.
    hass.services.async_register("adaptive_lighting", "apply", handle_service)
    return calls


@pytest.fixture
def adaptive_lighting_set_manual_control_calls(
    hass: HomeAssistant,
) -> list[ServiceCall]:
    """Capture calls to adaptive_lighting.set_manual_control during a test."""
    calls: list[ServiceCall] = []

    async def handle_service(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register(
        "adaptive_lighting",
        "set_manual_control",
        handle_service,
    )
    return calls


@pytest.fixture
def switch_service_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Register fake switch services that also update the entity state."""
    calls: list[ServiceCall] = []

    def set_entities_state(entity_id: str | list[str] | None, state: str) -> None:
        """Mirror HA target handling: entity_id may be one id or a list of ids."""
        if entity_id is None:
            return
        if isinstance(entity_id, str):
            hass.states.async_set(entity_id, state)
            return

        for one_entity_id in entity_id:
            hass.states.async_set(one_entity_id, state)

    async def handle_turn_on(call: ServiceCall) -> None:
        calls.append(call)
        set_entities_state(call.data.get("entity_id"), "on")

    async def handle_turn_off(call: ServiceCall) -> None:
        calls.append(call)
        set_entities_state(call.data.get("entity_id"), "off")

    hass.services.async_register("switch", "turn_on", handle_turn_on)
    hass.services.async_register("switch", "turn_off", handle_turn_off)
    return calls


@pytest.fixture
def input_boolean_service_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Register fake input_boolean services that also update entity state."""
    calls: list[ServiceCall] = []

    def set_entities_state(entity_id: str | list[str] | None, state: str) -> None:
        """Mirror HA target handling: entity_id may be one id or a list of ids."""
        if entity_id is None:
            return
        if isinstance(entity_id, str):
            hass.states.async_set(entity_id, state)
            return

        for one_entity_id in entity_id:
            hass.states.async_set(one_entity_id, state)

    async def handle_turn_on(call: ServiceCall) -> None:
        calls.append(call)
        set_entities_state(call.data.get("entity_id"), "on")

    async def handle_turn_off(call: ServiceCall) -> None:
        calls.append(call)
        set_entities_state(call.data.get("entity_id"), "off")

    hass.services.async_register("input_boolean", "turn_on", handle_turn_on)
    hass.services.async_register("input_boolean", "turn_off", handle_turn_off)
    return calls


@pytest.fixture
def light_service_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Register fake light services so light actions stay observable in tests."""
    calls: list[ServiceCall] = []

    def set_entities_state(entity_id: str | list[str] | None, state: str) -> None:
        """Mirror HA target handling: entity_id may be one id or a list of ids."""
        if entity_id is None:
            return
        if isinstance(entity_id, str):
            hass.states.async_set(entity_id, state)
            return

        for one_entity_id in entity_id:
            hass.states.async_set(one_entity_id, state)

    async def handle_turn_on(call: ServiceCall) -> None:
        calls.append(call)
        set_entities_state(call.data.get("entity_id"), "on")

    async def handle_turn_off(call: ServiceCall) -> None:
        calls.append(call)
        set_entities_state(call.data.get("entity_id"), "off")

    hass.services.async_register("light", "turn_on", handle_turn_on)
    hass.services.async_register("light", "turn_off", handle_turn_off)
    return calls
