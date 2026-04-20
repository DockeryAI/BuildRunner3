import subprocess

from fastapi.testclient import TestClient

from api.server import app


def test_runtime_resolve_endpoint_reports_default_claude(tmp_path):
    client = TestClient(app)

    response = client.get("/api/runtime/resolve", params={"cwd": str(tmp_path)})

    assert response.status_code == 200
    body = response.json()
    assert body["runtime"] == "claude"
    assert body["source"] == "default"
    assert body["available_runtimes"] == ["claude", "codex"]


def test_runtime_resolve_endpoint_prefers_project_config(tmp_path):
    project_root = tmp_path / "project"
    (project_root / ".buildrunner").mkdir(parents=True)
    (project_root / ".buildrunner" / "runtime.json").write_text(
        '{"schema_version":"br3.runtime.config.v1","default_runtime":"codex"}',
        encoding="utf-8",
    )

    client = TestClient(app)
    response = client.get("/api/runtime/resolve", params={"cwd": str(project_root)})

    assert response.status_code == 200
    body = response.json()
    assert body["runtime"] == "codex"
    assert body["source"] == "project_config"


def test_execute_route_uses_project_runtime_when_runtime_is_omitted(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    (project_root / ".buildrunner").mkdir(parents=True)
    (project_root / ".buildrunner" / "runtime.json").write_text(
        '{"schema_version":"br3.runtime.config.v1","default_runtime":"codex"}',
        encoding="utf-8",
    )
    captured = {}

    def fake_run(command, shell, cwd, capture_output, text, env, timeout):
        captured["env"] = env
        return type("Completed", (), {"stdout": "ok", "stderr": "", "returncode": 0})()

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = TestClient(app)
    response = client.post("/api/execute", json={"command": "br status", "cwd": str(project_root)})

    assert response.status_code == 200
    assert response.json()["resolved_runtime"] == "codex"
    assert response.json()["runtime_source"] == "project_config"
    assert captured["env"]["BR3_RUNTIME"] == "codex"
    assert captured["env"]["BR3_RUNTIME_SOURCE"] == "project_config"
