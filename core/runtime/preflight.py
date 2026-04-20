"""Shared BR3 runtime preflight policy extraction."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from functools import lru_cache
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
from typing import Any

from core.runtime.policy_result import (
    POLICY_ACTION_BLOCK,
    POLICY_ACTION_PASS,
    POLICY_ACTION_WARN,
    PolicyEvaluation,
    build_hook_payload,
)
from core.runtime.types import RuntimeTask


PROTECTED_PATH_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*id_rsa*",
    "*id_ed25519*",
    "secrets.*",
)
DEFAULT_CLAUDE_FIRST_COMMANDS = {
    "amend",
    "appdesign",
    "autopilot",
    "begin",
    "brainstorm",
    "design",
    "gaps",
    "guardrails",
    "learn",
    "llm",
    "opus",
    "prompt",
    "recraft",
    "research",
    "research-audit",
    "roadmap",
    "spec",
    "worktree",
}
SHADOW_SAFE_COMMANDS = {"review", "guard", "why", "diag", "plan_critique", "adversarial_review"}
PROMPT_PATTERN = re.compile(
    r"<identity>|<task>|<constraints>|<procedure>|<behavioral_rules>|<scope_constraints>|"
    r"claude -p|<system>|(?:^|\b)(?:system prompt|system_prompt|systemPrompt)\b|"
    r"You are (a |an )?(headless|build|autopilot|remote)",
    flags=re.IGNORECASE,
)
PROMPT_PATH_PATTERN = re.compile(r"prompt|system|skill|build|agent", flags=re.IGNORECASE)
PHASE_HEADING_PATTERN = re.compile(r"^### (?:Phase|NEW Phase)", flags=re.MULTILINE)
COMPLETE_PHASE_PATTERN = re.compile(r"Status.*(?:COMPLETE|✅)", flags=re.IGNORECASE)


def _inventory_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".buildrunner" / "runtime-command-inventory.json"


def _capability_map_path() -> Path:
    return Path(__file__).resolve().parent / "command_capabilities.json"


@lru_cache(maxsize=1)
def load_claude_first_commands() -> set[str]:
    inventory_path = _inventory_path()
    if not inventory_path.exists():
        return set(DEFAULT_CLAUDE_FIRST_COMMANDS)
    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("runtime-command-inventory.json must contain an object at the top level")
        commands = payload.get("commands", [])
        if not isinstance(commands, list):
            raise ValueError("runtime-command-inventory.json.commands must be a list")
        names = {
            str(item.get("name") or str(item.get("command", "")).lstrip("/")).strip()
            for item in commands
            if isinstance(item, dict)
        }
        filtered = {
            name
            for item in commands
            if isinstance(item, dict)
            if item.get("portability_rating") == "claude_first"
            or item.get("migration_bucket") == "keep-Claude-first"
            or item.get("fallback_runtime") == "claude"
            for name in [str(item.get("name") or str(item.get("command", "")).lstrip("/")).strip()]
        }
        return {name for name in filtered if name}
    except (OSError, json.JSONDecodeError, ValueError):
        return set(DEFAULT_CLAUDE_FIRST_COMMANDS)


@lru_cache(maxsize=1)
def load_command_capability_map() -> dict[str, dict[str, Any]]:
    path = _capability_map_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        commands = payload.get("commands", {})
        if not isinstance(commands, dict):
            raise ValueError("command_capabilities.json.commands must be an object")
        return {
            str(name).strip().lower(): value
            for name, value in commands.items()
            if isinstance(value, dict) and str(name).strip()
        }
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _evaluate_command_support(
    *,
    command_name: str,
    runtime_name: str,
    dispatch_mode: str,
    workflow_name: str,
) -> tuple[str, str]:
    capabilities = load_command_capability_map().get(command_name, {})
    support_level = str(capabilities.get("support_level") or "").strip().lower()

    if runtime_name != "codex":
        return POLICY_ACTION_PASS, "Runtime command gate passed."

    if support_level == "codex_ready":
        return POLICY_ACTION_PASS, "Command is explicitly enabled for Codex."
    if support_level == "codex_shadow_only":
        if dispatch_mode == "parallel_shadow":
            return POLICY_ACTION_PASS, "Command is enabled for Codex shadow execution only."
        return (
            POLICY_ACTION_BLOCK,
            f"Command '{command_name}' is restricted to Codex advisory shadow mode.",
        )
    if support_level == "codex_workflow_only":
        allowed_workflow = str(capabilities.get("workflow_name") or "").strip()
        if workflow_name and workflow_name == allowed_workflow:
            return POLICY_ACTION_PASS, "Command is enabled for the BR3-owned Codex workflow."
        return (
            POLICY_ACTION_BLOCK,
            f"Command '{command_name}' is only enabled for the BR3-owned workflow path.",
        )
    if support_level == "claude_only":
        return (
            POLICY_ACTION_BLOCK,
            f"Command '{command_name}' remains Claude-first under the locked migration plan.",
        )

    if command_name in load_claude_first_commands() and not (
        dispatch_mode == "parallel_shadow" and command_name in SHADOW_SAFE_COMMANDS
    ):
        return (
            POLICY_ACTION_BLOCK,
            f"Command '{command_name}' remains Claude-first under the locked migration plan.",
        )
    return POLICY_ACTION_PASS, "Runtime command gate passed."


def _normalize_file_path(path: str) -> str:
    try:
        return PurePosixPath(path).as_posix()
    except Exception:
        return path.replace("\\", "/")


def is_protected_file(path: str) -> bool:
    normalized = _normalize_file_path(path)
    basename = PurePosixPath(normalized).name
    for pattern in PROTECTED_PATH_PATTERNS:
        if "/" in pattern:
            if fnmatch(normalized, pattern):
                return True
            continue
        if fnmatch(basename, pattern):
            return True
    return False


def evaluate_protected_files(file_paths: list[str], *, stage: str = "preflight") -> PolicyEvaluation:
    evaluation = PolicyEvaluation(stage=stage)
    protected = sorted({path for path in file_paths if path and is_protected_file(path)})
    if protected:
        evaluation.add(
            policy_id="protected_files",
            action=POLICY_ACTION_BLOCK,
            message="Protected files require manual handling outside shared runtime execution.",
            details={"files": protected},
        )
    else:
        evaluation.add(
            policy_id="protected_files",
            action=POLICY_ACTION_PASS,
            message="No protected files detected in scope.",
        )
    return evaluation


def evaluate_prompt_file(path: str, content: str) -> PolicyEvaluation:
    evaluation = PolicyEvaluation(stage="preflight")
    if path and PROMPT_PATTERN.search(content or ""):
        basename = Path(path).name
        evaluation.add(
            policy_id="prompt_research_guard",
            action=POLICY_ACTION_WARN,
            message=f"Prompt-like file detected: {basename}",
            details={"file": path},
        )
        evaluation.extend_context(
            (
                f"PROMPT FILE DETECTED: {basename}. Before editing LLM prompts, ensure the "
                "session has current research context loaded. Prefer structured tags, tighter "
                "scope constraints, and avoid accidental planner drift."
            )
        )
    else:
        evaluation.add(
            policy_id="prompt_research_guard",
            action=POLICY_ACTION_PASS,
            message="No prompt-style file content detected.",
        )
    return evaluation


def _read_json_stdin() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _extract_project_dir(file_path: str) -> str:
    normalized = _normalize_file_path(file_path)
    build_marker = "/.buildrunner/builds/BUILD_"
    if build_marker in normalized:
        return normalized.split(build_marker)[0]
    return str(Path(file_path).resolve().parent)


def evaluate_build_gates(
    *,
    file_path: str,
    new_string: str,
    old_string: str,
    project_dir: str,
) -> PolicyEvaluation:
    evaluation = PolicyEvaluation(stage="preflight")

    normalized_file_path = _normalize_file_path(file_path)
    if "/.buildrunner/builds/BUILD_" not in normalized_file_path or not normalized_file_path.endswith(".md"):
        evaluation.add(
            policy_id="build_gates",
            action=POLICY_ACTION_PASS,
            message="Not a BUILD spec edit.",
        )
        return evaluation

    state_file = Path(project_dir) / ".buildrunner" / "skill-state.json"
    plans_dir = Path(project_dir) / ".buildrunner" / "plans"
    review_dir = Path(project_dir) / ".buildrunner" / "adversarial-reviews"
    review_1 = plans_dir / "amend-adversarial-findings.json"
    review_2 = plans_dir / "spec-adversarial-findings.json"

    if (
        ("## Overview" in new_string and "## Overview" not in old_string)
        or ("## Summary" in new_string and "## Summary" not in old_string)
    ):
        if not state_file.exists():
            evaluation.add(
                policy_id="build_spec_creation_gate",
                action=POLICY_ACTION_BLOCK,
                message="Cannot create BUILD spec without skill-state.json.",
                details={"required": ["3.7", "3.8"]},
            )
            return evaluation
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            spec = state.get("spec", {})
        except Exception as exc:
            evaluation.add(
                policy_id="build_spec_creation_gate",
                action=POLICY_ACTION_BLOCK,
                message=f"Failed reading skill-state.json: {exc}",
            )
            return evaluation

        missing = []
        if "3.7" not in spec:
            missing.append("3.7 (adversarial review)")
        if "3.8" not in spec:
            missing.append("3.8 (architecture validation)")
        if missing:
            evaluation.add(
                policy_id="build_spec_creation_gate",
                action=POLICY_ACTION_BLOCK,
                message=f"Cannot write BUILD spec; missing prerequisites: {', '.join(missing)}.",
                details={"missing": missing},
            )
            return evaluation

    new_phases = len(PHASE_HEADING_PATTERN.findall(new_string))
    old_phases = len(PHASE_HEADING_PATTERN.findall(old_string))
    if new_phases > old_phases:
        tracking_artifacts = sorted(review_dir.glob("phase-*.json")) if review_dir.exists() else []
        artifact = tracking_artifacts[-1] if tracking_artifacts else review_1 if review_1.exists() else review_2 if review_2.exists() else None
        if artifact is None:
            evaluation.add(
                policy_id="build_amend_review_gate",
                action=POLICY_ACTION_BLOCK,
                message="New BUILD phases require recorded adversarial review before edit application.",
                details={"added_phases": new_phases - old_phases},
            )
            return evaluation
        try:
            findings_data = json.loads(artifact.read_text(encoding="utf-8"))
            if isinstance(findings_data, list):
                findings = findings_data
                blockers = [item for item in findings if item.get("severity") == "blocker" and not item.get("resolved")]
            else:
                blockers = list(findings_data.get("consensus_blockers", []))
                blockers.extend(findings_data.get("unresolved_disagreements", []))
        except Exception:
            blockers = []
        if blockers:
            evaluation.add(
                policy_id="build_amend_review_gate",
                action=POLICY_ACTION_BLOCK,
                message=f"Unresolved adversarial blockers remain in {artifact.name}.",
                details={"artifact": str(artifact), "blocker_count": len(blockers)},
            )
            return evaluation

    if COMPLETE_PHASE_PATTERN.search(old_string):
        unchecked_task_pattern = r"^\s*-\s*\[\s*\]"
        new_tasks = len(re.findall(unchecked_task_pattern, new_string, flags=re.MULTILINE))
        old_tasks = len(re.findall(unchecked_task_pattern, old_string, flags=re.MULTILINE))
        if new_tasks > old_tasks:
            evaluation.add(
                policy_id="complete_phase_mutation",
                action=POLICY_ACTION_BLOCK,
                message="Cannot add tasks to a COMPLETE phase; create a new phase instead.",
            )
            return evaluation

    evaluation.add(
        policy_id="build_gates",
        action=POLICY_ACTION_PASS,
        message="BUILD/spec gates passed.",
    )
    return evaluation


def evaluate_runtime_task_preflight(task: RuntimeTask, runtime_name: str) -> PolicyEvaluation:
    evaluation = PolicyEvaluation(stage="preflight")
    changed_files = [str(path) for path in task.metadata.get("changed_files", [])]
    dispatch_mode = str(task.metadata.get("dispatch_mode") or "").strip()
    workflow_name = str(task.metadata.get("workflow_name") or "").strip()
    protected = evaluate_protected_files(changed_files)
    evaluation.results.extend(protected.results)

    command_name = str(task.metadata.get("command_name") or "").strip().lower()
    action, message = _evaluate_command_support(
        command_name=command_name,
        runtime_name=runtime_name,
        dispatch_mode=dispatch_mode,
        workflow_name=workflow_name,
    )
    evaluation.add(
        policy_id="runtime_command_gate",
        action=action,
        message=message,
        details={
            "command_name": command_name,
            "runtime": runtime_name,
            "dispatch_mode": dispatch_mode,
            "workflow_name": workflow_name,
        },
    )

    prompt_candidates = []
    if changed_files:
        prompt_candidates.extend([path for path in changed_files if PROMPT_PATH_PATTERN.search(path)])
    if task.spec_text and PROMPT_PATTERN.search(task.spec_text):
        prompt_candidates.append("spec_text")
    if task.diff_text and PROMPT_PATTERN.search(task.diff_text):
        prompt_candidates.append("diff_text")
    if prompt_candidates:
        evaluation.add(
            policy_id="prompt_research_guard",
            action=POLICY_ACTION_WARN,
            message="Prompt-like content detected in task scope; ensure research context is current.",
            details={"matches": prompt_candidates},
        )
    else:
        evaluation.add(
            policy_id="prompt_research_guard",
            action=POLICY_ACTION_PASS,
            message="No prompt-like content detected in task scope.",
        )

    return evaluation


def emit_hook_json(message: str, event_name: str = "PreToolUse") -> None:
    print(json.dumps(build_hook_payload(message, event_name)))


def _handle_protect_files() -> int:
    payload = _read_json_stdin()
    file_path = payload.get("tool_input", {}).get("file_path", "")
    evaluation = evaluate_protected_files([file_path])
    if evaluation.blocked:
        print(f"BLOCKED: {evaluation.results[0].message}", file=sys.stderr)
        files = evaluation.results[0].details.get("files", [])
        if files:
            print("Files:", ", ".join(files), file=sys.stderr)
        return 2
    return 0


def _handle_build_gates() -> int:
    payload = _read_json_stdin()
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    evaluation = evaluate_build_gates(
        file_path=file_path,
        new_string=tool_input.get("new_string", "") or "",
        old_string=tool_input.get("old_string", "") or "",
        project_dir=_extract_project_dir(file_path),
    )
    if evaluation.blocked:
        for result in evaluation.results:
            if result.action == POLICY_ACTION_BLOCK:
                print(f"BLOCKED: {result.message}", file=sys.stderr)
        return 2
    return 0


def _handle_prompt_advice() -> int:
    payload = _read_json_stdin()
    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path or not os.path.isfile(file_path):
        return 0
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return 0
    if size >= 500_000:
        return 0
    content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    evaluation = evaluate_prompt_file(file_path, content)
    if evaluation.additional_context:
        emit_hook_json("\n".join(evaluation.additional_context))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared BR3 runtime preflight policies")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("protect-files")
    subparsers.add_parser("build-gates")
    subparsers.add_parser("prompt-advice")
    args = parser.parse_args()

    if args.command == "protect-files":
        return _handle_protect_files()
    if args.command == "build-gates":
        return _handle_build_gates()
    if args.command == "prompt-advice":
        return _handle_prompt_advice()
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
