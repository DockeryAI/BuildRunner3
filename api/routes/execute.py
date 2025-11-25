"""
Execute API Routes

Provides endpoint for executing BuildRunner CLI commands from the web interface.
This enables the UI to have full CLI functionality.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import subprocess
import os
from pathlib import Path

router = APIRouter()


class ExecuteRequest(BaseModel):
    """Request model for command execution"""

    command: str
    cwd: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Response model for command execution"""

    output: str
    error: Optional[str] = None
    return_code: int


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

        # Execute the command
        result = subprocess.run(
            request.command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
        )

        # Return the results
        return ExecuteResponse(
            output=result.stdout or result.stderr,
            error=result.stderr if result.returncode != 0 else None,
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command execution timeout (60 seconds)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")


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
