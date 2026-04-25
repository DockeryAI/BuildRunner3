from __future__ import annotations

import shutil
import stat
import subprocess
from typing import TYPE_CHECKING

import pytest

from core.asset_resolver import resolve_asset_path
from core.installer.hook_installer import install_hooks

if TYPE_CHECKING:
    from pathlib import Path


def _git_executable() -> str:
    git = shutil.which("git")
    assert git is not None
    return git


def _init_git_repo(project: Path) -> None:
    template_dir = project.parent / "git-template"
    template_dir.mkdir(exist_ok=True)
    subprocess.run(  # noqa: S603
        [_git_executable(), "init", f"--template={template_dir}"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    (project / ".git" / "hooks").mkdir(parents=True, exist_ok=True)


@pytest.fixture
def br2_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    _init_git_repo(project)

    pre_commit = project / ".git" / "hooks" / "pre-commit"
    pre_commit.write_text("#!/bin/sh\nbrandock-spec --run\n", encoding="utf-8")
    pre_commit.chmod(0o755)

    return project


def test_install_hooks_replaces_br2_hook_and_logs_swap(br2_project: Path) -> None:
    result = install_hooks(br2_project)

    assert result.replaced == ["pre-commit"]

    legacy_dir = br2_project / ".buildrunner" / "hooks" / "legacy"
    backups = sorted(legacy_dir.glob("pre-commit.*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "#!/bin/sh\nbrandock-spec --run\n"
    assert result.backed_up == backups

    installed_pre_commit = br2_project / ".git" / "hooks" / "pre-commit"
    assert installed_pre_commit.read_text(encoding="utf-8") == resolve_asset_path(
        ".buildrunner/hooks/pre-commit-enforced"
    ).read_text(encoding="utf-8")
    assert installed_pre_commit.stat().st_mode & stat.S_IXUSR

    assert result.pre_push_d == br2_project / ".git" / "hooks" / "pre-push.d"
    assert result.pre_push_d.is_dir()
    assert (result.pre_push_d / "50-ship-gate.sh").is_file()

    decisions_log = br2_project / ".buildrunner" / "decisions.log"
    contents = decisions_log.read_text(encoding="utf-8")
    assert "hook-installer replaced=pre-commit" in contents
    assert f"backup={backups[0]}" in contents
    assert (
        f"source={resolve_asset_path('.buildrunner/hooks/pre-commit-enforced')}" in contents
    )


def test_install_hooks_is_idempotent_for_existing_br3_hooks(br2_project: Path) -> None:
    first_result = install_hooks(br2_project)
    second_result = install_hooks(br2_project)

    assert first_result.replaced == ["pre-commit"]
    assert second_result.replaced == []
    assert second_result.backed_up == []

    backups = sorted((br2_project / ".buildrunner" / "hooks" / "legacy").glob("pre-commit.*"))
    assert len(backups) == 1

    decisions_log = br2_project / ".buildrunner" / "decisions.log"
    lines = decisions_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "replaced=pre-commit" in lines[0]


def test_install_hooks_clean_install_has_no_replacements(tmp_path: Path) -> None:
    project = tmp_path / "clean-project"
    project.mkdir()
    _init_git_repo(project)

    result = install_hooks(project)

    assert result.replaced == []
    assert result.backed_up == []
    assert (project / ".git" / "hooks" / "pre-commit").is_file()
    assert (project / ".git" / "hooks" / "pre-push").is_file()
    assert (project / ".git" / "hooks" / "pre-push.d").is_dir()
    assert (project / ".git" / "hooks" / "pre-push.d" / "50-ship-gate.sh").is_file()
