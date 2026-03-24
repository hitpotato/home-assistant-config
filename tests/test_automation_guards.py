from __future__ import annotations

from typing import Any


MASTER_TOGGLE_ENTITY_ID = "input_boolean.automations_enabled"


def is_master_toggle_condition(condition: dict[str, Any]) -> bool:
    """Return True when a condition is the repo-wide automation gate."""
    return (
        condition.get("condition") == "state"
        and condition.get("entity_id") == MASTER_TOGGLE_ENTITY_ID
        and condition.get("state") == "on"
    )


def test_all_automations_include_master_toggle_condition(
    automations_yaml: list[dict[str, Any]],
) -> None:
    """Keep every tracked automation behind the same repo-wide enable switch."""
    missing_aliases: list[str] = []

    for automation in automations_yaml:
        conditions = automation.get("conditions") or []
        first_condition = conditions[0] if conditions else None

        if not isinstance(first_condition, dict) or not is_master_toggle_condition(first_condition):
            missing_aliases.append(str(automation.get("alias", automation.get("id"))))

    assert missing_aliases == []
