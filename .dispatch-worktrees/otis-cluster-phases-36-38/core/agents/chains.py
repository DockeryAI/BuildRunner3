"""
Multi-Agent Workflow Chains

Provides sequential and parallel agent execution capabilities:
- AgentChain: Sequential execution of agents (explore → implement → test → review)
- ParallelAgentPool: Parallel execution for independent tasks
- WorkflowTemplates: Pre-defined workflow patterns

Integrates with ClaudeAgentBridge for actual agent execution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Tuple, Set
from datetime import datetime
from pathlib import Path
import json
import time
from uuid import uuid4
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed

from core.agents.claude_agent_bridge import (
    ClaudeAgentBridge,
    AgentType,
    AgentStatus,
    AgentResponse,
    AgentAssignment,
)
from core.task_queue import QueuedTask, TaskStatus


class WorkflowStatus(str, Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowPhase(str, Enum):
    """Phases in a workflow"""

    EXPLORE = "explore"  # Understanding and analysis
    IMPLEMENT = "implement"  # Feature implementation
    TEST = "test"  # Testing and validation
    REVIEW = "review"  # Code review and optimization
    COMPLETE = "complete"  # Workflow completion


@dataclass
class AgentWorkItem:
    """A single work item in the workflow"""

    item_id: str
    agent_type: AgentType
    prompt: str
    task: QueuedTask
    context: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.PENDING
    response: Optional[AgentResponse] = None
    assignment: Optional[AgentAssignment] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def duration_ms(self) -> Optional[float]:
        """Get execution duration in milliseconds"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "item_id": self.item_id,
            "agent_type": self.agent_type.value,
            "task_id": self.task.id,
            "status": self.status.value,
            "duration_ms": self.duration_ms(),
            "error_message": self.error_message,
        }


@dataclass
class WorkflowCheckpoint:
    """Checkpoint for workflow recovery"""

    checkpoint_id: str
    workflow_id: str
    phase: WorkflowPhase
    completed_items: List[str]
    timestamp: datetime
    state_data: Dict[str, Any]


class AgentChain:
    """
    Orchestrates sequential execution of agents.

    Workflow: explore → implement → test → review

    Sequential execution ensures each phase builds on previous results.
    Provides checkpointing for recovery and state persistence.
    """

    def __init__(
        self,
        agent_bridge: ClaudeAgentBridge,
        workflow_id: Optional[str] = None,
        checkpoint_dir: Optional[Path] = None,
        enable_checkpointing: bool = True,
    ):
        """
        Initialize AgentChain.

        Args:
            agent_bridge: ClaudeAgentBridge instance for agent dispatch
            workflow_id: Unique workflow identifier
            checkpoint_dir: Directory for checkpoint storage
            enable_checkpointing: Enable checkpoint saving
        """
        self.agent_bridge = agent_bridge
        self.workflow_id = workflow_id or str(uuid4())[:8]
        self.checkpoint_dir = checkpoint_dir or Path(".buildrunner/workflows")
        self.enable_checkpointing = enable_checkpointing

        # Ensure checkpoint directory exists
        if self.enable_checkpointing:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Workflow state
        self.status = WorkflowStatus.PENDING
        self.items: Dict[str, AgentWorkItem] = {}
        self.completed_items: List[str] = []
        self.failed_items: List[str] = []
        self.phase = WorkflowPhase.EXPLORE

        # Execution tracking
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.total_duration_ms: float = 0.0

        # Statistics
        self.stats = {
            "total_items": 0,
            "completed_items": 0,
            "failed_items": 0,
            "avg_item_duration_ms": 0.0,
            "by_phase": {},
            "by_agent_type": {},
        }

    def add_work_item(
        self,
        agent_type: AgentType,
        task: QueuedTask,
        prompt: str,
        context: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        """
        Add a work item to the workflow.

        Args:
            agent_type: Type of agent to execute
            task: Task to execute
            prompt: Prompt for the agent
            context: Optional context
            dependencies: List of item IDs this depends on

        Returns:
            Item ID
        """
        item_id = str(uuid4())[:8]
        item = AgentWorkItem(
            item_id=item_id,
            agent_type=agent_type,
            prompt=prompt,
            task=task,
            context=context,
            dependencies=dependencies or [],
        )

        self.items[item_id] = item
        self.stats["total_items"] += 1

        return item_id

    def execute(
        self,
        on_item_complete: Optional[Callable[[AgentWorkItem], None]] = None,
        on_item_failed: Optional[Callable[[AgentWorkItem, str], None]] = None,
    ) -> bool:
        """
        Execute the workflow sequentially.

        Args:
            on_item_complete: Callback when item completes
            on_item_failed: Callback when item fails

        Returns:
            True if all items completed successfully

        Raises:
            ValueError: If workflow is already running or has invalid state
        """
        if self.status == WorkflowStatus.RUNNING:
            raise ValueError("Workflow is already running")

        if not self.items:
            raise ValueError("No work items in workflow")

        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now()

        try:
            # Execute items sequentially
            for item_id in self._get_execution_order():
                item = self.items[item_id]

                # Check dependencies
                if not self._dependencies_met(item_id):
                    item.error_message = "Dependencies not met"
                    item.status = AgentStatus.FAILED
                    self.failed_items.append(item_id)
                    if on_item_failed:
                        on_item_failed(item, "Dependencies not met")
                    continue

                # Execute item
                try:
                    self._execute_item(item)

                    if item.response and item.response.success:
                        item.status = AgentStatus.COMPLETED
                        self.completed_items.append(item_id)
                        if on_item_complete:
                            on_item_complete(item)
                    else:
                        item.status = AgentStatus.FAILED
                        self.failed_items.append(item_id)
                        error_msg = (
                            item.response.errors[0]
                            if item.response and item.response.errors
                            else "Unknown error"
                        )
                        if on_item_failed:
                            on_item_failed(item, error_msg)

                except Exception as e:
                    item.status = AgentStatus.FAILED
                    item.error_message = str(e)
                    self.failed_items.append(item_id)
                    if on_item_failed:
                        on_item_failed(item, str(e))

                # Checkpoint after each item
                if self.enable_checkpointing:
                    self._save_checkpoint()

            # Final status
            self.completed_at = datetime.now()
            self.total_duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

            if self.failed_items:
                self.status = WorkflowStatus.FAILED
                return False
            else:
                self.status = WorkflowStatus.COMPLETED
                return True

        except Exception as e:
            self.status = WorkflowStatus.FAILED
            self.completed_at = datetime.now()
            raise

    def _get_execution_order(self) -> List[str]:
        """Get execution order respecting dependencies"""
        executed = set()
        order = []

        while len(executed) < len(self.items):
            ready_items = [
                item_id
                for item_id in self.items
                if item_id not in executed
                and all(dep in executed for dep in self.items[item_id].dependencies)
            ]

            if not ready_items:
                # Circular dependency or blocked items
                remaining = [item_id for item_id in self.items if item_id not in executed]
                if remaining:
                    # Just add remaining items (will fail gracefully)
                    order.extend(remaining)
                break

            order.extend(ready_items)
            executed.update(ready_items)

        return order

    def _dependencies_met(self, item_id: str) -> bool:
        """Check if all dependencies for an item are completed"""
        item = self.items[item_id]
        return all(dep in self.completed_items for dep in item.dependencies)

    def _execute_item(self, item: AgentWorkItem) -> None:
        """Execute a single work item"""
        item.started_at = datetime.now()

        try:
            assignment = self.agent_bridge.dispatch_task(
                task=item.task,
                agent_type=item.agent_type,
                prompt=item.prompt,
                context=item.context,
            )

            item.assignment = assignment
            item.response = assignment.response

        finally:
            item.completed_at = datetime.now()

    def _save_checkpoint(self) -> None:
        """Save workflow checkpoint"""
        if not self.enable_checkpointing:
            return

        checkpoint = WorkflowCheckpoint(
            checkpoint_id=str(uuid4())[:8],
            workflow_id=self.workflow_id,
            phase=self.phase,
            completed_items=self.completed_items.copy(),
            timestamp=datetime.now(),
            state_data={
                "status": self.status.value,
                "total_items": self.stats["total_items"],
                "completed_count": len(self.completed_items),
                "failed_count": len(self.failed_items),
            },
        )

        checkpoint_file = self.checkpoint_dir / f"workflow_{self.workflow_id}_checkpoint.json"
        try:
            with open(checkpoint_file, "w") as f:
                json.dump(
                    {
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "workflow_id": checkpoint.workflow_id,
                        "phase": checkpoint.phase.value,
                        "completed_items": checkpoint.completed_items,
                        "timestamp": checkpoint.timestamp.isoformat(),
                        "state_data": checkpoint.state_data,
                    },
                    f,
                    indent=2,
                )
        except IOError:
            pass

    def get_results(self) -> Dict[str, Any]:
        """Get workflow results"""
        items_by_status = {
            "completed": [self.items[item_id].to_dict() for item_id in self.completed_items],
            "failed": [self.items[item_id].to_dict() for item_id in self.failed_items],
            "pending": [
                self.items[item_id].to_dict()
                for item_id in self.items
                if item_id not in self.completed_items and item_id not in self.failed_items
            ],
        }

        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "phase": self.phase.value,
            "duration_ms": self.total_duration_ms,
            "items": items_by_status,
            "stats": self._update_stats(),
        }

    def _update_stats(self) -> Dict[str, Any]:
        """Update and return statistics"""
        completed_durations = [
            self.items[item_id].duration_ms()
            for item_id in self.completed_items
            if self.items[item_id].duration_ms()
        ]

        self.stats["completed_items"] = len(self.completed_items)
        self.stats["failed_items"] = len(self.failed_items)

        if completed_durations:
            self.stats["avg_item_duration_ms"] = sum(completed_durations) / len(completed_durations)

        return self.stats


class ParallelAgentPool:
    """
    Executes multiple agents in parallel for independent tasks.

    Uses ThreadPoolExecutor to run multiple agents concurrently.
    Provides result aggregation and error handling.
    Supports different concurrency levels and timeout configuration.
    """

    def __init__(
        self,
        agent_bridge: ClaudeAgentBridge,
        max_workers: int = 3,
        timeout_seconds: int = 300,
        checkpoint_dir: Optional[Path] = None,
    ):
        """
        Initialize ParallelAgentPool.

        Args:
            agent_bridge: ClaudeAgentBridge instance
            max_workers: Maximum number of concurrent agents
            timeout_seconds: Timeout for each agent execution
            checkpoint_dir: Directory for checkpoint storage
        """
        self.agent_bridge = agent_bridge
        self.max_workers = min(max_workers, 10)  # Cap at 10 workers
        self.timeout_seconds = timeout_seconds
        self.checkpoint_dir = checkpoint_dir or Path(".buildrunner/workflows")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Execution state
        self.pool_id = str(uuid4())[:8]
        self.items: Dict[str, AgentWorkItem] = {}
        self.futures: Dict[str, Future] = {}
        self.results: Dict[str, AgentWorkItem] = {}

        # Statistics
        self.stats = {
            "total_items": 0,
            "completed_items": 0,
            "failed_items": 0,
            "total_duration_ms": 0.0,
            "avg_item_duration_ms": 0.0,
        }

    def add_work_item(
        self,
        agent_type: AgentType,
        task: QueuedTask,
        prompt: str,
        context: Optional[str] = None,
    ) -> str:
        """
        Add a work item to the pool.

        Args:
            agent_type: Type of agent
            task: Task to execute
            prompt: Prompt for agent
            context: Optional context

        Returns:
            Item ID
        """
        item_id = str(uuid4())[:8]
        item = AgentWorkItem(
            item_id=item_id,
            agent_type=agent_type,
            prompt=prompt,
            task=task,
            context=context,
        )

        self.items[item_id] = item
        self.stats["total_items"] += 1

        return item_id

    def execute(
        self,
        on_item_complete: Optional[Callable[[AgentWorkItem], None]] = None,
        on_item_failed: Optional[Callable[[AgentWorkItem, str], None]] = None,
    ) -> bool:
        """
        Execute all work items in parallel.

        Args:
            on_item_complete: Callback when item completes
            on_item_failed: Callback when item fails

        Returns:
            True if all items completed successfully
        """
        if not self.items:
            raise ValueError("No work items in pool")

        start_time = datetime.now()
        failed_items = []

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all work items
                for item_id, item in self.items.items():
                    future = executor.submit(self._execute_item, item)
                    self.futures[item_id] = future

                # Wait for completion and process results
                for future in as_completed(self.futures.values(), timeout=self.timeout_seconds):
                    item_id = next(item_id for item_id, f in self.futures.items() if f == future)
                    item = self.items[item_id]

                    try:
                        item = future.result()
                        self.results[item_id] = item

                        if item.response and item.response.success:
                            item.status = AgentStatus.COMPLETED
                            self.stats["completed_items"] += 1
                            if on_item_complete:
                                on_item_complete(item)
                        else:
                            item.status = AgentStatus.FAILED
                            failed_items.append(item_id)
                            error_msg = (
                                item.response.errors[0]
                                if item.response and item.response.errors
                                else "Unknown error"
                            )
                            if on_item_failed:
                                on_item_failed(item, error_msg)

                    except Exception as e:
                        item.status = AgentStatus.FAILED
                        item.error_message = str(e)
                        failed_items.append(item_id)
                        if on_item_failed:
                            on_item_failed(item, str(e))

        except TimeoutError:
            self.stats["failed_items"] = len(self.items) - self.stats["completed_items"]
            return False

        finally:
            # Calculate duration
            duration = datetime.now() - start_time
            self.stats["total_duration_ms"] = duration.total_seconds() * 1000

            # Calculate average duration
            durations = [item.duration_ms() for item in self.results.values() if item.duration_ms()]
            if durations:
                self.stats["avg_item_duration_ms"] = sum(durations) / len(durations)

            self.stats["failed_items"] = len(failed_items)

            # Save checkpoint
            self._save_checkpoint()

        return len(failed_items) == 0

    def _execute_item(self, item: AgentWorkItem) -> AgentWorkItem:
        """Execute a single work item (called in thread pool)"""
        item.started_at = datetime.now()

        try:
            assignment = self.agent_bridge.dispatch_task(
                task=item.task,
                agent_type=item.agent_type,
                prompt=item.prompt,
                context=item.context,
            )

            item.assignment = assignment
            item.response = assignment.response

        finally:
            item.completed_at = datetime.now()

        return item

    def _save_checkpoint(self) -> None:
        """Save pool execution checkpoint"""
        checkpoint_file = self.checkpoint_dir / f"pool_{self.pool_id}_checkpoint.json"

        try:
            with open(checkpoint_file, "w") as f:
                json.dump(
                    {
                        "pool_id": self.pool_id,
                        "timestamp": datetime.now().isoformat(),
                        "stats": self.stats,
                        "results": {
                            item_id: item.to_dict() for item_id, item in self.results.items()
                        },
                    },
                    f,
                    indent=2,
                )
        except IOError:
            pass

    def get_results(self) -> Dict[str, Any]:
        """Get pool execution results"""
        completed = [
            item.to_dict() for item in self.results.values() if item.status == AgentStatus.COMPLETED
        ]
        failed = [
            item.to_dict() for item in self.results.values() if item.status == AgentStatus.FAILED
        ]

        return {
            "pool_id": self.pool_id,
            "total_items": self.stats["total_items"],
            "completed": len(completed),
            "failed": len(failed),
            "duration_ms": self.stats["total_duration_ms"],
            "avg_duration_ms": self.stats["avg_item_duration_ms"],
            "results": {
                "completed": completed,
                "failed": failed,
            },
        }


class WorkflowTemplates:
    """Pre-defined workflow templates for common patterns"""

    @staticmethod
    def full_workflow(
        agent_bridge: ClaudeAgentBridge,
        task: QueuedTask,
    ) -> AgentChain:
        """
        Create a full workflow: explore → implement → test → review

        Args:
            agent_bridge: Agent bridge for execution
            task: Task to execute

        Returns:
            Configured AgentChain
        """
        workflow = AgentChain(agent_bridge)

        # Phase 1: Explore
        workflow.add_work_item(
            agent_type=AgentType.EXPLORE,
            task=task,
            prompt=f"Explore and understand the requirements for: {task.name}",
        )

        # Phase 2: Implement
        workflow.add_work_item(
            agent_type=AgentType.IMPLEMENT,
            task=task,
            prompt=f"Implement the solution for: {task.name}",
        )

        # Phase 3: Test
        workflow.add_work_item(
            agent_type=AgentType.TEST,
            task=task,
            prompt=f"Write comprehensive tests for: {task.name}",
        )

        # Phase 4: Review
        workflow.add_work_item(
            agent_type=AgentType.REVIEW,
            task=task,
            prompt=f"Review and optimize the implementation of: {task.name}",
        )

        return workflow

    @staticmethod
    def test_workflow(
        agent_bridge: ClaudeAgentBridge,
        task: QueuedTask,
    ) -> AgentChain:
        """
        Create a test-focused workflow: implement → test → review

        Args:
            agent_bridge: Agent bridge for execution
            task: Task to execute

        Returns:
            Configured AgentChain
        """
        workflow = AgentChain(agent_bridge)

        workflow.add_work_item(
            agent_type=AgentType.IMPLEMENT,
            task=task,
            prompt=f"Implement: {task.name}",
        )

        workflow.add_work_item(
            agent_type=AgentType.TEST,
            task=task,
            prompt=f"Write tests for: {task.name}",
        )

        workflow.add_work_item(
            agent_type=AgentType.REVIEW,
            task=task,
            prompt=f"Review: {task.name}",
        )

        return workflow

    @staticmethod
    def review_workflow(
        agent_bridge: ClaudeAgentBridge,
        task: QueuedTask,
    ) -> AgentChain:
        """
        Create a review-focused workflow: review → optimize

        Args:
            agent_bridge: Agent bridge for execution
            task: Task to execute

        Returns:
            Configured AgentChain
        """
        workflow = AgentChain(agent_bridge)

        workflow.add_work_item(
            agent_type=AgentType.REVIEW,
            task=task,
            prompt=f"Review: {task.name}",
        )

        return workflow
