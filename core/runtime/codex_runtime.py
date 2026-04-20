"""Isolated Codex runtime wrapper for the Phase 1 review spike."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
import time
from pathlib import Path

from core.cluster.cross_model_review import (
    build_review_prompt,
    check_codex_auth,
    ensure_codex_compatible,
    extract_codex_message_and_usage,
    log_runtime_capability,
    parse_codex_event_stream,
    parse_findings,
)
from core.runtime.base import BaseRuntime
from core.runtime.policy_result import POLICY_ACTION_BLOCK
from core.runtime.types import RuntimeFinding, RuntimeResult, RuntimeTask


class CodexRuntime(BaseRuntime):
    """Run Codex review in an isolated temp workspace without touching the live repo."""

    runtime_name = "codex"
    backend_name = "codex-cli"

    def __init__(self, command: str = "codex", timeout_seconds: int = 60):
        self.command = command
        self.timeout_seconds = timeout_seconds

    def get_capabilities(self) -> dict[str, object]:
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
            "cluster_suitable": True,
            "isolated_workspace_only": True,
            "edit_formats": ["unified_diff", "shell_action", "advisory_only"],
            "json_events": True,
        }

    async def run_review(self, task: RuntimeTask) -> RuntimeResult:
        return await asyncio.to_thread(self._run_review_blocking, task)

    async def run_plan(self, task: RuntimeTask) -> RuntimeResult:
        return await asyncio.to_thread(self._run_plan_blocking, task)

    async def run_execution_step(self, task: RuntimeTask) -> RuntimeResult:
        return await asyncio.to_thread(self._run_execution_blocking, task)

    def _run_review_blocking(self, task: RuntimeTask) -> RuntimeResult:
        start = time.time()
        exit_code = None
        errors = self.validate_task(task)
        if errors:
            duration_ms = int((time.time() - start) * 1000)
            return RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend=self.backend_name,
                status="error",
                error_class="ValueError",
                error_message="; ".join(errors),
                metrics={
                    "duration_ms": duration_ms,
                    "timeout_seconds": self.timeout_seconds,
                    "cost_usd": 0.0,
                    "exit_code": 1,
                },
                metadata={"mode": "parallel_shadow", "isolated": True},
            )

        preflight = self.evaluate_preflight(task)
        if preflight.blocked:
            duration_ms = int((time.time() - start) * 1000)
            message = next(
                (
                    result.message
                    for result in preflight.results
                    if result.action == POLICY_ACTION_BLOCK
                ),
                "Runtime preflight blocked execution",
            )
            log_runtime_capability(
                {
                    "task_id": task.task_id,
                    "commit_sha": task.commit_sha,
                    "backend": self.runtime_name,
                    "status": "blocked",
                    "duration_ms": duration_ms,
                    "exit_code": 1,
                    "cost_usd": 0.0,
                    "isolated": True,
                    "error_class": "RuntimePolicyError",
                    "error_message": message,
                }
            )
            blocked = self.build_blocked_result(
                task=task,
                message=message,
                policy_stage="preflight",
                policy_payload=preflight.to_dict(),
                metrics={
                    "duration_ms": duration_ms,
                    "timeout_seconds": self.timeout_seconds,
                    "cost_usd": 0.0,
                    "exit_code": 1,
                },
                metadata={"mode": "parallel_shadow", "isolated": True},
            )
            return blocked

        try:
            with tempfile.TemporaryDirectory(prefix="br3-codex-shadow-") as temp_dir:
                try:
                    version_info = ensure_codex_compatible(self.command)
                except RuntimeError as exc:
                    return RuntimeResult(
                        task_id=task.task_id,
                        runtime=self.runtime_name,
                        backend=self.backend_name,
                        status="error",
                        error_class="RuntimeCompatibilityError",
                        error_message=str(exc),
                        metadata={"mode": "parallel_shadow", "isolated": True},
                    )

                auth_valid, auth_error = check_codex_auth(project_root=temp_dir, command=self.command)
                if not auth_valid:
                    return RuntimeResult(
                        task_id=task.task_id,
                        runtime=self.runtime_name,
                        backend=self.backend_name,
                        status="error",
                        error_class="CodexAuthError",
                        error_message=auth_error,
                        metadata={"mode": "parallel_shadow", "isolated": True},
                    )

                temp_path = Path(temp_dir)
                output_path = temp_path / "last_message.txt"
                prompt = build_review_prompt(task.diff_text, task.spec_text)
                cmd = [
                    self.command,
                    "--ask-for-approval",
                    "never",
                    "exec",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "workspace-write",
                    "--cd",
                    temp_dir,
                    "--output-last-message",
                    str(output_path),
                    "--json",
                    "--",
                    prompt,
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
                exit_code = result.returncode
                if result.returncode != 0:
                    stderr = result.stderr.strip() or "Codex returned a non-zero exit status"
                    raise RuntimeError(stderr)

                events = parse_codex_event_stream(result.stdout)
                message, usage = extract_codex_message_and_usage(events)
                session_id = next(
                    (
                        event.get("thread_id")
                        for event in events
                        if event.get("type") == "thread.started" and event.get("thread_id")
                    ),
                    None,
                )
                if not message and output_path.exists():
                    message = output_path.read_text(encoding="utf-8").strip()

                findings = [
                    RuntimeFinding(
                        finding=item["finding"],
                        severity=item.get("severity", "note"),
                        source=self.runtime_name,
                    )
                    for item in parse_findings(message or "[]")
                ]
                duration_ms = int((time.time() - start) * 1000)
                log_runtime_capability(
                    {
                        "task_id": task.task_id,
                        "commit_sha": task.commit_sha,
                        "backend": self.runtime_name,
                        "version": version_info["raw"],
                        "status": "completed",
                        "duration_ms": duration_ms,
                        "exit_code": exit_code,
                        "cost_usd": 0.0,
                        "isolated": True,
                        "workspace_root": temp_dir,
                        "session_id": session_id,
                    }
                )
                runtime_result = RuntimeResult(
                    task_id=task.task_id,
                    runtime=self.runtime_name,
                    backend=version_info["raw"],
                    status="completed",
                    findings=findings,
                    raw_output=message or "",
                    raw_payload={"events": events, "usage": usage},
                    stream_events=events,
                    shell_actions=[
                        {
                            "tool": "codex_exec",
                            "isolated": True,
                            "sandbox": "workspace-write",
                            "cwd": temp_dir,
                        }
                    ],
                    capability_profile=self.get_capability_profile(),
                    metrics={
                        "duration_ms": duration_ms,
                        "cost_usd": 0.0,
                        "usage": usage,
                        "timeout_seconds": self.timeout_seconds,
                        "exit_code": exit_code,
                    },
                    metadata={
                        "mode": "parallel_shadow",
                        "isolated": True,
                        "session_id": session_id,
                        "capabilities": self.get_capabilities(),
                        "dispatch_mode": task.metadata.get("dispatch_mode"),
                    },
                )
                postflight = self.evaluate_postflight(task, runtime_result)
                runtime_result.metadata["preflight_policy"] = preflight.to_dict()
                runtime_result.metadata["postflight_policy"] = postflight.to_dict()
                return runtime_result
        except Exception as exc:
            duration_ms = int((time.time() - start) * 1000)
            log_runtime_capability(
                {
                    "task_id": task.task_id,
                    "commit_sha": task.commit_sha,
                    "backend": self.runtime_name,
                    "status": "error",
                    "duration_ms": duration_ms,
                    "exit_code": exit_code,
                    "cost_usd": 0.0,
                    "isolated": True,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                }
            )
            return RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend=self.backend_name,
                status="error",
                error_class=exc.__class__.__name__,
                error_message=str(exc),
                metrics={
                    "duration_ms": duration_ms,
                    "timeout_seconds": self.timeout_seconds,
                    "cost_usd": 0.0,
                    "exit_code": exit_code,
                },
                metadata={"mode": "parallel_shadow", "isolated": True},
            )

    def _run_plan_blocking(self, task: RuntimeTask) -> RuntimeResult:
        return self._run_command_task_blocking(task, mode="compiled_command_bundle", cwd_override=None)

    def _run_execution_blocking(self, task: RuntimeTask) -> RuntimeResult:
        return self._run_command_task_blocking(task, mode="begin_workflow", cwd_override=task.project_root)

    def _run_command_task_blocking(
        self,
        task: RuntimeTask,
        *,
        mode: str,
        cwd_override: str | None,
    ) -> RuntimeResult:
        start = time.time()
        exit_code = None
        errors = self.validate_task(task)
        if errors:
            duration_ms = int((time.time() - start) * 1000)
            return RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend=self.backend_name,
                status="error",
                error_class="ValueError",
                error_message="; ".join(errors),
                metrics={"duration_ms": duration_ms, "timeout_seconds": self.timeout_seconds, "exit_code": 1},
                metadata={"mode": mode, "isolated": cwd_override is None},
            )

        preflight = self.evaluate_preflight(task)
        if preflight.blocked:
            duration_ms = int((time.time() - start) * 1000)
            message = next(
                (result.message for result in preflight.results if result.action == POLICY_ACTION_BLOCK),
                "Runtime preflight blocked execution",
            )
            return self.build_blocked_result(
                task=task,
                message=message,
                policy_stage="preflight",
                policy_payload=preflight.to_dict(),
                metrics={"duration_ms": duration_ms, "timeout_seconds": self.timeout_seconds, "exit_code": 1},
                metadata={"mode": mode, "isolated": cwd_override is None},
            )

        try:
            with tempfile.TemporaryDirectory(prefix="br3-codex-plan-") as temp_dir:
                version_info = ensure_codex_compatible(self.command)
                auth_root = cwd_override or temp_dir
                auth_valid, auth_error = check_codex_auth(project_root=auth_root, command=self.command)
                if not auth_valid:
                    raise RuntimeError(auth_error)
                command_cwd = cwd_override or temp_dir
                output_root = Path(command_cwd) / ".buildrunner" / "runtime"
                output_root.mkdir(parents=True, exist_ok=True)
                output_path = output_root / f"{task.task_id}-last_message.txt"
                cmd = [
                    self.command,
                    "--ask-for-approval",
                    "never",
                    "exec",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "workspace-write",
                    "--cd",
                    command_cwd,
                    "--output-last-message",
                    str(output_path),
                    "--json",
                    "--",
                    task.spec_text,
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
                exit_code = result.returncode
                if result.returncode != 0:
                    stderr = result.stderr.strip() or "Codex returned a non-zero exit status"
                    raise RuntimeError(stderr)
                message = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else result.stdout.strip()
                duration_ms = int((time.time() - start) * 1000)
                runtime_result = RuntimeResult(
                    task_id=task.task_id,
                    runtime=self.runtime_name,
                    backend=version_info["raw"],
                    status="completed",
                    raw_output=message,
                    raw_payload={"stdout": result.stdout, "stderr": result.stderr},
                    capability_profile=self.get_capability_profile(),
                    metrics={
                        "duration_ms": duration_ms,
                        "timeout_seconds": self.timeout_seconds,
                        "exit_code": exit_code,
                    },
                    metadata={
                        "mode": mode,
                        "isolated": cwd_override is None,
                        "command_name": task.metadata.get("command_name"),
                        "workflow_name": task.metadata.get("workflow_name"),
                        "preflight_policy": preflight.to_dict(),
                        "cwd": command_cwd,
                    },
                )
                postflight = self.evaluate_postflight(task, runtime_result)
                runtime_result.metadata["postflight_policy"] = postflight.to_dict()
                return runtime_result
        except Exception as exc:
            duration_ms = int((time.time() - start) * 1000)
            return RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend=self.backend_name,
                status="error",
                error_class=exc.__class__.__name__,
                error_message=str(exc),
                metrics={"duration_ms": duration_ms, "timeout_seconds": self.timeout_seconds, "exit_code": exit_code},
                metadata={"mode": mode, "isolated": cwd_override is None},
            )
