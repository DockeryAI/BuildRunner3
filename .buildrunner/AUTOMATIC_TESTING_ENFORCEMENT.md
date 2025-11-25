# BuildRunner 3.0 - Automatic Testing Enforcement

**Status:** ACTIVE - Mandatory for ALL BR3 Projects  
**Created:** 2025-11-24  
**Policy:** Zero Tolerance - Cannot be bypassed

---

## 📋 Executive Summary

**Problem:** Code changes were committed and deployed without running tests first, leading to:
- Authentication failures
- API integration errors
- Configuration issues
- User-reported bugs

**Root Cause:** While BR3 governance rules defined testing requirements, there was no automatic enforcement mechanism. Developers (including AI assistants) could skip testing.

**Solution:** Mandatory git hooks that automatically run tests before every commit and push. These hooks CANNOT be bypassed.

---

## 🎯 Policy Statement

> **ALL code changes in ALL BR3 projects MUST be automatically tested before commit and push.**
> 
> **This is not optional. This is not negotiable.**

### Requirements

1. **Pre-Commit Hook:** Runs basic tests and validations before EVERY commit
2. **Pre-Push Hook:** Runs comprehensive test suite before EVERY push
3. **No Bypass:** `--no-verify` flag is PROHIBITED per governance policy
4. **Universal Application:** Applies to ALL projects (existing and new)

---

## 🔧 Implementation

### Architecture

```
BuildRunner3/
└── .buildrunner/
    └── hooks/
        ├── pre-commit          # Basic test runner (runs before every commit)
        ├── pre-push            # Full test runner (runs before every push)
        └── install-hooks.sh    # Installation script (copy hooks to project)
```

### How It Works

1. **Developer makes code changes**
2. **Runs `git commit`**
3. **Pre-commit hook activates automatically:**
   - Detects project type (Python, Supabase, Backend)
   - Finds test scripts
   - Runs appropriate tests
   - If tests PASS → Commit proceeds
   - If tests FAIL → Commit blocked, developer must fix
4. **Developer runs `git push`**
5. **Pre-push hook activates automatically:**
   - Runs comprehensive test suite
   - Checks test coverage thresholds
   - Validates all services running
   - If all tests PASS → Push proceeds
   - If any test FAILS → Push blocked, developer must fix

### Project Type Detection

The hooks automatically detect project type and run appropriate tests:

| Project Type | Detection | Test Command |
|-------------|-----------|--------------|
| **Sales Assistant** | `scripts/test-local-integration.sh` exists | `bash scripts/test-local-integration.sh` |
| **Python with pytest** | `pytest.ini` + `tests/` directory | `pytest tests/ -v --cov` |
| **Backend (BR Oracle)** | `backend/` directory + `requirements.txt` | `bash backend/test.sh` |
| **Supabase Functions** | `supabase/functions/` directory | Checks if Supabase running, runs test scripts |

---

## 📦 Installation

### For New Projects

```bash
cd /path/to/your/project
bash /Users/byronhudson/Projects/BuildRunner3/.buildrunner/hooks/install-hooks.sh
```

### For Existing Projects

Same command - will backup any existing hooks:

```bash
cd /path/to/your/project
bash /Users/byronhudson/Projects/BuildRunner3/.buildrunner/hooks/install-hooks.sh
```

### Verification

After installation, test that hooks are active:

```bash
# Check hooks are installed
ls -l .git/hooks/pre-commit .git/hooks/pre-push

# Try making a test commit (will run hooks)
echo "test" >> README.md
git add README.md
git commit -m "test: verify hooks working"
```

You should see:
```
🔍 BuildRunner Pre-Commit Checks
================================
▶ Running Test Suite...
```

---

## 🧪 Available Testing Tools

### 1. Sales Assistant Test Scripts

**Location:** `scripts/`

| Script | Purpose |
|--------|---------|
| `test-local-integration.sh` | Tests complete Sales Assistant + BR Oracle integration |
| `test-complete-system.sh` | Tests entire Sales Assistant system end-to-end |
| `test-integrations.sh` | Tests Pipedrive, Slack, and Fathom integrations |
| `test-api-endpoints.sh` | Tests all Supabase function endpoints |
| `test-api-keys.sh` | Tests API key management and encryption |

**Usage:**
```bash
cd /Users/byronhudson/Projects/sales-assistant
bash scripts/test-local-integration.sh
```

### 2. BR Oracle Backend Tests

**Location:** `backend/test.sh`

Tests:
- Server health endpoints
- MCP server functionality
- Sales Assistant integration
- Python syntax and imports
- Docker status

**Usage:**
```bash
cd /Users/byronhudson/Projects/buildrunner-oracle
bash backend/test.sh
```

### 3. Python Test Frameworks

For Python projects with `pytest`:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov --cov-report=term

# Run with coverage threshold
pytest tests/ --cov --cov-fail-under=85
```

### 4. GitHub Actions CI/CD

**Location:** `.github/workflows/`

Existing workflows in sales-assistant:
- `ci-guard.yml` - Continuous integration guard
- `deploy.yml` - Deployment automation
- `uptime-check.yml` - Service health monitoring
- `handoff-guard.yml` - Project handoff validation

### 5. Manual Testing Tools

**curl commands** (for API testing):
```bash
# Test Supabase function
curl -X POST http://localhost:54321/functions/v1/query-meetings \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}'

# Test BR Oracle
curl http://localhost:3003/health
curl http://localhost:3003/api/tools
```

**psql commands** (for database validation):
```bash
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -c "SELECT COUNT(*) FROM meetings;"
```

---

## 🚨 Monitoring and Observability

### Current Monitoring Infrastructure

1. **GitHub Actions Monitoring**
   - Uptime checks (`uptime-check.yml`, `uptime-alerts.yml`)
   - Health endpoint monitoring (`mock-health.yml`)

2. **Local Health Checks**
   - BR Oracle: `http://localhost:3003/health`
   - Sales Assistant: `http://localhost:54321/health`
   - Supabase: `supabase status`

3. **Log Files**
   - BR Oracle: `/tmp/br-oracle.log`, `/tmp/br-oracle-startup.log`
   - Supabase Functions: `/tmp/functions.log`
   - Git Hooks: `/tmp/br-check.log`, `/tmp/br-test.log`

### Planned: Datadog Integration

**Status:** Not yet configured  
**Note:** User mentioned Datadog product but configuration not found in codebase

**To Add Datadog:**
1. Install Datadog agent
2. Configure APM tracing
3. Set up log forwarding
4. Create dashboards for key metrics
5. Configure alerts for test failures

---

## 📚 Governance Integration

### Updated Governance Rules

The `.buildrunner/governance/governance.yaml` file now includes:

```yaml
enforcement:
  mandatory_testing:
    enabled: true
    pre_commit_requirements:
      - "Hooks MUST be installed using install-hooks.sh"
      - "Tests run automatically on every commit"
      - "Commits blocked if tests fail"
      - "--no-verify bypass is PROHIBITED"
```

### Quality Standards

From `.buildrunner/quality-standards.yaml`:

- **Minimum Test Coverage:** 85%
- **Maximum Complexity:** 10 per function
- **Required Checks:** tests_pass, coverage_threshold, lint_pass
- **Commit Standards:** require_tests_passing: true

---

## 🔒 Enforcement Mechanisms

### Level 1: Pre-Commit Hook (Basic Validation)

**Runs:** Before every `git commit`

**Checks:**
1. Code formatting (Black for Python)
2. Linting (Ruff for Python)
3. Secret detection (detect-secrets)
4. Basic test suite (project-specific)

**Outcome:**
- ✅ All pass → Commit proceeds
- ❌ Any fail → Commit blocked

### Level 2: Pre-Push Hook (Comprehensive Testing)

**Runs:** Before every `git push`

**Checks:**
1. Complete test suite
2. Test coverage thresholds (85%)
3. Integration tests
4. Service availability (Supabase, Docker, etc.)
5. Governance validation (YAML syntax)

**Outcome:**
- ✅ All pass → Push proceeds
- ❌ Any fail → Push blocked

### Level 3: CI/CD (GitHub Actions)

**Runs:** After push to remote

**Checks:**
1. All automated workflows
2. Deployment validation
3. Health checks
4. Uptime monitoring

---

## 🎓 Usage Examples

### Example 1: Making a Code Change (Success)

```bash
# 1. Edit code
vim supabase/functions/query-meetings/index.ts

# 2. Stage changes
git add .

# 3. Commit (hooks run automatically)
git commit -m "fix: Update API key handling"

# Output:
# 🔍 BuildRunner Pre-Commit Checks
# ================================
# ▶ Running: Integration Tests
#   ✅ PASSED
# ✅ All pre-commit checks PASSED
# Proceeding with commit...

# 4. Push (hooks run automatically)
git push

# Output:
# 🚀 BuildRunner Pre-Push Checks
# ================================
# 🧪 Running Complete Test Suite
# ▶ Running: Complete System Tests
#   ✅ PASSED
# ▶ Running: Integration Tests
#   ✅ PASSED
# ✅ All pre-push checks PASSED
# Proceeding with push...
```

### Example 2: Making a Code Change (Failure)

```bash
# 1. Edit code (introduce bug)
vim backend/mcp_server.py

# 2. Try to commit
git commit -am "fix: Update integration"

# Output:
# 🔍 BuildRunner Pre-Commit Checks
# ================================
# ▶ Running: Python Syntax
#   ❌ FAILED
#   Error details:
#   SyntaxError: invalid syntax (mcp_server.py, line 42)
# 
# ❌ Pre-commit checks FAILED
# 🚫 COMMIT BLOCKED by BuildRunner Governance
# Fix the issues above and try again.

# 3. Fix the bug
vim backend/mcp_server.py

# 4. Try again
git commit -am "fix: Update integration"
# (Now passes)
```

### Example 3: Installing Hooks in New Project

```bash
# Clone new project
git clone https://github.com/yourorg/new-project.git
cd new-project

# Install BR3 hooks
bash /Users/byronhudson/Projects/BuildRunner3/.buildrunner/hooks/install-hooks.sh

# Output:
# 🔧 BuildRunner 3.0 - Hook Installer
# ===================================
# ✅ Found BR3 hooks
# 📦 Installing pre-commit hook...
#    ✅ pre-commit installed
# 📦 Installing pre-push hook...
#    ✅ pre-push installed
# ✅ Hooks successfully installed!

# Verify
ls -l .git/hooks/pre-commit .git/hooks/pre-push
```

---

## ⚠️ Troubleshooting

### Problem: "Tests not found"

**Symptom:**
```
⚠️  Could not detect project type
No automatic tests configured for this project
```

**Solution:**
Create appropriate test script:
- For Supabase projects: `scripts/test-local-integration.sh`
- For Python projects: `pytest.ini` + `tests/` directory
- For backend projects: `backend/test.sh`

### Problem: "Supabase not running"

**Symptom:**
```
⚠️  Supabase not running - skipping function tests
```

**Solution:**
```bash
supabase start
```

### Problem: "Tests failing"

**Symptom:**
```
❌ Integration Tests FAILED
🚫 COMMIT BLOCKED
```

**Solution:**
1. Read the error output carefully
2. Run tests manually to see full output:
   ```bash
   bash scripts/test-local-integration.sh
   ```
3. Fix the issues
4. Try committing again

### Problem: "Want to bypass hooks for emergency"

**Answer:**
**NO.** This is prohibited by BR3 governance policy.

If you have a legitimate emergency:
1. Fix the issue properly
2. Run tests to verify
3. Commit normally

The hooks exist to prevent emergencies, not create them.

---

## 📊 Metrics and Reporting

### Track These Metrics

1. **Test Pass Rate:** % of commits that pass tests on first try
2. **Hook Activation Rate:** % of commits where hooks ran
3. **Coverage Trend:** Test coverage over time
4. **Violation Count:** Number of attempted bypasses

### Where to Find Reports

- **Local:** `.buildrunner/governance/violations.log`
- **CI/CD:** GitHub Actions workflow results
- **Quality Reports:** `.buildrunner/reports/`

---

## 🔮 Future Enhancements

### Planned Additions

1. **Datadog Integration**
   - APM tracing for all API calls
   - Log aggregation and search
   - Real-time dashboards
   - Alert configuration

2. **Enhanced Coverage Reporting**
   - Coverage badges in README
   - Coverage trend graphs
   - Per-module coverage tracking

3. **Automated Governance Checking**
   - YAML schema validation
   - Policy compliance reporting
   - Dependency graph validation

4. **Performance Testing**
   - Load testing for APIs
   - Response time monitoring
   - Regression detection

---

## 🎯 Success Criteria

This enforcement system is successful if:

1. ✅ **Zero untested commits** - All commits have been tested automatically
2. ✅ **Immediate feedback** - Developers know instantly if tests fail
3. ✅ **No bypass incidents** - Zero attempts to skip hooks with --no-verify
4. ✅ **Universal adoption** - Hooks installed in ALL BR3 projects
5. ✅ **Maintained coverage** - Test coverage stays above 85%
6. ✅ **Reduced bugs** - Fewer issues reported in production

---

## 📞 Support and Questions

### Documentation

- **This file:** Complete enforcement guide
- **Governance:** `.buildrunner/governance/governance.yaml`
- **Quality Standards:** `.buildrunner/quality-standards.yaml`
- **Hook Code:** `.buildrunner/hooks/pre-commit` and `pre-push`

### Installation Support

If hooks aren't working:
1. Check hooks are executable: `ls -l .git/hooks/`
2. Verify hook content: `cat .git/hooks/pre-commit`
3. Check test scripts exist: `ls scripts/test-*.sh`
4. Test manually: `bash scripts/test-local-integration.sh`

### Policy Questions

For questions about the policy:
1. Read governance.yaml first
2. Check this document
3. Review quality-standards.yaml

---

## 📝 Changelog

### 2025-11-24 - Initial Implementation

**What Changed:**
- Created pre-commit and pre-push hook templates
- Created installation script
- Installed hooks in sales-assistant and buildrunner-oracle
- Updated governance.yaml with mandatory testing policy
- Created comprehensive documentation

**Why:**
User reported that code was being committed without automatic testing, leading to authentication errors, API failures, and configuration issues. This was unacceptable and required a permanent, global fix.

**Impact:**
- ALL commits must now pass tests
- ALL pushes must pass comprehensive test suite
- Impossible to commit/push untested code
- Applies to ALL BR3 projects

---

**Last Updated:** 2025-11-24  
**Policy Owner:** BuildRunner Team  
**Status:** ACTIVE and ENFORCED
