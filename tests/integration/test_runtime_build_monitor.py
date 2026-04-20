from fastapi.testclient import TestClient

from api.server import app


def test_build_session_status_includes_runtime_metadata():
    client = TestClient(app)

    response = client.post(
        "/api/build/init",
        json={
            "project_name": "BuildRunner3",
            "project_alias": "br3-runtime",
            "project_path": "/tmp/br3-runtime",
            "runtime": "codex",
            "backend": "codex-cli 0.48.0",
            "runtime_source": "explicit",
            "runtime_session_id": "thread-123",
            "capabilities": {"review": True, "execution": False},
            "dispatch_mode": "parallel_shadow",
            "shadow_runtime": "codex",
            "shadow_status": "shadow_completed",
        },
    )

    assert response.status_code == 200

    status = client.get("/api/build/status/br3-runtime")

    assert status.status_code == 200
    payload = status.json()
    assert payload["runtime"] == "codex"
    assert payload["backend"] == "codex-cli 0.48.0"
    assert payload["runtime_source"] == "explicit"
    assert payload["runtime_session_id"] == "thread-123"
    assert payload["projectName"] == "BuildRunner3"
    assert payload["projectAlias"] == "br3-runtime"
    assert payload["dispatch_mode"] == "parallel_shadow"
    assert payload["shadow_runtime"] == "codex"
    assert payload["shadow_status"] == "shadow_completed"


def test_build_session_runtime_patch_updates_metadata():
    client = TestClient(app)

    init_response = client.post(
        "/api/build/init",
        json={
            "project_name": "BuildRunner3",
            "project_alias": "br3-runtime-patch",
            "project_path": "/tmp/br3-runtime-patch",
        },
    )
    assert init_response.status_code == 200

    patch_response = client.patch(
        "/api/build/status/br3-runtime-patch/runtime",
        json={
            "runtime": "codex",
            "backend": "codex-cli 0.48.0",
            "runtime_source": "project_config",
            "runtime_session_id": "thread-456",
            "capabilities": {"review": True, "shell": True},
            "dispatch_mode": "parallel_shadow",
            "shadow_runtime": "codex",
            "shadow_status": "shadow_completed",
        },
    )

    assert patch_response.status_code == 200
    payload = patch_response.json()["session"]
    assert payload["runtime"] == "codex"
    assert payload["backend"] == "codex-cli 0.48.0"
    assert payload["dispatchMode"] == "parallel_shadow"


def test_list_sessions_backend_filter_returns_only_matching_backend():
    client = TestClient(app)

    client.post(
        "/api/build/init",
        json={
            "project_name": "BuildRunner3",
            "project_alias": "br3-runtime-none-backend",
            "project_path": "/tmp/br3-runtime-none-backend",
        },
    )
    client.post(
        "/api/build/init",
        json={
            "project_name": "BuildRunner3",
            "project_alias": "br3-runtime-codex-backend",
            "project_path": "/tmp/br3-runtime-codex-backend",
            "runtime": "codex",
            "backend": "codex-cli 0.48.0",
        },
    )

    filtered = client.get("/api/build/sessions", params={"backend": "codex-cli 0.48.0"})

    assert filtered.status_code == 200
    aliases = {item["project_alias"] for item in filtered.json()["sessions"]}
    assert "br3-runtime-none-backend" not in aliases
    assert "br3-runtime-codex-backend" in aliases
