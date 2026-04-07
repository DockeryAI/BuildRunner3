# BuildRunner 3.1 - Integration Guide

**Version:** v3.1.0-alpha
**Last Updated:** 2025-11-18
**Status:** ⚠️ Beta - Core functionality tested, orchestrator integration in progress

---

## Overview

This guide shows you how to integrate BuildRunner 3.1 into your existing software projects. BuildRunner provides:

- **Security scanning** - Automated secret detection and SQL injection checks
- **Model routing** - Intelligent AI model selection and cost tracking
- **Telemetry** - Comprehensive metrics and monitoring
- **Parallel orchestration** - Multi-session task coordination

---

## Integration Levels

### Level 1: Security Only (10 minutes)

Minimum integration - adds secret detection to prevent credential leaks.

**Best for:** All projects, especially those with API integrations

### Level 2: Security + Routing (30 minutes)

Adds intelligent model selection and cost tracking.

**Best for:** AI-powered development workflows

### Level 3: Full Integration (1-2 hours)

Includes security, routing, telemetry, and parallel orchestration.

**Best for:** Large projects with multiple developers

---

## Level 1: Security Integration

### Step 1: Install BuildRunner

```bash
cd /path/to/your/project
pip install -e /path/to/buildrunner3
```

### Step 2: Install Pre-Commit Hooks

```bash
br security hooks install
```

This creates `.git/hooks/pre-commit` that automatically scans for:
- API keys (13 types)
- SQL injection vulnerabilities
- Database credentials

⚠️ **Note:** Hook code exists but needs production validation.

### Step 3: Scan Existing Code

```bash
# Scan entire project
br security scan

# Or scan specific directory
br security scan --directory src/
```

### Step 4: Fix Any Issues

If secrets are detected:

```bash
# 1. Move secrets to .env file
echo "API_KEY=your-secret-here" >> .env

# 2. Add .env to .gitignore
echo ".env" >> .gitignore
echo "*.env" >> .gitignore

# 3. Update code to use environment variables
```

**Python example:**
```python
# Before
api_key = "sk-ant-abc123"

# After
import os
api_key = os.getenv("API_KEY")
```

**JavaScript example:**
```javascript
// Before
const apiKey = "sk-ant-abc123";

// After
require('dotenv').config();
const apiKey = process.env.API_KEY;
```

### Step 5: Verify

```bash
# Check staged files
br security check --staged

# Should show: ✅ No security issues detected
```

**✅ Level 1 Complete!** Your project now has automated security scanning.

---

## Level 2: Security + Routing Integration

### Prerequisites

- Level 1 complete
- Anthropic API key (optional, for AI-powered estimation)

### Step 1: Configure API Key

Create `.env` file (if not already created):

```bash
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
```

Ensure `.env` is in `.gitignore`:

```bash
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
```

### Step 2: Test Routing

```bash
# Test complexity estimation
br routing estimate "Add user authentication"

# Should show:
# Complexity: moderate
# Recommended model: sonnet
# Estimated cost: $0.XX
```

⚠️ **Note:** Uses heuristic-based estimation. AI-powered estimation optional (requires API key, not yet integrated).

### Step 3: Create Project Config

Create `.buildrunner/config.json`:

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
  }
}
```

### Step 4: Track Costs

```bash
# View current costs
br routing costs

# View weekly summary
br routing costs --period week
```

⚠️ **Note:** Cost tracking interface defined, persistence layer in development (SQLite).

**✅ Level 2 Complete!** Your project now has intelligent model routing and cost tracking.

---

## Level 3: Full Integration

### Prerequisites

- Level 2 complete
- Multiple team members (for parallel orchestration)

### Step 1: Configure Telemetry

Update `.buildrunner/config.json`:

```json
{
  "routing": {
    "default_model": "sonnet",
    "cost_optimization": true
  },
  "telemetry": {
    "enabled": true,
    "storage_dir": ".buildrunner/telemetry",
    "export_dir": ".buildrunner/exports",
    "thresholds": {
      "success_rate_warning": 80,
      "latency_warning_ms": 2000,
      "cost_daily_critical": 10.0,
      "error_rate_warning": 10
    }
  }
}
```

### Step 2: Test Telemetry

```bash
# View metrics
br telemetry summary

# Check for alerts
br telemetry alerts

# Export data
br telemetry export metrics.csv
```

⚠️ **Note:** Event schemas defined, collection needs orchestrator integration.

### Step 3: Configure Parallel Orchestration

Update `.buildrunner/config.json`:

```json
{
  "routing": { ... },
  "telemetry": { ... },
  "parallel": {
    "enabled": true,
    "default_workers": 3,
    "session_storage": ".buildrunner/sessions",
    "heartbeat_timeout": 30,
    "task_timeout": 3600
  }
}
```

### Step 4: Test Parallel Execution

```bash
# Start a test session
br parallel start "Test Build" --tasks 10 --workers 2

# View status
br parallel status

# Check workers
br parallel workers

# Stop session
br parallel stop <session-id>
```

⚠️ **Note:** Unit tested (28 tests), end-to-end execution not yet tested in production.

**✅ Level 3 Complete!** Your project now has full BuildRunner integration.

---

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/buildrunner.yml`:

```yaml
name: BuildRunner Security & Quality

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install BuildRunner
        run: |
          pip install -e /path/to/buildrunner3

      - name: Security scan
        run: |
          br security scan
          br security check

      - name: Quality check
        run: |
          br quality check

  costs:
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install BuildRunner
        run: |
          pip install -e /path/to/buildrunner3

      - name: Cost tracking
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          br routing costs --period week
          br telemetry export costs-${{ github.run_id }}.csv

      - name: Upload cost report
        uses: actions/upload-artifact@v3
        with:
          name: cost-report
          path: costs-*.csv
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - security
  - quality
  - report

security_scan:
  stage: security
  image: python:3.10
  before_script:
    - pip install -e /path/to/buildrunner3
  script:
    - br security scan
    - br security check
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'

quality_check:
  stage: quality
  image: python:3.10
  before_script:
    - pip install -e /path/to/buildrunner3
  script:
    - br quality check
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

cost_tracking:
  stage: report
  image: python:3.10
  before_script:
    - pip install -e /path/to/buildrunner3
  script:
    - br routing costs --period week
    - br telemetry export costs-$CI_JOB_ID.csv
  artifacts:
    paths:
      - costs-*.csv
    expire_in: 30 days
  only:
    - main
```

---

## Programmatic Integration

### Python API

```python
from core.security.scanner import SecretScanner
from core.routing.complexity_estimator import ComplexityEstimator
from core.telemetry.event_collector import EventCollector

# Security scanning
scanner = SecretScanner()
secrets = scanner.scan_file("config.py")
if secrets:
    print(f"⚠️ Found {len(secrets)} secrets!")
    for secret in secrets:
        print(f"  Line {secret.line_number}: {secret.secret_type}")

# Complexity estimation
estimator = ComplexityEstimator()
result = estimator.estimate("Add user authentication with JWT")
print(f"Complexity: {result.complexity_level}")
print(f"Recommended model: {result.recommended_model}")
print(f"Estimated cost: ${result.estimated_cost:.2f}")

# Telemetry
collector = EventCollector()
collector.collect_event({
    "type": "task_started",
    "task_id": "task-001",
    "description": "Add user authentication"
})

# Later...
collector.collect_event({
    "type": "task_completed",
    "task_id": "task-001",
    "duration_ms": 1500,
    "cost": 0.15
})
```

### JavaScript/TypeScript API

⚠️ **Note:** JavaScript API not yet implemented. Use CLI via child_process:

```javascript
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

async function scanForSecrets(file) {
  try {
    const { stdout } = await execPromise(`br security check --file ${file}`);
    return stdout;
  } catch (error) {
    console.error('Security scan failed:', error);
    throw error;
  }
}

async function estimateComplexity(task) {
  try {
    const { stdout } = await execPromise(`br routing estimate "${task}"`);
    return JSON.parse(stdout);
  } catch (error) {
    console.error('Estimation failed:', error);
    throw error;
  }
}

// Usage
scanForSecrets('src/config.js')
  .then(result => console.log('Scan result:', result));

estimateComplexity('Add user authentication')
  .then(result => console.log('Complexity:', result.complexity_level));
```

---

## Integration Patterns

### Pattern 1: Pre-Commit Security Gate

**Goal:** Block commits with secrets or SQL injection vulnerabilities.

**Implementation:**

1. Install hooks: `br security hooks install`
2. Configure whitelist for false positives:
   ```
   # .buildrunner/security/whitelist.txt
   tests/test_data.py
   docs/examples/
   ```
3. Team onboarding:
   ```bash
   # Add to README.md
   ## Setup
   1. Clone repo
   2. Install BuildRunner: `pip install -e /path/to/buildrunner3`
   3. Install hooks: `br security hooks install`
   ```

### Pattern 2: Cost-Aware Development

**Goal:** Track and optimize AI model costs across team.

**Implementation:**

1. Set cost limits in `.buildrunner/config.json`:
   ```json
   {
     "routing": {
       "cost_limits": {
         "daily": 10.00,
         "weekly": 50.00
       }
     }
   }
   ```

2. Weekly cost review:
   ```bash
   # Export weekly costs
   br routing costs --period week
   br telemetry export weekly-costs.csv

   # Review in spreadsheet
   ```

3. Team guidelines:
   - Use Haiku for simple tasks
   - Use Sonnet for moderate complexity
   - Reserve Opus for critical/complex work

⚠️ **Note:** Cost tracking interface defined, persistence layer in development.

### Pattern 3: Parallel Build Workflow

**Goal:** Run multiple build sessions concurrently without conflicts.

**Implementation:**

1. Define file ownership:
   ```json
   // .buildrunner/parallel_config.json
   {
     "worker_1": {
       "files": ["src/auth/**", "tests/test_auth.py"]
     },
     "worker_2": {
       "files": ["src/api/**", "tests/test_api.py"]
     },
     "worker_3": {
       "files": ["src/db/**", "tests/test_db.py"]
     }
   }
   ```

2. Start parallel session:
   ```bash
   br parallel start "Sprint 42" --tasks 30 --workers 3 --watch
   ```

3. Monitor progress:
   ```bash
   # In separate terminal
   br parallel dashboard
   ```

⚠️ **Note:** Unit tested, end-to-end execution not yet tested in production.

### Pattern 4: Continuous Monitoring

**Goal:** Track build performance and costs over time.

**Implementation:**

1. Enable telemetry in `.buildrunner/config.json`
2. Export daily metrics:
   ```bash
   # Cron job or CI/CD
   br telemetry export daily-metrics-$(date +%Y%m%d).csv
   ```

3. Analyze trends:
   - Success rate over time
   - Average latency
   - Daily costs
   - Error patterns

4. Set up alerts:
   ```bash
   # Check alerts in CI/CD
   br telemetry alerts --level critical
   if [ $? -ne 0 ]; then
     echo "⚠️ Critical alerts detected!"
     exit 1
   fi
   ```

⚠️ **Note:** Event schemas defined, collection needs orchestrator integration.

---

## Configuration Reference

### Complete config.json Example

```json
{
  "routing": {
    "default_model": "sonnet",
    "cost_optimization": true,
    "cost_limits": {
      "daily": 10.00,
      "weekly": 50.00,
      "monthly": 200.00
    },
    "fallback_strategy": "exponential_backoff",
    "retry_attempts": 3
  },
  "security": {
    "enforce_hooks": true,
    "whitelist_file": ".buildrunner/security/whitelist.txt",
    "sql_injection_check": true,
    "secret_patterns": [
      "anthropic_key",
      "openai_key",
      "jwt_token",
      "aws_key",
      "github_token"
    ]
  },
  "telemetry": {
    "enabled": true,
    "storage_dir": ".buildrunner/telemetry",
    "export_dir": ".buildrunner/exports",
    "thresholds": {
      "success_rate_warning": 80,
      "latency_warning_ms": 2000,
      "cost_daily_critical": 10.0,
      "error_rate_warning": 10
    },
    "retention_days": 30
  },
  "parallel": {
    "enabled": true,
    "default_workers": 3,
    "session_storage": ".buildrunner/sessions",
    "heartbeat_timeout": 30,
    "task_timeout": 3600,
    "file_locking": true
  },
  "quality": {
    "thresholds": {
      "overall": 80,
      "security": 90,
      "testing": 80,
      "documentation": 70,
      "structure": 75
    }
  }
}
```

---

## Best Practices

### Security

1. **Install hooks immediately** after cloning
2. **Never bypass hooks** unless absolutely necessary
3. **Whitelist test data** to avoid false positives
4. **Rotate secrets** if accidentally committed
5. **Review security scans** in code review

### Cost Management

1. **Set realistic limits** based on team size
2. **Review costs weekly** in team meetings
3. **Use Haiku by default** for simple tasks
4. **Export cost data** for finance reporting
5. **Optimize prompts** to reduce token usage

### Monitoring

1. **Enable telemetry** from day one
2. **Check alerts daily** in standup
3. **Export metrics weekly** for trend analysis
4. **Set appropriate thresholds** for your workload
5. **Correlate costs with outcomes** to measure ROI

### Parallel Execution

1. **Declare file ownership** explicitly
2. **Monitor worker health** during long builds
3. **Use live dashboard** for visibility
4. **Clean up old sessions** regularly
5. **Start small** (2-3 workers) and scale up

---

## Troubleshooting

### Integration fails with "br command not found"

```bash
# Check installation
which br

# If not found, reinstall
pip install -e /path/to/buildrunner3

# Or add to PATH
export PATH=$PATH:/path/to/buildrunner3/cli
```

### Pre-commit hook blocks valid code

```bash
# Add to whitelist
echo "path/to/file.py:line_number" >> .buildrunner/security/whitelist.txt

# Or bypass once (not recommended)
git commit --no-verify -m "Message"
```

### Cost tracking not working

⚠️ **Note:** Cost tracking interface defined, persistence layer in development (SQLite).

```bash
# Check API key
echo $ANTHROPIC_API_KEY

# If empty, add to .env
echo "ANTHROPIC_API_KEY=sk-ant-your-key" >> .env

# Verify config
cat .buildrunner/config.json
```

### Telemetry not collecting events

⚠️ **Note:** Event collection needs orchestrator integration.

```bash
# Check telemetry enabled
grep "enabled" .buildrunner/config.json

# Check storage directory exists
ls -la .buildrunner/telemetry/

# Create if missing
mkdir -p .buildrunner/telemetry
```

### Parallel session conflicts

```bash
# Check file locks
br parallel status

# List active sessions
br parallel list --status running

# Stop conflicting session
br parallel stop <session-id>
```

---

## Migration from v3.0

### Breaking Changes

- Config file moved from `config.json` to `.buildrunner/config.json`
- Telemetry storage changed from JSON to structured format
- Parallel session IDs now use UUID format

### Migration Steps

1. **Backup old config:**
   ```bash
   cp config.json config.json.backup
   ```

2. **Create new config location:**
   ```bash
   mkdir -p .buildrunner
   mv config.json .buildrunner/config.json
   ```

3. **Update config format:**
   ```bash
   # Add new telemetry section to .buildrunner/config.json
   ```

4. **Reinstall hooks:**
   ```bash
   br security hooks uninstall
   br security hooks install
   ```

5. **Test integration:**
   ```bash
   br security check
   br routing estimate "test task"
   br telemetry summary
   ```

---

## Support

**Documentation:**
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [API_REFERENCE.md](API_REFERENCE.md) - Complete API reference
- [SECURITY.md](../SECURITY.md) - Security features
- [ROUTING.md](../ROUTING.md) - Model routing
- [TELEMETRY.md](../TELEMETRY.md) - Monitoring
- [PARALLEL.md](../PARALLEL.md) - Parallel orchestration

**Get Help:**
- GitHub Issues: https://github.com/your-org/buildrunner3/issues
- Email: support@your-org.com

**Report Security Issues:**
- Email: security@your-org.com

---

*BuildRunner v3.1.0-alpha - Seamless integration for modern development workflows*
