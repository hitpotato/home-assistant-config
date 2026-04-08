from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))

import backup_real_yaml


def test_backup_real_yaml_files_copies_both_real_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Back up both real YAML files into one timestamped directory."""
    real_dir = tmp_path / ".local" / "real"
    backup_root = tmp_path / ".local" / "backups"
    real_dir.mkdir(parents=True)

    (real_dir / "configuration.yaml").write_text("config: real\n", encoding="utf-8")
    (real_dir / "automations.yaml").write_text("automation: real\n", encoding="utf-8")

    monkeypatch.setattr(backup_real_yaml, "REAL_DIR", real_dir)
    monkeypatch.setattr(backup_real_yaml, "BACKUP_ROOT", backup_root)

    backup_dir = backup_real_yaml.backup_real_yaml_files(
        now=datetime(2026, 4, 8, 15, 30, 0)
    )

    assert backup_dir == backup_root / "20260408-153000"
    assert (backup_dir / "configuration.yaml").read_text(encoding="utf-8") == "config: real\n"
    assert (backup_dir / "automations.yaml").read_text(encoding="utf-8") == "automation: real\n"


def test_backup_real_yaml_files_fails_if_any_real_file_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail clearly instead of pretending the backup succeeded."""
    real_dir = tmp_path / ".local" / "real"
    backup_root = tmp_path / ".local" / "backups"
    real_dir.mkdir(parents=True)

    (real_dir / "configuration.yaml").write_text("config: real\n", encoding="utf-8")

    monkeypatch.setattr(backup_real_yaml, "REAL_DIR", real_dir)
    monkeypatch.setattr(backup_real_yaml, "BACKUP_ROOT", backup_root)

    with pytest.raises(SystemExit, match="Missing local real YAML file"):
        backup_real_yaml.backup_real_yaml_files()
