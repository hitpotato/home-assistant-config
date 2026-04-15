from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from sanitize_yaml import sanitize_yaml_pair


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CONFIGURATION = REPO_ROOT / "configuration.yaml"
PUBLIC_AUTOMATIONS = REPO_ROOT / "automations.yaml"
DEFAULT_PRIVATE_REPO = REPO_ROOT / ".local" / "real"
MAIN_BRANCH = "main"
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


def run_gh(repo_path: Path, *args: str) -> str:
    """Run one gh command in one repo and return stripped stdout."""
    result = subprocess.run(
        ("gh", *args),
        cwd=repo_path,
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


def current_branch(repo_path: Path, repo_label: str) -> str:
    """Return the current branch name for one repo."""
    branch = run_git(repo_path, "branch", "--show-current")
    if not branch:
        raise SystemExit(f"Could not determine the current {repo_label} branch.")
    return branch


def current_public_branch() -> str:
    """Return the current branch name in the public repo."""
    return current_branch(REPO_ROOT, "public")


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


def repo_has_tracked_changes(repo_path: Path) -> bool:
    """Return True if one git repo has staged or modified tracked files."""
    status = run_git(repo_path, "status", "--short", "--untracked-files=no")
    return bool(status)


def failure_details(error: subprocess.CalledProcessError) -> str:
    """Return the most useful stderr/stdout text from one failed subprocess call."""
    stderr = error.stderr.strip()
    if stderr:
        return stderr

    stdout = error.stdout.strip()
    if stdout:
        return stdout

    return str(error)


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

    run_git(private_repo, "switch", "-c", branch_name, f"origin/{MAIN_BRANCH}")


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


def push_branch(repo_path: Path, repo_label: str, branch_name: str) -> None:
    """Push one branch to origin and set upstream."""
    try:
        run_git(repo_path, "push", "-u", "origin", branch_name)
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            f"Could not push the {repo_label} branch {branch_name}.\n"
            f"{failure_details(error)}"
        ) from error


def find_matching_pr_url(repo_path: Path, branch_name: str, *, base_branch: str) -> str | None:
    """Return one open PR URL only when head and base exactly match."""
    try:
        output = run_gh(
            repo_path,
            "pr",
            "list",
            "--state",
            "open",
            "--head",
            branch_name,
            "--base",
            base_branch,
            "--json",
            "url,headRefName,baseRefName",
        )
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            "Could not inspect existing pull requests.\n"
            f"{failure_details(error)}"
        ) from error

    try:
        pull_requests = json.loads(output)
    except json.JSONDecodeError as error:
        raise SystemExit(
            "GitHub CLI returned unreadable pull request data.\n"
            f"{output}"
        ) from error

    for pull_request in pull_requests:
        if (
            pull_request["headRefName"] == branch_name
            and pull_request["baseRefName"] == base_branch
        ):
            return pull_request["url"]

    return None


def ensure_pr(repo_path: Path, repo_label: str, branch_name: str) -> tuple[str, bool]:
    """Create one PR if needed, or return the existing matching PR URL."""
    existing_url = find_matching_pr_url(repo_path, branch_name, base_branch=MAIN_BRANCH)
    if existing_url:
        return existing_url, True

    try:
        created_url = run_gh(
            repo_path,
            "pr",
            "create",
            "--base",
            MAIN_BRANCH,
            "--head",
            branch_name,
            "--fill",
        )
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            f"Could not create the {repo_label} pull request.\n"
            f"{failure_details(error)}"
        ) from error

    return created_url.splitlines()[-1], False


def branch_has_commits_over_main(repo_path: Path, branch_name: str) -> bool:
    """Return True when one branch is ahead of origin/main."""
    ahead_count = run_git(
        repo_path,
        "rev-list",
        "--count",
        f"origin/{MAIN_BRANCH}..{branch_name}",
    )
    return ahead_count != "0"


def refresh_origin_main(repo_path: Path, repo_label: str) -> None:
    """Fetch the latest origin/main before making PR decisions."""
    try:
        run_git(repo_path, "fetch", "origin", MAIN_BRANCH)
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            f"Could not refresh {repo_label} origin/{MAIN_BRANCH}.\n"
            f"{failure_details(error)}"
        ) from error


def start() -> None:
    """Create or switch the matching private branch."""
    private_repo = resolve_private_repo_path()
    ensure_repo_exists(private_repo)
    branch_name = current_public_branch()

    switch_or_create_private_branch(private_repo, branch_name)

    print(f"Ready on branch {branch_name}.")
    print(f"Private repo: {private_repo}")
    print(f"Private repo state: {'dirty' if repo_is_dirty(private_repo) else 'clean'}")
    print("Private branch is ready.")
    print("Run `uv run python scripts/yaml_flow.py refresh` when you want to rewrite public YAML.")


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


def open_prs() -> None:
    """Push both branches and create or reuse the matching PR pair."""
    private_repo = resolve_private_repo_path()
    ensure_repo_exists(private_repo)
    public_branch = current_public_branch()

    if public_branch == MAIN_BRANCH:
        raise SystemExit("yaml_flow open-prs only works from a feature branch, not main.")

    private_branch = current_branch(private_repo, "private")
    if private_branch != public_branch:
        raise SystemExit(
            "Public and private current branches do not match.\n"
            "Run `uv run python scripts/yaml_flow.py start` first."
        )

    if repo_has_tracked_changes(REPO_ROOT):
        raise SystemExit(
            "Public repo has tracked changes.\n"
            "Commit or stash them before running yaml_flow open-prs."
        )

    if repo_has_tracked_changes(private_repo):
        raise SystemExit(
            "Private repo has tracked changes.\n"
            "Commit or stash them before running yaml_flow open-prs."
        )

    refresh_origin_main(REPO_ROOT, "public repo")
    refresh_origin_main(private_repo, "private repo")

    if not branch_has_commits_over_main(REPO_ROOT, public_branch):
        raise SystemExit(
            f"Public branch {public_branch} has no commits ahead of origin/{MAIN_BRANCH}.\n"
            "There is nothing to open a public pull request for."
        )

    private_has_diff = branch_has_commits_over_main(private_repo, private_branch)

    print(f"Public repo: {REPO_ROOT}")
    print(f"Private repo: {private_repo}")
    print(f"Branch: {public_branch}")

    if private_has_diff:
        print("Pushing private branch...")
        push_branch(private_repo, "private", private_branch)
        print("Private branch pushed.")

        print("Ensuring private pull request...")
        private_pr_url, private_reused = ensure_pr(private_repo, "private", private_branch)
        print(f"Private PR {'reused' if private_reused else 'created'}: {private_pr_url}")
    else:
        print(f"Private branch {private_branch} has no commits ahead of origin/{MAIN_BRANCH}.")
        print("Skipping private push and private pull request.")

    print("Pushing public branch...")
    push_branch(REPO_ROOT, "public", public_branch)
    print("Public branch pushed.")

    print("Ensuring public pull request...")
    public_pr_url, public_reused = ensure_pr(REPO_ROOT, "public", public_branch)
    print(f"Public PR {'reused' if public_reused else 'created'}: {public_pr_url}")

    if private_has_diff:
        print("Both pull requests are ready.")
    else:
        print("Public pull request is ready. No private pull request was needed for this branch.")


def parse_args() -> argparse.Namespace:
    """Parse the yaml_flow command line."""
    parser = argparse.ArgumentParser(description="Manage private/public YAML sync.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("start", help="Create or switch the matching private branch.")
    subcommands.add_parser("refresh", help="Refresh tracked public YAML from private real YAML.")
    subcommands.add_parser(
        "open-prs",
        help="Push both branches and create or reuse the matching private/public PR pair.",
    )

    return parser.parse_args()


def main() -> None:
    """Dispatch yaml_flow subcommands."""
    args = parse_args()

    if args.command == "start":
        start()
    elif args.command == "refresh":
        refresh()
    elif args.command == "open-prs":
        open_prs()
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
