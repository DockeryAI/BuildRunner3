from pathlib import Path

from core.runtime.command_compiler import compile_command_bundle, load_command_capabilities
from core.runtime.context_compiler import compile_command_task
from core.runtime.preflight import evaluate_runtime_task_preflight


def test_compile_command_bundle_for_spec_uses_workflow_only_support():
    bundle = compile_command_bundle(
        command_name="spec",
        runtime="codex",
        project_root=Path(__file__).resolve().parents[2],
        user_request="Plan a guarded Codex /spec run",
    )

    assert bundle.command_name == "spec"
    assert bundle.support_level == "codex_workflow_only"
    assert bundle.workflow_name == "spec_workflow"
    assert any(skill.target_name == "br3-planning" for skill in bundle.skill_mappings)
    assert any(item.path == ".buildrunner/runtime-command-inventory.md" for item in bundle.context_files)
    assert "Strategic Project Spec" in bundle.command_doc


def test_compile_command_task_sets_workflow_metadata_for_preflight():
    task, summary = compile_command_task(
        command_name="spec",
        runtime="codex",
        project_root=Path(__file__).resolve().parents[2],
        user_request="Draft a BUILD spec",
        metadata={"workflow_name": "spec_workflow"},
    )

    evaluation = evaluate_runtime_task_preflight(task, "codex")
    assert not evaluation.blocked
    assert summary.support_level == "codex_workflow_only"
    assert task.metadata["workflow_name"] == "spec_workflow"
    assert task.metadata["command_name"] == "spec"


def test_direct_codex_spec_task_is_still_blocked_without_workflow_marker():
    task, _ = compile_command_task(
        command_name="spec",
        runtime="codex",
        project_root=Path(__file__).resolve().parents[2],
        user_request="Draft a BUILD spec",
    )
    task.metadata.pop("workflow_name", None)

    evaluation = evaluate_runtime_task_preflight(task, "codex")
    assert evaluation.blocked
    assert any("BR3-owned workflow" in result.message for result in evaluation.results)


def test_command_capability_map_preserves_begin_as_claude_only():
    capabilities = load_command_capabilities()

    assert capabilities["commands"]["begin"]["support_level"] == "codex_workflow_only"
    assert capabilities["commands"]["begin"]["workflow_name"] == "begin_workflow"


def test_compile_command_task_sets_begin_workflow_metadata_for_preflight():
    task, summary = compile_command_task(
        command_name="begin",
        runtime="codex",
        project_root=Path(__file__).resolve().parents[2],
        user_request="Run a bounded begin workflow",
        task_type="execution",
        metadata={"workflow_name": "begin_workflow"},
    )

    evaluation = evaluate_runtime_task_preflight(task, "codex")
    assert not evaluation.blocked
    assert summary.support_level == "codex_workflow_only"
    assert task.metadata["workflow_name"] == "begin_workflow"


def test_direct_codex_begin_task_is_blocked_without_workflow_marker():
    task, _ = compile_command_task(
        command_name="begin",
        runtime="codex",
        project_root=Path(__file__).resolve().parents[2],
        user_request="Run a bounded begin workflow",
        task_type="execution",
    )
    task.metadata.pop("workflow_name", None)

    evaluation = evaluate_runtime_task_preflight(task, "codex")
    assert evaluation.blocked
    assert any("BR3-owned workflow" in result.message for result in evaluation.results)
