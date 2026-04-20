"""
Execute API Routes

Provides endpoint for executing BuildRunner CLI commands from the web interface.
This enables the UI to have full CLI functionality.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional
import subprocess
import os
from pathlib import Path

from core.runtime.config import RuntimeConfigError, resolve_runtime_selection
from core.runtime.workflows import BeginWorkflowRequest as RuntimeBeginWorkflowRequest
from core.runtime.workflows import run_begin_workflow
from core.runtime.workflows import SpecWorkflowRequest as RuntimeSpecWorkflowRequest
from core.runtime.workflows import run_spec_workflow

router = APIRouter()


class ExecuteRequest(BaseModel):
    """Request model for command execution"""

    command: str
    cwd: Optional[str] = None
    runtime: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Response model for command execution"""

    output: str
    error: Optional[str] = None
    return_code: int
    resolved_runtime: Optional[str] = None
    runtime_source: Optional[str] = None


class ReviewSpikeRequest(BaseModel):
    """Explicit Phase 1 shadow review request."""

    diff_text: str
    spec_text: str
    project_root: Optional[str] = None
    commit_sha: Optional[str] = None
    runtime: Optional[str] = None
    runtimes: list[str] = Field(default_factory=lambda: ["claude", "codex"])


class ReviewSpikeResponse(BaseModel):
    """Normalized review spike response envelope."""

    task_id: str
    mode: str
    dispatch_mode: str
    live_routing_changed: bool
    selected_runtimes: list[dict[str, Any]]
    task_metadata: dict[str, Any]
    results: list[dict[str, Any]]


class RuntimeResolutionResponse(BaseModel):
    """Resolved runtime selection and provenance."""

    runtime: str
    source: str
    explicit_runtime: Optional[str] = None
    project_config_path: Optional[str] = None
    user_config_path: Optional[str] = None
    available_runtimes: list[str]


class SpecWorkflowRequest(BaseModel):
    """Explicit BR3-owned Codex `/spec` workflow request."""

    user_request: str
    project_root: Optional[str] = None
    runtime: str = "codex"
    draft_path: Optional[str] = None


class SpecWorkflowResponse(BaseModel):
    """Structured response for the BR3-owned Codex `/spec` workflow."""

    task_id: str
    status: str
    runtime: str
    support_level: str
    draft_path: Optional[str] = None
    fallback_runtime: Optional[str] = None
    validation_exit_code: Optional[int] = None
    validation_output: Optional[str] = None
    adversarial_findings: list[dict[str, Any]] = Field(default_factory=list)
    runtime_result: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class BeginWorkflowRequest(BaseModel):
    """Explicit BR3-owned bounded Codex `/begin` workflow request."""

    user_request: str
    project_root: Optional[str] = None
    runtime: str = "codex"
    build_path: Optional[str] = None
    max_phases: int = 5
    approval_granted: bool = False
    allowed_phase_numbers: list[int] = Field(default_factory=list)


class BeginWorkflowPhaseResponse(BaseModel):
    phase_number: int
    phase_name: str
    status: str
    gate: dict[str, Any]
    runtime_result: dict[str, Any] = Field(default_factory=dict)
    lock_path: Optional[str] = None
    progress_path: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class BeginWorkflowResponse(BaseModel):
    task_id: str
    status: str
    runtime: str
    support_level: str
    build_path: Optional[str] = None
    fallback_runtime: Optional[str] = None
    phase_results: list[BeginWorkflowPhaseResponse] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


@router.post("/execute", response_model=ExecuteResponse)
async def execute_command(request: ExecuteRequest) -> ExecuteResponse:
    """
    Execute a BuildRunner CLI command.

    Args:
        request: Command to execute and optional working directory

    Returns:
        Command output, errors, and return code
    """
    try:
        # Validate command starts with 'br'
        if not request.command.strip().startswith("br"):
            raise HTTPException(
                status_code=400, detail="Only BuildRunner (br) commands are allowed"
            )

        # Use provided cwd or default to current directory
        cwd = request.cwd or str(Path.cwd())

        # Ensure cwd exists
        if not os.path.exists(cwd):
            raise HTTPException(status_code=400, detail=f"Working directory does not exist: {cwd}")

        resolution = resolve_runtime_selection(explicit_runtime=request.runtime, project_root=cwd)

        # Execute the command
        env = os.environ.copy()
        env["BR3_RUNTIME"] = resolution.runtime
        env["BR3_RUNTIME_SOURCE"] = resolution.source
        result = subprocess.run(
            request.command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,  # 60 second timeout
        )

        # Return the results
        return ExecuteResponse(
            output=result.stdout or result.stderr,
            error=result.stderr if result.returncode != 0 else None,
            return_code=result.returncode,
            resolved_runtime=resolution.runtime,
            runtime_source=resolution.source,
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command execution timeout (60 seconds)")
    except HTTPException:
        raise
    except RuntimeConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")


@router.post("/runtime/review-spike", response_model=ReviewSpikeResponse)
async def execute_review_spike(request: ReviewSpikeRequest) -> ReviewSpikeResponse:
    """
    Explicit shadow-only Phase 1 review spike.

    This does not modify the live BR3 runtime routing path.
    """
    allowed_runtimes = {"claude", "codex"}
    invalid_runtimes = sorted({runtime for runtime in request.runtimes if runtime not in allowed_runtimes})
    if invalid_runtimes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported runtimes for review spike: {', '.join(invalid_runtimes)}",
        )

    project_root = request.project_root or str(Path.cwd())
    if not os.path.exists(project_root):
        raise HTTPException(status_code=400, detail=f"Project root does not exist: {project_root}")

    if request.runtime:
        request.runtimes = [request.runtime]

    from core.cluster.cross_model_review import run_review_spike_async

    try:
        payload = await run_review_spike_async(
            diff_text=request.diff_text,
            spec_text=request.spec_text,
            commit_sha=request.commit_sha,
            project_root=project_root,
            runtimes=request.runtimes,
        )
        return ReviewSpikeResponse(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Review spike failed: {exc}") from exc


@router.get("/runtime/resolve", response_model=RuntimeResolutionResponse)
async def resolve_runtime(runtime: Optional[str] = None, cwd: Optional[str] = None) -> RuntimeResolutionResponse:
    """Resolve runtime selection using explicit -> project -> user -> default precedence."""
    project_root = cwd or str(Path.cwd())
    if not os.path.exists(project_root):
        raise HTTPException(status_code=400, detail=f"Working directory does not exist: {project_root}")
    try:
        resolution = resolve_runtime_selection(explicit_runtime=runtime, project_root=project_root)
        return RuntimeResolutionResponse(**resolution.to_dict())
    except RuntimeConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/runtime/spec-workflow", response_model=SpecWorkflowResponse)
async def execute_spec_workflow(request: SpecWorkflowRequest) -> SpecWorkflowResponse:
    """Run the BR3-owned Codex `/spec` workflow without changing live routing."""
    project_root = request.project_root or str(Path.cwd())
    if not os.path.exists(project_root):
        raise HTTPException(status_code=400, detail=f"Project root does not exist: {project_root}")
    try:
        result = await run_spec_workflow(
            RuntimeSpecWorkflowRequest(
                user_request=request.user_request,
                project_root=project_root,
                runtime=request.runtime,
                draft_path=request.draft_path,
            )
        )
        return SpecWorkflowResponse(**result.to_dict())
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Spec workflow failed: {exc}") from exc


@router.post("/runtime/begin-workflow", response_model=BeginWorkflowResponse)
async def execute_begin_workflow(request: BeginWorkflowRequest) -> BeginWorkflowResponse:
    """Run the BR3-owned bounded Codex `/begin` workflow without broadening live routing."""
    project_root = request.project_root or str(Path.cwd())
    if not os.path.exists(project_root):
        raise HTTPException(status_code=400, detail=f"Project root does not exist: {project_root}")
    try:
        result = await run_begin_workflow(
            RuntimeBeginWorkflowRequest(
                user_request=request.user_request,
                project_root=project_root,
                runtime=request.runtime,
                build_path=request.build_path,
                max_phases=request.max_phases,
                approval_granted=request.approval_granted,
                allowed_phase_numbers=request.allowed_phase_numbers,
            )
        )
        return BeginWorkflowResponse(**result.to_dict())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Begin workflow failed: {exc}") from exc


@router.get("/commands")
async def list_commands():
    """
    List available BuildRunner commands.

    Returns:
        List of available BR commands with descriptions
    """
    commands = {
        "init": "Initialize a new project",
        "run": "Run the build process",
        "status": "Check project status",
        "task list": "List all tasks",
        "quality check": "Run quality checks",
        "quality lint": "Run Ruff linter",
        "quality typecheck": "Run MyPy type checker",
        "quality fix": "Auto-fix formatting issues",
        "quality report": "Generate quality report",
        "quality score": "Show quality score",
        "agent list": "List AI agents",
        "agent assign": "Assign task to agent",
        "agent status": "Check agent status",
        "plan": "Start planning mode",
        "prd": "Create PRD from spec",
        "test": "Run test suite",
        "validate": "Validate project",
        "generate": "Generate code",
        "checkpoint save": "Save checkpoint",
        "checkpoint restore": "Restore checkpoint",
        "telemetry start": "Start telemetry",
        "telemetry status": "Check telemetry status",
        "parallel enable": "Enable parallel execution",
        "routing status": "Check routing status",
        "security scan": "Run security scan",
    }

    return [{"command": f"br {cmd}", "description": desc} for cmd, desc in commands.items()]
