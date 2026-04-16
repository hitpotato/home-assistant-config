from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import yaml_flow


def git(repo_path: Path, *args: str) -> str:
    """Run one git command in one temporary repo."""
    result = subprocess.run(
        ("git", "-C", str(repo_path), *args),
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def init_repo(repo_path: Path) -> None:
    """Create one git repo with a local test identity."""
    repo_path.mkdir(parents=True, exist_ok=True)
    git(repo_path, "init", "-b", "main")
    git(repo_path, "config", "user.name", "Test User")
    git(repo_path, "config", "user.email", "test@example.com")


def init_bare_remote(remote_path: Path) -> None:
    """Create one bare remote repo for branch and fetch tests."""
    subprocess.run(
        ("git", "init", "--bare", str(remote_path)),
        check=True,
        text=True,
        capture_output=True,
    )


def commit_all(repo_path: Path, message: str) -> None:
    """Stage and commit all current changes in one test repo."""
    git(repo_path, "add", ".")
    git(repo_path, "commit", "-m", message)


def write_public_yaml(repo_path: Path, configuration_text: str, automations_text: str) -> None:
    """Write the tracked public YAML files used by yaml_flow."""
    (repo_path / "configuration.yaml").write_text(configuration_text, encoding="utf-8")
    (repo_path / "automations.yaml").write_text(automations_text, encoding="utf-8")


def write_private_yaml(repo_path: Path, configuration_text: str, automations_text: str) -> None:
    """Write the real YAML files inside the private repo."""
    (repo_path / "configuration.yaml").write_text(configuration_text, encoding="utf-8")
    (repo_path / "automations.yaml").write_text(automations_text, encoding="utf-8")


def clone_private_remote(remote_path: Path, clone_path: Path) -> None:
    """Clone the private remote and configure the local identity."""
    subprocess.run(
        ("git", "clone", str(remote_path), str(clone_path)),
        check=True,
        text=True,
        capture_output=True,
    )
    git(clone_path, "config", "user.name", "Test User")
    git(clone_path, "config", "user.email", "test@example.com")


def seed_private_remote(
    remote_path: Path,
    seed_path: Path,
    *,
    configuration_text: str,
    automations_text: str,
) -> None:
    """Create the private remote main branch before cloning from it."""
    init_repo(seed_path)
    git(seed_path, "remote", "add", "origin", str(remote_path))
    write_private_yaml(seed_path, configuration_text, automations_text)
    commit_all(seed_path, "seed private main")
    git(seed_path, "push", "-u", "origin", "main")


def seed_public_repo_with_origin(
    public_repo: Path,
    public_remote: Path,
    *,
    configuration_text: str,
    automations_text: str,
) -> None:
    """Create a public repo with origin/main already pushed."""
    init_repo(public_repo)
    git(public_repo, "remote", "add", "origin", str(public_remote))
    write_public_yaml(public_repo, configuration_text, automations_text)
    commit_all(public_repo, "seed public main")
    git(public_repo, "push", "-u", "origin", "main")


def patch_repo_paths(
    monkeypatch: pytest.MonkeyPatch,
    *,
    public_repo: Path,
    private_repo: Path,
) -> None:
    """Point yaml_flow at temporary public and private repos."""
    monkeypatch.setattr(yaml_flow, "REPO_ROOT", public_repo)
    monkeypatch.setattr(yaml_flow, "PUBLIC_CONFIGURATION", public_repo / "configuration.yaml")
    monkeypatch.setattr(yaml_flow, "PUBLIC_AUTOMATIONS", public_repo / "automations.yaml")
    monkeypatch.setattr(yaml_flow, "DEFAULT_PRIVATE_REPO", private_repo)


def test_resolve_private_repo_path_prefers_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The env override should win over the default sibling path."""
    private_repo = tmp_path / "custom-private"
    monkeypatch.setenv("HA_PRIVATE_YAML_REPO", str(private_repo))

    assert yaml_flow.resolve_private_repo_path() == private_repo


def test_refresh_rejects_private_repo_path_inside_public_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refresh should fail if the private path is still nested in the public repo."""
    public_repo = tmp_path / "public"
    nested_private_path = public_repo / ".local" / "real"

    init_repo(public_repo)
    write_public_yaml(public_repo, "config: public\n", "automation: public\n")
    commit_all(public_repo, "init public")
    nested_private_path.mkdir(parents=True, exist_ok=True)
    patch_repo_paths(monkeypatch, public_repo=public_repo, private_repo=nested_private_path)

    with pytest.raises(SystemExit, match="own private git clone"):
        yaml_flow.refresh()


def test_refresh_refuses_to_overwrite_dirty_public_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refresh should stop instead of clobbering local tracked YAML edits."""
    public_repo = tmp_path / "public"
    private_remote = tmp_path / "private-remote.git"
    private_seed = tmp_path / "private-seed"
    private_repo = tmp_path / "private"

    init_repo(public_repo)
    write_public_yaml(public_repo, "config: public\n", "automation: public\n")
    commit_all(public_repo, "init public")

    init_bare_remote(private_remote)
    seed_private_remote(
        private_remote,
        private_seed,
        configuration_text="config: real\n",
        automations_text="automation: real\n",
    )
    clone_private_remote(private_remote, private_repo)

    write_public_yaml(public_repo, "config: changed locally\n", "automation: public\n")
    patch_repo_paths(monkeypatch, public_repo=public_repo, private_repo=private_repo)

    with pytest.raises(SystemExit, match="before running yaml_flow refresh"):
        yaml_flow.refresh()


def test_refresh_uses_private_working_tree_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Refresh should mirror uncommitted private edits, not only committed state."""
    public_repo = tmp_path / "public"
    private_remote = tmp_path / "private-remote.git"
    private_seed = tmp_path / "private-seed"
    private_repo = tmp_path / "private"

    init_repo(public_repo)
    write_public_yaml(public_repo, "mode: old\n", "alias: old\n")
    commit_all(public_repo, "init public")

    init_bare_remote(private_remote)
    seed_private_remote(
        private_remote,
        private_seed,
        configuration_text="mode: before\nnotify_target: notify.mobile_app_longchen_iphone\n",
        automations_text="- alias: before\n",
    )
    clone_private_remote(private_remote, private_repo)

    write_private_yaml(
        private_repo,
        "mode: after\nnotify_target: notify.mobile_app_longchen_iphone\n",
        "- alias: after\n",
    )
    patch_repo_paths(monkeypatch, public_repo=public_repo, private_repo=private_repo)

    yaml_flow.refresh()

    configuration_text = (public_repo / "configuration.yaml").read_text(encoding="utf-8")
    automations_text = (public_repo / "automations.yaml").read_text(encoding="utf-8")
    output = capsys.readouterr().out

    assert "mode: after" in configuration_text
    assert "- alias: after" in automations_text
    assert "notify.mobile_app_longchen_iphone" not in configuration_text
    assert "Private repo state: dirty" in output
    assert "Changed public YAML:" in output
    assert "- configuration.yaml" in output
    assert "- automations.yaml" in output


def test_start_creates_private_branch_from_origin_main_without_rewriting_public_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Start should create the matching private branch from private origin/main."""
    public_repo = tmp_path / "public"
    private_remote = tmp_path / "private-remote.git"
    private_seed = tmp_path / "private-seed"
    private_repo = tmp_path / "private"
    branch_name = "feature/private-yaml-workflow"

    init_repo(public_repo)
    write_public_yaml(public_repo, "mode: public\n", "- alias: public\n")
    commit_all(public_repo, "init public")
    git(public_repo, "switch", "-c", branch_name)

    init_bare_remote(private_remote)
    seed_private_remote(
        private_remote,
        private_seed,
        configuration_text="mode: start\nnotify_target: notify.mobile_app_longchen_iphone\n",
        automations_text="- alias: start\n",
    )
    clone_private_remote(private_remote, private_repo)
    patch_repo_paths(monkeypatch, public_repo=public_repo, private_repo=private_repo)

    yaml_flow.start()

    configuration_text = (public_repo / "configuration.yaml").read_text(encoding="utf-8")
    automations_text = (public_repo / "automations.yaml").read_text(encoding="utf-8")
    output = capsys.readouterr().out

    assert git(private_repo, "branch", "--show-current") == branch_name
    assert git(private_repo, "rev-parse", branch_name) == git(private_repo, "rev-parse", "origin/main")
    assert configuration_text == "mode: public\n"
    assert automations_text == "- alias: public\n"
    assert f"Ready on branch {branch_name}." in output
    assert "Private repo state: clean" in output
    assert "Private branch is ready." in output


def test_start_tracks_existing_remote_branch_when_local_branch_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start should track a matching remote branch instead of forking a new one."""
    public_repo = tmp_path / "public"
    private_remote = tmp_path / "private-remote.git"
    private_seed = tmp_path / "private-seed"
    private_repo = tmp_path / "private"
    branch_name = "feature/existing-remote"

    init_repo(public_repo)
    write_public_yaml(public_repo, "mode: public\n", "- alias: public\n")
    commit_all(public_repo, "init public")
    git(public_repo, "switch", "-c", branch_name)

    init_bare_remote(private_remote)
    seed_private_remote(
        private_remote,
        private_seed,
        configuration_text="mode: main\n",
        automations_text="- alias: main\n",
    )
    git(private_seed, "switch", "-c", branch_name)
    write_private_yaml(
        private_seed,
        "mode: remote-branch\n",
        "- alias: remote-branch\n",
    )
    commit_all(private_seed, "add remote branch content")
    git(private_seed, "push", "-u", "origin", branch_name)

    clone_private_remote(private_remote, private_repo)
    patch_repo_paths(monkeypatch, public_repo=public_repo, private_repo=private_repo)

    yaml_flow.start()

    assert git(private_repo, "branch", "--show-current") == branch_name
    assert git(private_repo, "rev-parse", branch_name) == git(private_repo, "rev-parse", f"origin/{branch_name}")


def remote_branch_exists(remote_path: Path, branch_name: str) -> bool:
    """Return True if a bare remote currently has one branch head."""
    result = subprocess.run(
        ("git", "ls-remote", "--heads", str(remote_path), branch_name),
        check=True,
        text=True,
        capture_output=True,
    )
    return bool(result.stdout.strip())


def test_push_private_branch_pushes_matching_private_branch_for_yaml_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Push-private-branch should publish the matching private branch when it has real work."""
    public_repo = tmp_path / "public"
    public_remote = tmp_path / "public-remote.git"
    private_remote = tmp_path / "private-remote.git"
    private_seed = tmp_path / "private-seed"
    private_repo = tmp_path / "private"
    branch_name = "feature/paired-yaml-change"

    init_bare_remote(public_remote)
    seed_public_repo_with_origin(
        public_repo,
        public_remote,
        configuration_text="mode: public-main\n",
        automations_text="- alias: public-main\n",
    )
    git(public_repo, "switch", "-c", branch_name)
    write_public_yaml(public_repo, "mode: sanitized-branch\n", "- alias: sanitized-branch\n")
    commit_all(public_repo, "public yaml branch change")

    init_bare_remote(private_remote)
    seed_private_remote(
        private_remote,
        private_seed,
        configuration_text="mode: real-main\nnotify_target: notify.mobile_app_longchen_iphone\n",
        automations_text="- alias: real-main\n",
    )
    clone_private_remote(private_remote, private_repo)
    patch_repo_paths(monkeypatch, public_repo=public_repo, private_repo=private_repo)

    yaml_flow.start()
    capsys.readouterr()

    write_private_yaml(
        private_repo,
        "mode: real-branch\nnotify_target: notify.mobile_app_longchen_iphone\n",
        "- alias: real-branch\n",
    )
    commit_all(private_repo, "private yaml branch change")

    yaml_flow.push_private_branch()

    git(private_repo, "fetch", "origin")
    output = capsys.readouterr().out

    assert remote_branch_exists(private_remote, branch_name)
    assert git(private_repo, "rev-parse", branch_name) == git(private_repo, "rev-parse", f"origin/{branch_name}")
    assert "Pushing private branch..." in output
    assert "Private branch pushed." in output
    assert "The matching private branch is ready for YAML parity." in output
    assert "Push the public branch and create the public pull request manually." in output


def test_push_private_branch_noops_for_public_only_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Push-private-branch should succeed without pushing when there is no private diff."""
    public_repo = tmp_path / "public"
    public_remote = tmp_path / "public-remote.git"
    private_remote = tmp_path / "private-remote.git"
    private_seed = tmp_path / "private-seed"
    private_repo = tmp_path / "private"
    branch_name = "feature/public-only-docs"

    init_bare_remote(public_remote)
    seed_public_repo_with_origin(
        public_repo,
        public_remote,
        configuration_text="mode: public-main\n",
        automations_text="- alias: public-main\n",
    )
    git(public_repo, "switch", "-c", branch_name)
    (public_repo / "README.md").write_text("docs change\n", encoding="utf-8")
    commit_all(public_repo, "public-only change")

    init_bare_remote(private_remote)
    seed_private_remote(
        private_remote,
        private_seed,
        configuration_text="mode: real-main\n",
        automations_text="- alias: real-main\n",
    )
    clone_private_remote(private_remote, private_repo)
    patch_repo_paths(monkeypatch, public_repo=public_repo, private_repo=private_repo)

    yaml_flow.start()
    capsys.readouterr()

    yaml_flow.push_private_branch()

    output = capsys.readouterr().out

    assert not remote_branch_exists(private_remote, branch_name)
    assert f"Private branch {branch_name} has no commits ahead of origin/main." in output
    assert "No private sync is needed for this branch." in output
    assert "Push the public branch and create the public pull request manually." in output


def test_push_private_branch_refreshes_public_origin_main_before_branch_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Push-private-branch should refresh public origin/main before it decides a PR is needed."""
    public_repo = tmp_path / "public"
    public_remote = tmp_path / "public-remote.git"
    private_remote = tmp_path / "private-remote.git"
    private_seed = tmp_path / "private-seed"
    private_repo = tmp_path / "private"
    branch_name = "feature/already-merged"

    init_bare_remote(public_remote)
    seed_public_repo_with_origin(
        public_repo,
        public_remote,
        configuration_text="mode: public-main\n",
        automations_text="- alias: public-main\n",
    )
    git(public_repo, "switch", "-c", branch_name)
    (public_repo / "README.md").write_text("feature branch change\n", encoding="utf-8")
    commit_all(public_repo, "feature change")
    git(public_repo, "push", "origin", f"{branch_name}:main")

    init_bare_remote(private_remote)
    seed_private_remote(
        private_remote,
        private_seed,
        configuration_text="mode: real-main\n",
        automations_text="- alias: real-main\n",
    )
    clone_private_remote(private_remote, private_repo)
    patch_repo_paths(monkeypatch, public_repo=public_repo, private_repo=private_repo)

    yaml_flow.start()

    with pytest.raises(SystemExit, match="There is nothing to prepare for a public pull request."):
        yaml_flow.push_private_branch()
