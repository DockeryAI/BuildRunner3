"""Advisory-only BR3 runtime shadow runner."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from core.runtime.context_compiler import compile_review_task
from core.runtime.runtime_registry import RuntimeRegistration, create_runtime_registry
from core.runtime.types import RuntimeResult, RuntimeTask


SHADOW_LOG_PATH = Path.home() / ".buildrunner" / "logs" / "runtime-shadow.log"
DEFAULT_METRICS_FILENAME = ".buildrunner/runtime-shadow-metrics.md"
DEFAULT_SHADOW_TIMEOUT_SECONDS = 120
PROMOTION_THRESHOLDS = {
    "min_completed_runs": 25,
    "min_blocker_agreement": 0.6,
    "max_false_blocker_rate": 0.1,
}
SUPPORTED_SHADOW_COMMANDS = {
    "review",
    "guard",
    "why",
    "diag",
    "plan_critique",
    "adversarial_review",
}


@dataclass
class ShadowRun:
    task_id: str
    command_name: str
    primary_runtime: str
    shadow_runtime: str
    primary_result: RuntimeResult
    shadow_result: RuntimeResult | None
    shadow_status: str
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "command_name": self.command_name,
            "primary_runtime": self.primary_runtime,
            "shadow_runtime": self.shadow_runtime,
            "shadow_status": self.shadow_status,
            "metrics": self.metrics,
            "primary_result": self.primary_result.to_dict(),
            "shadow_result": self.shadow_result.to_dict() if self.shadow_result else None,
        }


def _normalize_findings(result: RuntimeResult | None, severity: str) -> set[str]:
    if not result:
        return set()
    findings = result.findings or []
    normalized: set[str] = set()
    for finding in findings:
        data = finding.to_dict() if hasattr(finding, "to_dict") else dict(finding)
        if data.get("severity") == severity:
            normalized.add((data.get("finding") or "").strip())
    return normalized


def compute_shadow_metrics(
    primary_result: RuntimeResult,
    shadow_result: RuntimeResult | None,
    *,
    operator_verdict: str | None = None,
) -> dict[str, Any]:
    primary_blockers = _normalize_findings(primary_result, "blocker")
    shadow_blockers = _normalize_findings(shadow_result, "blocker")
    primary_warnings = _normalize_findings(primary_result, "warning")
    shadow_warnings = _normalize_findings(shadow_result, "warning")

    blocker_union = primary_blockers | shadow_blockers
    warning_union = primary_warnings | shadow_warnings
    blocker_overlap = primary_blockers & shadow_blockers
    warning_overlap = primary_warnings & shadow_warnings
    false_blocker = bool(shadow_blockers and not primary_blockers)
    operator_false_blocker = operator_verdict == "false_blocker"

    return {
        "primary_duration_ms": primary_result.metrics.get("duration_ms"),
        "shadow_duration_ms": shadow_result.metrics.get("duration_ms") if shadow_result else None,
        "primary_blocker_count": len(primary_blockers),
        "shadow_blocker_count": len(shadow_blockers),
        "blocker_overlap_count": len(blocker_overlap),
        "warning_overlap_count": len(warning_overlap),
        "blocker_agreement": 1.0 if not blocker_union else len(blocker_overlap) / len(blocker_union),
        "warning_overlap_ratio": 1.0 if not warning_union else len(warning_overlap) / len(warning_union),
        "false_blocker": false_blocker,
        "false_blocker_rate": 1.0 if (false_blocker and operator_false_blocker) else 0.0,
        "operator_verdict": operator_verdict,
    }


def _ensure_supported_command(command_name: str) -> None:
    if command_name not in SUPPORTED_SHADOW_COMMANDS:
        raise ValueError(
            f"Unsupported shadow command '{command_name}'. Supported: {', '.join(sorted(SUPPORTED_SHADOW_COMMANDS))}"
        )


def _shadow_kill_switch(config: dict[str, Any] | None = None) -> bool:
    if os.environ.get("BR3_DISABLE_CODEX_SHADOW") == "1":
        return True
    config = config or {}
    return not config.get("shadow", {}).get("enabled", True)


def _attach_shadow_metadata(task: RuntimeTask, *, shadow_role: str, command_name: str) -> RuntimeTask:
    metadata = dict(task.metadata)
    metadata.update({"shadow_role": shadow_role, "command_name": command_name, "dispatch_mode": "parallel_shadow"})
    return RuntimeTask(
        task_id=task.task_id,
        task_type=task.task_type,
        diff_text=task.diff_text,
        spec_text=task.spec_text,
        project_root=task.project_root,
        commit_sha=task.commit_sha,
        schema_version=task.schema_version,
        conflict_boundary=task.conflict_boundary,
        authoritative_runtime=task.authoritative_runtime,
        metadata=metadata,
    )


async def _run_registration(registration: RuntimeRegistration, task: RuntimeTask) -> RuntimeResult:
    if task.task_type != "review":
        raise NotImplementedError("Phase 8 shadow runner currently supports review-shaped tasks only")
    return await registration.adapter.run_review(task)


def _build_shadow_status(shadow_result: RuntimeResult | None) -> str:
    if shadow_result is None:
        return "shadow_skipped"
    if shadow_result.status == "completed":
        return "shadow_completed"
    if shadow_result.error_class in {"CodexAuthError", "RuntimePolicyError", "RuntimeCompatibilityError"}:
        return "shadow_skipped"
    return "shadow_failed"


def _write_shadow_log(entry: dict[str, Any]) -> None:
    SHADOW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SHADOW_LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def _summarize_shadow_log(log_path: Path) -> dict[str, Any]:
    if not log_path.exists():
        return {"total_runs": 0, "median_shadow_latency_ms": None, "median_primary_latency_ms": None}
    entries = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not entries:
        return {"total_runs": 0, "median_shadow_latency_ms": None, "median_primary_latency_ms": None}

    shadow_latencies = [entry.get("metrics", {}).get("shadow_duration_ms") for entry in entries]
    shadow_latencies = [value for value in shadow_latencies if isinstance(value, (int, float))]
    primary_latencies = [entry.get("metrics", {}).get("primary_duration_ms") for entry in entries]
    primary_latencies = [value for value in primary_latencies if isinstance(value, (int, float))]
    blocker_agreements = [
        entry.get("metrics", {}).get("blocker_agreement")
        for entry in entries
        if isinstance(entry.get("metrics", {}).get("blocker_agreement"), (int, float))
    ]
    false_blocker_rates = [
        entry.get("metrics", {}).get("false_blocker_rate")
        for entry in entries
        if isinstance(entry.get("metrics", {}).get("false_blocker_rate"), (int, float))
    ]
    completed = sum(1 for entry in entries if entry.get("shadow_status") == "shadow_completed")
    skipped = sum(1 for entry in entries if entry.get("shadow_status") == "shadow_skipped")
    return {
        "total_runs": len(entries),
        "shadow_completed": completed,
        "shadow_skipped": skipped,
        "median_shadow_latency_ms": median(shadow_latencies) if shadow_latencies else None,
        "median_primary_latency_ms": median(primary_latencies) if primary_latencies else None,
        "median_blocker_agreement": median(blocker_agreements) if blocker_agreements else None,
        "median_false_blocker_rate": median(false_blocker_rates) if false_blocker_rates else None,
    }


def update_shadow_metrics_doc(project_root: str, log_path: Path | None = None) -> Path:
    summary = _summarize_shadow_log(log_path or SHADOW_LOG_PATH)
    promotion_ready = (
        summary["shadow_completed"] >= PROMOTION_THRESHOLDS["min_completed_runs"]
        and (summary.get("median_blocker_agreement") or 0) >= PROMOTION_THRESHOLDS["min_blocker_agreement"]
        and (summary.get("median_false_blocker_rate") or 0) <= PROMOTION_THRESHOLDS["max_false_blocker_rate"]
    )
    metrics_path = Path(project_root) / DEFAULT_METRICS_FILENAME
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        "\n".join(
            [
                "# Runtime Shadow Metrics",
                "",
                f"- Total runs: {summary['total_runs']}",
                f"- Shadow completed: {summary.get('shadow_completed', 0)}",
                f"- Shadow skipped: {summary.get('shadow_skipped', 0)}",
                f"- Median primary latency (ms): {summary['median_primary_latency_ms']}",
                f"- Median shadow latency (ms): {summary['median_shadow_latency_ms']}",
                f"- Median blocker agreement: {summary.get('median_blocker_agreement')}",
                f"- Median false blocker rate: {summary.get('median_false_blocker_rate')}",
                f"- Promotion readiness: {'ready_for_owner_signoff' if promotion_ready else 'not_ready'}",
                "",
                "## Promotion Thresholds",
                "",
                f"- Completed shadow runs required: {PROMOTION_THRESHOLDS['min_completed_runs']}",
                f"- Minimum blocker agreement: {PROMOTION_THRESHOLDS['min_blocker_agreement']}",
                f"- Maximum false blocker rate: {PROMOTION_THRESHOLDS['max_false_blocker_rate']}",
                "",
                "## Owner Sign-Off",
                "",
                "- Owner: pending",
                "- Decision: pending",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return metrics_path


async def _run_shadow_runtime(
    registration: RuntimeRegistration,
    task: RuntimeTask,
    *,
    timeout_seconds: int,
) -> RuntimeResult | None:
    try:
        return await asyncio.wait_for(_run_registration(registration, task), timeout=timeout_seconds)
    except TimeoutError:
        return RuntimeResult(
            task_id=task.task_id,
            runtime=registration.name,
            backend=registration.name,
            status="failed",
            error_class="ShadowTimeoutError",
            error_message=f"Shadow runtime timed out after {timeout_seconds}s",
            metadata={"shadow_role": "secondary", "timeout_seconds": timeout_seconds},
        )
    except Exception as exc:
        return RuntimeResult(
            task_id=task.task_id,
            runtime=registration.name,
            backend=registration.name,
            status="failed",
            error_class=exc.__class__.__name__,
            error_message=str(exc),
            metadata={"shadow_role": "secondary"},
        )


async def run_shadow_command_async(
    *,
    diff_text: str,
    spec_text: str,
    project_root: str,
    commit_sha: str | None,
    command_name: str = "review",
    primary_runtime: str = "claude",
    shadow_runtime: str = "codex",
    config: dict[str, Any] | None = None,
    operator_verdict: str | None = None,
) -> ShadowRun:
    _ensure_supported_command(command_name)
    config = config or {}

    task, _ = compile_review_task(
        diff_text=diff_text,
        spec_text=spec_text,
        project_root=project_root,
        commit_sha=commit_sha,
        metadata={"command_name": command_name},
    )
    primary_task = _attach_shadow_metadata(task, shadow_role="primary", command_name=command_name)
    shadow_task = _attach_shadow_metadata(task, shadow_role="secondary", command_name=command_name)

    registry = create_runtime_registry(config)
    primary_registration = registry.get(primary_runtime)
    shadow_registration = registry.get(shadow_runtime)

    shadow_result: RuntimeResult | None = None
    if _shadow_kill_switch(config):
        primary_result = await _run_registration(primary_registration, primary_task)
    else:
        timeout_seconds = int(config.get("shadow", {}).get("timeout_seconds", DEFAULT_SHADOW_TIMEOUT_SECONDS))
        primary_future = asyncio.create_task(_run_registration(primary_registration, primary_task))
        shadow_future = asyncio.create_task(
            _run_shadow_runtime(shadow_registration, shadow_task, timeout_seconds=timeout_seconds)
        )
        primary_result = await primary_future
        shadow_result = await shadow_future

    shadow_status = _build_shadow_status(shadow_result)
    metrics = compute_shadow_metrics(primary_result, shadow_result, operator_verdict=operator_verdict)
    run = ShadowRun(
        task_id=task.task_id,
        command_name=command_name,
        primary_runtime=primary_runtime,
        shadow_runtime=shadow_runtime,
        primary_result=primary_result,
        shadow_result=shadow_result,
        shadow_status=shadow_status,
        metrics=metrics,
    )

    log_entry = run.to_dict()
    log_entry["project_root"] = project_root
    log_entry["commit_sha"] = commit_sha
    log_entry["promotion_thresholds"] = PROMOTION_THRESHOLDS
    _write_shadow_log(log_entry)
    update_shadow_metrics_doc(project_root)
    return run


def run_shadow_command(**kwargs) -> ShadowRun:
    return asyncio.run(run_shadow_command_async(**kwargs))


def _load_diff(project_root: str, commit_sha: str | None) -> str:
    try:
        if commit_sha:
            result = subprocess.run(
                ["git", "show", "--format=", "--no-ext-diff", commit_sha],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=20,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        result = subprocess.run(
            ["git", "diff", "HEAD~1"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        return result.stdout or ""
    except Exception:
        return ""


def _load_spec(spec_path: str | None) -> str:
    if not spec_path:
        return ""
    path = Path(spec_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="BR3 advisory-only runtime shadow runner")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--commit-sha")
    parser.add_argument("--command-name", default="review")
    parser.add_argument("--spec-path")
    parser.add_argument("--operator-verdict")
    args = parser.parse_args()

    shadow_run = run_shadow_command(
        diff_text=_load_diff(args.project_root, args.commit_sha),
        spec_text=_load_spec(args.spec_path),
        project_root=args.project_root,
        commit_sha=args.commit_sha,
        command_name=args.command_name,
        operator_verdict=args.operator_verdict,
    )
    print(json.dumps(shadow_run.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
