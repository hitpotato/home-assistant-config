from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_yaml_parity


def write_yaml_pair(repo_path: Path, configuration_text: str, automations_text: str) -> None:
    """Write one configuration and automations pair into a repo root."""
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / "configuration.yaml").write_text(configuration_text, encoding="utf-8")
    (repo_path / "automations.yaml").write_text(automations_text, encoding="utf-8")


def test_canonicalize_yaml_pair_normalizes_random_mask_tokens() -> None:
    """Different random mask strings should compare equal after canonicalization."""
    public_pair = check_yaml_parity.canonicalize_yaml_pair(
        "device_id: masked_device_aaaaaaaaaaaaaaaa\n",
        "- switch: masked_entity_bbbbbbbbbbbbbbbb\n"
        "- action: notify.mobile_app_public_phone_cccccccccccccccc\n"
        "- switch: masked_entity_bbbbbbbbbbbbbbbb\n",
    )
    generated_pair = check_yaml_parity.canonicalize_yaml_pair(
        "device_id: masked_device_1111111111111111\n",
        "- switch: masked_entity_2222222222222222\n"
        "- action: notify.mobile_app_public_phone_3333333333333333\n"
        "- switch: masked_entity_2222222222222222\n",
    )

    assert public_pair == generated_pair


def test_check_yaml_parity_accepts_semantically_matching_public_yaml(tmp_path: Path) -> None:
    """Parity should pass even when the random public masks differ from this run."""
    public_repo = tmp_path / "public"
    private_repo = tmp_path / "private"

    write_yaml_pair(
        private_repo,
        "device_id: 1234567890abcdef\nnotify_target: notify.mobile_app_longchen_iphone\n",
        "- entity_id: abcdef1234567890\n",
    )
    write_yaml_pair(
        public_repo,
        "device_id: masked_device_aaaaaaaaaaaaaaaa\n"
        "notify_target: notify.mobile_app_public_phone_bbbbbbbbbbbbbbbb\n",
        "- entity_id: masked_entity_cccccccccccccccc\n",
    )

    check_yaml_parity.check_yaml_parity(public_repo=public_repo, private_repo=private_repo)


def test_check_yaml_parity_fails_when_public_yaml_is_stale(tmp_path: Path) -> None:
    """Parity should fail with a helpful message when tracked YAML differs semantically."""
    public_repo = tmp_path / "public"
    private_repo = tmp_path / "private"

    write_yaml_pair(
        private_repo,
        "device_id: 1234567890abcdef\n",
        "- alias: bedroom\n",
    )
    write_yaml_pair(
        public_repo,
        "device_id: masked_device_aaaaaaaaaaaaaaaa\n",
        "- alias: kitchen\n",
    )

    with pytest.raises(SystemExit, match="Tracked public YAML is out of sync"):
        check_yaml_parity.check_yaml_parity(public_repo=public_repo, private_repo=private_repo)
