"""Claude runtime wrapper for the Phase 1 review spike."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
import time
from typing import Callable

from core.runtime.policy_result import POLICY_ACTION_BLOCK
from core.ai_code_review import CodeReviewer
from core.cluster.cross_model_review import build_review_prompt, log_runtime_capability, parse_findings
from core.runtime.base import BaseRuntime
from core.runtime.types import RuntimeFinding, RuntimeResult, RuntimeTask


class ClaudeRuntime(BaseRuntime):
    """Run Claude review through the local Claude CLI, with API fallback for tests."""

    runtime_name = "claude"
    backend_name = "claude-cli"

    def __init__(
        self,
        reviewer_factory: Callable[..., CodeReviewer] | None = None,
        command: str = "claude",
        model: str = "sonnet",
    ):
        self._reviewer_factory = reviewer_factory
        self.command = command
        self.model = model

    def get_capabilities(self) -> dict[str, object]:
        return {
            "review": True,
            "analysis": False,
            "plan": False,
            "execution": False,
            "streaming": False,
            "shell": False,
            "browser": False,
            "subagents": False,
            "orchestration_checkpoint": False,
            "cluster_suitable": True,
            "isolated_workspace_only": True,
            "edit_formats": [],
            "json_result": True,
        }

    async def run_review(self, task: RuntimeTask) -> RuntimeResult:
        return await asyncio.to_thread(self._run_review_blocking, task)

    def _run_review_blocking(self, task: RuntimeTask) -> RuntimeResult:
        start = time.time()
        errors = self.validate_task(task)
        if errors:
            duration_ms = int((time.time() - start) * 1000)
            log_runtime_capability(
                {
                    "task_id": task.task_id,
                    "commit_sha": task.commit_sha,
                    "backend": self.runtime_name,
                    "version": self.backend_name,
                    "status": "error",
                    "duration_ms": duration_ms,
                    "exit_code": 1,
                    "cost_usd": None,
                    "isolated": True,
                    "error_class": "ValueError",
                    "error_message": "; ".join(errors),
                }
            )
            return RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend=self.backend_name,
                status="error",
                error_class="ValueError",
                error_message="; ".join(errors),
                metrics={"duration_ms": duration_ms, "cost_usd": None, "exit_code": 1},
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
                    "version": self.backend_name,
                    "status": "blocked",
                    "duration_ms": duration_ms,
                    "exit_code": 1,
                    "cost_usd": None,
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
                metrics={"duration_ms": duration_ms, "cost_usd": None, "exit_code": 1},
                metadata={"mode": "parallel_shadow", "isolated": True},
            )
            return blocked

        if shutil.which(self.command):
            return self._run_via_claude_cli(task, start, preflight=preflight)
        if self._reviewer_factory:
            return self._run_via_reviewer_factory(task, start, preflight=preflight)

        duration_ms = int((time.time() - start) * 1000)
        error_message = f"{self.command} CLI not found and no reviewer_factory fallback provided"
        log_runtime_capability(
            {
                "task_id": task.task_id,
                "commit_sha": task.commit_sha,
                "backend": self.runtime_name,
                "version": self.backend_name,
                "status": "error",
                "duration_ms": duration_ms,
                "exit_code": 1,
                "cost_usd": None,
                "isolated": True,
                "error_class": "RuntimeError",
                "error_message": error_message,
            }
        )
        return RuntimeResult(
            task_id=task.task_id,
            runtime=self.runtime_name,
            backend=self.backend_name,
            status="error",
            error_class="RuntimeError",
            error_message=error_message,
            metrics={"duration_ms": duration_ms, "cost_usd": None, "exit_code": 1},
            metadata={"mode": "parallel_shadow", "isolated": True},
        )

    def _run_via_claude_cli(self, task: RuntimeTask, start: float, preflight) -> RuntimeResult:
        exit_code = None
        try:
            with tempfile.TemporaryDirectory(prefix="br3-claude-shadow-") as temp_dir:
                prompt = build_review_prompt(task.diff_text, task.spec_text)
                cmd = [
                    self.command,
                    "-p",
                    "--output-format",
                    "json",
                    "--dangerously-skip-permissions",
                    "--tools",
                    "",
                    "--model",
                    self.model,
                    prompt,
                ]
                result = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                exit_code = result.returncode
                if result.returncode != 0:
                    stderr = result.stderr.strip() or "Claude CLI returned a non-zero exit status"
                    raise RuntimeError(stderr)

                payload = json.loads(result.stdout)
                message = payload.get("result", "")
                findings = [
                    RuntimeFinding(
                        finding=item["finding"],
                        severity=item.get("severity", "note"),
                        source=self.runtime_name,
                    )
                    for item in parse_findings(message or "[]")
                ]
                duration_ms = int((time.time() - start) * 1000)
                total_cost = payload.get("total_cost_usd")
                session_id = payload.get("session_id")
                model_usage = payload.get("modelUsage", {})
                backend = next(iter(model_usage.keys()), self.backend_name)
                log_runtime_capability(
                    {
                        "task_id": task.task_id,
                        "commit_sha": task.commit_sha,
                        "backend": self.runtime_name,
                        "version": backend,
                        "status": "completed",
                        "duration_ms": duration_ms,
                        "exit_code": exit_code,
                        "cost_usd": total_cost,
                        "isolated": True,
                        "session_id": session_id,
                    }
                )
                runtime_result = RuntimeResult(
                    task_id=task.task_id,
                    runtime=self.runtime_name,
                    backend=backend,
                    status="completed",
                    findings=findings,
                    raw_output=message,
                    raw_payload=payload,
                    capability_profile=self.get_capability_profile(),
                    metrics={
                        "duration_ms": duration_ms,
                        "cost_usd": total_cost,
                        "exit_code": exit_code,
                        "usage": payload.get("usage", {}),
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
                    "version": self.backend_name,
                    "status": "error",
                    "duration_ms": duration_ms,
                    "exit_code": exit_code,
                    "cost_usd": None,
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
                metrics={"duration_ms": duration_ms, "cost_usd": None, "exit_code": exit_code},
                metadata={"mode": "parallel_shadow", "isolated": True},
            )

    def _run_via_reviewer_factory(self, task: RuntimeTask, start: float, preflight) -> RuntimeResult:
        try:
            reviewer = self._reviewer_factory(project_root=task.project_root)
            loop = asyncio.new_event_loop()
            try:
                review = loop.run_until_complete(
                    reviewer.review_diff(
                        task.diff_text,
                        context={"commit_sha": task.commit_sha, "task_id": task.task_id},
                    )
                )
            finally:
                loop.close()
            findings = [
                RuntimeFinding(finding=issue, severity="warning", source=self.runtime_name)
                for issue in review.get("issues", [])
            ]
            findings.extend(
                RuntimeFinding(finding=suggestion, severity="note", source=self.runtime_name)
                for suggestion in review.get("suggestions", [])
            )
            duration_ms = int((time.time() - start) * 1000)
            log_runtime_capability(
                {
                    "task_id": task.task_id,
                    "commit_sha": task.commit_sha,
                    "backend": self.runtime_name,
                    "version": "anthropic/claude-sonnet-4-20250514",
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "exit_code": 0,
                    "cost_usd": None,
                    "isolated": False,
                }
            )
            runtime_result = RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend="anthropic/claude-sonnet-4-20250514",
                status="completed",
                findings=findings,
                raw_output=review.get("summary", ""),
                raw_payload=review,
                capability_profile=self.get_capability_profile(),
                metrics={
                    "duration_ms": duration_ms,
                    "score": review.get("score"),
                    "cost_usd": None,
                    "exit_code": 0,
                },
                metadata={"mode": "parallel_shadow", "isolated": False},
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
                    "version": "anthropic/claude-sonnet-4-20250514",
                    "status": "error",
                    "duration_ms": duration_ms,
                    "exit_code": 1,
                    "cost_usd": None,
                    "isolated": False,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                }
            )
            return RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend="anthropic/claude-sonnet-4-20250514",
                status="error",
                error_class=exc.__class__.__name__,
                error_message=str(exc),
                metrics={"duration_ms": duration_ms, "cost_usd": None, "exit_code": 1},
                metadata={"mode": "parallel_shadow", "isolated": False},
            )
