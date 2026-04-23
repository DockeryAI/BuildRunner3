"""BR3-owned bounded Codex `/begin` workflow."""

from __future__ import annotations

import asyncio
import json
import shutil
import socket
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.runtime.capability_gate import CapabilityGateResult, pending_build_phases, evaluate_phase_capabilities
from core.runtime.command_compiler import compile_command_bundle
from core.runtime.context_compiler import compile_command_task
from core.runtime.runtime_registry import RuntimeRegistry, create_runtime_registry
from core.runtime.types import RuntimeResult, RuntimeTask


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_build_path(project_root: Path) -> Path:
    builds_dir = project_root / ".buildrunner" / "builds"
    matches = sorted(builds_dir.glob("BUILD_*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError("No BUILD_*.md file found under .buildrunner/builds")
    return matches[0]


def _phase_plan_path(project_root: Path, phase_number: int) -> Path:
    return project_root / ".buildrunner" / "plans" / f"phase-{phase_number}-plan.md"


def _phase_lock_dir(project_root: Path, phase_number: int) -> Path:
    return project_root / ".buildrunner" / "locks" / f"phase-{phase_number}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _replace_phase_status(build_text: str, phase_number: int, new_status: str) -> str:
    marker = f"### Phase {phase_number}:"
    start = build_text.find(marker)
    if start == -1:
        raise ValueError(f"Phase {phase_number} not found in BUILD document")
    next_index = build_text.find("\n### Phase ", start + len(marker))
    if next_index == -1:
        next_index = len(build_text)
    block = build_text[start:next_index]
    updated_block, count = __import__("re").subn(r"(\*\*Status:\*\*\s*)([^\n]+)", rf"\1{new_status}", block, count=1)
    if count != 1:
        raise ValueError(f"Phase {phase_number} block did not contain a Status line")
    return build_text[:start] + updated_block + build_text[next_index:]


def _build_phase_prompt(bundle_prompt: str, phase_body: str, *, approval_granted: bool, build_path: Path) -> str:
    approval_line = "granted" if approval_granted else "missing"
    return (
        f"{bundle_prompt}\n"
        "## BR3 Begin Workflow\n"
        f"BUILD Path: {build_path}\n"
        f"Approval Gate: {approval_line}\n"
        "Execute only the single phase below.\n"
        "Keep execution sequential and bounded.\n"
        "Do not use subagents, parallel work, browser tools, or autopilot behavior.\n"
        "If the phase appears to need unsupported capabilities, stop and explain why instead of guessing.\n\n"
        "## Phase Scope\n"
        f"{phase_body.strip()}\n"
    )


@dataclass
class BeginWorkflowRequest:
    """Input for the BR3-owned bounded Codex `/begin` workflow."""

    user_request: str
    project_root: str
    runtime: str = "codex"
    build_path: str | None = None
    max_phases: int = 5
    approval_granted: bool = False
    allowed_phase_numbers: list[int] = field(default_factory=list)


@dataclass
class BeginWorkflowPhaseResult:
    """Structured status for one attempted `/begin` phase."""

    phase_number: int
    phase_name: str
    status: str
    gate: dict[str, Any]
    runtime_result: dict[str, Any] = field(default_factory=dict)
    lock_path: str | None = None
    progress_path: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BeginWorkflowResult:
    """Structured output from the BR3-owned bounded Codex `/begin` workflow."""

    task_id: str
    status: str
    runtime: str
    support_level: str
    build_path: str | None = None
    fallback_runtime: str | None = None
    phase_results: list[BeginWorkflowPhaseResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["phase_results"] = [item.to_dict() for item in self.phase_results]
        return payload


def _run_spec_drift_check(project_root: Path) -> list[str]:
    """
    Step 0 spec-drift check: compare BUILD spec deliverables against codebase.

    Returns a list of advisory note strings (empty if skipped or clean).
    Never raises — all errors are captured as a note.

    Project-scoping guard: silently returns [] when no BUILD_*.md exists.
    Rollback: BR3_SPEC_DRIFT=off → returns [] immediately.
    """
    try:
        from core.cluster.below.spec_drift import detect_spec_drift, format_drift_report
        report = detect_spec_drift(project_root)
        if report.skipped:
            return []
        summary = format_drift_report(report)
        if report.has_drift or report.error:
            return [f"[spec-drift advisory] {summary}"]
        return []
    except Exception as exc:  # noqa: BLE001
        return [f"[spec-drift] check failed silently: {exc}"]


async def run_begin_workflow(
    request: BeginWorkflowRequest,
    *,
    registry: RuntimeRegistry | None = None,
) -> BeginWorkflowResult:
    """Execute bounded, sequential Codex `/begin` phases under BR3 lock/approval control."""
    project_root = Path(request.project_root)
    build_path = Path(request.build_path) if request.build_path else _default_build_path(project_root)

    # Step 0: Spec-drift detection (advisory, non-blocking, fail-open)
    drift_notes = _run_spec_drift_check(project_root)

    bundle = compile_command_bundle(
        command_name="begin",
        runtime=request.runtime,
        project_root=request.project_root,
        user_request=request.user_request,
    )
    task, _ = compile_command_task(
        command_name="begin",
        runtime=request.runtime,
        project_root=request.project_root,
        user_request=request.user_request,
        task_type="execution",
        metadata={"workflow_name": "begin_workflow"},
    )
    result = BeginWorkflowResult(
        task_id=task.task_id,
        status="pending",
        runtime=request.runtime,
        support_level=bundle.support_level,
        build_path=str(build_path),
        fallback_runtime=bundle.fallback_runtime,
    )
    result.notes.extend(drift_notes)

    if bundle.support_level != "codex_workflow_only":
        result.status = "fallback_required"
        result.notes.append("Codex `/begin` support is only enabled through the BR3-owned bounded workflow.")
        return result

    if not request.approval_granted:
        result.status = "approval_required"
        result.notes.append("BR3 approval gate blocked `/begin` execution before any phase lock was acquired.")
        return result

    build_text = build_path.read_text(encoding="utf-8")
    phases = pending_build_phases(build_text)
    if request.allowed_phase_numbers:
        allowed = set(request.allowed_phase_numbers)
        phases = [phase for phase in phases if phase.number in allowed]

    if not phases:
        result.status = "no_pending_phases"
        result.notes.append("No pending BUILD phases were eligible for bounded Codex `/begin` execution.")
        return result

    phases = phases[: max(1, request.max_phases)]
    runtime_registry = registry or create_runtime_registry()
    runtime_adapter = runtime_registry.get(request.runtime).adapter
    runtime_capabilities = runtime_adapter.get_capabilities()

    current_phase_path = project_root / ".buildrunner" / "current-phase.json"
    completed_any = False

    for phase in phases:
        gate = evaluate_phase_capabilities(
            phase,
            runtime_name=request.runtime,
            runtime_capabilities=runtime_capabilities,
        )
        phase_result = BeginWorkflowPhaseResult(
            phase_number=phase.number,
            phase_name=phase.name,
            status="gated",
            gate=gate.to_dict(),
        )
        result.phase_results.append(phase_result)

        if gate.decision == "handoff_to_claude":
            phase_result.status = "handoff_required"
            phase_result.notes.append("Phase requires unsupported capabilities and must hand off to Claude.")
            result.status = "partial_completed" if completed_any else "handoff_required"
            result.notes.append(f"Phase {phase.number} handed off to Claude due to explicit capability gate failure.")
            break
        if gate.decision != "allow":
            phase_result.status = "refused"
            phase_result.notes.append("Phase failed the bounded Codex `/begin` admission gate.")
            result.status = "partial_completed" if completed_any else "refused"
            result.notes.append(f"Phase {phase.number} was refused by the BR3 capability gate.")
            break

        plan_path = _phase_plan_path(project_root, phase.number)
        if not plan_path.exists():
            phase_result.status = "approval_required"
            phase_result.notes.append("Phase plan file is missing; BR3 will not start execution without plan context.")
            result.status = "partial_completed" if completed_any else "approval_required"
            result.notes.append(f"Phase {phase.number} is blocked until its plan file exists.")
            break

        lock_dir = _phase_lock_dir(project_root, phase.number)
        try:
            lock_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            phase_result.status = "lock_conflict"
            phase_result.lock_path = str(lock_dir)
            phase_result.notes.append("Phase lock already exists; BR3 refused to take over automatically.")
            result.status = "partial_completed" if completed_any else "lock_conflict"
            result.notes.append(f"Phase {phase.number} is already locked.")
            break

        phase_result.lock_path = str(lock_dir)
        progress_path = lock_dir / "progress.json"
        phase_result.progress_path = str(progress_path)
        claim_path = lock_dir / "claim.json"
        heartbeat_path = lock_dir / "heartbeat"

        claim_payload = {
            "phase": phase.number,
            "name": phase.name,
            "claimed_at": _utc_now(),
            "host": socket.gethostname(),
            "build": str(build_path.name),
            "runtime": request.runtime,
            "workflow": "begin_workflow",
        }
        _write_json(claim_path, claim_payload)
        heartbeat_path.write_text(_utc_now(), encoding="utf-8")
        _write_json(
            current_phase_path,
            {"phase": phase.number, "name": phase.name, "started": _utc_now(), "runtime": request.runtime},
        )
        _write_json(
            progress_path,
            {
                "phase": phase.number,
                "name": phase.name,
                "step": 4,
                "step_name": "execute",
                "step_label": "Executing bounded Codex phase",
                "status": "active",
                "tasks_total": 1,
                "tasks_done": 0,
                "current_task": f"{phase.number} — {phase.name}",
                "tests_written": 0,
                "tests_passing": 0,
                "commits": 0,
                "errors": [],
                "warnings": [],
                "started_at": claim_payload["claimed_at"],
                "updated_at": claim_payload["claimed_at"],
                "history": [{"step": 1, "name": "lock", "label": "Lock acquired", "at": claim_payload["claimed_at"], "status": "done"}],
                "verify_results": [],
                "consecutive_failures": 0,
                "interaction_count": 0,
                "compaction_count": 0,
                "files_actual": phase.files,
                "runtime": request.runtime,
            },
        )

        try:
            phase_task = RuntimeTask(
                task_id=f"{task.task_id}-phase-{phase.number}",
                task_type="execution",
                diff_text="",
                spec_text=_build_phase_prompt(
                    bundle.render_prompt(),
                    phase.body,
                    approval_granted=request.approval_granted,
                    build_path=build_path,
                ),
                project_root=request.project_root,
                commit_sha="begin-workflow-unpinned",
                metadata={
                    "mode": "begin_workflow",
                    "dispatch_mode": "direct",
                    "workflow_name": "begin_workflow",
                    "command_name": "begin",
                    "phase_number": phase.number,
                    "phase_name": phase.name,
                    "changed_files": phase.files,
                    "live_routing_changed": False,
                },
            )
            runtime_result: RuntimeResult = await runtime_adapter.run_execution_step(phase_task)
            phase_result.runtime_result = runtime_result.to_dict()
            if runtime_result.status != "completed":
                phase_result.status = "runtime_error"
                phase_result.notes.append("Runtime failed before BR3 could mark the phase complete.")
                result.status = "partial_completed" if completed_any else "runtime_error"
                result.notes.append(f"Phase {phase.number} failed in the runtime adapter.")
                break

            build_text = build_path.read_text(encoding="utf-8")
            build_path.write_text(_replace_phase_status(build_text, phase.number, "✅ COMPLETE"), encoding="utf-8")
            heartbeat_path.write_text(_utc_now(), encoding="utf-8")
            _write_json(
                progress_path,
                {
                    "phase": phase.number,
                    "name": phase.name,
                    "step": 7,
                    "step_name": "report",
                    "step_label": "Phase complete",
                    "status": "complete",
                    "tasks_total": 1,
                    "tasks_done": 1,
                    "current_task": None,
                    "tests_written": 0,
                    "tests_passing": 0,
                    "commits": 0,
                    "errors": [],
                    "warnings": [],
                    "started_at": claim_payload["claimed_at"],
                    "updated_at": _utc_now(),
                    "history": [
                        {"step": 1, "name": "lock", "label": "Lock acquired", "at": claim_payload["claimed_at"], "status": "done"},
                        {"step": 4, "name": "execute", "label": "Runtime completed", "at": _utc_now(), "status": "done"},
                    ],
                    "verify_results": [],
                    "consecutive_failures": 0,
                    "interaction_count": 0,
                    "compaction_count": 0,
                    "files_actual": phase.files,
                    "runtime": request.runtime,
                },
            )
            phase_result.status = "completed"
            phase_result.notes.append("Phase completed under BR3-owned lock and approval control.")
            completed_any = True
        finally:
            if phase_result.status == "completed":
                shutil.rmtree(lock_dir, ignore_errors=True)

    if result.status == "pending":
        result.status = "completed"
    if completed_any and result.status in {"pending", "completed"}:
        result.notes.append("Bounded sequential Codex `/begin` execution completed without silent fallback.")
    return result
