from __future__ import annotations

from datetime import datetime
from pathlib import Path
from shutil import copy2


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_DIR = REPO_ROOT / ".local" / "real"
BACKUP_ROOT = REPO_ROOT / ".local" / "backups"
REAL_FILE_NAMES = ("configuration.yaml", "automations.yaml")


def ensure_real_files_exist() -> list[Path]:
    """Return the real YAML files, or fail early if any are missing."""
    real_files = [REAL_DIR / name for name in REAL_FILE_NAMES]
    missing_files = [path for path in real_files if not path.exists()]

    if missing_files:
        missing_list = "\n".join(f"- {path}" for path in missing_files)
        raise SystemExit(
            "Missing local real YAML file(s):\n"
            f"{missing_list}\n\n"
            "Create them first under .local/real/ before running the backup script."
        )

    return real_files


def create_backup_directory(now: datetime | None = None) -> Path:
    """Create and return one timestamped backup directory."""
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_ROOT / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    return backup_dir


def backup_real_yaml_files(now: datetime | None = None) -> Path:
    """Copy the real YAML files into one timestamped backup directory."""
    real_files = ensure_real_files_exist()
    backup_dir = create_backup_directory(now=now)

    for source_path in real_files:
        copy2(source_path, backup_dir / source_path.name)

    return backup_dir


def main() -> None:
    """Create a timestamped backup of the ignored real YAML files."""
    backup_dir = backup_real_yaml_files()
    print("Backed up local real YAML files:")
    print(f"- {backup_dir / 'configuration.yaml'}")
    print(f"- {backup_dir / 'automations.yaml'}")


if __name__ == "__main__":
    main()
