# BuildRunner 3.2 - Automated Debugging & Testing Tools

**Date:** 2025-11-18
**Status:** ✅ CORE INTEGRATION COMPLETE

## Overview

BuildRunner 3.2 now includes comprehensive automated debugging and testing tools that provide real-time monitoring, static analysis, and automatic error detection/correction capabilities.

## Implemented Tools

### 1. ✅ OpenTelemetry with Datadog Integration

**Purpose:** Real-time distributed tracing and monitoring of LLM operations

**Components:**
- `core/telemetry/otel_instrumentation.py` - Core telemetry module
- `otel-collector-config.yaml` - Collector configuration
- `scripts/start-otel-collector.sh` - Collector startup script

**Features:**
- Automatic tracing of all API calls
- LLM token usage tracking
- Performance metrics (latency, throughput)
- Error rate monitoring
- Custom metric recording

**Configuration:**
```env
DD_API_KEY=dd26b2ad8b65e2634048a0d9a09db7a7
DD_SITE=us5.datadoghq.com
DD_ENV=development
DD_SERVICE=buildrunner
```

**Usage:**
```bash
# Start the collector
./scripts/start-otel-collector.sh

# Telemetry auto-initializes with API server
uvicorn api.server:app
```

### 2. ✅ Ruff - Fast Python Linter

**Purpose:** Comprehensive linting with 600+ built-in rules

**Configuration:** `.ruff.toml`
- Line length: 100
- Target: Python 3.11+
- Enabled rule sets: pycodestyle, pyflakes, pyupgrade, bugbear, simplify, and more
- Auto-fix capability

**CLI Commands:**
```bash
# Check for issues
br quality lint

# Auto-fix issues
br quality lint --fix

# Check specific path
br quality lint core/
```

### 3. ✅ MyPy - Static Type Checker

**Purpose:** Type safety and early error detection

**Configuration:** `mypy.ini`
- Strict mode available
- Gradual typing support
- Plugin support (Pydantic)
- Incremental checking

**CLI Commands:**
```bash
# Run type check
br quality typecheck

# Strict mode
br quality typecheck --strict

# Check specific module
br quality typecheck api/
```

### 4. ✅ Pre-commit Hooks

**Purpose:** Automated quality checks before commits

**Configuration:** `.pre-commit-config.yaml`

**Hooks Included:**
- Black (code formatting)
- Ruff (linting with auto-fix)
- MyPy (type checking)
- Bandit (security scanning)
- detect-secrets (credential leak prevention)
- YAML/JSON/TOML validation
- Large file detection
- Trailing whitespace removal
- Markdown linting

**Setup:**
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### 5. ✅ Enhanced Quality Commands

**Updated Commands:**
```bash
# Run all quality checks
br quality check

# Generate detailed report
br quality report --output quality.md

# Show quality score
br quality score

# Auto-fix formatting and linting
br quality fix --apply

# Lint with Ruff
br quality lint [--fix]

# Type check with MyPy
br quality typecheck [--strict]
```

### 6. ✅ CI/CD Integration

**GitHub Actions Updates:**
- Ruff linting in CI pipeline
- MyPy type checking
- Security scanning with Bandit
- Automated Playwright E2E tests
- Coverage reporting to Codecov

## Testing Infrastructure

### Existing Test Suite
- **Unit Tests:** 435+ tests
- **Coverage:** 93% average
- **E2E Tests:** 25+ Playwright scenarios
- **Browsers:** Chrome, Firefox, WebKit, Mobile

### Added Capabilities
- **pytest-xdist:** Parallel test execution (configured)
- **Pre-commit Testing:** Automatic before commits
- **Type Safety:** MyPy validation
- **Security Scanning:** Bandit + detect-secrets

## Monitoring Dashboard (Datadog)

### Metrics Available
- **LLM Performance:**
  - Token usage by model
  - Response latency
  - Error rates
  - Cost tracking

- **API Performance:**
  - Endpoint latency
  - Request volume
  - Error distribution
  - Status codes

- **Task Execution:**
  - Task completion rate
  - Duration by type
  - Success/failure ratio
  - Queue depth

- **System Health:**
  - CPU/Memory usage
  - Disk I/O
  - Network traffic
  - Process metrics

## Automated Debugging Flow

### On Code Change:
1. **Pre-commit hooks** run automatically
   - Format with Black
   - Lint with Ruff
   - Type check with MyPy
   - Scan for secrets

### On Commit:
1. **CI Pipeline** executes
   - Unit tests (pytest)
   - Integration tests
   - E2E tests (Playwright)
   - Security scanning
   - Coverage reporting

### During Runtime:
1. **OpenTelemetry** traces all operations
2. **Datadog** monitors and alerts on anomalies
3. **Error tracking** captures exceptions
4. **Performance metrics** identify bottlenecks

### Manual Debugging:
```bash
# Full quality check
br quality check --strict

# Fix all auto-fixable issues
br quality fix --apply

# Generate quality report
br quality report --verbose

# Run specific checks
br quality lint
br quality typecheck
```

## Configuration Files Created

1. **`.ruff.toml`** - Ruff linter configuration
2. **`mypy.ini`** - MyPy type checker settings
3. **`.pre-commit-config.yaml`** - Pre-commit hooks
4. **`otel-collector-config.yaml`** - OpenTelemetry collector
5. **Updated `pyproject.toml`** - Added dev dependencies
6. **Updated `.env`** - Datadog configuration

## Dependencies Added

**Main:**
```toml
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp>=1.20.0
opentelemetry-instrumentation-fastapi>=0.41b0
opentelemetry-instrumentation-requests>=0.41b0
opentelemetry-instrumentation-logging>=0.41b0
opentelemetry-instrumentation-httpx>=0.41b0
```

**Dev:**
```toml
pytest-xdist>=3.0.0
mypy>=1.7.0
types-PyYAML
types-requests
ruff>=0.1.0  # already present
black>=23.0.0  # already present
```

## Quick Start Guide

### 1. Install Dependencies
```bash
pip install -e ".[dev]"
```

### 2. Set Up Pre-commit
```bash
pre-commit install
```

### 3. Start Monitoring
```bash
# Start OpenTelemetry collector
./scripts/start-otel-collector.sh

# Start API server (auto-initializes telemetry)
uvicorn api.server:app
```

### 4. Run Quality Checks
```bash
# Full check
br quality check

# Auto-fix issues
br quality fix --apply
```

### 5. View Metrics
- Visit Datadog dashboard at https://us5.datadoghq.com
- View traces, metrics, and logs for BuildRunner service

## Remaining Tasks

- [ ] Integrate Sentry for automatic error tracking
- [ ] Add GitHub status checks to phase system
- [ ] Update phase_manager for automated testing
- [ ] Create AI debugger agent for auto-fixing errors

## Benefits

1. **Early Error Detection:** Type checking and linting catch issues before runtime
2. **Automatic Fixes:** Many issues auto-corrected without manual intervention
3. **Real-time Monitoring:** Track performance and errors in production
4. **Consistent Code Quality:** Enforced standards across the codebase
5. **Security Scanning:** Prevent credential leaks and vulnerabilities
6. **LLM Observability:** Monitor token usage and costs
7. **Faster Debugging:** Distributed tracing shows exact failure points
8. **Automated Workflow:** Pre-commit hooks ensure quality before commits

## Summary

BuildRunner 3.2 now features a comprehensive automated debugging and testing infrastructure that:

- **Prevents** errors through static analysis and type checking
- **Detects** issues early with pre-commit hooks
- **Monitors** runtime behavior with OpenTelemetry/Datadog
- **Auto-fixes** common problems with Ruff and Black
- **Validates** code quality continuously through CI/CD
- **Tracks** LLM usage and performance metrics

This provides a robust foundation for maintaining code quality and quickly identifying/resolving issues in both development and production environments.

---

*Generated: 2025-11-18*
*BuildRunner Version: 3.2.0*