import json
from pathlib import Path

import pytest

from core.runtime.runtime_registry import RuntimeRegistration, RuntimeRegistry
from core.runtime.types import RuntimeResult
from core.runtime.workflows import BeginWorkflowRequest, run_begin_workflow


class FakeCodexRuntime:
    runtime_name = "codex"
    backend_name = "codex-cli"

    def __init__(self):
        self.execution_prompts: list[str] = []

    def get_capabilities(self):
        return {
            "review": True,
            "analysis": False,
            "plan": True,
            "execution": True,
            "streaming": True,
            "shell": True,
            "browser": False,
            "subagents": False,
            "orchestration_checkpoint": False,
        }

    async def run_execution_step(self, task):
        self.execution_prompts.append(task.spec_text)
        return RuntimeResult(
            task_id=task.task_id,
            runtime="codex",
            backend="codex-cli 0.48.0",
            status="completed",
            raw_output="phase complete",
            metadata={"phase_number": task.metadata.get("phase_number")},
        )


def _registry(runtime: FakeCodexRuntime) -> RuntimeRegistry:
    registry = RuntimeRegistry()
    registry.register(RuntimeRegistration(name="codex", adapter=runtime, dispatch_mode="direct"))
    return registry


def _write_build(project_root: Path, content: str) -> Path:
    build_path = project_root / ".buildrunner" / "builds" / "BUILD_test.md"
    build_path.parent.mkdir(parents=True, exist_ok=True)
    build_path.write_text(content, encoding="utf-8")
    return build_path


def _write_plan(project_root: Path, phase_number: int) -> None:
    plan_path = project_root / ".buildrunner" / "plans" / f"phase-{phase_number}-plan.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(f"# Phase {phase_number} Plan\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_begin_workflow_runs_bounded_phases_and_cleans_locks(tmp_path: Path):
    runtime = FakeCodexRuntime()
    project_root = tmp_path
    build_path = _write_build(
        project_root,
        """# Build

### Phase 1: Adapter
**Status:** pending
**Files to MODIFY:**
- `core/runtime/base.py`

### Phase 2: Workflow
**Status:** not_started
**Files to CREATE:**
- `core/runtime/workflows/begin_workflow.py`
""",
    )
    _write_plan(project_root, 1)
    _write_plan(project_root, 2)

    result = await run_begin_workflow(
        BeginWorkflowRequest(
            user_request="Run bounded begin",
            project_root=str(project_root),
            build_path=str(build_path),
            approval_granted=True,
            max_phases=2,
        ),
        registry=_registry(runtime),
    )

    assert result.status == "completed"
    assert [item.status for item in result.phase_results] == ["completed", "completed"]
    updated_build = build_path.read_text(encoding="utf-8")
    assert updated_build.count("**Status:** ✅ COMPLETE") == 2
    assert not (project_root / ".buildrunner" / "locks" / "phase-1").exists()
    assert not (project_root / ".buildrunner" / "locks" / "phase-2").exists()
    current_phase = json.loads((project_root / ".buildrunner" / "current-phase.json").read_text(encoding="utf-8"))
    assert current_phase["phase"] == 2
    assert "Execute only the single phase below." in runtime.execution_prompts[0]


@pytest.mark.asyncio
async def test_begin_workflow_hands_off_unsupported_phase_to_claude(tmp_path: Path):
    runtime = FakeCodexRuntime()
    project_root = tmp_path
    build_path = _write_build(
        project_root,
        """# Build

### Phase 1: Browser Research
**Status:** pending
**Files to MODIFY:**
- `notes.md`

**Deliverables:**
- Use browser research and ask user to pick one of three designs.
""",
    )
    _write_plan(project_root, 1)

    result = await run_begin_workflow(
        BeginWorkflowRequest(
            user_request="Run bounded begin",
            project_root=str(project_root),
            build_path=str(build_path),
            approval_granted=True,
        ),
        registry=_registry(runtime),
    )

    assert result.status == "handoff_required"
    assert result.phase_results[0].status == "handoff_required"
    assert result.phase_results[0].gate["decision"] == "handoff_to_claude"
    assert "browser" in result.phase_results[0].gate["unsupported"]
    assert runtime.execution_prompts == []
    assert "**Status:** pending" in build_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_begin_workflow_requires_explicit_approval_before_locking(tmp_path: Path):
    runtime = FakeCodexRuntime()
    build_path = _write_build(
        tmp_path,
        """# Build

### Phase 1: Adapter
**Status:** pending
**Files to MODIFY:**
- `core/runtime/base.py`
""",
    )

    result = await run_begin_workflow(
        BeginWorkflowRequest(
            user_request="Run bounded begin",
            project_root=str(tmp_path),
            build_path=str(build_path),
            approval_granted=False,
        ),
        registry=_registry(runtime),
    )

    assert result.status == "approval_required"
    assert not (tmp_path / ".buildrunner" / "locks").exists()
