import json
import os
import subprocess
import textwrap
from pathlib import Path


SCRIPT_HOME_FILES = [
    Path.home() / ".buildrunner" / "scripts" / "adversarial-review.sh",
    Path.home() / ".buildrunner" / "hooks" / "require-adversarial-review.sh",
]


def _copy_home_scripts(fake_home: Path) -> None:
    for source in SCRIPT_HOME_FILES:
        target = fake_home / ".buildrunner" / ("scripts" if source.parent.name == "scripts" else "hooks") / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        target.chmod(0o755)


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _base_env(fake_home: Path, fake_bin: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    return env


def _init_repo(project_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_root, check=True)


def test_consensus_review_writes_phase_tracking_files(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    project_root = tmp_path / "project"
    plan_file = project_root / ".buildrunner" / "plans" / "phase-plan.md"

    _copy_home_scripts(fake_home)
    fake_bin.mkdir(parents=True)
    project_root.mkdir(parents=True)
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text(
        textwrap.dedent(
            """\
            # Plan

            ### Phase 13: Hardening
            **Status:** pending

            ### Phase 14: Enforcement
            **Status:** pending
            """
        ),
        encoding="utf-8",
    )

    _write_executable(fake_bin / "claude", "#!/usr/bin/env bash\nprintf '%s\n' '[]'\n")
    _write_executable(
        fake_bin / "codex",
        "#!/usr/bin/env bash\nprintf '%s\n' '[{\"finding\":\"Missing rollout note\",\"severity\":\"warning\"}]'\n",
    )

    env = _base_env(fake_home, fake_bin)
    result = subprocess.run(
        [
            "bash",
            str(fake_home / ".buildrunner" / "scripts" / "adversarial-review.sh"),
            "--consensus",
            str(plan_file),
            str(project_root),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=project_root,
        check=False,
    )

    assert result.returncode == 0
    findings = json.loads(result.stdout)
    assert findings[0]["finding"] == "Missing rollout note"
    reviews_dir = project_root / ".buildrunner" / "adversarial-reviews"
    phase_13 = sorted(reviews_dir.glob("phase-13-*.json"))
    phase_14 = sorted(reviews_dir.glob("phase-14-*.json"))
    assert phase_13 and phase_14
    record = json.loads(phase_13[-1].read_text(encoding="utf-8"))
    assert record["pass"] is True
    assert record["reviewers"][0]["runtime"] == "claude"
    assert record["reviewers"][1]["runtime"] == "codex"
    assert record["unresolved_disagreements"] == []


def test_require_adversarial_review_blocks_new_phase_without_tracking_file(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    project_root = tmp_path / "project"

    _copy_home_scripts(fake_home)
    fake_bin.mkdir(parents=True)
    project_root.mkdir(parents=True)
    _init_repo(project_root)

    build_file = project_root / ".buildrunner" / "builds" / "BUILD_test.md"
    build_file.parent.mkdir(parents=True, exist_ok=True)
    build_file.write_text("# Build\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=project_root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=project_root, check=True, capture_output=True)

    build_file.write_text("# Build\n\n### Phase 14: Enforcement\n**Status:** pending\n", encoding="utf-8")
    subprocess.run(["git", "add", str(build_file)], cwd=project_root, check=True)

    env = _base_env(fake_home, fake_bin)
    result = subprocess.run(
        ["bash", str(fake_home / ".buildrunner" / "hooks" / "require-adversarial-review.sh"), str(project_root)],
        capture_output=True,
        text=True,
        env=env,
        cwd=project_root,
        check=False,
    )

    assert result.returncode == 1
    assert "adversarial-reviews is missing" in result.stderr


def test_require_adversarial_review_allows_reviewed_new_phase(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    project_root = tmp_path / "project"

    _copy_home_scripts(fake_home)
    fake_bin.mkdir(parents=True)
    project_root.mkdir(parents=True)
    _init_repo(project_root)

    build_file = project_root / ".buildrunner" / "builds" / "BUILD_test.md"
    reviews_dir = project_root / ".buildrunner" / "adversarial-reviews"
    build_file.parent.mkdir(parents=True, exist_ok=True)
    reviews_dir.mkdir(parents=True, exist_ok=True)
    build_file.write_text("# Build\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=project_root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=project_root, check=True, capture_output=True)

    build_file.write_text("# Build\n\n### Phase 14: Enforcement\n**Status:** pending\n", encoding="utf-8")
    (reviews_dir / "phase-14-20260416T120000Z.json").write_text(
        json.dumps(
            {
                "schema_version": "br3.adversarial_review.v1",
                "phase_number": 14,
                "artifact_path": str(build_file),
                "task_id": "task-1",
                "pass": True,
                "consensus_blockers": [],
                "unresolved_disagreements": [],
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(build_file)], cwd=project_root, check=True)

    env = _base_env(fake_home, fake_bin)
    result = subprocess.run(
        ["bash", str(fake_home / ".buildrunner" / "hooks" / "require-adversarial-review.sh"), str(project_root)],
        capture_output=True,
        text=True,
        env=env,
        cwd=project_root,
        check=False,
    )

    assert result.returncode == 0
