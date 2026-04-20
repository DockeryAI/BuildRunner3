import subprocess

from fastapi.testclient import TestClient

from api.server import app


def test_execute_route_defaults_to_claude_when_runtime_is_omitted(monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, shell, cwd, capture_output, text, env, timeout):
        captured["env"] = env
        return type("Completed", (), {"stdout": "claude ok", "stderr": "", "returncode": 0})()

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = TestClient(app)
    response = client.post("/api/execute", json={"command": "br status", "cwd": str(tmp_path)})

    assert response.status_code == 200
    body = response.json()
    assert body["resolved_runtime"] == "claude"
    assert body["runtime_source"] == "default"
    assert captured["env"]["BR3_RUNTIME"] == "claude"
    assert captured["env"]["BR3_RUNTIME_SOURCE"] == "default"


def test_execute_route_rejects_non_br_commands_even_when_runtime_is_selected(tmp_path):
    client = TestClient(app)

    response = client.post("/api/execute", json={"command": "echo nope", "cwd": str(tmp_path), "runtime": "codex"})

    assert response.status_code == 400
    assert "Only BuildRunner" in response.json()["detail"]


def test_runtime_resolve_rejects_invalid_runtime_value(tmp_path):
    client = TestClient(app)

    response = client.get("/api/runtime/resolve", params={"cwd": str(tmp_path), "runtime": "invalid"})

    assert response.status_code == 400
    assert "Unsupported runtime" in response.json()["detail"]
