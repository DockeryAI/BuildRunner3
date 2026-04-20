"""Normalize runtime edits into BR3-owned canonical edit records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Any

from core.runtime.result_schema import ObservedChange


CANONICAL_EDIT_KINDS = {
    "write_file",
    "replace_range",
    "unified_diff",
    "shell_action",
    "advisory_only",
}


@dataclass
class NormalizedEdit:
    """Canonical BR3 edit proposal or authoritative edit."""

    edit_type: str
    source_runtime: str
    path: str | None = None
    content: str | None = None
    replacement: str | None = None
    diff: str | None = None
    command: str | list[str] | None = None
    start_line: int | None = None
    end_line: int | None = None
    authoritative: bool = True
    task_id: str | None = None
    proposal_kind: str | None = None
    conflict_state: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sanitize_path(path: str | None) -> str | None:
    if not path:
        return None
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"Unsupported edit path: {path}")
    return normalized.as_posix()


def _canonical_kind(raw_kind: str) -> str:
    mapping = {
        "full_file_rewrite": "write_file",
        "write": "write_file",
        "replace": "replace_range",
        "range_replace": "replace_range",
        "patch": "unified_diff",
        "diff": "unified_diff",
        "shell": "shell_action",
    }
    canonical = mapping.get(raw_kind, raw_kind)
    if canonical not in CANONICAL_EDIT_KINDS:
        raise ValueError(f"Unsupported edit type: {raw_kind}")
    return canonical


def normalize_edit(
    raw_edit: dict[str, Any],
    *,
    source_runtime: str,
    authoritative: bool,
    task_id: str | None = None,
) -> NormalizedEdit:
    """Normalize one runtime edit payload into a BR3 edit record."""
    raw_kind = str(raw_edit.get("type") or raw_edit.get("edit_type") or "").strip()
    canonical_kind = _canonical_kind(raw_kind)

    if canonical_kind == "write_file":
        normalized = NormalizedEdit(
            edit_type="write_file",
            source_runtime=source_runtime,
            path=_sanitize_path(raw_edit.get("path")),
            content=raw_edit.get("content") or raw_edit.get("text"),
            authoritative=authoritative,
            task_id=task_id,
            metadata={k: v for k, v in raw_edit.items() if k not in {"type", "edit_type", "path", "content", "text"}},
        )
    elif canonical_kind == "replace_range":
        normalized = NormalizedEdit(
            edit_type="replace_range",
            source_runtime=source_runtime,
            path=_sanitize_path(raw_edit.get("path")),
            replacement=raw_edit.get("replacement") or raw_edit.get("content"),
            start_line=raw_edit.get("start_line"),
            end_line=raw_edit.get("end_line"),
            authoritative=authoritative,
            task_id=task_id,
            metadata={k: v for k, v in raw_edit.items() if k not in {"type", "edit_type", "path", "replacement", "content", "start_line", "end_line"}},
        )
    elif canonical_kind == "unified_diff":
        normalized = NormalizedEdit(
            edit_type="unified_diff",
            source_runtime=source_runtime,
            diff=raw_edit.get("diff") or raw_edit.get("content"),
            authoritative=authoritative,
            task_id=task_id,
            metadata={k: v for k, v in raw_edit.items() if k not in {"type", "edit_type", "diff", "content"}},
        )
    elif canonical_kind == "shell_action":
        normalized = NormalizedEdit(
            edit_type="shell_action",
            source_runtime=source_runtime,
            command=raw_edit.get("command"),
            authoritative=authoritative,
            task_id=task_id,
            metadata={k: v for k, v in raw_edit.items() if k not in {"type", "edit_type", "command"}},
        )
    else:
        normalized = NormalizedEdit(
            edit_type="advisory_only",
            source_runtime=source_runtime,
            authoritative=False,
            task_id=task_id,
            metadata=dict(raw_edit),
        )

    if authoritative:
        return normalized

    return NormalizedEdit(
        edit_type="advisory_only",
        source_runtime=source_runtime,
        path=normalized.path,
        authoritative=False,
        task_id=task_id,
        proposal_kind=normalized.edit_type,
        metadata={"proposal": normalized.to_dict()},
    )


def normalize_edits(
    raw_edits: list[dict[str, Any]] | None,
    *,
    source_runtime: str,
    authoritative: bool,
    task_id: str | None = None,
) -> list[NormalizedEdit]:
    """Normalize a list of runtime edit payloads."""
    return [
        normalize_edit(edit, source_runtime=source_runtime, authoritative=authoritative, task_id=task_id)
        for edit in (raw_edits or [])
    ]


def observed_changes_from_workspace_diff(workspace_diff: str) -> list[ObservedChange]:
    """Infer changed files from a unified diff."""
    changes: list[ObservedChange] = []
    seen_paths: set[str] = set()
    for line in workspace_diff.splitlines():
        if not line.startswith("+++ b/"):
            continue
        path = _sanitize_path(line[6:].strip())
        if not path or path == "/dev/null" or path in seen_paths:
            continue
        seen_paths.add(path)
        changes.append(ObservedChange(path=path, change_type="modified", source="workspace_diff"))
    return changes


def observed_changes_from_shell_actions(shell_actions: list[dict[str, Any]] | None) -> list[ObservedChange]:
    """Infer touched files from shell action metadata when available."""
    changes: list[ObservedChange] = []
    for action in shell_actions or []:
        for path in action.get("touched_files", []) or []:
            safe_path = _sanitize_path(path)
            if not safe_path:
                continue
            changes.append(ObservedChange(path=safe_path, change_type="modified", source="shell_action"))
    return changes


def build_normalized_edit_bundle(
    *,
    raw_edits: list[dict[str, Any]] | None,
    workspace_diff: str,
    shell_actions: list[dict[str, Any]] | None,
    source_runtime: str,
    authoritative: bool,
    task_id: str | None = None,
) -> tuple[list[NormalizedEdit], list[ObservedChange]]:
    """Build normalized edits plus observed changes from all available evidence."""
    edits = normalize_edits(
        raw_edits,
        source_runtime=source_runtime,
        authoritative=authoritative,
        task_id=task_id,
    )
    observed_changes = observed_changes_from_workspace_diff(workspace_diff)
    observed_changes.extend(observed_changes_from_shell_actions(shell_actions))
    return edits, observed_changes


def mark_conflicted_proposals(task_id: str, edits: list[NormalizedEdit]) -> tuple[str | None, list[NormalizedEdit]]:
    """Fail closed when more than one runtime proposes touching the same file for one task."""
    path_to_runtimes: dict[str, set[str]] = {}
    for edit in edits:
        if edit.path:
            path_to_runtimes.setdefault(edit.path, set()).add(edit.source_runtime)

    conflicted_paths = {path for path, runtimes in path_to_runtimes.items() if len(runtimes) > 1}
    if not conflicted_paths:
        return None, edits

    updated: list[NormalizedEdit] = []
    for edit in edits:
        if edit.path in conflicted_paths:
            edit.conflict_state = "conflicted_proposal"
            edit.task_id = task_id
        updated.append(edit)
    return "conflicted_proposal", updated
