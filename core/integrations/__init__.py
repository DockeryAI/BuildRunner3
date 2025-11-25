"""
Integration modules for BuildRunner 3.1 Orchestrator

This package provides integration utilities for wiring core systems into the orchestrator:
- Telemetry integration: Event collection and tracking
- Routing integration: Model selection and complexity estimation
- Parallel integration: Multi-session coordination and worker management
"""

from .telemetry_integration import (
    integrate_telemetry,
    emit_task_event,
    emit_batch_event,
    create_telemetry_context,
    get_event_summary,
)

from .routing_integration import (
    integrate_routing,
    select_model_for_task,
    estimate_task_complexity,
    track_model_cost,
    get_routing_summary,
)

from .parallel_integration import (
    integrate_parallel,
    create_parallel_session,
    assign_task_to_worker,
    coordinate_parallel_execution,
    get_parallel_summary,
)

__all__ = [
    # Telemetry integration
    "integrate_telemetry",
    "emit_task_event",
    "emit_batch_event",
    "create_telemetry_context",
    "get_event_summary",
    # Routing integration
    "integrate_routing",
    "select_model_for_task",
    "estimate_task_complexity",
    "track_model_cost",
    "get_routing_summary",
    # Parallel integration
    "integrate_parallel",
    "create_parallel_session",
    "assign_task_to_worker",
    "coordinate_parallel_execution",
    "get_parallel_summary",
]
