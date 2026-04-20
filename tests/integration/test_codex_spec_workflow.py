import json
from pathlib import Path

import pytest

from core.runtime.runtime_registry import RuntimeRegistration, RuntimeRegistry
from core.runtime.types import RuntimeResult
from core.runtime.workflows import SpecWorkflowRequest, run_spec_workflow


class FakeCodexRuntime:
    runtime_name = "codex"
    backend_name = "codex-cli"

    async def run_plan(self, task):
        return RuntimeResult(
            task_id=task.task_id,
            runtime="codex",
            backend="codex-cli 0.48.0",
            status="completed",
            raw_output="# Project Spec\n\n### Phase 1: Foundation\n",
            metadata={"command_name": task.metadata.get("command_name")},
        )


def _registry() -> RuntimeRegistry:
    registry = RuntimeRegistry()
    registry.register(RuntimeRegistration(name="codex", adapter=FakeCodexRuntime(), dispatch_mode="direct"))
    return registry


@pytest.mark.asyncio
async def test_spec_workflow_runs_validation_and_adversarial_review(tmp_path: Path):
    project_root = tmp_path
    buildrunner_dir = project_root / ".buildrunner"
    buildrunner_dir.mkdir()
    (buildrunner_dir / "PROJECT_SPEC.md").write_text("# Existing Spec\n", encoding="utf-8")
    (buildrunner_dir / "runtime-command-inventory.md").write_text("# Inventory\n", encoding="utf-8")
    (buildrunner_dir / "runtime-skill-mapping.md").write_text("# Skill Map\n", encoding="utf-8")
    (buildrunner_dir / "builds").mkdir()
    (buildrunner_dir / "builds" / "BUILD_test.md").write_text("# Build\n", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_runner(args: list[str], *, cwd: str):
        calls.append(args)
        if "validate-spec-paths.sh" in args[0]:
            return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        return type(
            "Completed",
            (),
            {"returncode": 0, "stdout": json.dumps([{"finding": "Looks good", "severity": "note"}]), "stderr": ""},
        )()

    result = await run_spec_workflow(
        SpecWorkflowRequest(user_request="Build a guarded spec", project_root=str(project_root)),
        registry=_registry(),
        subprocess_runner=fake_runner,
    )

    assert result.status == "completed"
    assert result.draft_path is not None
    assert Path(result.draft_path).read_text(encoding="utf-8").startswith("# Project Spec")
    assert len(calls) == 2
    assert result.adversarial_findings[0]["severity"] == "note"


@pytest.mark.asyncio
async def test_spec_workflow_blocks_on_validation_failure(tmp_path: Path):
    project_root = tmp_path
    buildrunner_dir = project_root / ".buildrunner"
    buildrunner_dir.mkdir()
    (buildrunner_dir / "PROJECT_SPEC.md").write_text("# Existing Spec\n", encoding="utf-8")
    (buildrunner_dir / "runtime-command-inventory.md").write_text("# Inventory\n", encoding="utf-8")
    (buildrunner_dir / "runtime-skill-mapping.md").write_text("# Skill Map\n", encoding="utf-8")
    (buildrunner_dir / "builds").mkdir()
    (buildrunner_dir / "builds" / "BUILD_test.md").write_text("# Build\n", encoding="utf-8")

    def fake_runner(args: list[str], *, cwd: str):
        return type("Completed", (), {"returncode": 1, "stdout": "", "stderr": "BLOCKER"})()

    result = await run_spec_workflow(
        SpecWorkflowRequest(user_request="Build a guarded spec", project_root=str(project_root)),
        registry=_registry(),
        subprocess_runner=fake_runner,
    )

    assert result.status == "validation_failed"
    assert result.validation_exit_code == 1
    assert "validation" in result.notes[0].lower()
