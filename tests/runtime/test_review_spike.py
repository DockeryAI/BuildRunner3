import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.server import app
from core.cluster import cross_model_review
from core.runtime import (
    ClaudeRuntime,
    CodexRuntime,
    RuntimeResult,
    RuntimeTask,
    compile_review_task,
    create_phase1_runtime_registry,
)


def make_task() -> RuntimeTask:
    return RuntimeTask(
        task_id="review-spike-deadbeef",
        task_type="review",
        diff_text="diff --git a/app.py b/app.py\n+print('hello')\n",
        spec_text="# Build Spec\nKeep review isolated.",
        project_root="/tmp/project",
        commit_sha="deadbeef",
        metadata={"mode": "parallel_shadow"},
    )


@pytest.mark.asyncio
async def test_claude_runtime_logs_shadow_metadata(monkeypatch):
    task = make_task()
    log_entries = []

    class FakeReviewer:
        def __init__(self, project_root=None):
            self.project_root = project_root

        async def review_diff(self, diff_text, context=None):
            return {
                "summary": "Looks fine",
                "issues": ["Missing test"],
                "suggestions": ["Add a smoke test"],
                "score": 80,
            }

    runtime = ClaudeRuntime(reviewer_factory=FakeReviewer, command="missing-claude")
    monkeypatch.setattr("core.runtime.claude_runtime.log_runtime_capability", log_entries.append)

    result = await runtime.run_review(task)

    assert result.status == "completed"
    assert result.metrics["exit_code"] == 0
    assert log_entries[0]["task_id"] == task.task_id
    assert log_entries[0]["backend"] == "claude"


def test_claude_runtime_uses_isolated_cli_json(monkeypatch):
    task = make_task()
    log_entries = []

    monkeypatch.setattr("core.runtime.claude_runtime.shutil.which", lambda command: "/opt/homebrew/bin/claude")
    monkeypatch.setattr("core.runtime.claude_runtime.log_runtime_capability", log_entries.append)

    def fake_run(cmd, cwd, capture_output, text, timeout):
        assert cwd.startswith("/var/folders/") or "br3-claude-shadow-" in cwd or cwd.startswith("/tmp/")
        assert "--output-format" in cmd
        assert "json" in cmd
        assert "--tools" in cmd
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "result": '[{"finding":"test","severity":"note"}]',
                    "session_id": "session-123",
                    "total_cost_usd": 0.001,
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                    "modelUsage": {"claude-sonnet-test": {"costUSD": 0.001}},
                }
            ),
            stderr="",
        )

    monkeypatch.setattr("core.runtime.claude_runtime.subprocess.run", fake_run)

    result = asyncio.run(ClaudeRuntime().run_review(task))

    assert result.status == "completed"
    assert result.metadata["isolated"] is True
    assert result.metrics["cost_usd"] == 0.001
    assert result.backend == "claude-sonnet-test"
    assert log_entries[0]["session_id"] == "session-123"


def test_codex_runtime_uses_isolated_exec_flags(monkeypatch):
    task = make_task()
    runtime = CodexRuntime(timeout_seconds=45)
    captured = {}

    monkeypatch.setattr("core.runtime.codex_runtime.check_codex_auth", lambda project_root=None, command="codex": (True, None))
    monkeypatch.setattr(
        "core.runtime.codex_runtime.ensure_codex_compatible",
        lambda command="codex": {"raw": "codex-cli 0.48.0", "parsed": (0, 48, 0)},
    )
    monkeypatch.setattr("core.runtime.codex_runtime.log_runtime_capability", lambda entry: None)

    def fake_run(cmd, capture_output, text, timeout, cwd=None):
        captured["cmd"] = cmd
        captured["timeout"] = timeout
        captured["cwd"] = cwd
        stdout = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "abc"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "[]"},
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {"input_tokens": 100, "output_tokens": 10},
                    }
                ),
            ]
        )
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr("core.runtime.codex_runtime.subprocess.run", fake_run)

    result = asyncio.run(runtime.run_review(task))

    assert result.status == "completed"
    assert result.metrics["exit_code"] == 0
    assert captured["timeout"] == 45
    assert "--ask-for-approval" in captured["cmd"]
    assert "never" in captured["cmd"]
    assert "--skip-git-repo-check" in captured["cmd"]
    assert "--sandbox" in captured["cmd"]
    assert "workspace-write" in captured["cmd"]
    assert "--cd" in captured["cmd"]
    assert captured["cwd"] is None


def test_compile_review_task_builds_shared_shadow_metadata():
    task, summary = compile_review_task(
        diff_text=(
            "diff --git a/api/app.py b/api/app.py\n"
            "--- a/api/app.py\n"
            "+++ b/api/app.py\n"
            "@@\n"
            "+print('hello')\n"
        ),
        spec_text="# Build Spec\nKeep review isolated.",
        project_root="/tmp/project",
        commit_sha="deadbeef",
    )

    assert task.task_id == "review-spike-deadbeef"
    assert task.metadata["dispatch_mode"] == "parallel_shadow"
    assert task.metadata["changed_files"] == ["api/app.py"]
    assert summary.file_count == 1


def test_phase1_runtime_registry_describes_registered_runtimes():
    registry = create_phase1_runtime_registry({"backends": {"codex": {"timeout_seconds": 45}}})

    registrations = registry.create_many(["claude", "codex"])

    assert [registration.name for registration in registrations] == ["claude", "codex"]
    assert registrations[0].describe()["dispatch_mode"] == "parallel_shadow"
    assert registrations[1].describe()["capabilities"]["isolated_workspace_only"] is True


def test_runtime_result_to_dict_preserves_finding_dicts():
    result = RuntimeResult(
        task_id="task-1",
        runtime="claude",
        backend="claude-test",
        status="completed",
        findings=[{"finding": "dict finding", "severity": "note", "source": "claude"}],
    )

    payload = result.to_dict()

    assert payload["findings"][0]["finding"] == "dict finding"


@pytest.mark.asyncio
async def test_run_review_spike_async_returns_parallel_shadow_envelopes(monkeypatch):
    class FakeShadowRun:
        task_id = "review-spike-deadbeef"
        shadow_status = "shadow_completed"
        metrics = {"blocker_agreement": 1.0}
        primary_result = RuntimeResult(
            task_id="review-spike-deadbeef",
            runtime="claude",
            backend="claude-test",
            status="completed",
            metadata={"mode": "parallel_shadow"},
        )
        shadow_result = RuntimeResult(
            task_id="review-spike-deadbeef",
            runtime="codex",
            backend="codex-test",
            status="completed",
            metadata={"mode": "parallel_shadow", "isolated": True},
        )

    async def fake_shadow_runner(**kwargs):
        return FakeShadowRun()

    monkeypatch.setattr("core.runtime.shadow_runner.run_shadow_command_async", fake_shadow_runner)

    payload = await cross_model_review.run_review_spike_async(
        diff_text="diff --git a/app.py b/app.py\n+print('hello')\n",
        spec_text="# spec",
        commit_sha="deadbeef",
        project_root="/tmp/project",
        runtimes=["claude", "codex"],
        config={"backends": {"codex": {"timeout_seconds": 30}}},
    )

    assert payload["mode"] == "parallel_shadow"
    assert payload["dispatch_mode"] == "parallel_shadow"
    assert payload["live_routing_changed"] is False
    assert payload["selected_runtimes"][0]["runtime"] == "claude"
    assert payload["task_metadata"]["dispatch_mode"] == "parallel_shadow"
    assert [result["runtime"] for result in payload["results"]] == ["claude", "codex"]
    assert payload["task_metadata"]["shadow_status"] == "shadow_completed"


def test_review_spike_api_route(monkeypatch):
    async def fake_run_review_spike_async(**kwargs):
        return {
            "task_id": "review-spike-deadbeef",
            "mode": "parallel_shadow",
            "dispatch_mode": "parallel_shadow",
            "live_routing_changed": False,
            "selected_runtimes": [{"runtime": "codex", "backend": "codex-cli"}],
            "task_metadata": {"dispatch_mode": "parallel_shadow"},
            "results": [{"runtime": "codex", "status": "completed"}],
        }

    monkeypatch.setattr(
        "core.cluster.cross_model_review.run_review_spike_async",
        AsyncMock(side_effect=fake_run_review_spike_async),
    )

    client = TestClient(app)
    response = client.post(
        "/api/runtime/review-spike",
        json={
            "diff_text": "diff --git a/app.py b/app.py\n+print('hello')\n",
            "spec_text": "# spec",
            "project_root": "/tmp",
            "commit_sha": "deadbeef",
            "runtimes": ["codex"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "parallel_shadow"
    assert payload["dispatch_mode"] == "parallel_shadow"
    assert payload["live_routing_changed"] is False
    assert payload["selected_runtimes"][0]["runtime"] == "codex"
    assert payload["results"][0]["runtime"] == "codex"
