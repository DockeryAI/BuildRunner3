"""
BuildRunner 3.0 FastAPI Backend

Main API application with all endpoints.
Because REST APIs are how we pretend distributed systems are simple.
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.feature_registry import FeatureRegistry
from core.status_generator import StatusGenerator
from core.governance import GovernanceManager
from api.models import *
from api.config_service import ConfigService
from api.test_runner import get_test_runner
from api.error_watcher import get_error_watcher
from api.supabase_client import get_supabase_client
from api.routes.analytics import router as analytics_router
from api.routes.build import router as build_router
from api.websocket_handler import router as websocket_router


# Project root - because assumptions are fun
PROJECT_ROOT = Path(__file__).parent.parent

# Global instances - singletons everywhere
feature_registry = FeatureRegistry(str(PROJECT_ROOT))
config_service = ConfigService(str(PROJECT_ROOT))
test_runner = get_test_runner(str(PROJECT_ROOT))
error_watcher = get_error_watcher(str(PROJECT_ROOT))
supabase_client = get_supabase_client()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Startup and shutdown events.
    """
    # Startup
    print("🚀 BuildRunner API starting up...")
    print(f"📁 Project root: {PROJECT_ROOT}")

    # Start error watcher
    await error_watcher.start_watching()

    yield

    # Shutdown
    print("🛑 BuildRunner API shutting down...")

    # Stop background services
    if test_runner.is_running:
        await test_runner.stop()

    if error_watcher.is_watching:
        await error_watcher.stop_watching()


# Create FastAPI app
app = FastAPI(
    title="BuildRunner 3.0 API",
    description="Git-backed governance system for AI-assisted project development",
    version="3.0.0",
    lifespan=lifespan
)


# CORS middleware - because browsers are paranoid
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route routers
app.include_router(analytics_router)
app.include_router(build_router)
app.include_router(websocket_router)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all API requests to context.
    Track response times because performance matters (until it doesn't).
    """
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log to context
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 2)
    }

    # Log slow requests
    if duration > 1.0:
        print(f"⚠️  Slow request: {request.method} {request.url.path} took {duration:.2f}s")

    # Add custom header with response time
    response.headers["X-Response-Time"] = str(duration)

    return response


# ============================================================================
# Core Feature Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns OK if the API hasn't exploded yet.
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(),
        version="3.0.0"
    )


@app.get("/features", response_model=List[FeatureModel])
async def get_features(
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    """
    Get all features with optional filtering.

    Args:
        status: Filter by status (planned, in_progress, complete)
        priority: Filter by priority (critical, high, medium, low)

    Returns:
        List of features
    """
    try:
        features = feature_registry.list_features()

        # Apply filters
        if status:
            features = [f for f in features if f.get("status") == status]
        if priority:
            features = [f for f in features if f.get("priority") == priority]

        return features
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/features", response_model=FeatureModel, status_code=201)
async def create_feature(feature: FeatureCreate):
    """
    Create a new feature.

    Args:
        feature: Feature data

    Returns:
        Created feature
    """
    try:
        result = feature_registry.add_feature(
            feature_id=feature.id,
            name=feature.name,
            description=feature.description,
            priority=feature.priority,
            week=feature.week,
            build=feature.build
        )

        # Sync to Supabase if enabled
        if supabase_client.is_enabled():
            await supabase_client.sync_feature(result)

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/features/{feature_id}", response_model=FeatureModel)
async def update_feature(feature_id: str, updates: FeatureUpdate):
    """
    Update an existing feature.

    Args:
        feature_id: ID of feature to update
        updates: Updates to apply

    Returns:
        Updated feature
    """
    try:
        # Filter out None values
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

        result = feature_registry.update_feature(feature_id, **update_data)

        if not result:
            raise HTTPException(status_code=404, detail="Feature not found")

        # Sync to Supabase if enabled
        if supabase_client.is_enabled():
            await supabase_client.sync_feature(result)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/features/{feature_id}", status_code=204)
async def delete_feature(feature_id: str):
    """
    Delete a feature.

    Args:
        feature_id: ID of feature to delete
    """
    try:
        success = feature_registry.delete_feature(feature_id)

        if not success:
            raise HTTPException(status_code=404, detail="Feature not found")

        # Delete from Supabase if enabled
        if supabase_client.is_enabled():
            await supabase_client.delete_feature(feature_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/metrics", response_model=MetricsModel)
async def get_metrics():
    """
    Get system metrics.

    Returns:
        Complete metrics
    """
    try:
        # Get feature metrics
        features = feature_registry.list_features()
        total = len(features)
        completed = len([f for f in features if f.get("status") == "complete"])
        in_progress = len([f for f in features if f.get("status") == "in_progress"])
        planned = len([f for f in features if f.get("status") == "planned"])

        feature_metrics = FeatureMetrics(
            total=total,
            completed=completed,
            in_progress=in_progress,
            planned=planned,
            completion_percentage=round((completed / total * 100) if total > 0 else 0, 2)
        )

        # Get test metrics if available
        test_metrics = None
        latest_results = test_runner.get_latest_results()
        if latest_results:
            test_metrics = TestMetrics(
                total_tests=latest_results.get("total", 0),
                passing=latest_results.get("passed", 0),
                failing=latest_results.get("failed", 0),
                coverage=latest_results.get("coverage", 0.0),
                last_run=datetime.fromisoformat(latest_results["timestamp"])
            )

        # Get error metrics
        error_summary = error_watcher.get_error_summary()
        error_metrics = ErrorMetrics(
            total_errors=error_summary["total_errors"],
            critical=error_summary["by_severity"].get("critical", 0),
            resolved=len([e for e in error_watcher.errors if e["resolved"]]),
            average_resolution_time=None  # TODO: track resolution times
        )

        return MetricsModel(
            features=feature_metrics,
            tests=test_metrics,
            errors=error_metrics,
            last_sync=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync", response_model=SyncResponse)
async def sync_features():
    """
    Trigger feature sync.
    Regenerate STATUS.md and sync with remote if configured.

    Returns:
        Sync result
    """
    try:
        features = feature_registry.list_features()

        # Regenerate STATUS.md
        generator = StatusGenerator(str(PROJECT_ROOT))
        generator.generate()

        return SyncResponse(
            success=True,
            message="Features synced successfully",
            synced_features=len(features),
            timestamp=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/governance")
async def get_governance():
    """
    Get governance rules.

    Returns:
        Governance configuration
    """
    try:
        governance = GovernanceManager(str(PROJECT_ROOT))
        config = governance.config
        return {"governance": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Config Endpoints
# ============================================================================

@app.get("/config", response_model=ConfigModel)
async def get_config(source: str = "merged"):
    """
    Get configuration.

    Args:
        source: Config source (global, project, merged)

    Returns:
        Configuration
    """
    try:
        if source == "global":
            config = config_service.get_global_config()
            return ConfigModel(
                global_config=config,
                project_config={},
                merged=config,
                source="global"
            )
        elif source == "project":
            config = config_service.get_project_config()
            return ConfigModel(
                global_config={},
                project_config=config,
                merged=config,
                source="project"
            )
        else:
            global_cfg = config_service.get_global_config()
            project_cfg = config_service.get_project_config()
            merged = config_service.get_merged_config()
            return ConfigModel(
                global_config=global_cfg,
                project_config=project_cfg,
                merged=merged,
                source="merged"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/config", response_model=ConfigModel)
async def update_config(updates: ConfigUpdate):
    """
    Update project configuration.

    Args:
        updates: Configuration updates

    Returns:
        Updated configuration
    """
    try:
        # Filter out None values
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

        # Update project config
        updated = config_service.update_project_config(update_data)

        # Return merged config
        return ConfigModel(
            global_config=config_service.get_global_config(),
            project_config=updated,
            merged=config_service.get_merged_config(),
            source="merged"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/config/schema")
async def get_config_schema():
    """
    Get configuration schema.

    Returns:
        JSON schema for behavior.yaml
    """
    try:
        schema = config_service.get_config_schema()
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Debug Endpoints
# ============================================================================

@app.get("/debug/status", response_model=SystemStatus)
async def get_debug_status():
    """
    Get system status and diagnostics.

    Returns:
        System status
    """
    try:
        features = feature_registry.list_features()
        error_summary = error_watcher.get_error_summary()

        # Determine overall status
        status = "healthy"
        issues = []

        if error_summary["by_severity"].get("critical", 0) > 0:
            status = "critical"
            issues.append(f"{error_summary['by_severity']['critical']} critical errors detected")
        elif error_summary["total_errors"] > 10:
            status = "degraded"
            issues.append(f"{error_summary['total_errors']} errors detected")

        if not features:
            issues.append("No features loaded")

        return SystemStatus(
            status=status,
            uptime=time.time(),  # Simplified - should track actual uptime
            version="3.0.0",
            features_loaded=len(features),
            tests_running=test_runner.is_running,
            error_count=error_summary["total_errors"],
            last_sync=datetime.now(),
            issues=issues
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/blockers", response_model=List[Blocker])
async def get_blockers():
    """
    Get current blockers from context.

    Returns:
        List of blockers
    """
    try:
        # Read blockers from context file
        blockers_file = PROJECT_ROOT / ".buildrunner" / "context" / "blockers.md"

        if not blockers_file.exists():
            return []

        # Parse blockers file
        # This is a simplified implementation
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/test", response_model=TestResultModel)
async def run_test():
    """
    Run test suite immediately.

    Returns:
        Test results
    """
    try:
        results = await test_runner.run_once()
        return TestResultModel(**results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/errors", response_model=ErrorSummary)
async def get_errors(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    unresolved_only: bool = False
):
    """
    Get recent errors.

    Args:
        category: Filter by category
        severity: Filter by severity
        unresolved_only: Only unresolved errors

    Returns:
        Error summary
    """
    try:
        errors = error_watcher.get_errors(category, severity, unresolved_only)
        summary = error_watcher.get_error_summary()

        return ErrorSummary(
            total_errors=summary["total_errors"],
            by_category=summary["by_category"],
            by_severity=summary["by_severity"],
            recent_errors=[ErrorModel(**e) for e in errors[-10:]]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/retry/{command_id}")
async def retry_command(command_id: str, force: bool = False):
    """
    Retry a failed command.

    Args:
        command_id: Command ID to retry
        force: Force retry even if not retriable

    Returns:
        Retry result
    """
    # This is a placeholder - would need actual command tracking
    return {
        "command_id": command_id,
        "status": "not_implemented",
        "message": "Command retry not yet implemented"
    }


# ============================================================================
# Test Runner Endpoints
# ============================================================================

@app.post("/test/start")
async def start_test_runner(interval: int = 60):
    """
    Start background test runner.

    Args:
        interval: Test interval in seconds

    Returns:
        Start result
    """
    try:
        result = await test_runner.start(interval)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/stop")
async def stop_test_runner():
    """
    Stop background test runner.

    Returns:
        Stop result
    """
    try:
        result = await test_runner.stop()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test/results", response_model=Optional[TestResultModel])
async def get_test_results():
    """
    Get latest test results.

    Returns:
        Latest test results or None
    """
    try:
        results = test_runner.get_latest_results()
        if results:
            return TestResultModel(**results)
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test/status")
async def get_test_status():
    """
    Get test runner status.

    Returns:
        Test runner status
    """
    try:
        return test_runner.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/test/stream")
async def test_stream_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for streaming test results.

    Clients connect here to receive real-time test updates.
    """
    await websocket.accept()
    test_runner.add_websocket_client(websocket)

    try:
        # Keep connection alive and receive messages
        while True:
            data = await websocket.receive_text()
            # Echo back for keepalive
            await websocket.send_json({"type": "ping", "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        test_runner.remove_websocket_client(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        test_runner.remove_websocket_client(websocket)


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Run the API
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
