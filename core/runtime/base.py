"""Base runtime contract for BR3 runtime adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.runtime.capabilities import CapabilityProfile
from core.runtime.postflight import evaluate_runtime_task_postflight
from core.runtime.preflight import evaluate_runtime_task_preflight
from core.runtime.types import RuntimeResult, RuntimeTask


class BaseRuntime(ABC):
    """Shared BR3-facing contract for runtime adapters."""

    runtime_name: str = ""
    backend_name: str = ""

    def get_capabilities(self) -> dict[str, Any]:
        return {"review": True, "analysis": False, "plan": False, "execution": False}

    def get_capability_profile(self) -> CapabilityProfile:
        return CapabilityProfile.from_legacy(self.get_capabilities())

    def validate_task(self, task: RuntimeTask) -> list[str]:
        errors: list[str] = []
        if task.task_type not in {"review", "plan", "execution"}:
            errors.append(f"Unsupported task_type: {task.task_type}")
        if task.task_type == "review" and not task.diff_text.strip():
            errors.append("Review diff_text is required")
        if task.task_type in {"plan", "execution"} and not task.spec_text.strip():
            errors.append(f"{task.task_type.title()} spec_text is required")
        if not task.project_root:
            errors.append("project_root is required")
        if not task.commit_sha:
            errors.append("commit_sha is required")
        return errors

    def evaluate_preflight(self, task: RuntimeTask):
        return evaluate_runtime_task_preflight(task, self.runtime_name)

    def evaluate_postflight(self, task: RuntimeTask, result: RuntimeResult):
        return evaluate_runtime_task_postflight(task, result)

    def build_blocked_result(
        self,
        *,
        task: RuntimeTask,
        backend: str | None = None,
        message: str,
        policy_stage: str,
        policy_payload: dict[str, Any],
        error_class: str = "RuntimePolicyError",
        metrics: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeResult:
        result_metadata = dict(metadata or {})
        result_metadata[f"{policy_stage}_policy"] = policy_payload
        return RuntimeResult(
            task_id=task.task_id,
            runtime=self.runtime_name,
            backend=backend or self.backend_name,
            status="blocked",
            error_class=error_class,
            error_message=message,
            metrics=metrics or {},
            metadata=result_metadata,
        )

    @abstractmethod
    async def run_review(self, task: RuntimeTask) -> RuntimeResult:
        """Execute a review task and return the normalized BR3 envelope."""

    async def run_analysis(self, task: RuntimeTask) -> RuntimeResult:
        raise NotImplementedError("Phase 1 scaffold only implements review")

    async def run_plan(self, task: RuntimeTask) -> RuntimeResult:
        raise NotImplementedError("Phase 1 scaffold only implements review")

    async def run_execution_step(self, task: RuntimeTask) -> RuntimeResult:
        raise NotImplementedError("Phase 1 scaffold only implements review")

    async def stream_events(self, task: RuntimeTask) -> list[dict[str, Any]]:
        return []

    async def cancel(self, task_id: str) -> bool:
        return False

    async def save_orchestration_checkpoint(self, task: RuntimeTask) -> dict[str, Any]:
        return {"task_id": task.task_id, "runtime": self.runtime_name, "saved": False}

    async def resume_orchestration_task(self, task: RuntimeTask) -> RuntimeResult:
        raise NotImplementedError("Phase 1 scaffold does not resume runtime tasks")
