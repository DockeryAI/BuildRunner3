"""Runtime abstraction scaffold for BR3 Phase 1 review spikes."""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "BaseRuntime": ("core.runtime.base", "BaseRuntime"),
    "CapabilityProfile": ("core.runtime.capabilities", "CapabilityProfile"),
    "shape_bundle": ("core.runtime.cache_policy", "shape_bundle"),
    "ClaudeRuntime": ("core.runtime.claude_runtime", "ClaudeRuntime"),
    "CommandContextFile": ("core.runtime.command_compiler", "CommandContextFile"),
    "CompiledCommandBundle": ("core.runtime.command_compiler", "CompiledCommandBundle"),
    "SkillTranslation": ("core.runtime.command_compiler", "SkillTranslation"),
    "compile_command_bundle": ("core.runtime.command_compiler", "compile_command_bundle"),
    "load_command_capabilities": ("core.runtime.command_compiler", "load_command_capabilities"),
    "load_command_inventory": ("core.runtime.command_compiler", "load_command_inventory"),
    "CodexRuntime": ("core.runtime.codex_runtime", "CodexRuntime"),
    "RuntimeResolution": ("core.runtime.config", "RuntimeResolution"),
    "apply_runtime_selection": ("core.runtime.config", "apply_runtime_selection"),
    "resolve_runtime_selection": ("core.runtime.config", "resolve_runtime_selection"),
    "CommandContextSummary": ("core.runtime.context_compiler", "CommandContextSummary"),
    "build_command_task_id": ("core.runtime.context_compiler", "build_command_task_id"),
    "compile_command_task": ("core.runtime.context_compiler", "compile_command_task"),
    "ReviewContextSummary": ("core.runtime.context_compiler", "ReviewContextSummary"),
    "build_runtime_task_id": ("core.runtime.context_compiler", "build_runtime_task_id"),
    "compile_review_task": ("core.runtime.context_compiler", "compile_review_task"),
    "extract_changed_files": ("core.runtime.context_compiler", "extract_changed_files"),
    "NormalizedEdit": ("core.runtime.edit_normalizer", "NormalizedEdit"),
    "build_normalized_edit_bundle": ("core.runtime.edit_normalizer", "build_normalized_edit_bundle"),
    "mark_conflicted_proposals": ("core.runtime.edit_normalizer", "mark_conflicted_proposals"),
    "normalize_edits": ("core.runtime.edit_normalizer", "normalize_edits"),
    "RuntimeCompatibilityError": ("core.runtime.errors", "RuntimeCompatibilityError"),
    "RuntimeConflictError": ("core.runtime.errors", "RuntimeConflictError"),
    "RuntimeErrorInfo": ("core.runtime.errors", "RuntimeErrorInfo"),
    "RuntimeExecutionError": ("core.runtime.errors", "RuntimeExecutionError"),
    "RuntimeValidationError": ("core.runtime.errors", "RuntimeValidationError"),
    "OrchestrationCheckpointStore": (
        "core.runtime.orchestration_checkpoint_store",
        "OrchestrationCheckpointStore",
    ),
    "PolicyEvaluation": ("core.runtime.policy_result", "PolicyEvaluation"),
    "PolicyResult": ("core.runtime.policy_result", "PolicyResult"),
    "build_recall_query": ("core.runtime.postflight", "build_recall_query"),
    "collect_session_snapshot": ("core.runtime.postflight", "collect_session_snapshot"),
    "evaluate_runtime_alerts": ("core.runtime.postflight", "evaluate_runtime_alerts"),
    "evaluate_runtime_task_postflight": (
        "core.runtime.postflight",
        "evaluate_runtime_task_postflight",
    ),
    "list_high_risk_staged_files": ("core.runtime.postflight", "list_high_risk_staged_files"),
    "evaluate_build_gates": ("core.runtime.preflight", "evaluate_build_gates"),
    "evaluate_prompt_file": ("core.runtime.preflight", "evaluate_prompt_file"),
    "evaluate_protected_files": ("core.runtime.preflight", "evaluate_protected_files"),
    "evaluate_runtime_task_preflight": (
        "core.runtime.preflight",
        "evaluate_runtime_task_preflight",
    ),
    "is_protected_file": ("core.runtime.preflight", "is_protected_file"),
    "load_claude_first_commands": ("core.runtime.preflight", "load_claude_first_commands"),
    "CheckpointRecord": ("core.runtime.result_schema", "CheckpointRecord"),
    "ObservedChange": ("core.runtime.result_schema", "ObservedChange"),
    "StreamEvent": ("core.runtime.result_schema", "StreamEvent"),
    "RuntimeRegistration": ("core.runtime.runtime_registry", "RuntimeRegistration"),
    "RuntimeRegistry": ("core.runtime.runtime_registry", "RuntimeRegistry"),
    "create_runtime_registry": ("core.runtime.runtime_registry", "create_runtime_registry"),
    "create_phase1_runtime_registry": (
        "core.runtime.runtime_registry",
        "create_phase1_runtime_registry",
    ),
    "RuntimeFinding": ("core.runtime.types", "RuntimeFinding"),
    "RuntimeResult": ("core.runtime.types", "RuntimeResult"),
    "RuntimeTask": ("core.runtime.types", "RuntimeTask"),
    "SpecWorkflowRequest": ("core.runtime.workflows", "SpecWorkflowRequest"),
    "SpecWorkflowResult": ("core.runtime.workflows", "SpecWorkflowResult"),
    "run_spec_workflow": ("core.runtime.workflows", "run_spec_workflow"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
