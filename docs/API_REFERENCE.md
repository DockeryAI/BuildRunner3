# BuildRunner 3.1 - API Reference

**Version:** v3.1.0-alpha
**Last Updated:** 2025-11-18
**Status:** ⚠️ Beta - Core functionality tested, orchestrator integration in progress

---

## Table of Contents

- [CLI Commands](#cli-commands)
  - [Security Commands](#security-commands)
  - [Routing Commands](#routing-commands)
  - [Telemetry Commands](#telemetry-commands)
  - [Parallel Commands](#parallel-commands)
  - [Quality Commands](#quality-commands)
  - [Gap Analysis Commands](#gap-analysis-commands)
- [Python API](#python-api)
  - [Security API](#security-api)
  - [Routing API](#routing-api)
  - [Telemetry API](#telemetry-api)
  - [Parallel API](#parallel-api)
- [Configuration](#configuration)
- [Data Structures](#data-structures)

---

## CLI Commands

All commands follow the format: `br <category> <command> [options]`

### Security Commands

#### `br security check`

Check staged files for security issues (secrets and SQL injection).

**Usage:**
```bash
br security check [OPTIONS]
```

**Options:**
- `--staged` - Check only staged files (faster)
- `--secrets` - Check only for secrets
- `--sql` - Check only for SQL injection
- `--no-secrets` - Skip secret detection
- `--no-sql` - Skip SQL injection detection

**Examples:**
```bash
# Check all staged files
br security check --staged

# Check only for secrets
br security check --secrets

# Check without SQL injection scanning
br security check --no-sql
```

**Exit Codes:**
- `0` - No issues found
- `1` - Security issues detected

---

#### `br security scan`

Scan files or directories for security vulnerabilities.

**Usage:**
```bash
br security scan [OPTIONS]
```

**Options:**
- `--file FILE` - Scan specific file
- `--directory DIR` - Scan specific directory
- `--recursive` - Scan subdirectories (default: true)

**Examples:**
```bash
# Scan entire project
br security scan

# Scan specific file
br security scan --file src/config.py

# Scan directory
br security scan --directory src/
```

**Output:**
```
Scanning: src/config.py

❌ SECRETS DETECTED:
  Line 12: [openrouter_key] sk-o...8810
  Line 15: [anthropic_key] sk-a...o012

💡 Recommendation:
  • Move secrets to .env file (add to .gitignore)
  • Use environment variables
  • Never commit API keys to git
```

---

#### `br security hooks install`

Install git pre-commit hook for automatic security scanning.

**Usage:**
```bash
br security hooks install [OPTIONS]
```

**Options:**
- `--force` - Overwrite existing hook

**Examples:**
```bash
# Install hook
br security hooks install

# Reinstall (overwrite existing)
br security hooks install --force
```

**Exit Codes:**
- `0` - Hook installed successfully
- `1` - Installation failed

⚠️ **Note:** Hook code exists but needs production validation.

---

#### `br security hooks status`

Check pre-commit hook installation status.

**Usage:**
```bash
br security hooks status
```

**Output:**
```
✅ Pre-commit hook installed
Location: .git/hooks/pre-commit
Permissions: -rwxr-xr-x
```

---

#### `br security hooks uninstall`

Remove pre-commit hook.

**Usage:**
```bash
br security hooks uninstall
```

---

#### `br security precommit`

Run pre-commit security checks (called by hook, not typically run manually).

**Usage:**
```bash
br security precommit
```

---

### Routing Commands

#### `br routing estimate`

Estimate task complexity and recommend model.

**Usage:**
```bash
br routing estimate TASK_DESCRIPTION [OPTIONS]
```

**Options:**
- `--format json` - Output as JSON
- `--verbose` - Show detailed analysis

**Examples:**
```bash
# Estimate complexity
br routing estimate "Add user authentication with JWT tokens"

# JSON output
br routing estimate "Fix bug in payment processor" --format json
```

**Output:**
```
Task: Add user authentication with JWT tokens

Complexity: moderate
Recommended Model: sonnet
Estimated Cost: $0.15
Estimated Time: 90 minutes

Reasoning:
- Multiple components (auth, JWT, validation)
- Moderate technical complexity
- Requires security considerations
```

**JSON Output:**
```json
{
  "task": "Add user authentication with JWT tokens",
  "complexity_level": "moderate",
  "complexity_score": 65,
  "recommended_model": "sonnet",
  "estimated_cost": 0.15,
  "estimated_time_minutes": 90,
  "reasoning": ["Multiple components", "Moderate technical complexity"]
}
```

⚠️ **Note:** Uses heuristic-based estimation. AI-powered estimation optional (requires API key, not yet integrated).

---

#### `br routing select`

Select optimal model for a task with optional constraints.

**Usage:**
```bash
br routing select TASK_DESCRIPTION [OPTIONS]
```

**Options:**
- `--cost-limit FLOAT` - Maximum cost constraint
- `--time-limit INT` - Maximum time constraint (minutes)
- `--model MODEL` - Force specific model (haiku/sonnet/opus)
- `--format json` - Output as JSON

**Examples:**
```bash
# Auto-select with cost limit
br routing select "Refactor database queries" --cost-limit 0.05

# Force specific model
br routing select "Critical bug fix" --model opus

# JSON output
br routing select "Add feature" --format json
```

**Output:**
```
Task: Refactor database queries
Cost Limit: $0.05

Selected Model: haiku
Estimated Cost: $0.03
Estimated Time: 60 minutes

✅ Meets cost constraint
```

---

#### `br routing costs`

View cost tracking summary.

**Usage:**
```bash
br routing costs [OPTIONS]
```

**Options:**
- `--period PERIOD` - Time period (day/week/month)
- `--format json` - Output as JSON
- `--format csv` - Output as CSV

**Examples:**
```bash
# Current session costs
br routing costs

# Weekly summary
br routing costs --period week

# Export as CSV
br routing costs --period month --format csv > costs.csv
```

**Output:**
```
Cost Summary (This Week)

Model Distribution:
  Haiku:  15 requests | $1.23
  Sonnet: 8 requests  | $4.56
  Opus:   2 requests  | $8.90

Total: 25 requests | $14.69

Daily Breakdown:
  2025-11-11: $2.34
  2025-11-12: $3.45
  2025-11-13: $4.56
  2025-11-14: $2.12
  2025-11-15: $2.22
```

⚠️ **Note:** Cost tracking interface defined, persistence layer in development (SQLite).

---

#### `br routing models`

List available models and pricing.

**Usage:**
```bash
br routing models
```

**Output:**
```
Available Models:

┌────────┬──────────────┬──────────────┬─────────────────┐
│ Model  │ Input Cost   │ Output Cost  │ Typical Latency │
├────────┼──────────────┼──────────────┼─────────────────┤
│ haiku  │ $0.25/1M     │ $1.25/1M     │ ~500ms          │
│ sonnet │ $3.00/1M     │ $15.00/1M    │ ~1000ms         │
│ opus   │ $15.00/1M    │ $75.00/1M    │ ~2000ms         │
└────────┴──────────────┴──────────────┴─────────────────┘

Recommendations:
  • haiku: Simple tasks, refactoring, documentation
  • sonnet: Moderate complexity, feature development
  • opus: Critical bugs, complex architecture, production issues
```

---

### Telemetry Commands

#### `br telemetry summary`

View telemetry metrics summary.

**Usage:**
```bash
br telemetry summary [OPTIONS]
```

**Options:**
- `--hours INT` - Last N hours (default: 24)
- `--format json` - Output as JSON

**Examples:**
```bash
# Last 24 hours
br telemetry summary

# Last week
br telemetry summary --hours 168

# JSON output
br telemetry summary --format json
```

**Output:**
```
Telemetry Summary (Last 24 Hours)

Success Rate: 90% (18/20 tasks)
Average Latency: 1250ms
Total Cost: $12.45
Error Count: 2
Event Count: 156

Top Errors:
  • API rate limit exceeded (2 times)
```

⚠️ **Note:** Event schemas defined, collection needs orchestrator integration.

---

#### `br telemetry events`

List recent events.

**Usage:**
```bash
br telemetry events [OPTIONS]
```

**Options:**
- `--type TYPE` - Filter by event type
- `--hours INT` - Last N hours (default: 24)
- `--limit INT` - Maximum events to show (default: 50)
- `--format json` - Output as JSON

**Examples:**
```bash
# Recent events
br telemetry events

# Failed tasks only
br telemetry events --type task_failed

# Last hour
br telemetry events --hours 1

# JSON export
br telemetry events --format json > events.json
```

**Output:**
```
Recent Events (Last 24 Hours)

2025-11-18 09:15:23 | task_started      | task-001 | Add user auth
2025-11-18 09:16:45 | task_completed    | task-001 | Duration: 82s
2025-11-18 09:20:12 | task_started      | task-002 | Fix bug #123
2025-11-18 09:21:34 | task_failed       | task-002 | Error: API timeout
2025-11-18 09:22:15 | task_retry        | task-002 | Attempt 2/3
2025-11-18 09:23:56 | task_completed    | task-002 | Duration: 104s
```

---

#### `br telemetry alerts`

Check for threshold alerts.

**Usage:**
```bash
br telemetry alerts [OPTIONS]
```

**Options:**
- `--level LEVEL` - Filter by severity (info/warning/critical)
- `--format json` - Output as JSON

**Examples:**
```bash
# All alerts
br telemetry alerts

# Critical only
br telemetry alerts --level critical

# JSON output
br telemetry alerts --format json
```

**Output:**
```
Active Alerts

⚠️ WARNING: Success rate below threshold
  Current: 75%
  Threshold: 80%
  Last triggered: 2025-11-18 09:30:45

🔴 CRITICAL: Daily cost exceeded
  Current: $12.45
  Threshold: $10.00
  Last triggered: 2025-11-18 09:35:12
```

---

#### `br telemetry performance`

View performance metrics.

**Usage:**
```bash
br telemetry performance [OPTIONS]
```

**Options:**
- `--hours INT` - Last N hours (default: 24)
- `--format json` - Output as JSON

**Examples:**
```bash
# Performance summary
br telemetry performance

# Last week
br telemetry performance --hours 168
```

**Output:**
```
Performance Metrics (Last 24 Hours)

Latency Percentiles:
  P50: 1250ms
  P95: 2450ms
  P99: 3890ms

Throughput:
  Tasks/hour: 12
  Events/hour: 156

Resource Usage:
  CPU: moderate
  Memory: 245 MB
  Disk: 1.2 GB
```

---

#### `br telemetry export`

Export telemetry data to CSV.

**Usage:**
```bash
br telemetry export OUTPUT_FILE [OPTIONS]
```

**Options:**
- `--type TYPE` - Export type (metrics/events/costs)
- `--hours INT` - Last N hours (default: 24)

**Examples:**
```bash
# Export all metrics
br telemetry export metrics.csv

# Export events
br telemetry export events.csv --type events

# Export weekly costs
br telemetry export weekly-costs.csv --type costs --hours 168
```

---

### Parallel Commands

#### `br parallel start`

Start a parallel build session.

**Usage:**
```bash
br parallel start SESSION_NAME [OPTIONS]
```

**Options:**
- `--tasks INT` - Number of tasks (required)
- `--workers INT` - Number of workers (default: 3)
- `--watch` - Show live dashboard
- `--config FILE` - Load configuration from file

**Examples:**
```bash
# Start session
br parallel start "Sprint 42" --tasks 20 --workers 3

# With live dashboard
br parallel start "Build v3.1" --tasks 50 --workers 5 --watch

# Custom config
br parallel start "Test Build" --config parallel-config.json
```

**Output:**
```
Starting parallel session: Sprint 42

Session ID: session-abc123
Tasks: 20
Workers: 3
Status: running

✅ Session started successfully
```

⚠️ **Note:** Unit tested (28 tests), end-to-end execution not yet tested in production.

---

#### `br parallel status`

View session status.

**Usage:**
```bash
br parallel status [SESSION_ID]
```

**Examples:**
```bash
# Current session
br parallel status

# Specific session
br parallel status session-abc123
```

**Output:**
```
Session: Sprint 42 (session-abc123)

Status: running
Progress: 12/20 tasks completed (60%)
Workers: 3 active

Recent Activity:
  09:15:23 | worker-1 | Completed task-005
  09:16:45 | worker-2 | Started task-013
  09:17:12 | worker-3 | Completed task-008
```

---

#### `br parallel dashboard`

Show live dashboard with real-time updates.

**Usage:**
```bash
br parallel dashboard [SESSION_ID]
```

**Features:**
- Real-time task progress
- Worker status and health
- Performance metrics
- Cost tracking
- Auto-refresh every 2 seconds

**Controls:**
- `q` - Quit
- `r` - Refresh
- `p` - Pause session
- `s` - Stop session

---

#### `br parallel list`

List all sessions.

**Usage:**
```bash
br parallel list [OPTIONS]
```

**Options:**
- `--status STATUS` - Filter by status (running/paused/completed/failed)
- `--format json` - Output as JSON

**Examples:**
```bash
# All sessions
br parallel list

# Running sessions only
br parallel list --status running

# JSON output
br parallel list --format json
```

**Output:**
```
Parallel Sessions

┌──────────────┬────────────┬─────────┬──────────┬─────────┐
│ Session ID   │ Name       │ Status  │ Progress │ Workers │
├──────────────┼────────────┼─────────┼──────────┼─────────┤
│ session-abc  │ Sprint 42  │ running │ 12/20    │ 3       │
│ session-def  │ Build v3.1 │ paused  │ 35/50    │ 5       │
│ session-ghi  │ Refactor   │ done    │ 10/10    │ 2       │
└──────────────┴────────────┴─────────┴──────────┴─────────┘
```

---

#### `br parallel workers`

View worker status and health.

**Usage:**
```bash
br parallel workers [SESSION_ID]
```

**Output:**
```
Workers (session-abc123)

┌──────────┬─────────┬───────────┬──────────┬────────────┐
│ Worker   │ Status  │ Current   │ Complete │ Last Ping  │
├──────────┼─────────┼───────────┼──────────┼────────────┤
│ worker-1 │ active  │ task-013  │ 4        │ 2s ago     │
│ worker-2 │ active  │ task-015  │ 5        │ 1s ago     │
│ worker-3 │ idle    │ -         │ 3        │ 3s ago     │
└──────────┴─────────┴───────────┴──────────┴────────────┘
```

---

#### `br parallel pause`

Pause a running session.

**Usage:**
```bash
br parallel pause SESSION_ID
```

---

#### `br parallel resume`

Resume a paused session.

**Usage:**
```bash
br parallel resume SESSION_ID
```

---

#### `br parallel stop`

Stop a session.

**Usage:**
```bash
br parallel stop SESSION_ID [OPTIONS]
```

**Options:**
- `--force` - Force stop without cleanup

---

#### `br parallel cleanup`

Remove completed/failed sessions.

**Usage:**
```bash
br parallel cleanup [OPTIONS]
```

**Options:**
- `--days INT` - Remove sessions older than N days (default: 7)
- `--all` - Remove all completed sessions

---

### Quality Commands

#### `br quality check`

Run quality gate checks.

**Usage:**
```bash
br quality check [OPTIONS]
```

**Options:**
- `--format json` - Output as JSON
- `--strict` - Fail on warnings

**Output:**
```
Quality Gate Results

Overall Score: 85/100 ✅

┌─────────────────┬───────┬───────────┬────────┐
│ Category        │ Score │ Threshold │ Status │
├─────────────────┼───────┼───────────┼────────┤
│ Security        │ 95    │ 90        │ ✅     │
│ Testing         │ 85    │ 80        │ ✅     │
│ Documentation   │ 75    │ 70        │ ✅     │
│ Structure       │ 80    │ 75        │ ✅     │
└─────────────────┴───────┴───────────┴────────┘
```

---

### Gap Analysis Commands

#### `br gaps analyze`

Analyze project for missing features and gaps.

**Usage:**
```bash
br gaps analyze [OPTIONS]
```

**Options:**
- `--format json` - Output as JSON
- `--severity LEVEL` - Filter by severity (high/medium/low)

**Output:**
```
Gap Analysis Results

HIGH SEVERITY (3):
  • Missing integration tests for auth module
  • No error handling in API client
  • Security: Hardcoded credentials in config.py

MEDIUM SEVERITY (5):
  • Incomplete documentation for routing module
  • No logging in worker coordinator
  • Missing type hints in utils.py

LOW SEVERITY (2):
  • Outdated dependency: requests 2.28.0 → 2.31.0
  • Code duplication in test files
```

---

## Python API

### Security API

#### SecretScanner

Scan files for exposed secrets.

```python
from core.security.scanner import SecretScanner

scanner = SecretScanner()

# Scan file
secrets = scanner.scan_file("config.py")
for secret in secrets:
    print(f"Line {secret.line_number}: {secret.secret_type}")
    print(f"Masked value: {secret.masked_value}")

# Scan directory
results = scanner.scan_directory("src/")
print(f"Found {len(results)} secrets across all files")

# Scan content
content = "API_KEY = 'sk-ant-abc123def456'"
secrets = scanner.scan_content(content)
```

**SecretMatch Data Structure:**
```python
@dataclass
class SecretMatch:
    file_path: str
    line_number: int
    secret_type: str  # e.g., "anthropic_key", "openai_key"
    masked_value: str  # e.g., "sk-a...f456"
    context: str  # surrounding code
```

---

#### SQLInjectionDetector

Detect SQL injection vulnerabilities.

```python
from core.security.sql_detector import SQLInjectionDetector

detector = SQLInjectionDetector()

# Check file
vulnerabilities = detector.check_file("database.py")
for vuln in vulnerabilities:
    print(f"Line {vuln.line_number}: {vuln.severity} - {vuln.description}")

# Check code
code = '''
query = f"SELECT * FROM users WHERE id={user_id}"
cursor.execute(query)
'''
vulnerabilities = detector.check_code(code, language="python")
```

---

### Routing API

#### ComplexityEstimator

Estimate task complexity.

```python
from core.routing.complexity_estimator import ComplexityEstimator

estimator = ComplexityEstimator()

# Estimate complexity
result = estimator.estimate("Add user authentication with JWT tokens")

print(f"Complexity: {result.complexity_level}")  # simple/moderate/complex/critical
print(f"Score: {result.complexity_score}")  # 0-100
print(f"Model: {result.recommended_model}")  # haiku/sonnet/opus
print(f"Cost: ${result.estimated_cost:.2f}")
print(f"Time: {result.estimated_time_minutes} minutes")

# Factors that influenced the score
for factor in result.factors:
    print(f"  • {factor.name}: {factor.weight}")
```

⚠️ **Note:** Uses heuristic-based estimation. AI integration optional.

---

#### ModelSelector

Select optimal model based on constraints.

```python
from core.routing.model_selector import ModelSelector

selector = ModelSelector()

# Auto-select
model = selector.select_model(
    task_description="Add user authentication",
    complexity_score=65,
    cost_limit=0.10,
    time_limit=120
)

print(f"Selected: {model.name}")  # haiku/sonnet/opus
print(f"Cost: ${model.estimated_cost:.2f}")
print(f"Time: {model.estimated_time_minutes} min")
print(f"Reasoning: {model.reasoning}")
```

---

#### CostTracker

Track model costs.

```python
from core.routing.cost_tracker import CostTracker

tracker = CostTracker()

# Track request
tracker.track_request(
    model="sonnet",
    input_tokens=1500,
    output_tokens=800,
    latency_ms=1250
)

# Get summary
summary = tracker.get_summary(period="week")
print(f"Total cost: ${summary.total_cost:.2f}")
print(f"Total requests: {summary.request_count}")
print(f"By model: {summary.by_model}")

# Export data
tracker.export_csv("costs.csv", period="month")
```

⚠️ **Note:** Persistence layer in development (SQLite).

---

### Telemetry API

#### EventCollector

Collect and manage events.

```python
from core.telemetry.event_collector import EventCollector

collector = EventCollector()

# Collect event
collector.collect_event({
    "type": "task_started",
    "task_id": "task-001",
    "description": "Add user authentication",
    "timestamp": datetime.now().isoformat()
})

# Later...
collector.collect_event({
    "type": "task_completed",
    "task_id": "task-001",
    "duration_ms": 82000,
    "cost": 0.15
})

# Query events
events = collector.get_events(
    event_type="task_failed",
    hours=24
)

# Register listener
def on_task_failed(event):
    print(f"Task {event['task_id']} failed: {event['error']}")

collector.add_listener("task_failed", on_task_failed)
```

---

#### MetricsAnalyzer

Analyze telemetry metrics.

```python
from core.telemetry.metrics_analyzer import MetricsAnalyzer

analyzer = MetricsAnalyzer()

# Calculate metrics
metrics = analyzer.analyze(hours=24)

print(f"Success rate: {metrics.success_rate:.1f}%")
print(f"Average latency: {metrics.avg_latency_ms:.0f}ms")
print(f"P95 latency: {metrics.p95_latency_ms:.0f}ms")
print(f"Total cost: ${metrics.total_cost:.2f}")
print(f"Error count: {metrics.error_count}")

# Get trends
trends = analyzer.get_trends(days=7)
for day, day_metrics in trends.items():
    print(f"{day}: {day_metrics.success_rate:.1f}% success")
```

⚠️ **Note:** Collection needs orchestrator integration.

---

### Parallel API

#### SessionManager

Manage parallel sessions.

```python
from core.parallel.session_manager import SessionManager

manager = SessionManager()

# Create session
session = manager.create_session(
    name="Sprint 42",
    total_tasks=20,
    num_workers=3
)

print(f"Session ID: {session.session_id}")

# Check status
status = manager.get_session_status(session.session_id)
print(f"Progress: {status.completed_tasks}/{status.total_tasks}")

# Pause/resume
manager.pause_session(session.session_id)
manager.resume_session(session.session_id)

# Stop
manager.stop_session(session.session_id)
```

---

#### WorkerCoordinator

Coordinate workers and task distribution.

```python
from core.parallel.worker_coordinator import WorkerCoordinator

coordinator = WorkerCoordinator(session_id="session-abc123")

# Register worker
worker_id = coordinator.register_worker()

# Get next task
task = coordinator.get_next_task(worker_id)
if task:
    print(f"Working on: {task.task_id}")

    # Complete task
    coordinator.complete_task(worker_id, task.task_id)

# Worker heartbeat
coordinator.heartbeat(worker_id)

# Check worker health
health = coordinator.get_worker_health(worker_id)
print(f"Status: {health.status}")  # active/idle/offline
```

---

## Configuration

### Config File Format

`.buildrunner/config.json`:

```json
{
  "routing": {
    "default_model": "sonnet",
    "cost_optimization": true,
    "cost_limits": {
      "daily": 10.00,
      "weekly": 50.00,
      "monthly": 200.00
    }
  },
  "security": {
    "enforce_hooks": true,
    "whitelist_file": ".buildrunner/security/whitelist.txt"
  },
  "telemetry": {
    "enabled": true,
    "storage_dir": ".buildrunner/telemetry",
    "thresholds": {
      "success_rate_warning": 80,
      "latency_warning_ms": 2000
    }
  },
  "parallel": {
    "enabled": true,
    "default_workers": 3,
    "heartbeat_timeout": 30
  }
}
```

---

## Data Structures

### ComplexityResult

```python
@dataclass
class ComplexityResult:
    task_description: str
    complexity_level: str  # simple/moderate/complex/critical
    complexity_score: int  # 0-100
    recommended_model: str  # haiku/sonnet/opus
    estimated_cost: float
    estimated_time_minutes: int
    factors: List[ComplexityFactor]
    reasoning: List[str]
```

### CostSummary

```python
@dataclass
class CostSummary:
    period: str  # day/week/month
    total_cost: float
    request_count: int
    by_model: Dict[str, float]  # {"haiku": 1.23, "sonnet": 4.56}
    by_day: Dict[str, float]  # {"2025-11-15": 2.34}
    avg_cost_per_request: float
```

### TelemetryMetrics

```python
@dataclass
class TelemetryMetrics:
    period_hours: int
    success_rate: float  # 0-100
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_cost: float
    error_count: int
    event_count: int
    top_errors: List[ErrorSummary]
```

### SessionStatus

```python
@dataclass
class SessionStatus:
    session_id: str
    name: str
    status: str  # running/paused/completed/failed
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    num_workers: int
    active_workers: int
    start_time: datetime
    elapsed_time_seconds: int
```

---

## Error Codes

### Exit Codes

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Security issues detected
- `4` - Quality gate failed
- `5` - API error
- `6` - File not found

### Exception Classes

```python
class BuildRunnerError(Exception):
    """Base exception for all BuildRunner errors"""
    pass

class SecurityError(BuildRunnerError):
    """Raised when security issues are detected"""
    pass

class RoutingError(BuildRunnerError):
    """Raised when model routing fails"""
    pass

class TelemetryError(BuildRunnerError):
    """Raised when telemetry operations fail"""
    pass

class ParallelError(BuildRunnerError):
    """Raised when parallel operations fail"""
    pass
```

---

## Environment Variables

- `ANTHROPIC_API_KEY` - Anthropic API key for AI-powered features
- `BR_COST_LIMIT_DAILY` - Daily cost limit (float)
- `BR_COST_LIMIT_WEEKLY` - Weekly cost limit (float)
- `BR_TELEMETRY_ENABLED` - Enable telemetry (true/false)
- `BR_TELEMETRY_EXPORT_DIR` - Directory for telemetry exports
- `BR_CONFIG_FILE` - Path to config file (default: .buildrunner/config.json)

---

## Support

**Documentation:**
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Integration guide

**Get Help:**
- GitHub Issues: https://github.com/your-org/buildrunner3/issues

---

*BuildRunner v3.1.0-alpha - Complete API Reference*
