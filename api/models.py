"""
Pydantic models for BuildRunner 3.0 API

These models define the data structures for all API endpoints.
Because apparently we need type safety in our chaos.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# Feature Models

class FeatureBase(BaseModel):
    """Base feature model - because we love inheritance"""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    status: Literal["planned", "in_progress", "complete"] = "planned"
    version: str = "3.0.0"
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    week: Optional[int] = None
    build: Optional[str] = None


class FeatureCreate(FeatureBase):
    """Model for creating a new feature - optimism in code form"""
    id: str = Field(..., pattern=r"^[a-z0-9-]+$")


class FeatureUpdate(BaseModel):
    """Model for updating an existing feature - aka admitting mistakes"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["planned", "in_progress", "complete"]] = None
    version: Optional[str] = None
    priority: Optional[Literal["critical", "high", "medium", "low"]] = None
    week: Optional[int] = None
    build: Optional[str] = None


class FeatureModel(FeatureBase):
    """Complete feature model with metadata"""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    components: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)
    docs: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Config Models

class ConfigSchema(BaseModel):
    """Schema for behavior.yaml configuration"""
    ai_behavior: Dict[str, Any] = Field(default_factory=dict)
    auto_commit: Dict[str, Any] = Field(default_factory=dict)
    testing: Dict[str, Any] = Field(default_factory=dict)
    notifications: Dict[str, Any] = Field(default_factory=dict)


class ConfigModel(BaseModel):
    """Merged configuration model"""
    global_config: Dict[str, Any] = Field(default_factory=dict)
    project_config: Dict[str, Any] = Field(default_factory=dict)
    merged: Dict[str, Any] = Field(default_factory=dict)
    source: Literal["global", "project", "merged"] = "merged"


class ConfigUpdate(BaseModel):
    """Model for updating project config"""
    ai_behavior: Optional[Dict[str, Any]] = None
    auto_commit: Optional[Dict[str, Any]] = None
    testing: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None


# Error Models

class ErrorCategory(BaseModel):
    """Error classification - because knowing what broke is half the battle"""
    type: Literal["syntax", "runtime", "test", "import", "type", "network", "unknown"]
    severity: Literal["critical", "high", "medium", "low"]
    confidence: float = Field(..., ge=0.0, le=1.0)


class ErrorModel(BaseModel):
    """Complete error model with context and suggestions"""
    id: str
    timestamp: datetime
    message: str
    traceback: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    category: ErrorCategory
    context: Dict[str, Any] = Field(default_factory=dict)
    suggestions: List[str] = Field(default_factory=list)
    resolved: bool = False


class ErrorSummary(BaseModel):
    """Summary of recent errors - the hall of shame"""
    total_errors: int
    by_category: Dict[str, int]
    by_severity: Dict[str, int]
    recent_errors: List[ErrorModel]


# Test Models

class TestCase(BaseModel):
    """Individual test case result"""
    name: str
    status: Literal["passed", "failed", "skipped", "error"]
    duration: float
    message: Optional[str] = None
    traceback: Optional[str] = None


class TestResultModel(BaseModel):
    """Complete test run results"""
    id: str
    timestamp: datetime
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    coverage: Optional[float] = None
    test_cases: List[TestCase] = Field(default_factory=list)
    status: Literal["running", "completed", "failed", "stopped"]


class TestStreamMessage(BaseModel):
    """WebSocket message for test streaming"""
    type: Literal["start", "progress", "result", "error", "complete"]
    timestamp: datetime
    data: Dict[str, Any]


# Metrics Models

class FeatureMetrics(BaseModel):
    """Feature completion metrics"""
    total: int
    completed: int
    in_progress: int
    planned: int
    completion_percentage: float


class TestMetrics(BaseModel):
    """Testing metrics"""
    total_tests: int
    passing: int
    failing: int
    coverage: float
    last_run: Optional[datetime] = None


class ErrorMetrics(BaseModel):
    """Error tracking metrics"""
    total_errors: int
    critical: int
    resolved: int
    average_resolution_time: Optional[float] = None


class MetricsModel(BaseModel):
    """Complete system metrics"""
    features: FeatureMetrics
    tests: Optional[TestMetrics] = None
    errors: Optional[ErrorMetrics] = None
    last_sync: Optional[datetime] = None


# Debug Models

class SystemStatus(BaseModel):
    """System health and diagnostics"""
    status: Literal["healthy", "degraded", "critical"]
    uptime: float
    version: str
    features_loaded: int
    tests_running: bool
    error_count: int
    last_sync: Optional[datetime] = None
    issues: List[str] = Field(default_factory=list)


class Blocker(BaseModel):
    """Development blocker"""
    id: str
    title: str
    description: str
    category: Literal["bug", "dependency", "design", "external", "other"]
    severity: Literal["critical", "high", "medium", "low"]
    created_at: datetime
    resolved: bool = False
    resolution: Optional[str] = None


class CommandRetry(BaseModel):
    """Command retry request"""
    command_id: str
    force: bool = False


# Response Models

class HealthResponse(BaseModel):
    """Health check response - lies we tell ourselves"""
    status: str
    timestamp: datetime
    version: str


class SyncResponse(BaseModel):
    """Sync operation response"""
    success: bool
    message: str
    synced_features: int
    timestamp: datetime


class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
