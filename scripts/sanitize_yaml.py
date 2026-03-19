from __future__ import annotations

from pathlib import Path
import re
import secrets
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_DIR = REPO_ROOT / ".local" / "real"

ROOT_CONFIGURATION = REPO_ROOT / "configuration.yaml"
ROOT_AUTOMATIONS = REPO_ROOT / "automations.yaml"


DEVICE_ID_RE = re.compile(r"(?<=device_id:\s)([0-9a-f]{16,})")
OPAQUE_ENTITY_ID_RE = re.compile(r"(?<=entity_id:\s)([0-9a-f]{16,})")
NOTIFY_RE = re.compile(r"notify\.mobile_app_[a-z0-9_]+")
QUOTED_ENTITY_REF_RE = re.compile(r"(?P<quote>['\"])(?P<entity>[a-z_]+\.[a-z0-9_]+)(?P=quote)")
INLINE_ENTITY_FIELD_RE = re.compile(r"^(\s*(?:entity_id|lights):\s*)([a-z_]+\.[a-z0-9_]+)(\s*(?:#.*)?)$")
LIST_ENTITY_ITEM_RE = re.compile(r"^(\s*-\s*)([a-z_]+\.[a-z0-9_]+)(\s*(?:#.*)?)$")
SLUG_RE = re.compile(r"[^a-z0-9]+")


class HomeAssistantYamlLoader(yaml.SafeLoader):
    """YAML loader that tolerates Home Assistant tags like !include."""


def _construct_home_assistant_tag(
    loader: HomeAssistantYamlLoader,
    tag_suffix: str,
    node: yaml.Node,
) -> object:
    """Return the underlying YAML value for any unknown Home Assistant tag."""
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)

    raise TypeError(f"Unsupported YAML node for tag !{tag_suffix}: {type(node)!r}")


HomeAssistantYamlLoader.add_multi_constructor("!", _construct_home_assistant_tag)


def next_mask(prefix: str, existing_values: set[str]) -> str:
    """Generate a unique random-looking fake value for one run."""
    while True:
        candidate = f"{prefix}{secrets.token_hex(8)}"
        if candidate not in existing_values:
            return candidate


def mapped_value(
    mapping: dict[str, dict[str, str]],
    group: str,
    real_value: str,
    prefix: str,
) -> str:
    """Return the fake value for one real input during this run."""
    table = mapping[group]

    if real_value not in table:
        table[real_value] = next_mask(prefix, set(table.values()))

    return table[real_value]


def load_yaml_file(path: Path) -> object:
    """Load a YAML file using the HA-friendly loader."""
    with path.open("r", encoding="utf-8") as file:
        return yaml.load(file, Loader=HomeAssistantYamlLoader)


def entity_object_id_from_name(name: str) -> str:
    """Convert a Home Assistant entity name into its default object_id form."""
    return SLUG_RE.sub("_", name.lower()).strip("_")


def preserved_entity_refs() -> set[str]:
    """Return locally defined entity ids that should stay stable in the public config."""
    configuration = load_yaml_file(REAL_DIR / "configuration.yaml")
    refs: set[str] = set()

    for object_id in (configuration.get("timer") or {}):
        refs.add(f"timer.{object_id}")

    for block in configuration.get("template", []):
        for sensor in block.get("binary_sensor", []):
            name = sensor.get("name")
            if name:
                refs.add(f"binary_sensor.{entity_object_id_from_name(name)}")

    return refs


def masked_entity_ref(
    mapping: dict[str, dict[str, str]],
    real_value: str,
    preserved_refs: set[str],
) -> str:
    """Return the public masked entity reference for one real entity id."""
    if real_value in preserved_refs:
        return real_value

    domain, _ = real_value.split(".", 1)
    if domain == "automation":
        return real_value

    return mapped_value(
        mapping,
        "entity_ref",
        real_value,
        f"{domain}.masked_{domain}_",
    )


def sanitize_entity_field_lines(
    source_text: str,
    mapping: dict[str, dict[str, str]],
    preserved_refs: set[str],
) -> str:
    """Mask entity refs that appear as bare YAML values under entity-aware keys."""
    sanitized_lines: list[str] = []
    in_entity_id_list = False
    entity_list_indent = 0

    for line in source_text.splitlines(keepends=True):
        line_body = line[:-1] if line.endswith("\n") else line
        line_break = "\n" if line.endswith("\n") else ""
        stripped = line_body.strip()
        indent = len(line_body) - len(line_body.lstrip(" "))

        if in_entity_id_list:
            list_match = LIST_ENTITY_ITEM_RE.match(line_body)
            if list_match and indent >= entity_list_indent:
                entity_ref = masked_entity_ref(mapping, list_match.group(2), preserved_refs)
                sanitized_lines.append(f"{list_match.group(1)}{entity_ref}{list_match.group(3)}{line_break}")
                continue

            if stripped and indent < entity_list_indent:
                in_entity_id_list = False
            elif not stripped or stripped.startswith("#"):
                sanitized_lines.append(line)
                continue
            else:
                in_entity_id_list = False

        if re.match(r"^\s*entity_id:\s*$", line_body):
            in_entity_id_list = True
            entity_list_indent = indent
            sanitized_lines.append(line)
            continue

        inline_match = INLINE_ENTITY_FIELD_RE.match(line_body)
        if inline_match:
            entity_ref = masked_entity_ref(mapping, inline_match.group(2), preserved_refs)
            sanitized_lines.append(f"{inline_match.group(1)}{entity_ref}{inline_match.group(3)}{line_break}")
            continue

        sanitized_lines.append(line)

    return "".join(sanitized_lines)


def sanitize_text(
    source_text: str,
    mapping: dict[str, dict[str, str]],
    preserved_refs: set[str],
) -> str:
    """Replace private IDs and personal notify targets with public-safe values."""
    source_text = sanitize_entity_field_lines(source_text, mapping, preserved_refs)
    source_text = QUOTED_ENTITY_REF_RE.sub(
        lambda match: (
            f"{match.group('quote')}"
            f"{masked_entity_ref(mapping, match.group('entity'), preserved_refs)}"
            f"{match.group('quote')}"
        ),
        source_text,
    )
    source_text = DEVICE_ID_RE.sub(
        lambda match: mapped_value(mapping, "device_id", match.group(1), "masked_device_"),
        source_text,
    )
    source_text = OPAQUE_ENTITY_ID_RE.sub(
        lambda match: mapped_value(mapping, "entity_id", match.group(1), "masked_entity_"),
        source_text,
    )
    source_text = NOTIFY_RE.sub(
        lambda match: mapped_value(
            mapping,
            "notify_target",
            match.group(0),
            "notify.mobile_app_public_phone_",
        ),
        source_text,
    )
    return source_text


def sanitize_file(
    source_path: Path,
    target_path: Path,
    mapping: dict[str, dict[str, str]],
    preserved_refs: set[str],
) -> None:
    """Read one real YAML file and write one sanitized repo copy."""
    source_text = source_path.read_text(encoding="utf-8")
    sanitized_text = sanitize_text(source_text, mapping, preserved_refs)
    target_path.write_text(sanitized_text, encoding="utf-8")


def ensure_real_files_exist() -> None:
    """Fail early if the ignored local source files are missing."""
    missing_files = []

    for path in (REAL_DIR / "configuration.yaml", REAL_DIR / "automations.yaml"):
        if not path.exists():
            missing_files.append(path)

    if missing_files:
        missing_list = "\n".join(f"- {path}" for path in missing_files)
        raise SystemExit(
            "Missing local real YAML file(s):\n"
            f"{missing_list}\n\n"
            "Create them first under .local/real/ before running the sanitizer."
        )


def main() -> None:
    """Refresh the tracked public-safe YAML files from .local/real/."""
    ensure_real_files_exist()

    mapping = {
        "device_id": {},
        "entity_id": {},
        "entity_ref": {},
        "notify_target": {},
    }
    preserved_refs = preserved_entity_refs()

    sanitize_file(REAL_DIR / "configuration.yaml", ROOT_CONFIGURATION, mapping, preserved_refs)
    sanitize_file(REAL_DIR / "automations.yaml", ROOT_AUTOMATIONS, mapping, preserved_refs)

    print("Sanitized configuration.yaml and automations.yaml from .local/real/")


if __name__ == "__main__":
    main()
