import json

from core.runtime import postflight, preflight
from core.runtime import (
    RuntimeResult,
    RuntimeTask,
    build_recall_query,
    collect_session_snapshot,
    evaluate_build_gates,
    evaluate_prompt_file,
    evaluate_protected_files,
    evaluate_runtime_alerts,
    evaluate_runtime_task_postflight,
    evaluate_runtime_task_preflight,
    is_protected_file,
)


def make_task(**overrides) -> RuntimeTask:
    payload = {
        "task_id": "task-1",
        "task_type": "review",
        "diff_text": "diff --git a/app.py b/app.py\n+++ b/app.py\n+print('hi')\n",
        "spec_text": "# Build Spec\nKeep review isolated.",
        "project_root": "/tmp/project",
        "commit_sha": "deadbeef",
        "metadata": {"changed_files": ["app.py"], "command_name": "review"},
    }
    payload.update(overrides)
    return RuntimeTask(**payload)


def test_shared_preflight_blocks_protected_files_for_both_runtimes():
    task = make_task(metadata={"changed_files": [".env"], "command_name": "review"})

    claude = evaluate_runtime_task_preflight(task, "claude")
    codex = evaluate_runtime_task_preflight(task, "codex")

    assert claude.blocked is True
    assert codex.blocked is True
    assert claude.results[0].details["files"] == [".env"]
    assert codex.results[0].details["files"] == [".env"]


def test_shared_preflight_blocks_codex_on_claude_first_command_only():
    task = make_task(task_type="review", metadata={"changed_files": [], "command_name": "spec"})

    claude = evaluate_runtime_task_preflight(task, "claude")
    codex = evaluate_runtime_task_preflight(task, "codex")

    assert claude.blocked is False
    assert codex.blocked is True
    assert any(result.policy_id == "runtime_command_gate" for result in codex.results)


def test_shared_preflight_allows_shadow_safe_review_command(monkeypatch):
    monkeypatch.setattr(preflight, "load_claude_first_commands", lambda: {"review"})
    task = make_task(metadata={"changed_files": [], "command_name": "review", "dispatch_mode": "parallel_shadow"})

    codex = evaluate_runtime_task_preflight(task, "codex")

    assert codex.blocked is False


def test_shared_preflight_still_blocks_claude_first_command_in_shadow_mode():
    task = make_task(metadata={"changed_files": [], "command_name": "spec", "dispatch_mode": "parallel_shadow"})

    codex = evaluate_runtime_task_preflight(task, "codex")

    assert codex.blocked is True


def test_build_gates_block_new_phase_without_review_artifact(tmp_path):
    project_root = tmp_path / "project"
    (project_root / ".buildrunner" / "builds").mkdir(parents=True)

    evaluation = evaluate_build_gates(
        file_path=str(project_root / ".buildrunner" / "builds" / "BUILD_test.md"),
        old_string="### Phase 1\n**Status:** pending\n",
        new_string="### Phase 1\n**Status:** pending\n### Phase 2\n**Status:** pending\n",
        project_dir=str(project_root),
    )

    assert evaluation.blocked is True
    assert evaluation.results[0].policy_id == "build_amend_review_gate"


def test_build_gates_block_when_skill_state_json_is_malformed(tmp_path):
    project_root = tmp_path / "project"
    build_path = project_root / ".buildrunner" / "builds" / "BUILD_test.md"
    build_path.parent.mkdir(parents=True)
    (project_root / ".buildrunner" / "skill-state.json").write_text("{not-json", encoding="utf-8")

    evaluation = evaluate_build_gates(
        file_path=str(build_path),
        old_string="",
        new_string="## Overview\nNew build\n",
        project_dir=str(project_root),
    )

    assert evaluation.blocked is True
    assert "Failed reading skill-state.json" in evaluation.results[0].message


def test_shared_postflight_evaluates_alerts_and_shadow_advisory_only():
    task = make_task(metadata={"changed_files": ["app.py"], "command_name": "review", "shadow_role": "secondary"})
    result = RuntimeResult(
        task_id=task.task_id,
        runtime="codex",
        backend="codex-cli 0.48.0",
        status="completed",
        metadata={
            "runtime_alerts": [{"severity": "warning", "message": "shadow mismatch"}],
            "session_snapshot": {"project": "demo"},
        },
    )

    evaluation = evaluate_runtime_task_postflight(task, result)

    assert evaluation.blocked is False
    assert any(result.policy_id == "runtime_alerts" for result in evaluation.results)
    assert any(result.policy_id == "shadow_advisory_only" for result in evaluation.results)


def test_shared_postflight_blocks_shadow_mutations():
    task = make_task(metadata={"changed_files": ["app.py"], "command_name": "review", "shadow_role": "secondary"})
    result = RuntimeResult(
        task_id=task.task_id,
        runtime="codex",
        backend="codex-cli 0.48.0",
        status="completed",
        normalized_edits=[{"type": "write_file", "path": "app.py"}],
        metadata={"session_snapshot": {"project": "demo"}},
    )

    evaluation = evaluate_runtime_task_postflight(task, result)

    assert evaluation.blocked is True
    shadow_result = next(item for item in evaluation.results if item.policy_id == "shadow_advisory_only")
    assert shadow_result.action == "block"


def test_shared_postflight_blocks_when_formatting_status_is_block():
    task = make_task(diff_text="")
    result = RuntimeResult(
        task_id=task.task_id,
        runtime="codex",
        backend="codex-cli 0.48.0",
        status="completed",
        workspace_diff="diff --git a/app.py b/app.py\n+++ b/app.py\n+print('hi')\n",
        metadata={"formatting_status": "block", "session_snapshot": {"project": "demo"}},
    )

    evaluation = evaluate_runtime_task_postflight(task, result)

    formatting_result = next(item for item in evaluation.results if item.policy_id == "formatting")
    assert formatting_result.action == "block"
    assert evaluation.blocked is True


def test_shared_postflight_uses_task_diff_when_workspace_diff_is_empty():
    task = make_task(diff_text="diff --git a/app.py b/app.py\n+++ b/app.py\n+print('hi')  \n")
    result = RuntimeResult(
        task_id=task.task_id,
        runtime="codex",
        backend="codex-cli 0.48.0",
        status="completed",
        workspace_diff="",
        metadata={"session_snapshot": {"project": "demo"}},
    )

    evaluation = evaluate_runtime_task_postflight(task, result)

    formatting_result = next(item for item in evaluation.results if item.policy_id == "formatting")
    assert formatting_result.action == "warn"
    assert formatting_result.details["patch_lines"] == [3]


def test_evaluate_protected_files_reports_multiple_protected_paths():
    evaluation = evaluate_protected_files([".env", "config/secrets.yaml", "id_rsa_backup"])

    protected_result = next(item for item in evaluation.results if item.policy_id == "protected_files")
    assert protected_result.action == "block"
    assert protected_result.details["files"] == sorted([".env", "config/secrets.yaml", "id_rsa_backup"])


def test_is_protected_file_applies_basename_patterns_without_matching_parent_dirs():
    assert is_protected_file("/tmp/.env.local") is True
    assert is_protected_file("/tmp/.env.local/config.py") is False


def test_load_claude_first_commands_prefers_inventory_when_present(tmp_path, monkeypatch):
    inventory_path = tmp_path / ".buildrunner" / "runtime-command-inventory.json"
    inventory_path.parent.mkdir(parents=True)
    inventory_path.write_text(
        json.dumps(
            {
                "commands": [
                    {"name": "review", "portability_rating": "claude_first"},
                    {"command": "/spec", "migration_bucket": "keep-Claude-first"},
                    {"name": "build", "fallback_runtime": "claude"},
                    {"name": "ignore-me", "portability_rating": "codex_first"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(preflight, "load_claude_first_commands", preflight.load_claude_first_commands.__wrapped__)
    monkeypatch.setattr(preflight, "_inventory_path", lambda: inventory_path)

    commands = preflight.load_claude_first_commands()

    assert commands == {"build", "review", "spec"}


def test_collect_session_snapshot_and_build_recall_query_capture_context(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    (project_root / ".buildrunner" / "builds").mkdir(parents=True)
    (project_root / ".buildrunner" / "current-phase.json").write_text(
        json.dumps({"name": "Phase 6"}),
        encoding="utf-8",
    )
    build_file = project_root / ".buildrunner" / "builds" / "BUILD_test.md"
    build_file.write_text("# test\n", encoding="utf-8")

    commands: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        commands.append(tuple(command))
        responses = {
            ("git", "branch", "--show-current"): "codex/phase-6\n",
            ("git", "log", "-1", "--oneline"): "abc123 phase 6\n",
            ("git", "diff", "--name-only", "HEAD~1"): "core/runtime/preflight.py\n",
            ("git", "diff", "--cached", "--name-only"): "supabase/migrations/001.sql\n",
        }
        stdout = responses.get(tuple(command), "")
        return type("Completed", (), {"stdout": stdout, "returncode": 0})()

    original_run = postflight.subprocess.run
    postflight.subprocess.run = fake_run
    try:
        snapshot = collect_session_snapshot(str(project_root), "summary")
    finally:
        postflight.subprocess.run = original_run

    assert snapshot["branch"] == "codex/phase-6"
    assert snapshot["last_commit"] == "abc123 phase 6"
    assert snapshot["changed_files"] == ["core/runtime/preflight.py"]
    assert snapshot["build_name"] == "BUILD_test"
    assert snapshot["phase"] == "Phase 6"
    assert snapshot["high_risk_files"] == ["supabase/migrations/001.sql"]
    assert ("git", "diff", "--cached", "--name-only") in commands

    recall = build_recall_query("supabase/functions/user-sync/index.ts")
    assert recall["query"] == "functions user-sync index index.ts supabase edge function"


def test_read_alert_file_rotates_processing_file(tmp_path):
    alert_file = tmp_path / "pending-alerts.jsonl"
    alert_file.write_text('{"severity":"warning","message":"test"}\n', encoding="utf-8")

    alerts = postflight._read_alert_file(alert_file)

    assert alerts == [{"severity": "warning", "message": "test"}]
    assert not alert_file.exists()
    processed_files = list(tmp_path.glob("pending-alerts.jsonl.processing.*.processed"))
    assert len(processed_files) == 1


def test_read_alert_file_falls_back_to_original_when_replace_fails(tmp_path, monkeypatch):
    alert_file = tmp_path / "pending-alerts.jsonl"
    alert_file.write_text('{"severity":"warning","message":"test"}\n', encoding="utf-8")
    original_replace = type(alert_file).replace

    def fake_replace(self, target):
        if self == alert_file:
            raise OSError("simulated rename failure")
        return original_replace(self, target)

    monkeypatch.setattr(type(alert_file), "replace", fake_replace)

    alerts = postflight._read_alert_file(alert_file)

    assert alerts == [
        {
            "severity": "critical",
            "message": "Pending alert file could not be locked for processing; retry required.",
            "file": str(alert_file),
        }
    ]
    assert alert_file.exists()


def test_runtime_alert_evaluation_blocks_on_critical_alert():
    evaluation = evaluate_runtime_alerts(
        [{"severity": "critical", "message": "runtime failed closed"}]
    )

    assert evaluation.blocked is True
    assert evaluation.results[0].action == "block"


def test_prompt_file_evaluation_warns_on_prompt_markers():
    evaluation = evaluate_prompt_file(
        "/tmp/system-prompt.md",
        "<identity>You are a headless build executor</identity>",
    )

    assert evaluation.warning_count == 1
    assert evaluation.additional_context
