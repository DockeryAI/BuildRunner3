"""BR3-owned Codex `/spec` workflow."""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.runtime.command_compiler import compile_command_bundle
from core.runtime.context_compiler import compile_command_task
from core.runtime.runtime_registry import RuntimeRegistry, create_runtime_registry
from core.runtime.types import RuntimeResult


DEFAULT_DRAFT_RELATIVE_PATH = Path(".buildrunner/plans/spec-draft-plan.md")


@dataclass
class SpecWorkflowRequest:
    """Input for the BR3-owned `/spec` workflow."""

    user_request: str
    project_root: str
    runtime: str = "codex"
    draft_path: str | None = None
    run_validation: bool = True
    run_adversarial_review: bool = True


@dataclass
class SpecWorkflowResult:
    """Structured output from the BR3-owned `/spec` workflow."""

    task_id: str
    status: str
    runtime: str
    support_level: str
    draft_path: str | None = None
    fallback_runtime: str | None = None
    validation_exit_code: int | None = None
    validation_output: str | None = None
    adversarial_findings: list[dict[str, Any]] = field(default_factory=list)
    runtime_result: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_subprocess(args: list[str], *, cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def _parse_findings(raw: str) -> list[dict[str, Any]]:
    if not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass
    return [{"finding": raw.strip(), "severity": "note"}]


async def run_spec_workflow(
    request: SpecWorkflowRequest,
    *,
    registry: RuntimeRegistry | None = None,
    subprocess_runner=_run_subprocess,
) -> SpecWorkflowResult:
    """Execute the BR3-owned `/spec` workflow through Codex without cutover."""
    bundle = compile_command_bundle(
        command_name="spec",
        runtime=request.runtime,
        project_root=request.project_root,
        user_request=request.user_request,
    )
    task, _ = compile_command_task(
        command_name="spec",
        runtime=request.runtime,
        project_root=request.project_root,
        user_request=request.user_request,
        metadata={"workflow_name": "spec_workflow"},
    )

    if bundle.support_level != "codex_workflow_only":
        return SpecWorkflowResult(
            task_id=task.task_id,
            status="fallback_required",
            runtime=request.runtime,
            support_level=bundle.support_level,
            fallback_runtime=bundle.fallback_runtime,
            notes=["Codex `/spec` support is only enabled through the BR3-owned workflow path."],
        )

    runtime_registry = registry or create_runtime_registry()
    runtime_adapter = runtime_registry.get(request.runtime).adapter
    runtime_result: RuntimeResult = await runtime_adapter.run_plan(task)
    result = SpecWorkflowResult(
        task_id=task.task_id,
        status=runtime_result.status,
        runtime=request.runtime,
        support_level=bundle.support_level,
        fallback_runtime=bundle.fallback_runtime,
        runtime_result=runtime_result.to_dict(),
    )
    if runtime_result.status != "completed":
        result.notes.append("Runtime failed before BR3 validation gates could run.")
        return result

    project_root = Path(request.project_root)
    draft_path = project_root / (request.draft_path or DEFAULT_DRAFT_RELATIVE_PATH)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(runtime_result.raw_output, encoding="utf-8")
    result.draft_path = str(draft_path)

    if request.run_validation:
        validation = await asyncio.to_thread(
            subprocess_runner,
            [str(Path.home() / ".buildrunner/scripts/validate-spec-paths.sh"), str(draft_path)],
            cwd=request.project_root,
        )
        result.validation_exit_code = validation.returncode
        result.validation_output = (validation.stdout or validation.stderr).strip()
        if validation.returncode != 0:
            result.status = "validation_failed"
            result.notes.append("Shared BR3 spec path validation blocked promotion.")
            return result

    if request.run_adversarial_review:
        review = await asyncio.to_thread(
            subprocess_runner,
            [
                str(Path.home() / ".buildrunner/scripts/adversarial-review.sh"),
                "--consensus",
                "--task-id",
                task.task_id,
                str(draft_path),
                request.project_root,
            ],
            cwd=request.project_root,
        )
        result.adversarial_findings = _parse_findings(review.stdout)
        blocker_count = sum(1 for item in result.adversarial_findings if item.get("severity") == "blocker")
        if review.returncode != 0:
            result.status = "review_failed"
            result.notes.append((review.stderr or "Adversarial review failed").strip())
            return result
        if blocker_count:
            result.status = "review_blocked"
            result.notes.append(f"Adversarial review returned {blocker_count} blocker findings.")
            return result

    result.status = "completed"
    result.notes.append("Codex `/spec` draft completed through the BR3-owned workflow path.")
    return result
