import importlib.util
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "core/cluster/cross_model_review.py"
SCRIPT_PATH = Path.home() / ".buildrunner/scripts/check-runtime-auth.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("cross_model_review", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_runtime_preflight_shadow_skips_on_codex_auth_failure(monkeypatch):
    module = load_module()

    monkeypatch.setattr(module.shutil, "which", lambda command: f"/usr/local/bin/{command}")
    monkeypatch.setattr(
        module,
        "ensure_codex_compatible",
        lambda command="codex": {"raw": "codex-cli 0.48.0", "parsed": (0, 48, 0)},
    )
    monkeypatch.setattr(module, "check_codex_auth_file", lambda auth_file=None: (False, "Codex tokens missing. Run: codex"))
    monkeypatch.setattr(module, "log_runtime_capability", lambda entry: None)

    preflight = module.build_runtime_preflight(runtime="codex", mode="shadow", probe=False, node_name="walter")

    assert preflight["policy_action"] == "shadow_skipped"
    assert preflight["dispatch_ok"] is True
    assert preflight["failure_class"] == "RuntimeAuthError"
    assert preflight["auth"]["error"] == "Codex tokens missing. Run: codex"


def test_check_codex_auth_fails_on_non_auth_probe_error(monkeypatch):
    module = load_module()

    monkeypatch.setattr(module, "check_codex_auth_file", lambda auth_file=None: (True, None))
    monkeypatch.setattr(
        module,
        "run_codex_probe",
        lambda command="codex", timeout=module.DEFAULT_CODEX_PROBE_TIMEOUT_SECONDS, project_root=None: {
            "ok": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "network timeout",
            "auth_error": False,
            "timeout_seconds": timeout,
        },
    )

    auth_ok, auth_error = module.check_codex_auth(project_root="/tmp")

    assert auth_ok is False
    assert auth_error == "network timeout"


def test_check_runtime_auth_script_reports_success_with_fake_codex(tmp_path):
    fake_codex = tmp_path / "codex"
    fake_codex.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo 'codex-cli 0.48.0'\n"
        "  exit 0\n"
        "fi\n"
        "echo 'ok'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    auth_dir = tmp_path / ".codex"
    auth_dir.mkdir()
    auth_file = auth_dir / "auth.json"
    auth_file.write_text(
        json.dumps({"tokens": {"access_token": "token"}}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT_PATH),
            "--runtime",
            "codex",
            "--json",
            "--command",
            str(fake_codex),
            "--auth-file",
            str(auth_file),
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["runtime"] == "codex"
    assert payload["policy_action"] == "allow"
    assert payload["dispatch_ok"] is True
    assert payload["version"]["raw"] == "codex-cli 0.48.0"


def test_check_runtime_auth_script_helper_file_overrides_repo_lookup(tmp_path):
    fake_codex = tmp_path / "codex"
    fake_codex.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo 'codex-cli 0.48.0'\n"
        "  exit 0\n"
        "fi\n"
        "echo 'ok'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    auth_dir = tmp_path / ".codex"
    auth_dir.mkdir()
    auth_file = auth_dir / "auth.json"
    auth_file.write_text(
        json.dumps({"tokens": {"access_token": "token"}}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT_PATH),
            "--runtime",
            "codex",
            "--json",
            "--command",
            str(fake_codex),
            "--auth-file",
            str(auth_file),
            "--helper-file",
            str(MODULE_PATH),
            "--repo",
            str(tmp_path / "missing-repo"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["policy_action"] == "allow"
    assert payload["dispatch_ok"] is True


def test_check_runtime_auth_script_shadow_skip_returns_zero(tmp_path):
    fake_codex = tmp_path / "codex"
    fake_codex.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo 'codex-cli 0.48.0'\n"
        "  exit 0\n"
        "fi\n"
        "echo 'auth missing' >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT_PATH),
            "--runtime",
            "codex",
            "--mode",
            "shadow",
            "--json",
            "--command",
            str(fake_codex),
            "--auth-file",
            str(tmp_path / "missing-auth.json"),
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["policy_action"] == "shadow_skipped"
    assert payload["dispatch_ok"] is True
