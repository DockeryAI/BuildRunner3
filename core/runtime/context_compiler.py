"""Shared BR3 context assembly for runtime-aware BR3 task bundles."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath

from core.runtime.command_compiler import compile_command_bundle
from core.runtime.types import RuntimeTask


@dataclass
class ReviewContextSummary:
    """Compact summary of the review payload passed to runtime adapters."""

    task_id: str
    dispatch_mode: str
    changed_files: list[str]
    file_count: int
    diff_line_count: int
    diff_chars: int
    spec_chars: int
    project_root: str
    commit_sha: str

    def to_metadata(self) -> dict[str, object]:
        return {
            "dispatch_mode": self.dispatch_mode,
            "changed_files": self.changed_files,
            "file_count": self.file_count,
            "diff_line_count": self.diff_line_count,
            "diff_chars": self.diff_chars,
            "spec_chars": self.spec_chars,
            "project_root": self.project_root,
            "commit_sha": self.commit_sha,
        }


@dataclass
class CommandContextSummary:
    """Compact summary of a command bundle passed to runtime adapters."""

    task_id: str
    command_name: str
    runtime: str
    support_level: str
    skill_names: list[str]
    context_files: list[str]
    project_root: str

    def to_metadata(self) -> dict[str, object]:
        return {
            "command_name": self.command_name,
            "runtime": self.runtime,
            "support_level": self.support_level,
            "skill_names": self.skill_names,
            "context_files": self.context_files,
            "project_root": self.project_root,
        }


def build_runtime_task_id(commit_sha: str | None, diff_text: str) -> str:
    """Generate a stable review spike task id before orchestration ids exist."""
    digest = hashlib.sha256(diff_text.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"review-spike-{commit_sha or digest}"


def build_command_task_id(command_name: str, runtime: str, user_request: str, project_root: str) -> str:
    """Generate a stable task id for command compilation workflows."""
    digest_source = "::".join([command_name, runtime, str(project_root), user_request])
    digest = hashlib.sha256(digest_source.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"{command_name}-{runtime}-{digest}"


def extract_changed_files(diff_text: str) -> list[str]:
    """Extract changed file paths from a unified diff."""
    changed_files: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+++ b/"):
            continue
        path = line[6:].strip()
        if not path or path == "/dev/null":
            continue
        normalized = PurePosixPath(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            continue
        safe_path = normalized.as_posix()
        if safe_path and safe_path not in changed_files:
            changed_files.append(safe_path)
    return changed_files


def compile_review_task(
    diff_text: str,
    spec_text: str,
    project_root: str,
    commit_sha: str | None,
    metadata: dict[str, object] | None = None,
) -> tuple[RuntimeTask, ReviewContextSummary]:
    """Build the shared BR3-owned review task envelope used by both runtimes."""
    task_id = build_runtime_task_id(commit_sha, diff_text)
    changed_files = extract_changed_files(diff_text)
    summary = ReviewContextSummary(
        task_id=task_id,
        dispatch_mode="parallel_shadow",
        changed_files=changed_files,
        file_count=len(changed_files),
        diff_line_count=len(diff_text.splitlines()),
        diff_chars=len(diff_text),
        spec_chars=len(spec_text),
        project_root=project_root,
        commit_sha=commit_sha or "shadow-unpinned",
    )
    task_metadata = {
        "mode": "parallel_shadow",
        "live_routing_changed": False,
        **summary.to_metadata(),
    }
    if metadata:
        task_metadata.update(metadata)
    task = RuntimeTask(
        task_id=task_id,
        task_type="review",
        diff_text=diff_text,
        spec_text=spec_text,
        project_root=project_root,
        commit_sha=summary.commit_sha,
        metadata=task_metadata,
    )
    return task, summary


def compile_command_task(
    *,
    command_name: str,
    runtime: str,
    project_root: str,
    user_request: str,
    task_type: str = "plan",
    metadata: dict[str, object] | None = None,
) -> tuple[RuntimeTask, CommandContextSummary]:
    """Compile a runtime-neutral command bundle into a BR3 task envelope."""
    bundle = compile_command_bundle(
        command_name=command_name,
        runtime=runtime,
        project_root=project_root,
        user_request=user_request,
    )
    task_id = build_command_task_id(command_name, runtime, user_request, project_root)
    summary = CommandContextSummary(
        task_id=task_id,
        command_name=bundle.command_name,
        runtime=runtime,
        support_level=bundle.support_level,
        skill_names=[skill.target_name for skill in bundle.skill_mappings],
        context_files=[item.path for item in bundle.context_files],
        project_root=project_root,
    )
    task_metadata = {
        "mode": "compiled_command_bundle",
        "live_routing_changed": False,
        "dispatch_mode": "direct",
        **summary.to_metadata(),
        "fallback_runtime": bundle.fallback_runtime,
        "workflow_name": bundle.workflow_name,
        "command_doc_path": bundle.command_doc_path,
    }
    if metadata:
        task_metadata.update(metadata)
    task = RuntimeTask(
        task_id=task_id,
        task_type=task_type,
        diff_text="",
        spec_text=bundle.render_prompt(),
        project_root=project_root,
        commit_sha="command-bundle-unpinned",
        metadata=task_metadata,
    )
    return task, summary
