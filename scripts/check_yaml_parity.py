from __future__ import annotations

import argparse
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from sanitize_yaml import sanitize_yaml_pair


CONFIGURATION_NAME = "configuration.yaml"
AUTOMATIONS_NAME = "automations.yaml"

MASK_PATTERNS = (
    (re.compile(r"masked_device_[0-9a-f]+"), "masked_device"),
    (re.compile(r"masked_entity_[0-9a-f]+"), "masked_entity"),
    (re.compile(r"notify\.mobile_app_public_phone_[0-9a-f]+"), "notify.mobile_app_public_phone"),
)


def canonicalize_yaml_pair(
    configuration_text: str,
    automations_text: str,
) -> tuple[str, str]:
    """Normalize random-looking masks so semantic parity checks stay stable."""
    seen_tokens = {label: {} for _, label in MASK_PATTERNS}
    counters = {label: 0 for _, label in MASK_PATTERNS}

    def canonicalize_text(source_text: str) -> str:
        for pattern, label in MASK_PATTERNS:
            token_map = seen_tokens[label]

            def replace(match: re.Match[str]) -> str:
                token = match.group(0)
                if token not in token_map:
                    counters[label] += 1
                    token_map[token] = f"{label}_{counters[label]}"
                return token_map[token]

            source_text = pattern.sub(replace, source_text)

        return source_text

    return canonicalize_text(configuration_text), canonicalize_text(automations_text)


def load_yaml_pair(repo_path: Path) -> tuple[str, str]:
    """Read one configuration and automations pair from a repo root."""
    configuration_text = (repo_path / CONFIGURATION_NAME).read_text(encoding="utf-8")
    automations_text = (repo_path / AUTOMATIONS_NAME).read_text(encoding="utf-8")
    return configuration_text, automations_text


def generated_private_yaml_pair(private_repo: Path) -> tuple[str, str]:
    """Sanitize the private repo YAML into a temporary generated pair."""
    with TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        configuration_target = temp_dir / CONFIGURATION_NAME
        automations_target = temp_dir / AUTOMATIONS_NAME

        sanitize_yaml_pair(
            configuration_source=private_repo / CONFIGURATION_NAME,
            automations_source=private_repo / AUTOMATIONS_NAME,
            configuration_target=configuration_target,
            automations_target=automations_target,
        )

        return (
            configuration_target.read_text(encoding="utf-8"),
            automations_target.read_text(encoding="utf-8"),
        )


def parity_mismatches(public_repo: Path, private_repo: Path) -> list[str]:
    """Return the tracked YAML filenames that do not match the private repo."""
    public_configuration, public_automations = load_yaml_pair(public_repo)
    generated_configuration, generated_automations = generated_private_yaml_pair(private_repo)

    canonical_public = canonicalize_yaml_pair(public_configuration, public_automations)
    canonical_generated = canonicalize_yaml_pair(generated_configuration, generated_automations)

    mismatches: list[str] = []

    if canonical_public[0] != canonical_generated[0]:
        mismatches.append(CONFIGURATION_NAME)
    if canonical_public[1] != canonical_generated[1]:
        mismatches.append(AUTOMATIONS_NAME)

    return mismatches


def check_yaml_parity(public_repo: Path, private_repo: Path) -> None:
    """Fail clearly when tracked public YAML is stale versus the private repo."""
    mismatches = parity_mismatches(public_repo, private_repo)
    if not mismatches:
        print("Tracked public YAML matches the sanitized private repo.")
        return

    mismatch_list = "\n".join(f"- {name}" for name in mismatches)
    raise SystemExit(
        "Tracked public YAML is out of sync with the matching private branch.\n"
        "Run `uv run python scripts/yaml_flow.py refresh`, commit the updated public YAML, and push again.\n\n"
        f"Mismatched files:\n{mismatch_list}"
    )


def parse_args() -> argparse.Namespace:
    """Parse the yaml parity command line."""
    parser = argparse.ArgumentParser(description="Compare public YAML against the private repo.")
    parser.add_argument(
        "--public-repo",
        type=Path,
        required=True,
        help="Path to the public repo root.",
    )
    parser.add_argument(
        "--private-repo",
        type=Path,
        required=True,
        help="Path to the private repo root.",
    )
    return parser.parse_args()


def main() -> None:
    """Run one parity check between the public and private repos."""
    args = parse_args()
    check_yaml_parity(
        public_repo=args.public_repo.resolve(),
        private_repo=args.private_repo.resolve(),
    )


if __name__ == "__main__":
    main()
