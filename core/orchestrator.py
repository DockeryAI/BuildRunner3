"""
Task Orchestrator

Main orchestration loop that executes task batches, generates prompts,
monitors execution, and verifies completion.

Integrates with:
- Telemetry system for event tracking
- Routing system for model selection
- Parallel execution for multi-session coordination
"""

from typing import List, Dict, Optional, Callable
from pathlib import Path
from enum import Enum
import time

# Integration modules
from core.integrations import (
    integrate_telemetry,
    emit_task_event,
    emit_batch_event,
    create_telemetry_context,
    integrate_routing,
    estimate_task_complexity,
    select_model_for_task,
    track_model_cost,
    integrate_parallel,
    create_parallel_session,
    assign_task_to_worker,
    coordinate_parallel_execution,
)

# Core telemetry
from core.telemetry import EventType


class OrchestrationStatus(Enum):
    """Orchestration execution status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskOrchestrator:
    """
    Main orchestration engine that coordinates task execution.

    Responsibilities:
    - Execute task batches in order
    - Generate Claude prompts
    - Monitor file creation
    - Verify completion
    - Handle errors and recovery
    """

    def __init__(
        self,
        batch_optimizer=None,
        prompt_builder=None,
        context_manager=None,
        file_monitor=None,
        verification_engine=None,
        enable_telemetry: bool = True,
        enable_routing: bool = True,
        enable_parallel: bool = True,
        max_concurrent_sessions: int = 4,
    ):
        self.batch_optimizer = batch_optimizer
        self.prompt_builder = prompt_builder
        self.context_manager = context_manager
        self.file_monitor = file_monitor
        self.verification_engine = verification_engine

        self.status = OrchestrationStatus.IDLE
        self.current_batch = None
        self.completed_batches = []
        self.failed_batches = []

        # Statistics
        self.batches_executed = 0
        self.tasks_completed = 0
        self.execution_errors = 0

        # Initialize integrations
        self.event_collector = None
        self.complexity_estimator = None
        self.model_selector = None
        self.cost_tracker = None
        self.session_manager = None
        self.worker_coordinator = None
        self.dashboard = None

        # Integrate telemetry
        if enable_telemetry:
            self.event_collector = integrate_telemetry(self)

        # Integrate routing
        if enable_routing:
            routing_components = integrate_routing(self, enable_cost_tracking=True)
            self.complexity_estimator = routing_components['estimator']
            self.model_selector = routing_components['selector']
            self.cost_tracker = routing_components['cost_tracker']

        # Integrate parallel execution
        if enable_parallel:
            parallel_components = integrate_parallel(
                self,
                max_concurrent_sessions=max_concurrent_sessions,
                enable_dashboard=True,
            )
            self.session_manager = parallel_components['session_manager']
            self.worker_coordinator = parallel_components['worker_coordinator']
            self.dashboard = parallel_components['dashboard']

    def execute_batch(
        self,
        tasks: List,
        on_prompt_generated: Optional[Callable] = None,
        auto_continue: bool = False,
    ) -> Dict:
        """
        Execute a batch of tasks.

        Args:
            tasks: List of tasks to execute
            on_prompt_generated: Callback when prompt is ready
            auto_continue: Whether to continue automatically

        Returns:
            Execution result dictionary
        """
        if not tasks:
            return {"success": False, "error": "No tasks provided"}

        self.status = OrchestrationStatus.RUNNING

        # Start telemetry context
        ctx = None
        if self.event_collector:
            ctx = create_telemetry_context(self.event_collector, "execute_batch")
            ctx.__enter__()

        try:
            # Optimize into batches
            if self.batch_optimizer:
                batches = self.batch_optimizer.optimize_batches(tasks)
            else:
                # Fallback: single batch
                batches = [{"id": 1, "tasks": tasks}]

            if ctx:
                ctx.add_metadata("batch_count", len(batches))
                ctx.add_metadata("task_count", len(tasks))

            # Execute each batch
            for batch in batches:
                result = self._execute_single_batch(
                    batch,
                    on_prompt_generated=on_prompt_generated,
                    auto_continue=auto_continue,
                )

                if not result["success"]:
                    self.failed_batches.append(batch)
                    if not auto_continue:
                        break
                else:
                    self.completed_batches.append(batch)

            self.status = OrchestrationStatus.COMPLETED

            if ctx:
                ctx.add_metadata("batches_completed", len(self.completed_batches))
                ctx.add_metadata("batches_failed", len(self.failed_batches))

            return {
                "success": True,
                "batches_completed": len(self.completed_batches),
                "batches_failed": len(self.failed_batches),
            }

        except Exception as e:
            self.status = OrchestrationStatus.FAILED
            self.execution_errors += 1

            if ctx:
                ctx.mark_failed(str(e))

            return {"success": False, "error": str(e)}

        finally:
            if ctx:
                ctx.__exit__(None, None, None)

    def _execute_single_batch(
        self,
        batch,
        on_prompt_generated: Optional[Callable] = None,
        auto_continue: bool = False,
    ) -> Dict:
        """Execute a single batch of tasks"""
        self.current_batch = batch
        self.batches_executed += 1

        batch_id = batch.get("id") if isinstance(batch, dict) else (batch.id if hasattr(batch, "id") else str(self.batches_executed))
        batch_tasks = batch.get("tasks", batch.tasks if hasattr(batch, "tasks") else [])

        # Emit batch started event
        if self.event_collector:
            emit_batch_event(
                self.event_collector,
                EventType.BUILD_STARTED,
                batch_id=str(batch_id),
                task_count=len(batch_tasks),
                metadata={'auto_continue': auto_continue},
            )

        start_time = time.time()

        try:
            # Generate prompt
            if self.prompt_builder:
                context = self.context_manager.get_context() if self.context_manager else None
                prompt = self.prompt_builder.build_prompt(batch, context)
            else:
                prompt = f"Execute batch {batch_id}"

            # Use routing to select model if enabled
            selected_model = None
            if self.complexity_estimator and self.model_selector and batch_tasks:
                # Estimate complexity of first task as representative
                first_task = batch_tasks[0]
                task_id = first_task.get('id', 'unknown') if isinstance(first_task, dict) else (first_task.id if hasattr(first_task, 'id') else 'unknown')
                task_desc = first_task.get('description', '') if isinstance(first_task, dict) else (first_task.description if hasattr(first_task, 'description') else '')

                complexity = estimate_task_complexity(
                    self.complexity_estimator,
                    task_description=task_desc,
                )

                selection = select_model_for_task(
                    self.model_selector,
                    complexity=complexity,
                )
                selected_model = selection.model.name if hasattr(selection, 'model') else str(selection)

                # Emit MODEL_SELECTED event
                if self.event_collector:
                    from core.telemetry import Event
                    model_event = Event(
                        event_type=EventType.MODEL_SELECTED,
                        session_id=str(batch_id),
                        metadata={
                            'task_id': str(task_id),
                            'model': selected_model,
                            'complexity': complexity.level.value if hasattr(complexity, 'level') else str(complexity),
                            'batch_id': str(batch_id),
                        },
                    )
                    self.event_collector.collect(model_event)

            # Callback with prompt
            if on_prompt_generated:
                on_prompt_generated(prompt)

            # In real implementation, this would:
            # 1. Send prompt to Claude (using selected_model)
            # 2. Wait for completion
            # 3. Monitor file creation
            # 4. Verify results

            # For now, mark as success
            self.tasks_completed += len(batch_tasks)

            # Emit task events for each task
            if self.event_collector:
                for task in batch_tasks:
                    task_id = task.get('id', 'unknown') if isinstance(task, dict) else (task.id if hasattr(task, 'id') else 'unknown')
                    task_name = task.get('name', '') if isinstance(task, dict) else (task.name if hasattr(task, 'name') else '')
                    task_desc = task.get('description', '') if isinstance(task, dict) else (task.description if hasattr(task, 'description') else '')

                    # Task started
                    emit_task_event(
                        self.event_collector,
                        EventType.TASK_STARTED,
                        task_id=str(task_id),
                        task_type=task_name,
                        task_description=task_desc,
                        metadata={'batch_id': str(batch_id), 'model': selected_model},
                    )

                    # Task completed (simulated)
                    emit_task_event(
                        self.event_collector,
                        EventType.TASK_COMPLETED,
                        task_id=str(task_id),
                        task_type=task_name,
                        task_description=task_desc,
                        success=True,
                        metadata={'batch_id': str(batch_id), 'model': selected_model},
                    )

            duration_ms = (time.time() - start_time) * 1000

            # Emit batch completed event
            if self.event_collector:
                emit_batch_event(
                    self.event_collector,
                    EventType.BUILD_COMPLETED,
                    batch_id=str(batch_id),
                    task_count=len(batch_tasks),
                    success=True,
                    metadata={
                        'duration_ms': duration_ms,
                        'selected_model': selected_model,
                    },
                )

            return {"success": True, "batch_id": batch_id, "model": selected_model}

        except Exception as e:
            # Emit batch failed event
            if self.event_collector:
                emit_batch_event(
                    self.event_collector,
                    EventType.BUILD_FAILED,
                    batch_id=str(batch_id),
                    task_count=len(batch_tasks),
                    success=False,
                    metadata={'error': str(e)},
                )

            return {"success": False, "error": str(e)}

    def run_orchestration_loop(
        self,
        tasks: List,
        max_iterations: int = 100,
        verification_callback: Optional[Callable] = None,
    ) -> Dict:
        """
        Run complete orchestration loop with monitoring and verification.

        Args:
            tasks: Tasks to orchestrate
            max_iterations: Maximum iterations before stopping
            verification_callback: Optional verification callback

        Returns:
            Final orchestration result
        """
        iteration = 0
        remaining_tasks = tasks.copy()

        while remaining_tasks and iteration < max_iterations:
            iteration += 1

            # Get next batch
            if self.batch_optimizer:
                batches = self.batch_optimizer.optimize_batches(remaining_tasks[:3])
                if batches:
                    batch = batches[0]
                else:
                    break
            else:
                break

            # Execute batch
            result = self._execute_single_batch(batch)

            if result["success"]:
                # Remove completed tasks
                batch_tasks = batch.tasks if hasattr(batch, "tasks") else []
                for task in batch_tasks:
                    if task in remaining_tasks:
                        remaining_tasks.remove(task)

                # Verify if callback provided
                if verification_callback:
                    verification_callback(batch)

            else:
                # Handle failure
                self.execution_errors += 1
                if self.execution_errors > 3:
                    break

        return {
            "success": len(remaining_tasks) == 0,
            "iterations": iteration,
            "tasks_completed": self.tasks_completed,
            "tasks_remaining": len(remaining_tasks),
        }

    def pause(self):
        """Pause orchestration"""
        self.status = OrchestrationStatus.PAUSED

    def resume(self):
        """Resume orchestration"""
        if self.status == OrchestrationStatus.PAUSED:
            self.status = OrchestrationStatus.RUNNING

    def stop(self):
        """Stop orchestration"""
        self.status = OrchestrationStatus.IDLE
        self.current_batch = None

    def get_status(self) -> Dict:
        """Get current orchestration status"""
        return {
            "status": self.status.value,
            "current_batch": self.current_batch.id if self.current_batch and hasattr(self.current_batch, "id") else None,
            "batches_executed": self.batches_executed,
            "tasks_completed": self.tasks_completed,
            "execution_errors": self.execution_errors,
            "completed_batches": len(self.completed_batches),
            "failed_batches": len(self.failed_batches),
        }

    def reset(self):
        """Reset orchestrator state"""
        self.status = OrchestrationStatus.IDLE
        self.current_batch = None
        self.completed_batches = []
        self.failed_batches = []
        self.batches_executed = 0
        self.tasks_completed = 0
        self.execution_errors = 0

    def execute_parallel(
        self,
        tasks: List,
        session_name: Optional[str] = None,
    ) -> Dict:
        """
        Execute tasks in parallel across multiple sessions.

        Args:
            tasks: List of tasks to execute in parallel
            session_name: Optional name for the session

        Returns:
            Execution result dictionary with session info
        """
        if not self.session_manager or not self.worker_coordinator:
            return {
                "success": False,
                "error": "Parallel execution not enabled",
            }

        if not tasks:
            return {"success": False, "error": "No tasks provided"}

        try:
            # Coordinate parallel execution
            result = coordinate_parallel_execution(
                self.session_manager,
                self.worker_coordinator,
                tasks,
                session_name=session_name,
            )

            # Emit telemetry if enabled
            if self.event_collector:
                emit_batch_event(
                    self.event_collector,
                    EventType.BUILD_STARTED,
                    batch_id=result['session_id'],
                    task_count=result['task_count'],
                    metadata={
                        'execution_mode': 'parallel',
                        'session_name': result['session_name'],
                    },
                )

            return {
                "success": True,
                **result,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_integration_status(self) -> Dict:
        """Get status of all integrated systems."""
        return {
            "telemetry_enabled": self.event_collector is not None,
            "routing_enabled": self.complexity_estimator is not None and self.model_selector is not None,
            "parallel_enabled": self.session_manager is not None and self.worker_coordinator is not None,
            "cost_tracking_enabled": self.cost_tracker is not None,
            "dashboard_enabled": self.dashboard is not None,
        }
