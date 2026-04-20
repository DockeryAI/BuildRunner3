"""OllamaRuntime — BR3 local inference adapter for Below/Jimmy via Ollama /api/chat."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

from core.cluster.cross_model_review import build_review_prompt, parse_findings
from core.runtime.base import BaseRuntime
from core.runtime.claude_runtime import ClaudeRuntime
from core.runtime.types import RuntimeFinding, RuntimeResult, RuntimeTask

logger = logging.getLogger(__name__)

_DEFAULT_OLLAMA_HOST = "http://10.0.1.105"
_DEFAULT_OLLAMA_PORT = 11434
_DEFAULT_MODEL = "llama3.3:70b"
_CLUSTER_CHECK_SCRIPT = Path.home() / ".buildrunner/scripts/cluster-check.sh"
_CLUSTER_JSON = Path.home() / ".buildrunner/cluster.json"


def _resolve_ollama_base_url() -> str:
    """Resolve Ollama base URL from cluster.json (role=inference), fallback to default."""
    try:
        if _CLUSTER_JSON.exists():
            cluster = json.loads(_CLUSTER_JSON.read_text(encoding="utf-8"))
            for node in cluster.get("nodes", {}).values():
                roles = node.get("roles", [node.get("role", "")])
                if "inference" in roles:
                    host = node.get("host", "10.0.1.105")
                    return f"http://{host}"
    except (OSError, ValueError, KeyError):
        pass
    return _DEFAULT_OLLAMA_HOST


def _check_ollama_health(base_url: str, port: int = _DEFAULT_OLLAMA_PORT) -> bool:
    """Health check via cluster-check.sh inference, fallback to direct HTTP check."""
    try:
        if _CLUSTER_CHECK_SCRIPT.exists():
            result = subprocess.run(  # noqa: S603
                [str(_CLUSTER_CHECK_SCRIPT), "inference"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Fallback: direct HTTP check
    try:
        url = f"{base_url}:{port}/api/tags"
        req = urllib.request.Request(url, method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            return resp.status == 200  # type: ignore[no-any-return]
    except (OSError, ValueError):
        return False


class OllamaRuntime(BaseRuntime):
    """Run tasks against Ollama /api/chat on the cluster inference node (Below/Jimmy).

    On 503 or timeout, falls back to ClaudeRuntime SILENTLY — logs the fallback,
    never raises a user-visible error.
    """

    runtime_name = "ollama"
    backend_name = "ollama-api"

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        host: str | None = None,
        port: int = _DEFAULT_OLLAMA_PORT,
        timeout: int = 120,
    ) -> None:
        self.model = model
        self._host = host  # None = resolve from cluster.json at call time
        self.port = port
        self.timeout = timeout

    def _get_base_url(self) -> str:
        return self._host if self._host else _resolve_ollama_base_url()

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "review": True,
            "analysis": True,
            "plan": True,
            "execution": False,
            "streaming": False,
            "shell": False,
            "browser": False,
            "subagents": False,
            "orchestration_checkpoint": False,
            "cluster_suitable": True,
            "isolated_workspace_only": False,
            "edit_formats": [],
            "json_result": False,
            "local_inference": True,
        }

    def _call_ollama(self, prompt: str, base_url: str) -> tuple[str, dict[str, Any]]:
        """POST to Ollama /api/chat. Returns (message_text, usage_dict)."""
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
        ).encode("utf-8")

        url = f"{base_url}:{self.port}/api/chat"
        req = urllib.request.Request(  # noqa: S310
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            status = resp.status
            if status != 200:
                raise RuntimeError(f"Ollama returned HTTP {status}")
            body = json.loads(resp.read().decode("utf-8"))

        message = body.get("message", {}).get("content", "")
        usage: dict[str, Any] = {
            "prompt_tokens": body.get("prompt_eval_count", 0),
            "completion_tokens": body.get("eval_count", 0),
            "total_duration_ns": body.get("total_duration", 0),
        }
        return message, usage

    def _fallback_to_claude(self, task: RuntimeTask, reason: str, start: float) -> RuntimeResult:
        """Silently fall back to ClaudeRuntime on health-check failure or 503/timeout."""
        logger.warning(
            "OllamaRuntime fallback to ClaudeRuntime: task_id=%s reason=%s",
            task.task_id,
            reason,
        )
        claude = ClaudeRuntime()
        try:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(claude.run_review(task))
            finally:
                loop.close()
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.time() - start) * 1000)
            return RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend=self.backend_name,
                status="error",
                error_class=exc.__class__.__name__,
                error_message=str(exc),
                metrics={"duration_ms": duration_ms},
                metadata={"fallback": "claude", "fallback_reason": reason},
            )

        result.metadata["fallback"] = "claude"
        result.metadata["fallback_reason"] = reason
        return result

    async def run_review(self, task: RuntimeTask) -> RuntimeResult:
        return await asyncio.to_thread(self._run_blocking, task)

    def _run_blocking(self, task: RuntimeTask) -> RuntimeResult:
        start = time.time()
        base_url = self._get_base_url()

        # Health check — fall back silently on failure
        if not _check_ollama_health(base_url, self.port):
            return self._fallback_to_claude(task, "health_check_failed", start)

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
                metrics={"duration_ms": duration_ms},
                metadata={"mode": "local_inference"},
            )

        prompt = build_review_prompt(task.diff_text, task.spec_text)

        try:
            message, usage = self._call_ollama(prompt, base_url)
        except Exception as exc:  # noqa: BLE001
            error_str = str(exc)
            # 503 / timeout / connection refused → silent fallback to Claude
            is_fallback_trigger = (
                "503" in error_str
                or "timed out" in error_str.lower()
                or "timeout" in error_str.lower()
                or "connection refused" in error_str.lower()
                or "urlopen error" in error_str.lower()
            )
            if is_fallback_trigger:
                logger.warning(
                    "OllamaRuntime: recoverable error for task %s: %s",
                    task.task_id,
                    error_str,
                )
                return self._fallback_to_claude(task, f"ollama_error: {exc.__class__.__name__}", start)

            # Non-recoverable — return error result
            duration_ms = int((time.time() - start) * 1000)
            return RuntimeResult(
                task_id=task.task_id,
                runtime=self.runtime_name,
                backend=self.backend_name,
                status="error",
                error_class=exc.__class__.__name__,
                error_message=error_str,
                metrics={"duration_ms": duration_ms, "model": self.model},
                metadata={"mode": "local_inference"},
            )

        duration_ms = int((time.time() - start) * 1000)
        findings = [
            RuntimeFinding(
                finding=item["finding"],
                severity=item.get("severity", "note"),
                source=self.runtime_name,
            )
            for item in parse_findings(message or "[]")
        ]

        return RuntimeResult(
            task_id=task.task_id,
            runtime=self.runtime_name,
            backend=f"ollama/{self.model}",
            status="completed",
            findings=findings,
            raw_output=message,
            raw_payload={"usage": usage},
            capability_profile=self.get_capability_profile(),
            metrics={
                "duration_ms": duration_ms,
                "model": self.model,
                "usage": usage,
                "cost_usd": 0.0,
            },
            metadata={
                "mode": "local_inference",
                "host": base_url,
                "model": self.model,
            },
        )
