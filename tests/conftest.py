from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
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


def find_template_binary_sensor(
    template_config: dict[str, Any],
    unique_id: str,
) -> dict[str, Any]:
    """Return one template binary sensor config by unique_id."""
    for block in template_config["template"]:
        for sensor in block.get("binary_sensor", []):
            if sensor.get("unique_id") == unique_id:
                return deepcopy(sensor)

    raise AssertionError(f"Template binary sensor {unique_id!r} was not found in configuration.yaml")


def entity_object_id_from_name(name: str) -> str:
    """Convert a Home Assistant entity name into its default object_id form."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


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
def bedroom_auto_on_entities(bedroom_auto_on_config: dict[str, Any]) -> dict[str, str]:
    """Extract the tracked public entity ids used by the bedroom auto-on automation."""
    automation = bedroom_auto_on_config["automation"][0]

    motion_trigger = next(
        trigger
        for trigger in automation["triggers"]
        if trigger.get("id") == "motion_trigger"
    )
    manual_trigger = next(
        trigger
        for trigger in automation["triggers"]
        if trigger.get("id") == "manual_on"
    )

    motion_branch = next(
        branch
        for branch in automation["actions"][0]["choose"]
        if any(condition.get("id") == "motion_trigger" for condition in branch["conditions"])
    )

    illuminance_condition = next(
        condition
        for condition in motion_branch["conditions"]
        if condition.get("condition") == "numeric_state"
    )

    guard_entities = [
        condition["entity_id"]
        for condition in automation["conditions"]
        if condition.get("condition") == "state"
    ]

    return {
        "motion_sensor": motion_trigger["entity_id"][0],
        "light": manual_trigger["entity_id"][0],
        "illuminance_sensor": illuminance_condition["entity_id"],
        "sleeping_mode": guard_entities[0],
        "focus_mode": guard_entities[1],
    }


@pytest.fixture
def bedroom_occupancy_entities(
    bedroom_timer_config: dict[str, Any],
    bedroom_template_config: dict[str, Any],
) -> dict[str, str]:
    """Extract the tracked public entity ids used by the bedroom occupancy logic."""
    activity_sensor = find_template_binary_sensor(
        bedroom_template_config,
        "bedroom_activity_signal",
    )
    occupancy_sensor = find_template_binary_sensor(
        bedroom_template_config,
        "bedroom_occupancy_logic_lock",
    )

    activity_entity = f"binary_sensor.{entity_object_id_from_name(activity_sensor['name'])}"
    occupancy_entity = f"binary_sensor.{entity_object_id_from_name(occupancy_sensor['name'])}"

    activity_refs = re.findall(r"is_state\('([^']+)'", activity_sensor["state"])
    occupancy_refs = re.findall(r"(?:is_state|states)\('([^']+)'", occupancy_sensor["state"])

    motion_sensor = next(entity_id for entity_id in activity_refs if entity_id.startswith("binary_sensor."))
    tv_entity = next(entity_id for entity_id in occupancy_refs if entity_id.startswith("media_player."))
    plug_entity = next(entity_id for entity_id in occupancy_refs if entity_id.startswith("switch."))
    door_entity = next(
        entity_id
        for entity_id in occupancy_refs
        if entity_id.startswith("binary_sensor.") and entity_id not in {activity_entity, occupancy_entity}
    )
    hold_timer = f"timer.{next(iter(bedroom_timer_config['timer']))}"

    return {
        "activity_entity": activity_entity,
        "occupancy_entity": occupancy_entity,
        "motion_sensor": motion_sensor,
        "tv": tv_entity,
        "plug": plug_entity,
        "door": door_entity,
        "hold_timer": hold_timer,
    }


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
