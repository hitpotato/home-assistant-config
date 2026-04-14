from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from sanitize_yaml import sanitize_yaml_pair


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CONFIGURATION = REPO_ROOT / "configuration.yaml"
PUBLIC_AUTOMATIONS = REPO_ROOT / "automations.yaml"
DEFAULT_PRIVATE_REPO = REPO_ROOT / ".local" / "real"
PRIVATE_MAIN_BRANCH = "main"
PRIVATE_CONFIGURATION = "configuration.yaml"
PRIVATE_AUTOMATIONS = "automations.yaml"


def run_git(repo_path: Path, *args: str) -> str:
    """Run one git command and return stripped stdout."""
    result = subprocess.run(
        ("git", "-C", str(repo_path), *args),
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def git_toplevel(repo_path: Path) -> Path:
    """Return the resolved working-tree root for one git repo path."""
    return Path(run_git(repo_path, "rev-parse", "--show-toplevel")).resolve()


def resolve_private_repo_path() -> Path:
    """Return the private repo path from env, or the sibling default."""
    override = os.environ.get("HA_PRIVATE_YAML_REPO")
    return Path(override).expanduser() if override else DEFAULT_PRIVATE_REPO


def current_public_branch() -> str:
    """Return the current branch name in the public repo."""
    branch = run_git(REPO_ROOT, "branch", "--show-current")
    if not branch:
        raise SystemExit("Could not determine the current public branch.")
    return branch


def ensure_repo_exists(repo_path: Path) -> None:
    """Fail early if the target repo path is missing or not a separate git repo."""
    if not repo_path.exists():
        raise SystemExit(
            f"Private repo not found: {repo_path}\n"
            "Set HA_PRIVATE_YAML_REPO or clone the private repo into .local/real."
        )

    try:
        private_git_root = git_toplevel(repo_path)
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"Path is not a git repo: {repo_path}") from error

    public_git_root = git_toplevel(REPO_ROOT)
    if private_git_root == public_git_root:
        raise SystemExit(
            f"Private repo path points at the public repo working tree: {repo_path}\n"
            "Make .local/real its own private git clone or set HA_PRIVATE_YAML_REPO to a separate private repo."
        )


def public_yaml_is_dirty() -> bool:
    """Return True if the tracked public YAML files have local changes."""
    status = run_git(
        REPO_ROOT,
        "status",
        "--short",
        "--",
        str(PUBLIC_CONFIGURATION),
        str(PUBLIC_AUTOMATIONS),
    )
    return bool(status)


def changed_public_yaml_paths() -> list[Path]:
    """Return the tracked public YAML files that currently differ from HEAD."""
    status = run_git(
        REPO_ROOT,
        "status",
        "--short",
        "--",
        str(PUBLIC_CONFIGURATION),
        str(PUBLIC_AUTOMATIONS),
    )
    changed_paths: list[Path] = []

    for line in status.splitlines():
        if not line:
            continue
        changed_paths.append(REPO_ROOT / line.split(maxsplit=1)[1])

    return changed_paths


def repo_is_dirty(repo_path: Path) -> bool:
    """Return True if one git repo has any local changes."""
    status = run_git(repo_path, "status", "--short")
    return bool(status)


def ensure_clean_public_yaml(command_name: str) -> None:
    """Refuse to overwrite dirty tracked public YAML."""
    if public_yaml_is_dirty():
        raise SystemExit(
            "Tracked public YAML has local changes.\n"
            f"Commit, stash, or discard them before running yaml_flow {command_name}."
        )


def print_public_yaml_result() -> None:
    """Print which tracked YAML files changed after one sync operation."""
    changed_paths = changed_public_yaml_paths()

    if not changed_paths:
        print("Public YAML unchanged.")
        return

    print("Changed public YAML:")
    for path in changed_paths:
        print(f"- {path.relative_to(REPO_ROOT)}")


def branch_exists(repo_path: Path, branch_name: str, *, remote: bool = False) -> bool:
    """Return True if one local or remote-tracking branch exists."""
    ref = f"refs/remotes/origin/{branch_name}" if remote else f"refs/heads/{branch_name}"
    result = subprocess.run(
        ("git", "-C", str(repo_path), "show-ref", "--verify", "--quiet", ref),
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def switch_or_create_private_branch(private_repo: Path, branch_name: str) -> None:
    """Switch to the matching private branch, or create it from private main."""
    run_git(private_repo, "fetch", "origin")

    if branch_exists(private_repo, branch_name):
        run_git(private_repo, "switch", branch_name)
        return

    if branch_exists(private_repo, branch_name, remote=True):
        run_git(private_repo, "switch", "--track", "-c", branch_name, f"origin/{branch_name}")
        return

    run_git(private_repo, "switch", "-c", branch_name, f"origin/{PRIVATE_MAIN_BRANCH}")


def private_yaml_paths(private_repo: Path) -> tuple[Path, Path]:
    """Return the real YAML source files in the private repo."""
    return private_repo / PRIVATE_CONFIGURATION, private_repo / PRIVATE_AUTOMATIONS


def sanitize_from_private_repo(private_repo: Path) -> None:
    """Refresh the public mirror from the current private working tree."""
    configuration_source, automations_source = private_yaml_paths(private_repo)
    sanitize_yaml_pair(
        configuration_source=configuration_source,
        automations_source=automations_source,
        configuration_target=PUBLIC_CONFIGURATION,
        automations_target=PUBLIC_AUTOMATIONS,
    )


def start() -> None:
    """Create or switch the matching private branch, then refresh the mirror."""
    private_repo = resolve_private_repo_path()
    ensure_repo_exists(private_repo)
    branch_name = current_public_branch()
    ensure_clean_public_yaml("start")

    switch_or_create_private_branch(private_repo, branch_name)
    sanitize_from_private_repo(private_repo)

    print(f"Ready on branch {branch_name}.")
    print(f"Private repo: {private_repo}")
    print(f"Private repo state: {'dirty' if repo_is_dirty(private_repo) else 'clean'}")
    print("Sanitized private YAML into the public repo.")
    print_public_yaml_result()


def refresh() -> None:
    """Refresh the public mirror from the current private working tree."""
    private_repo = resolve_private_repo_path()
    ensure_repo_exists(private_repo)
    ensure_clean_public_yaml("refresh")

    sanitize_from_private_repo(private_repo)

    print(f"Private repo: {private_repo}")
    print(f"Private repo state: {'dirty' if repo_is_dirty(private_repo) else 'clean'}")
    print("Sanitized current private working tree into the public repo.")
    print_public_yaml_result()


def parse_args() -> argparse.Namespace:
    """Parse the yaml_flow command line."""
    parser = argparse.ArgumentParser(description="Manage private/public YAML sync.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("start", help="Create or switch the matching private branch.")
    subcommands.add_parser("refresh", help="Refresh tracked public YAML from private real YAML.")

    return parser.parse_args()


def main() -> None:
    """Dispatch yaml_flow subcommands."""
    args = parse_args()

    if args.command == "start":
        start()
    elif args.command == "refresh":
        refresh()
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
