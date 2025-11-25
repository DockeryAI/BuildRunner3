"""
Claude Agent Bridge - Bridge between BuildRunner tasks and Claude Code's native /agent command

Provides:
- Task dispatch to Claude agents (explore, test, review, refactor, implement)
- Agent response parsing and validation
- Telemetry tracking of agent assignments
- Error handling and fallback mechanisms
- Agent status tracking and statistics
"""

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4

from core.task_queue import QueuedTask, TaskStatus
from core.telemetry import EventCollector, EventType, TaskEvent


class AgentType(str, Enum):
    """Available Claude agent types in Claude Code"""

    EXPLORE = "explore"  # Explore and understand code
    TEST = "test"  # Write and run tests
    REVIEW = "review"  # Code review and analysis
    REFACTOR = "refactor"  # Refactor code
    IMPLEMENT = "implement"  # Implement features


class AgentStatus(str, Enum):
    """Agent execution status"""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class AgentResponse:
    """Parsed response from Claude agent"""

    agent_type: AgentType
    task_id: str
    status: AgentStatus
    success: bool
    output: str
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "agent_type": self.agent_type.value,
            "task_id": self.task_id,
            "status": self.status.value,
            "success": self.success,
            "output": self.output,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AgentAssignment:
    """Record of a task assigned to an agent"""

    assignment_id: str
    task_id: str
    agent_type: AgentType
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    response: Optional[AgentResponse] = None
    retry_count: int = 0
    max_retries: int = 3

    def duration_ms(self) -> Optional[float]:
        """Get duration in milliseconds"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None


class AgentError(Exception):
    """Base exception for agent-related errors"""

    pass


class AgentDispatchError(AgentError):
    """Error dispatching task to agent"""

    pass


class AgentTimeoutError(AgentError):
    """Agent execution timeout"""

    pass


class AgentParseError(AgentError):
    """Error parsing agent response"""

    pass


class ClaudeAgentBridge:
    """
    Bridge between BuildRunner tasks and Claude Code's native /agent command.

    Handles:
    - Dispatching tasks to Claude agents
    - Parsing agent responses
    - Tracking agent assignments in telemetry
    - Error handling and retries
    - Agent statistics and status
    """

    def __init__(
        self,
        project_root: str,
        event_collector: Optional[EventCollector] = None,
        timeout_seconds: int = 300,
        enable_retries: bool = True,
    ):
        """
        Initialize Claude Agent Bridge.

        Args:
            project_root: Root directory of the project
            event_collector: Optional telemetry event collector
            timeout_seconds: Timeout for agent execution
            enable_retries: Enable automatic retries on failure
        """
        self.project_root = Path(project_root)
        self.event_collector = event_collector or EventCollector()
        self.timeout_seconds = timeout_seconds
        self.enable_retries = enable_retries

        # Track assignments
        self.assignments: Dict[str, AgentAssignment] = {}
        self.responses: Dict[str, AgentResponse] = {}

        # Statistics
        self.stats = {
            "total_dispatched": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retries": 0,
            "by_agent_type": {},
            "by_status": {},
        }

        # Initialize agent state file
        self.state_file = self.project_root / ".buildrunner" / "agent_bridge_state.json"
        self._load_state()

    def _load_state(self) -> None:
        """Load persisted state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.stats = state.get("stats", self.stats)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_state(self) -> None:
        """Save state to disk"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_file, "w") as f:
                json.dump({"stats": self.stats}, f, indent=2)
        except IOError as e:
            # Log but don't fail if state save fails
            pass

    def dispatch_task(
        self,
        task: QueuedTask,
        agent_type: AgentType,
        prompt: str,
        context: Optional[str] = None,
    ) -> AgentAssignment:
        """
        Dispatch a task to a Claude agent.

        Args:
            task: Task to dispatch
            agent_type: Type of agent to use
            prompt: The prompt/instruction for the agent
            context: Optional context information

        Returns:
            AgentAssignment with task assignment details

        Raises:
            AgentDispatchError: If dispatch fails
        """
        assignment_id = str(uuid4())[:8]
        assignment = AgentAssignment(
            assignment_id=assignment_id,
            task_id=task.id,
            agent_type=agent_type,
            created_at=datetime.now(),
        )

        try:
            # Update statistics
            self.stats["total_dispatched"] += 1
            self.stats["by_agent_type"][agent_type.value] = (
                self.stats["by_agent_type"].get(agent_type.value, 0) + 1
            )

            # Build the agent command
            full_prompt = self._build_prompt(task, agent_type, prompt, context)

            # Execute agent via Claude Code CLI
            assignment.started_at = datetime.now()
            response = self._execute_agent(
                agent_type=agent_type,
                prompt=full_prompt,
                task_id=task.id,
            )
            assignment.completed_at = datetime.now()
            assignment.response = response

            # Track assignment
            self.assignments[assignment_id] = assignment
            self.responses[task.id] = response

            # Update statistics
            self.stats["total_completed"] += 1
            self.stats["by_status"][response.status.value] = (
                self.stats["by_status"].get(response.status.value, 0) + 1
            )

            # Emit telemetry
            self._emit_assignment_telemetry(assignment, response)
            self._save_state()

            return assignment

        except AgentError as e:
            assignment.completed_at = datetime.now()
            self.stats["total_failed"] += 1

            # Emit error telemetry
            self._emit_error_telemetry(assignment, str(e))

            if self.enable_retries and assignment.retry_count < assignment.max_retries:
                assignment.retry_count += 1
                self.stats["total_retries"] += 1
                # Retry with backoff
                time.sleep(2**assignment.retry_count)
                return self.dispatch_task(task, agent_type, prompt, context)

            raise

    def _build_prompt(
        self,
        task: QueuedTask,
        agent_type: AgentType,
        prompt: str,
        context: Optional[str] = None,
    ) -> str:
        """
        Build the full prompt for the agent.

        Args:
            task: The task being dispatched
            agent_type: Type of agent
            prompt: Base prompt
            context: Optional context

        Returns:
            Full formatted prompt
        """
        lines = [
            f"# Task: {task.name}",
            f"Task ID: {task.id}",
            f"Domain: {task.domain}",
            f"Complexity: {task.complexity}",
            f"",
            "## Description",
            task.description,
            "",
            "## Requirements",
        ]

        # Add acceptance criteria
        for criterion in task.acceptance_criteria:
            lines.append(f"- {criterion}")

        lines.extend(
            [
                "",
                "## Instructions",
                prompt,
            ]
        )

        # Add context if provided
        if context:
            lines.extend(
                [
                    "",
                    "## Additional Context",
                    context,
                ]
            )

        # Add agent-specific instructions
        lines.extend(
            [
                "",
                f"## Agent: {agent_type.value.upper()}",
                self._get_agent_instructions(agent_type),
            ]
        )

        return "\n".join(lines)

    def _get_agent_instructions(self, agent_type: AgentType) -> str:
        """Get agent-specific instructions"""
        instructions = {
            AgentType.EXPLORE: (
                "Your role is to explore and understand the codebase.\n"
                "- Analyze existing patterns and architecture\n"
                "- Document findings\n"
                "- Suggest improvements\n"
                "- Provide implementation approach"
            ),
            AgentType.TEST: (
                "Your role is to write comprehensive tests.\n"
                "- Create unit tests with high coverage (90%+)\n"
                "- Test edge cases and error conditions\n"
                "- Ensure tests pass\n"
                "- Document test strategy"
            ),
            AgentType.REVIEW: (
                "Your role is to review code and provide feedback.\n"
                "- Analyze code quality and style\n"
                "- Check for security issues\n"
                "- Suggest optimizations\n"
                "- Provide actionable recommendations"
            ),
            AgentType.REFACTOR: (
                "Your role is to refactor code for improvement.\n"
                "- Improve code clarity and maintainability\n"
                "- Reduce complexity\n"
                "- Apply design patterns\n"
                "- Maintain functionality while improving structure"
            ),
            AgentType.IMPLEMENT: (
                "Your role is to implement features.\n"
                "- Write production-quality code\n"
                "- Follow established patterns\n"
                "- Include tests and documentation\n"
                "- Ensure code is complete and working"
            ),
        }
        return instructions.get(agent_type, "Unknown agent type")

    def _execute_agent(
        self,
        agent_type: AgentType,
        prompt: str,
        task_id: str,
    ) -> AgentResponse:
        """
        Execute an agent via Claude Code CLI.

        Args:
            agent_type: Type of agent
            prompt: Prompt to send to agent
            task_id: Task ID for tracking

        Returns:
            Parsed agent response

        Raises:
            AgentDispatchError: If dispatch fails
            AgentTimeoutError: If execution times out
            AgentParseError: If response cannot be parsed
        """
        try:
            # Build agent command
            # Note: This assumes Claude Code CLI has an /agent command
            # In production, this would integrate with Claude Code's actual API
            cmd = [
                "claude",
                "agent",
                agent_type.value,
                "--task-id",
                task_id,
                "--timeout",
                str(self.timeout_seconds),
            ]

            start_time = time.time()

            # Execute command (with proper error handling)
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds + 10,  # Add buffer
            )

            duration_ms = (time.time() - start_time) * 1000

            # Parse response
            response = self._parse_agent_response(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                agent_type=agent_type,
                task_id=task_id,
                duration_ms=duration_ms,
            )

            return response

        except subprocess.TimeoutExpired as e:
            raise AgentTimeoutError(f"Agent execution timeout after {self.timeout_seconds}s")
        except FileNotFoundError:
            raise AgentDispatchError(
                "Claude Code CLI not found. Is 'claude' installed and in PATH?"
            )
        except Exception as e:
            raise AgentDispatchError(f"Failed to dispatch agent: {e}")

    def _parse_agent_response(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        agent_type: AgentType,
        task_id: str,
        duration_ms: float,
    ) -> AgentResponse:
        """
        Parse response from agent execution.

        Args:
            stdout: Standard output
            stderr: Standard error
            returncode: Return code
            agent_type: Type of agent
            task_id: Task ID
            duration_ms: Execution duration

        Returns:
            Parsed AgentResponse

        Raises:
            AgentParseError: If response cannot be parsed
        """
        try:
            # Check for success
            success = returncode == 0

            # Parse JSON if available (agent should return structured output)
            metadata = {}
            files_created = []
            files_modified = []
            errors = []

            if stdout.strip():
                try:
                    # Try to extract JSON from output
                    json_match = re.search(r"\{.*\}", stdout, re.DOTALL)
                    if json_match:
                        metadata = json.loads(json_match.group())
                        files_created = metadata.get("files_created", [])
                        files_modified = metadata.get("files_modified", [])
                except (json.JSONDecodeError, AttributeError):
                    pass

            if stderr.strip():
                errors = stderr.strip().split("\n")

            # Determine status
            if returncode == 0:
                status = AgentStatus.COMPLETED
            elif returncode == 124:  # Timeout signal
                status = AgentStatus.TIMEOUT
            else:
                status = AgentStatus.FAILED

            response = AgentResponse(
                agent_type=agent_type,
                task_id=task_id,
                status=status,
                success=success,
                output=stdout,
                files_created=files_created,
                files_modified=files_modified,
                errors=errors,
                duration_ms=duration_ms,
                metadata=metadata,
            )

            return response

        except Exception as e:
            raise AgentParseError(f"Failed to parse agent response: {e}")

    def _emit_assignment_telemetry(
        self,
        assignment: AgentAssignment,
        response: AgentResponse,
    ) -> None:
        """Emit telemetry for successful agent assignment"""
        if not self.event_collector:
            return

        event = TaskEvent(
            event_type=EventType.TASK_COMPLETED if response.success else EventType.TASK_FAILED,
            task_id=assignment.task_id,
            task_type=assignment.agent_type.value,
            success=response.success,
            duration_ms=response.duration_ms,
            tokens_used=response.tokens_used,
            error_message="; ".join(response.errors) if response.errors else "",
            metadata={
                "assignment_id": assignment.assignment_id,
                "agent_type": assignment.agent_type.value,
                "files_created": response.files_created,
                "files_modified": response.files_modified,
                "agent_status": response.status.value,
            },
        )

        self.event_collector.collect(event)

    def _emit_error_telemetry(
        self,
        assignment: AgentAssignment,
        error_message: str,
    ) -> None:
        """Emit telemetry for agent errors"""
        if not self.event_collector:
            return

        from core.telemetry import ErrorEvent

        event = ErrorEvent(
            event_type=EventType.ERROR_OCCURRED,
            error_type="agent_dispatch_error",
            error_message=error_message,
            task_id=assignment.task_id,
            component="claude_agent_bridge",
            severity="warning",
            recoverable=True,
            recovery_action="retry" if self.enable_retries else "manual_intervention",
        )

        self.event_collector.collect(event)

    def get_assignment(self, assignment_id: str) -> Optional[AgentAssignment]:
        """Get an assignment by ID"""
        return self.assignments.get(assignment_id)

    def get_response(self, task_id: str) -> Optional[AgentResponse]:
        """Get response for a task"""
        return self.responses.get(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        return {
            "total_dispatched": self.stats["total_dispatched"],
            "total_completed": self.stats["total_completed"],
            "total_failed": self.stats["total_failed"],
            "total_retries": self.stats["total_retries"],
            "success_rate": (
                self.stats["total_completed"] / self.stats["total_dispatched"]
                if self.stats["total_dispatched"] > 0
                else 0
            ),
            "by_agent_type": self.stats["by_agent_type"],
            "by_status": self.stats["by_status"],
        }

    def list_assignments(self, limit: int = 50) -> List[AgentAssignment]:
        """List recent assignments"""
        return list(self.assignments.values())[-limit:]

    def cancel_assignment(self, assignment_id: str) -> bool:
        """Cancel an assignment"""
        if assignment_id in self.assignments:
            assignment = self.assignments[assignment_id]
            if assignment.response:
                assignment.response.status = AgentStatus.CANCELLED
            return True
        return False

    def retry_assignment(
        self,
        assignment_id: str,
        task: QueuedTask,
        agent_type: AgentType,
        prompt: str,
    ) -> AgentAssignment:
        """Retry a failed assignment"""
        assignment = self.assignments.get(assignment_id)
        if not assignment:
            raise AgentDispatchError(f"Assignment {assignment_id} not found")

        # Reset for retry
        assignment.retry_count += 1
        assignment.started_at = None
        assignment.completed_at = None
        assignment.response = None

        return self.dispatch_task(task, agent_type, prompt)
