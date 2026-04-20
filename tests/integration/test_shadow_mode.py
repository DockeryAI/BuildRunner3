from pathlib import Path

import pytest

from core.runtime.shadow_runner import (
    ShadowRun,
    compute_shadow_metrics,
    run_shadow_command_async,
    update_shadow_metrics_doc,
)
from core.runtime.types import RuntimeResult


def make_result(runtime: str, *, status: str = "completed", duration_ms: int = 10, findings=None):
    return RuntimeResult(
        task_id="task-1",
        runtime=runtime,
        backend=f"{runtime}-backend",
        status=status,
        findings=findings or [],
        metrics={"duration_ms": duration_ms},
        metadata={"mode": "parallel_shadow"},
    )


def test_compute_shadow_metrics_tracks_overlap():
    primary = make_result(
        "claude",
        findings=[{"finding": "shared blocker", "severity": "blocker", "source": "claude"}],
    )
    shadow = make_result(
        "codex",
        findings=[{"finding": "shared blocker", "severity": "blocker", "source": "codex"}],
    )

    metrics = compute_shadow_metrics(primary, shadow)

    assert metrics["blocker_agreement"] == 1.0
    assert metrics["blocker_overlap_count"] == 1


@pytest.mark.asyncio
async def test_run_shadow_command_async_logs_and_writes_metrics(monkeypatch, tmp_path):
    from core.runtime import shadow_runner

    shadow_log = tmp_path / "runtime-shadow.log"
    monkeypatch.setattr(shadow_runner, "SHADOW_LOG_PATH", shadow_log)

    class FakeAdapter:
        def __init__(self, runtime):
            self.runtime_name = runtime

        async def run_review(self, task):
            return make_result(
                self.runtime_name,
                duration_ms=25 if self.runtime_name == "claude" else 40,
                findings=[{"finding": "shared blocker", "severity": "blocker", "source": self.runtime_name}],
            )

    class FakeRegistration:
        def __init__(self, name):
            self.name = name
            self.adapter = FakeAdapter(name)

    class FakeRegistry:
        def get(self, name):
            return FakeRegistration(name)

    monkeypatch.setattr(shadow_runner, "create_runtime_registry", lambda config=None: FakeRegistry())

    result = await run_shadow_command_async(
        diff_text="diff --git a/app.py b/app.py\n+++ b/app.py\n+print('shadow')\n",
        spec_text="# Build Spec\nReview only.",
        project_root=str(tmp_path),
        commit_sha="deadbeef",
        command_name="review",
        config={},
    )

    assert result.shadow_status == "shadow_completed"
    assert shadow_log.exists()
    metrics_doc = Path(tmp_path) / ".buildrunner" / "runtime-shadow-metrics.md"
    assert metrics_doc.exists()
    assert "Total runs: 1" in metrics_doc.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_run_shadow_command_async_respects_kill_switch(monkeypatch, tmp_path):
    from core.runtime import shadow_runner

    monkeypatch.setenv("BR3_DISABLE_CODEX_SHADOW", "1")
    monkeypatch.setattr(shadow_runner, "SHADOW_LOG_PATH", tmp_path / "runtime-shadow.log")

    class FakeAdapter:
        async def run_review(self, task):
            return make_result("claude", duration_ms=20)

    class FakeRegistry:
        def get(self, name):
            return type("Registration", (), {"name": name, "adapter": FakeAdapter()})()

    monkeypatch.setattr(shadow_runner, "create_runtime_registry", lambda config=None: FakeRegistry())

    result = await run_shadow_command_async(
        diff_text="diff --git a/app.py b/app.py\n+++ b/app.py\n+print('shadow')\n",
        spec_text="# Build Spec\nReview only.",
        project_root=str(tmp_path),
        commit_sha="deadbeef",
        command_name="review",
        config={},
    )

    assert result.shadow_status == "shadow_skipped"
    assert result.shadow_result is None


@pytest.mark.asyncio
async def test_run_shadow_command_async_preserves_primary_when_shadow_fails(monkeypatch, tmp_path):
    from core.runtime import shadow_runner

    monkeypatch.setattr(shadow_runner, "SHADOW_LOG_PATH", tmp_path / "runtime-shadow.log")

    class FakeAdapter:
        def __init__(self, runtime):
            self.runtime_name = runtime

        async def run_review(self, task):
            if self.runtime_name == "codex":
                raise RuntimeError("shadow failure")
            return make_result("claude", duration_ms=15)

    class FakeRegistry:
        def get(self, name):
            return type("Registration", (), {"name": name, "adapter": FakeAdapter(name)})()

    monkeypatch.setattr(shadow_runner, "create_runtime_registry", lambda config=None: FakeRegistry())

    result = await run_shadow_command_async(
        diff_text="diff --git a/app.py b/app.py\n+++ b/app.py\n+print('shadow')\n",
        spec_text="# Build Spec\nReview only.",
        project_root=str(tmp_path),
        commit_sha="deadbeef",
        command_name="review",
        config={"shadow": {"timeout_seconds": 1}},
    )

    assert result.primary_result.runtime == "claude"
    assert result.shadow_result is not None
    assert result.shadow_result.error_class == "RuntimeError"
    assert result.shadow_status == "shadow_failed"
