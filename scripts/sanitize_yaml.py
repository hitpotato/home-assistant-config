from __future__ import annotations

from pathlib import Path
import re
import secrets


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_DIR = REPO_ROOT / ".local" / "real"

ROOT_CONFIGURATION = REPO_ROOT / "configuration.yaml"
ROOT_AUTOMATIONS = REPO_ROOT / "automations.yaml"


DEVICE_ID_RE = re.compile(r"(?<=device_id:\s)([0-9a-f]{16,})")
OPAQUE_ENTITY_ID_RE = re.compile(r"(?<=entity_id:\s)([0-9a-f]{16,})")
NOTIFY_RE = re.compile(r"notify\.mobile_app_[a-z0-9_]+")


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


def sanitize_text(source_text: str, mapping: dict[str, dict[str, str]]) -> str:
    """Replace private IDs and personal notify targets with public-safe values."""
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
) -> None:
    """Read one real YAML file and write one sanitized repo copy."""
    source_text = source_path.read_text(encoding="utf-8")
    sanitized_text = sanitize_text(source_text, mapping)
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
        "notify_target": {},
    }

    sanitize_file(REAL_DIR / "configuration.yaml", ROOT_CONFIGURATION, mapping)
    sanitize_file(REAL_DIR / "automations.yaml", ROOT_AUTOMATIONS, mapping)

    print("Sanitized configuration.yaml and automations.yaml from .local/real/")


if __name__ == "__main__":
    main()
