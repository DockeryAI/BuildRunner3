"""Runtime abstraction scaffold for BR3 Phase 1 review spikes."""

from core.runtime.base import BaseRuntime
from core.runtime.capabilities import CapabilityProfile
from core.runtime.claude_runtime import ClaudeRuntime
from core.runtime.command_compiler import (
    CommandContextFile,
    CompiledCommandBundle,
    SkillTranslation,
    compile_command_bundle,
    load_command_capabilities,
    load_command_inventory,
)
from core.runtime.config import RuntimeResolution, apply_runtime_selection, resolve_runtime_selection
from core.runtime.context_compiler import (
    CommandContextSummary,
    ReviewContextSummary,
    build_command_task_id,
    compile_command_task,
    build_runtime_task_id,
    compile_review_task,
    extract_changed_files,
)
from core.runtime.codex_runtime import CodexRuntime
from core.runtime.edit_normalizer import (
    NormalizedEdit,
    build_normalized_edit_bundle,
    mark_conflicted_proposals,
    normalize_edits,
)
from core.runtime.errors import (
    RuntimeCompatibilityError,
    RuntimeConflictError,
    RuntimeErrorInfo,
    RuntimeExecutionError,
    RuntimeValidationError,
)
from core.runtime.orchestration_checkpoint_store import OrchestrationCheckpointStore
from core.runtime.policy_result import PolicyEvaluation, PolicyResult
from core.runtime.postflight import (
    build_recall_query,
    collect_session_snapshot,
    evaluate_runtime_alerts,
    evaluate_runtime_task_postflight,
    list_high_risk_staged_files,
)
from core.runtime.preflight import (
    evaluate_build_gates,
    evaluate_prompt_file,
    evaluate_protected_files,
    evaluate_runtime_task_preflight,
    is_protected_file,
    load_claude_first_commands,
)
from core.runtime.result_schema import CheckpointRecord, ObservedChange, StreamEvent
from core.runtime.runtime_registry import (
    RuntimeRegistration,
    RuntimeRegistry,
    create_runtime_registry,
    create_phase1_runtime_registry,
)
from core.runtime.types import RuntimeFinding, RuntimeResult, RuntimeTask
from core.runtime.workflows import SpecWorkflowRequest, SpecWorkflowResult, run_spec_workflow

__all__ = [
    "BaseRuntime",
    "CapabilityProfile",
    "ClaudeRuntime",
    "CommandContextFile",
    "CompiledCommandBundle",
    "SkillTranslation",
    "compile_command_bundle",
    "load_command_capabilities",
    "load_command_inventory",
    "CodexRuntime",
    "RuntimeResolution",
    "apply_runtime_selection",
    "resolve_runtime_selection",
    "CommandContextSummary",
    "build_command_task_id",
    "compile_command_task",
    "ReviewContextSummary",
    "build_runtime_task_id",
    "compile_review_task",
    "extract_changed_files",
    "NormalizedEdit",
    "build_normalized_edit_bundle",
    "mark_conflicted_proposals",
    "normalize_edits",
    "RuntimeCompatibilityError",
    "RuntimeConflictError",
    "RuntimeErrorInfo",
    "RuntimeExecutionError",
    "RuntimeValidationError",
    "OrchestrationCheckpointStore",
    "PolicyEvaluation",
    "PolicyResult",
    "build_recall_query",
    "collect_session_snapshot",
    "evaluate_runtime_alerts",
    "evaluate_runtime_task_postflight",
    "list_high_risk_staged_files",
    "evaluate_build_gates",
    "evaluate_prompt_file",
    "evaluate_protected_files",
    "evaluate_runtime_task_preflight",
    "is_protected_file",
    "load_claude_first_commands",
    "CheckpointRecord",
    "ObservedChange",
    "StreamEvent",
    "RuntimeRegistration",
    "RuntimeRegistry",
    "create_runtime_registry",
    "create_phase1_runtime_registry",
    "RuntimeFinding",
    "RuntimeResult",
    "RuntimeTask",
    "SpecWorkflowRequest",
    "SpecWorkflowResult",
    "run_spec_workflow",
]
