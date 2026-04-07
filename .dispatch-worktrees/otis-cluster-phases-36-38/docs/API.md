# BuildRunner 3.0 API Documentation

FastAPI backend for BuildRunner 3.0 with feature management, config management, debugging tools, and background test execution.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication required. In production, add API keys or JWT auth.

## Core Endpoints

### Health Check

```http
GET /health
```

Returns API health status.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-17T10:30:00",
  "version": "3.0.0"
}
```

### Features

#### List Features
```http
GET /features?status=planned&priority=high
```

**Query Parameters:**
- `status` (optional): Filter by status (planned, in_progress, complete)
- `priority` (optional): Filter by priority (critical, high, medium, low)

**Response:**
```json
[
  {
    "id": "feature-registry",
    "name": "Feature Registry System",
    "description": "Core feature tracking",
    "status": "complete",
    "version": "3.0.0",
    "priority": "critical",
    "week": 1,
    "build": "1A"
  }
]
```

#### Create Feature
```http
POST /features
```

**Request Body:**
```json
{
  "id": "my-feature",
  "name": "My Feature",
  "description": "Feature description",
  "status": "planned",
  "version": "3.0.0",
  "priority": "high",
  "week": 2,
  "build": "2A"
}
```

**Response:** 201 Created

#### Update Feature
```http
PATCH /features/{feature_id}
```

**Request Body:**
```json
{
  "status": "in_progress",
  "priority": "critical"
}
```

**Response:** 200 OK

#### Delete Feature
```http
DELETE /features/{feature_id}
```

**Response:** 204 No Content

### Metrics

```http
GET /metrics
```

Returns system metrics including feature progress, test results, and error counts.

**Response:**
```json
{
  "features": {
    "total": 11,
    "completed": 2,
    "in_progress": 3,
    "planned": 6,
    "completion_percentage": 18.18
  },
  "tests": {
    "total_tests": 84,
    "passing": 84,
    "failing": 0,
    "coverage": 77.0,
    "last_run": "2025-01-17T10:30:00"
  },
  "errors": {
    "total_errors": 5,
    "critical": 1,
    "resolved": 3
  }
}
```

### Sync

```http
POST /sync
```

Triggers feature sync and STATUS.md regeneration.

**Response:**
```json
{
  "success": true,
  "message": "Features synced successfully",
  "synced_features": 11,
  "timestamp": "2025-01-17T10:30:00"
}
```

### Governance

```http
GET /governance
```

Returns governance rules and configuration.

## Configuration Endpoints

### Get Config

```http
GET /config?source=merged
```

**Query Parameters:**
- `source` (optional): global, project, or merged (default: merged)

**Response:**
```json
{
  "global_config": {},
  "project_config": {},
  "merged": {
    "ai_behavior": {
      "auto_suggest_tests": true,
      "auto_fix_errors": false,
      "verbosity": "normal",
      "max_retries": 3
    },
    "auto_commit": {
      "enabled": false,
      "on_feature_complete": true,
      "require_approval": true
    },
    "testing": {
      "auto_run": false,
      "coverage_threshold": 85
    }
  }
}
```

### Update Config

```http
PATCH /config
```

**Request Body:**
```json
{
  "ai_behavior": {
    "verbosity": "verbose",
    "max_retries": 5
  },
  "testing": {
    "auto_run": true,
    "coverage_threshold": 90
  }
}
```

**Response:** 200 OK

### Get Config Schema

```http
GET /config/schema
```

Returns JSON schema for behavior.yaml configuration.

## Debug Endpoints

### System Status

```http
GET /debug/status
```

Returns system health and diagnostics.

**Response:**
```json
{
  "status": "healthy",
  "uptime": 3600.5,
  "version": "3.0.0",
  "features_loaded": 11,
  "tests_running": false,
  "error_count": 2,
  "issues": []
}
```

### Get Blockers

```http
GET /debug/blockers
```

Returns current development blockers from context.

### Run Tests

```http
POST /debug/test
```

Runs test suite immediately and returns results.

**Response:**
```json
{
  "id": "abc123",
  "timestamp": "2025-01-17T10:30:00",
  "total": 84,
  "passed": 84,
  "failed": 0,
  "skipped": 0,
  "errors": 0,
  "duration": 0.86,
  "coverage": 77.0,
  "status": "completed"
}
```

### Get Errors

```http
GET /debug/errors?category=syntax&severity=high&unresolved_only=true
```

**Query Parameters:**
- `category` (optional): syntax, runtime, test, import, type, network
- `severity` (optional): critical, high, medium, low
- `unresolved_only` (optional): boolean

**Response:**
```json
{
  "total_errors": 5,
  "by_category": {
    "syntax": 2,
    "runtime": 3
  },
  "by_severity": {
    "high": 3,
    "medium": 2
  },
  "recent_errors": [...]
}
```

### Retry Command

```http
POST /debug/retry/{command_id}?force=false
```

Retries a failed command.

## Background Test Runner

### Start Test Runner

```http
POST /test/start?interval=60
```

**Query Parameters:**
- `interval` (optional): Seconds between test runs (default: 60)

**Response:**
```json
{
  "status": "started",
  "interval": 60,
  "message": "Background test runner started"
}
```

### Stop Test Runner

```http
POST /test/stop
```

Stops background test runner.

### Get Test Results

```http
GET /test/results
```

Returns latest test results or null if no tests run yet.

### Get Test Status

```http
GET /test/status
```

**Response:**
```json
{
  "is_running": true,
  "interval": 60,
  "connected_clients": 2,
  "latest_results": {...}
}
```

### Stream Test Results (WebSocket)

```
ws://localhost:8000/test/stream
```

Connect via WebSocket to receive real-time test result updates.

**Message Format:**
```json
{
  "type": "start|progress|result|error|complete",
  "timestamp": "2025-01-17T10:30:00",
  "data": {...}
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "detail": "Error message here"
}
```

**Status Codes:**
- `200` - Success
- `201` - Created
- `204` - No Content
- `400` - Bad Request
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## OpenAPI Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Running the API

```bash
cd /path/to/project
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

## Testing

```bash
pytest tests/ -v --cov=api --cov-report=term-missing
```

## CORS

CORS is enabled for all origins in development. Lock this down in production.
