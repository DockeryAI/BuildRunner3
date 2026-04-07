# BuildRunner 3.1 - Quick Start Guide

**Version:** v3.1.0-alpha
**Last Updated:** 2025-11-18
**Status:** ⚠️ Beta - Core functionality tested, orchestrator integration in progress

---

## What is BuildRunner?

BuildRunner 3.1 is a task orchestration engine for software development projects. It helps you:

- **Generate tasks** from project specifications
- **Orchestrate execution** with AI-powered complexity estimation
- **Track costs and performance** with built-in telemetry
- **Ensure security** with automated secret detection and SQL injection checks
- **Run builds in parallel** with multi-session coordination

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git (optional, for pre-commit hooks)

### Install BuildRunner

```bash
# Clone the repository
git clone https://github.com/your-org/buildrunner3.git
cd buildrunner3

# Install with pip
pip install -e .

# Verify installation
br --version
```

Expected output: `BuildRunner v3.1.0-alpha`

---

## First Steps

### 1. Check Your Installation

```bash
br --help
```

This shows all available commands organized by category:
- **security** - Secret detection and security scanning
- **routing** - Model selection and cost tracking
- **telemetry** - Metrics and monitoring
- **parallel** - Multi-session orchestration
- **quality** - Code quality gates
- **gaps** - Gap analysis

### 2. Install Security Hooks (Recommended)

Protect your code from accidentally committing secrets:

```bash
br security hooks install
```

This installs a git pre-commit hook that automatically scans for:
- API keys (13 types: Anthropic, OpenAI, AWS, GitHub, etc.)
- SQL injection vulnerabilities
- Other security issues

⚠️ **Note:** Hook code exists but needs production validation.

### 3. Scan Your Project

Check your existing codebase for security issues:

```bash
# Scan entire project
br security scan

# Scan specific directory
br security scan --directory src/

# Check only staged files (faster)
br security check --staged
```

---

## Common Tasks

### Security: Prevent Secret Leaks

**Check for secrets before committing:**

```bash
# Check all staged files
br security check --staged

# Check specific file
br security check --file config.py
```

**What gets detected:**
- Anthropic API keys (`sk-ant-*`)
- OpenAI API keys (`sk-proj-*`, `sk-*`)
- JWT tokens (`eyJ*`)
- AWS access keys (`AKIA*`)
- GitHub tokens (`gh*_*`)
- Database credentials
- And 7+ more patterns

**If secrets are detected:**
1. DO NOT commit the file
2. Remove the secret from the file
3. Move secrets to `.env` file
4. Add `.env` to `.gitignore`
5. Use environment variables in code

**Example - Safe secret storage:**

```python
# ❌ WRONG - Hardcoded secret
api_key = "sk-ant-abc123def456"

# ✅ CORRECT - Environment variable
import os
api_key = os.getenv("ANTHROPIC_API_KEY")
```

### Routing: Optimize Model Selection

**Estimate task complexity:**

```bash
# Estimate complexity of a task
br routing estimate "Add user authentication with JWT tokens"
```

Output shows:
- Complexity level (simple/moderate/complex/critical)
- Recommended model (Haiku/Sonnet/Opus)
- Estimated cost
- Estimated time

**Select optimal model:**

```bash
# Let BuildRunner choose
br routing select "Fix production bug in payment processor"

# With cost limit
br routing select "Refactor helper functions" --cost-limit 0.05
```

⚠️ **Note:** Uses heuristic-based estimation. AI-powered estimation optional (requires API key).

**View cost summary:**

```bash
# Current session
br routing costs

# Weekly costs
br routing costs --period week

# Monthly costs
br routing costs --period month
```

⚠️ **Note:** Cost tracking interface defined, persistence layer in development (SQLite).

### Telemetry: Monitor Performance

**View metrics summary:**

```bash
br telemetry summary
```

Shows:
- Success rate
- Average latency
- Total cost
- Error count
- Event count

**List recent events:**

```bash
# All events
br telemetry events

# Filter by type
br telemetry events --type task_failed

# Last 24 hours
br telemetry events --hours 24
```

**Check for alerts:**

```bash
br telemetry alerts
```

Built-in thresholds:
- Success rate < 80% (warning)
- Average latency > 2000ms (warning)
- Cost > $10/day (critical)
- Error rate > 10% (warning)

**Export data for analysis:**

```bash
br telemetry export metrics.csv
```

⚠️ **Note:** Event schemas defined, collection needs orchestrator integration.

### Parallel: Run Builds Concurrently

**Start parallel session:**

```bash
# Start session with 3 workers
br parallel start "Build v3.1" --tasks 50 --workers 3

# With live dashboard
br parallel start "Build v3.1" --tasks 50 --workers 3 --watch
```

**Monitor progress:**

```bash
# Check status
br parallel status

# Live dashboard
br parallel dashboard

# List all sessions
br parallel list

# Worker health
br parallel workers
```

**Manage sessions:**

```bash
# Pause session
br parallel pause session-id

# Resume session
br parallel resume session-id

# Stop session
br parallel stop session-id

# Cleanup old sessions
br parallel cleanup
```

⚠️ **Note:** Unit tested (28 tests), end-to-end execution not yet tested in production.

---

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# API Keys (optional, for AI-powered features)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Cost Limits (optional)
BR_COST_LIMIT_DAILY=10.00
BR_COST_LIMIT_WEEKLY=50.00

# Telemetry (optional)
BR_TELEMETRY_ENABLED=true
BR_TELEMETRY_EXPORT_DIR=/path/to/exports
```

**IMPORTANT:** Add `.env` to `.gitignore` to prevent committing secrets!

### Project Configuration

Create `.buildrunner/config.json`:

```json
{
  "quality_thresholds": {
    "overall": 80,
    "security": 90,
    "testing": 80,
    "documentation": 70
  },
  "routing": {
    "default_model": "sonnet",
    "cost_optimization": true
  },
  "security": {
    "enforce_hooks": true,
    "whitelist_file": ".buildrunner/security/whitelist.txt"
  }
}
```

---

## Troubleshooting

### "br command not found"

```bash
# Reinstall BuildRunner
pip install -e .

# Or use Python directly
python3 -m cli.main --help
```

### Pre-commit hook not running

```bash
# Check installation
br security hooks status

# Reinstall
br security hooks install --force

# Verify permissions
ls -la .git/hooks/pre-commit
# Should show: -rwxr-xr-x (executable)
```

### False positive in secret detection

Add to `.buildrunner/security/whitelist.txt`:

```
# Format: file:line:pattern
tests/test_examples.py:42:test_api_key
docs/examples/
```

### Slow performance

```bash
# Check only staged files
br security check --staged

# Skip specific checks
br security check --no-sql

# Increase workers for parallel builds
br parallel start "Build" --workers 5
```

---

## Next Steps

### Learn More

- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Integrate BuildRunner into your project
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API reference
- **[SECURITY.md](../SECURITY.md)** - Security features in depth
- **[ROUTING.md](../ROUTING.md)** - Model routing and cost optimization
- **[TELEMETRY.md](../TELEMETRY.md)** - Monitoring and metrics
- **[PARALLEL.md](../PARALLEL.md)** - Parallel orchestration

### Advanced Topics

- **Task Generation:** Auto-generate tasks from PROJECT_SPEC.md
- **Orchestration:** AI-powered batch execution
- **Quality Gates:** Enforce code quality standards
- **Gap Analysis:** Identify missing features
- **Custom Plugins:** Extend BuildRunner functionality

### Get Help

```bash
# Command help
br security --help
br routing --help
br telemetry --help

# Specific command help
br security check --help
br routing estimate --help
```

---

## Common Workflows

### Workflow 1: Secure Development

```bash
# 1. Install hooks
br security hooks install

# 2. Before committing
br security check --staged

# 3. If secrets detected
# - Remove secrets from code
# - Move to .env file
# - Add .env to .gitignore

# 4. Commit safely
git commit -m "Your message"
```

### Workflow 2: Cost-Optimized Development

```bash
# 1. Estimate complexity
br routing estimate "Your task description"

# 2. Select model with cost limit
br routing select "Your task" --cost-limit 0.10

# 3. Track spending
br routing costs --period week

# 4. Export for reporting
br telemetry export weekly-costs.csv
```

### Workflow 3: Parallel Build Execution

```bash
# 1. Start parallel session
br parallel start "Sprint 42" --tasks 20 --workers 3 --watch

# 2. Monitor in another terminal
br parallel dashboard

# 3. Check worker health
br parallel workers

# 4. Review results
br telemetry summary
```

---

## Status & Limitations

### ✅ What's Working

- Secret detection patterns (13 types)
- SQL injection detection (Python + JavaScript)
- Pre-commit hook code
- CLI commands (25 total)
- Heuristic-based complexity estimation
- Event schemas and metrics logic
- Unit tests (101 tests passing)

### ⚠️ What's In Progress

- **Security hooks:** Code exists but needs production validation
- **AI-powered estimation:** Optional, requires API key, not yet integrated
- **Cost tracking persistence:** SQLite layer in development
- **Telemetry collection:** Needs orchestrator integration
- **Parallel execution:** End-to-end testing needed

### 🚧 Known Issues

- File locking performance: O(n) conflict detection (typically <10 sessions, negligible impact)
- Worker offline detection: 30s delay before marked offline
- Telemetry storage growth: Events file grows unbounded (manual cleanup needed)

---

## Support

**Get Help:**
- GitHub Issues: https://github.com/your-org/buildrunner3/issues
- Documentation: https://github.com/your-org/buildrunner3/tree/main/docs

**Report Security Issues:**
- Email: security@your-org.com

---

*BuildRunner v3.1.0-alpha - Making development faster, safer, and smarter*
