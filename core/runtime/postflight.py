"""Shared BR3 runtime postflight policy extraction."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.runtime.policy_result import (
    POLICY_ACTION_BLOCK,
    POLICY_ACTION_PASS,
    POLICY_ACTION_WARN,
    PolicyEvaluation,
    build_hook_payload,
)
from core.runtime.types import RuntimeResult, RuntimeTask


HIGH_RISK_DIFF_PATTERN = (
    r"supabase/migrations/|\.sql$|/auth/|/payments/|rls|policies|edge.*functions.*db"
)


def evaluate_runtime_alerts(alerts: list[dict[str, Any]]) -> PolicyEvaluation:
    evaluation = PolicyEvaluation(stage="postflight")
    if not alerts:
        evaluation.add(
            policy_id="runtime_alerts",
            action=POLICY_ACTION_PASS,
            message="No pending runtime alerts.",
        )
        return evaluation

    max_action = POLICY_ACTION_WARN
    if any(str(alert.get("severity", "")).lower() in {"critical", "block"} for alert in alerts):
        max_action = POLICY_ACTION_BLOCK
    evaluation.add(
        policy_id="runtime_alerts",
        action=max_action,
        message="Pending runtime alerts require operator attention.",
        details={"alerts": alerts},
    )
    formatted = "\n".join(json.dumps(alert, sort_keys=True) for alert in alerts)
    evaluation.extend_context(
        "RUNTIME ALERT from BR3. Review and resolve the active failure before continuing.",
        formatted,
    )
    return evaluation


def list_high_risk_staged_files(project_dir: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []

    files = []
    for line in result.stdout.splitlines():
        path = line.strip()
        if path and re.search(HIGH_RISK_DIFF_PATTERN, path, flags=re.IGNORECASE):
            files.append(path)
    return files


def collect_session_snapshot(project_dir: str, summary_text: str | None = None) -> dict[str, Any]:
    project_path = Path(project_dir)

    def _git(*args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            return (result.stdout or "").strip()
        except Exception:
            return ""

    branch = _git("branch", "--show-current") or "unknown"
    last_commit = _git("log", "-1", "--oneline") or "none"
    changed_files_output = _git("diff", "--name-only", "HEAD~1")
    if not changed_files_output:
        changed_files_output = _git("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD")
    changed_files = changed_files_output.splitlines()
    changed_files = [item for item in changed_files if item][:20]
    build_dir = project_path / ".buildrunner" / "builds"
    latest_build = ""
    if build_dir.exists():
        builds = sorted(build_dir.glob("BUILD_*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
        if builds:
            latest_build = builds[0].stem
    phase_name = ""
    current_phase_file = project_path / ".buildrunner" / "current-phase.json"
    if current_phase_file.exists():
        try:
            phase_name = json.loads(current_phase_file.read_text(encoding="utf-8")).get("name", "")
        except Exception:
            phase_name = ""

    narrative = summary_text or (
        f"Last commit: {last_commit} | Branch: {branch} | Changed: {', '.join(changed_files)} | "
        f"Build: {latest_build}"
    )
    return {
        "project": project_path.name.lower(),
        "project_dir": str(project_path),
        "branch": branch,
        "last_commit": last_commit,
        "changed_files": changed_files,
        "build_name": latest_build,
        "phase": phase_name,
        "narrative": narrative,
        "high_risk_files": list_high_risk_staged_files(project_dir),
    }


def build_recall_query(file_path: str) -> dict[str, str]:
    path = Path(file_path)
    base = path.name
    parent = path.parent.name if path.parent.name not in {"", ".", "src", "components", "lib"} else ""
    grandparent = (
        path.parent.parent.name
        if path.parent.parent.name not in {"", ".", "src"}
        else ""
    )
    terms = [item for item in [grandparent, parent, path.stem.replace("-", " ").replace("_", " "), base] if item]
    if "supabase/functions" in file_path.replace("\\", "/"):
        terms.append("supabase edge function")
    return {"file": file_path, "query": " ".join(terms).strip()}


def evaluate_runtime_task_postflight(task: RuntimeTask, result: RuntimeResult) -> PolicyEvaluation:
    evaluation = PolicyEvaluation(stage="postflight")
    effective_diff = result.workspace_diff if result.workspace_diff.strip() else task.diff_text

    alerts = []
    alerts.extend(task.metadata.get("runtime_alerts", []) or [])
    alerts.extend(result.metadata.get("runtime_alerts", []) or [])
    alert_eval = evaluate_runtime_alerts(alerts)
    evaluation.results.extend(alert_eval.results)
    evaluation.additional_context.extend(alert_eval.additional_context)

    formatting_status = result.metadata.get("formatting_status") or task.metadata.get("formatting_status")
    if not effective_diff.strip():
        evaluation.add(
            policy_id="formatting",
            action=POLICY_ACTION_PASS,
            message="Formatting gate skipped because no runtime diff was available.",
        )
    else:
        added_lines: list[tuple[int, str]] = [
            (index + 1, line[1:])
            for index, line in enumerate(effective_diff.splitlines())
            if line.startswith("+") and not line.startswith("+++")
        ]
        trailing_whitespace_lines = [
            line_number for line_number, line in added_lines if line.rstrip() != line
        ]
        if trailing_whitespace_lines:
            evaluation.add(
                policy_id="formatting",
                action=POLICY_ACTION_WARN,
                message="Added patch lines contain trailing whitespace.",
                details={"patch_lines": trailing_whitespace_lines},
            )
        elif formatting_status in {"warn", "warning"}:
            evaluation.add(
                policy_id="formatting",
                action=POLICY_ACTION_WARN,
                message="Formatting follow-up is still required.",
            )
        elif formatting_status == "block":
            evaluation.add(
                policy_id="formatting",
                action=POLICY_ACTION_BLOCK,
                message="Formatting requirements failed the shared postflight gate.",
            )
        else:
            evaluation.add(
                policy_id="formatting",
                action=POLICY_ACTION_PASS,
                message="Formatting gate passed or was not required.",
            )

    session_snapshot = result.metadata.get("session_snapshot") or task.metadata.get("session_snapshot") or {}
    if not isinstance(session_snapshot, dict):
        session_snapshot = {}
    high_risk_files = session_snapshot.get("high_risk_files") or []
    if high_risk_files:
        evaluation.add(
            policy_id="high_risk_diff",
            action=POLICY_ACTION_WARN,
            message="High-risk staged files were detected in the shared postflight snapshot.",
            details={"files": high_risk_files},
        )
    else:
        evaluation.add(
            policy_id="high_risk_diff",
            action=POLICY_ACTION_PASS,
            message="No high-risk staged files detected in the shared postflight snapshot.",
        )

    if task.metadata.get("shadow_role") == "secondary":
        normalized_edits = result.normalized_edits if isinstance(result.normalized_edits, list) else []
        has_mutation = any(isinstance(edit, dict) for edit in normalized_edits) or bool(
            result.workspace_diff.strip()
        )
        action = POLICY_ACTION_BLOCK if has_mutation else POLICY_ACTION_PASS
        evaluation.add(
            policy_id="shadow_advisory_only",
            action=action,
            message=(
                "Shadow execution attempted file mutations."
                if has_mutation
                else "Shadow execution remained advisory-only."
            ),
        )
    else:
        evaluation.add(
            policy_id="shadow_advisory_only",
            action=POLICY_ACTION_PASS,
            message="Task is not running as a shadow secondary runtime.",
        )

    if result.metadata.get("session_snapshot"):
        evaluation.add(
            policy_id="session_persistence",
            action=POLICY_ACTION_PASS,
            message="Session snapshot metadata captured.",
        )
    else:
        evaluation.add(
            policy_id="session_persistence",
            action=POLICY_ACTION_WARN,
            message="Session snapshot metadata was not attached to the runtime result.",
        )

    return evaluation


def emit_hook_json(message: str, event_name: str = "PostToolUse") -> None:
    print(json.dumps(build_hook_payload(message, event_name)))


def _read_alert_file(alert_file: Path) -> list[dict[str, Any]]:
    if not alert_file.exists() or alert_file.stat().st_size == 0:
        return []
    try:
        processing_file = alert_file.with_name(f"{alert_file.name}.processing.{os.getpid()}")
        try:
            alert_file.replace(processing_file)
        except OSError:
            return [
                {
                    "severity": "critical",
                    "message": "Pending alert file could not be locked for processing; retry required.",
                    "file": str(alert_file),
                }
            ]
        lines = [line for line in processing_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        alerts: list[dict[str, Any]] = []
        for line in lines:
            try:
                alerts.append(json.loads(line))
            except json.JSONDecodeError:
                alerts.append(
                    {
                        "severity": "critical",
                        "message": "Pending alert file contained malformed JSON and requires cleanup.",
                        "file": str(alert_file),
                    }
                )
                break
        if processing_file.exists() and processing_file != alert_file:
            processed_file = processing_file.with_name(f"{processing_file.name}.processed")
            processing_file.replace(processed_file)
            processed_files = sorted(processed_file.parent.glob(f"{alert_file.name}.processing.*.processed"))
            for old_file in processed_files[:-5]:
                old_file.unlink(missing_ok=True)
    except Exception:
        return []
    return alerts


def _handle_runtime_alerts(alert_file: str | None) -> int:
    alerts = _read_alert_file(Path(alert_file or Path.home() / ".buildrunner" / "pending-alerts.jsonl"))
    evaluation = evaluate_runtime_alerts(alerts)
    if evaluation.additional_context:
        emit_hook_json("\n\n".join(evaluation.additional_context))
    return 0


def _handle_session_snapshot(project_dir: str | None) -> int:
    target = project_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    print(json.dumps(collect_session_snapshot(target), indent=2))
    return 0


def _handle_recall_query(file_path: str | None) -> int:
    if not file_path:
        payload = json.loads(sys.stdin.read() or "{}")
        file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path:
        print("{}")
        return 0
    print(json.dumps(build_recall_query(file_path)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared BR3 runtime postflight policies")
    subparsers = parser.add_subparsers(dest="command")

    runtime_alerts = subparsers.add_parser("runtime-alerts")
    runtime_alerts.add_argument("--alert-file")

    session_snapshot = subparsers.add_parser("session-snapshot")
    session_snapshot.add_argument("--project-dir")

    recall_query = subparsers.add_parser("recall-query")
    recall_query.add_argument("--file-path")

    args = parser.parse_args()
    if args.command == "runtime-alerts":
        return _handle_runtime_alerts(args.alert_file)
    if args.command == "session-snapshot":
        return _handle_session_snapshot(args.project_dir)
    if args.command == "recall-query":
        return _handle_recall_query(args.file_path)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
