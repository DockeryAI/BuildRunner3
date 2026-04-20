import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path


SCRIPT_HOME_FILES = [
    Path.home() / ".buildrunner" / "scripts" / "runtime-dispatch.sh",
    Path.home() / ".buildrunner" / "scripts" / "build-sidecar.sh",
    Path.home() / ".buildrunner" / "scripts" / "dispatch-to-node.sh",
    Path.home() / ".buildrunner" / "scripts" / "_dispatch-core.sh",
]


def _copy_scripts(fake_home: Path) -> None:
    scripts_dir = fake_home / ".buildrunner" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for source in SCRIPT_HOME_FILES:
        target = scripts_dir / source.name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        target.chmod(0o755)


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _base_env(fake_home: Path, fake_bin: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    return env


def test_runtime_dispatch_executes_codex_with_project_path_and_prompt(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    project_root = tmp_path / "project"
    prompt_file = tmp_path / "prompt.txt"
    log_path = tmp_path / "codex.log"

    _copy_scripts(fake_home)
    fake_bin.mkdir(parents=True)
    project_root.mkdir(parents=True)
    prompt_file.write_text("Phase 1 prompt from BR3", encoding="utf-8")

    _write_executable(
        fake_bin / "codex",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\\n' "$@" > "{log_path}"
            exit 0
            """
        ),
    )

    env = _base_env(fake_home, fake_bin)
    script = fake_home / ".buildrunner" / "scripts" / "runtime-dispatch.sh"
    result = subprocess.run(
        ["bash", str(script), "codex", str(project_root), str(prompt_file)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0
    logged = log_path.read_text(encoding="utf-8")
    assert "--ask-for-approval" in logged
    assert "--cd" in logged
    assert str(project_root) in logged
    assert "Phase 1 prompt from BR3" in logged


def test_build_sidecar_records_codex_runtime_metadata_and_heartbeat(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    project_root = tmp_path / "project"
    codex_log = tmp_path / "sidecar-codex.log"

    _copy_scripts(fake_home)
    fake_bin.mkdir(parents=True)
    (project_root / ".buildrunner" / "locks" / "phase-1").mkdir(parents=True, exist_ok=True)
    (project_root / ".git").mkdir()

    _write_executable(
        fake_bin / "codex",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\\n' "$@" > "{codex_log}"
            sleep 2
            exit 0
            """
        ),
    )

    env = _base_env(fake_home, fake_bin)
    env["BR3_SIDECAR_HEARTBEAT_SECONDS"] = "1"
    env["BR3_CODEX_BIN"] = str(fake_bin / "codex")
    sidecar_script = fake_home / ".buildrunner" / "scripts" / "build-sidecar.sh"

    result = subprocess.run(
        ["bash", str(sidecar_script), "demo:BUILD_demo", "1", str(project_root), "codex"],
        input="Read the BUILD spec at .buildrunner/builds/BUILD_demo.md.\n",
        text=True,
        capture_output=True,
        env=env,
        cwd=project_root,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0
    lock_dir = project_root / ".buildrunner" / "locks" / "phase-1"
    sidecar = json.loads((lock_dir / "sidecar.json").read_text(encoding="utf-8"))
    heartbeat = json.loads((lock_dir / "heartbeat").read_text(encoding="utf-8"))
    exit_status = json.loads((lock_dir / "exit-status.json").read_text(encoding="utf-8"))

    assert sidecar["runtime"] == "codex"
    assert sidecar["runtime_pid"] > 0
    assert sidecar["runtime_path"] == str(fake_bin / "codex")
    assert heartbeat["runtime"] == "codex"
    assert heartbeat["pid"] == sidecar["runtime_pid"]
    assert exit_status["exit_code"] == 0
    assert "--skip-git-repo-check" in codex_log.read_text(encoding="utf-8")


def test_dispatch_to_node_accepts_runtime_flag_for_codex(tmp_path: Path):
    fake_home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    project_root = tmp_path / "project"
    ssh_log = tmp_path / "ssh.log"
    remote_log = tmp_path / "remote.log"
    rsync_log = tmp_path / "rsync.log"

    _copy_scripts(fake_home)
    fake_bin.mkdir(parents=True)
    (fake_home / ".buildrunner").mkdir(parents=True, exist_ok=True)
    (fake_home / ".buildrunner" / ".env").write_text("CLUSTER_SSH_USER=tester\n", encoding="utf-8")
    (fake_home / ".buildrunner" / "cluster.json").write_text(
        json.dumps({"nodes": {"lomax": {"host": "127.0.0.1", "role": "builder", "description": "mac"}}}),
        encoding="utf-8",
    )
    _write_executable(
        fake_home / ".buildrunner" / "scripts" / "cluster-check.sh",
        "#!/usr/bin/env bash\necho http://node\n",
    )
    _write_executable(
        fake_home / ".buildrunner" / "scripts" / "check-runtime-auth.sh",
        "#!/usr/bin/env bash\necho '{\"runtime\":\"codex\",\"mode\":\"direct\",\"policy_action\":\"pass\",\"dispatch_ok\":true,\"version\":{\"raw\":\"codex-cli 0.48.0\"}}'\n",
    )
    _write_executable(
        fake_bin / "scp",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    _write_executable(
        fake_bin / "rsync",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\\n' "$*" >> "{rsync_log}"
            exit 0
            """
        ),
    )
    _write_executable(
        fake_bin / "ssh",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\\n' "$*" >> "{ssh_log}"
            cmd="${{@: -1}}"
            case "$cmd" in
              "exit 0") exit 0 ;;
              *"[ -f ~/repos/"* ) echo yes; exit 0 ;;
              *"git diff --stat HEAD"* ) echo " 1 file changed"; exit 0 ;;
              *"git log --oneline -1"* ) echo "remote123 commit"; exit 0 ;;
              *"build-sidecar.sh"* ) printf '%s\\n' "$cmd" >> "{remote_log}"; echo "[sidecar] Runtime codex exited with code 0"; exit 0 ;;
              *) exit 0 ;;
            esac
            """
        ),
    )

    project_root.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_root, check=True)
    (project_root / ".gitignore").write_text("", encoding="utf-8")
    (project_root / "README.md").write_text("demo\n", encoding="utf-8")
    (project_root / ".buildrunner" / "builds").mkdir(parents=True, exist_ok=True)
    (project_root / ".buildrunner" / "builds" / "BUILD_demo.md").write_text("# Build\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=project_root, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=project_root, check=True, capture_output=True)

    env = _base_env(fake_home, fake_bin)
    dispatch_script = fake_home / ".buildrunner" / "scripts" / "dispatch-to-node.sh"
    prompt = "Read the BUILD spec at .buildrunner/builds/BUILD_demo.md. Execute Phase 1."
    result = subprocess.run(
        ["bash", str(dispatch_script), "--runtime", "codex", "lomax", str(project_root), prompt, "session-1"],
        capture_output=True,
        text=True,
        env=env,
        cwd=project_root,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0
    remote_invocation = remote_log.read_text(encoding="utf-8")
    assert "build-sidecar.sh 'project:BUILD_demo' '1'" in remote_invocation
    assert "\"\\$(pwd)\" 'codex'" in remote_invocation or '"$(pwd)" \'codex\'' in remote_invocation
    assert "runtime-dispatch.sh" in rsync_log.read_text(encoding="utf-8")
