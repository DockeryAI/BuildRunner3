import subprocess

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from api.server import app as api_app
from cli.main import app as cli_app
from core.runtime.config import resolve_runtime_selection


def test_resolve_runtime_selection_precedence(tmp_path):
    user_home = tmp_path / "home"
    (user_home / ".buildrunner").mkdir(parents=True)
    (user_home / ".buildrunner/runtime.json").write_text(
        '{"schema_version":"br3.runtime.config.v1","default_runtime":"codex"}',
        encoding="utf-8",
    )

    project_root = tmp_path / "project"
    (project_root / ".buildrunner").mkdir(parents=True)
    (project_root / ".buildrunner/runtime.json").write_text(
        '{"schema_version":"br3.runtime.config.v1","default_runtime":"claude"}',
        encoding="utf-8",
    )

    assert resolve_runtime_selection(project_root=project_root, user_home=user_home).runtime == "claude"
    assert (
        resolve_runtime_selection(explicit_runtime="codex", project_root=project_root, user_home=user_home).runtime
        == "codex"
    )


def test_cli_runtime_option_applies_selection(monkeypatch):
    runner = CliRunner()
    captured = {}

    def fake_configure(explicit_runtime, project_root=None):
        captured["runtime"] = explicit_runtime
        return type("Resolution", (), {"to_dict": lambda self: {"runtime": "codex", "source": "explicit"}})()

    monkeypatch.setattr("cli.main.configure_runtime_selection", fake_configure)

    result = runner.invoke(cli_app, ["--runtime", "codex", "alias", "list"])

    assert result.exit_code == 0
    assert captured["runtime"] == "codex"


def test_execute_route_resolves_runtime_and_sets_env(monkeypatch, tmp_path):
    client = TestClient(api_app)
    captured = {}

    def fake_run(command, shell, cwd, capture_output, text, env, timeout):
        captured["env"] = env
        return type("Completed", (), {"stdout": "ok", "stderr": "", "returncode": 0})()

    monkeypatch.setattr(subprocess, "run", fake_run)

    response = client.post(
        "/api/execute",
        json={"command": "br status", "cwd": str(tmp_path), "runtime": "codex"},
    )

    assert response.status_code == 200
    assert response.json()["resolved_runtime"] == "codex"
    assert captured["env"]["BR3_RUNTIME"] == "codex"
    assert captured["env"]["BR3_RUNTIME_SOURCE"] == "explicit"


def test_orchestrator_runtime_endpoint_uses_project_config(tmp_path):
    project_root = tmp_path / "project"
    (project_root / ".buildrunner").mkdir(parents=True)
    (project_root / ".buildrunner/runtime.json").write_text(
        '{"schema_version":"br3.runtime.config.v1","default_runtime":"codex"}',
        encoding="utf-8",
    )

    client = TestClient(api_app)
    response = client.get("/api/orchestrator/runtime", params={"cwd": str(project_root)})

    assert response.status_code == 200
    assert response.json()["runtime"] == "codex"
    assert response.json()["source"] == "project_config"
