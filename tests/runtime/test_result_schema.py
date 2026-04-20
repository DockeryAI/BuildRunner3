from core.runtime.capabilities import CapabilityProfile
from core.runtime.edit_normalizer import NormalizedEdit
from core.runtime.errors import RuntimeErrorInfo
from core.runtime.result_schema import CheckpointRecord, ObservedChange, StreamEvent
from core.runtime.types import RuntimeResult, RuntimeTask


def test_runtime_task_defaults_conflict_boundary_to_task_id():
    task = RuntimeTask(
        task_id="task-123",
        task_type="review",
        diff_text="diff --git a/a.py b/a.py\n",
        spec_text="# spec",
        project_root="/tmp/project",
        commit_sha="deadbeef",
    )

    payload = task.to_dict()

    assert task.schema_version == "br3.runtime.task.v1"
    assert task.conflict_boundary == "task-123"
    assert payload["schema_version"] == "br3.runtime.task.v1"


def test_runtime_result_serializes_versioned_nested_schema_objects():
    result = RuntimeResult(
        task_id="task-123",
        runtime="codex",
        backend="codex-cli 0.48.0",
        status="completed",
        normalized_edits=[
            NormalizedEdit(
                edit_type="write_file",
                source_runtime="codex",
                path="src/app.py",
                content="print('ok')\n",
            )
        ],
        observed_changes=[ObservedChange(path="src/app.py", change_type="modified", source="workspace_diff")],
        stream_events=[StreamEvent(event_type="progress", sequence=1, message="running")],
        orchestration_checkpoints=[
            CheckpointRecord(
                checkpoint_id="cp-1",
                task_id="task-123",
                runtime="codex",
                status="running",
                current_step="review",
                timestamp="2026-04-16T12:00:00Z",
            )
        ],
        error_info=RuntimeErrorInfo(error_class="RuntimeExecutionError", message="retry", retryable=True),
        capability_profile=CapabilityProfile.from_legacy({"review": True, "shell": True}),
    )

    payload = result.to_dict()

    assert payload["schema_version"] == "br3.runtime.result.v1"
    assert payload["normalized_edits"][0]["edit_type"] == "write_file"
    assert payload["observed_changes"][0]["path"] == "src/app.py"
    assert payload["stream_events"][0]["event_type"] == "progress"
    assert payload["orchestration_checkpoints"][0]["checkpoint_id"] == "cp-1"
    assert payload["error_info"]["retryable"] is True
    assert payload["capability_profile"]["review"] is True
