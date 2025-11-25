# BuildRunner 3.0 - Project Setup

This project has been configured with **ALL 21 BuildRunner 3.0 systems**.

## ✅ Active Systems

### Tier 1: Automatic Enforcement (Always Active)
1. **Git Hooks** - Pre-commit and pre-push validation
2. **Deployment Enforcement** - Pre-deployment validation (see below)
3. **Auto-Debug Pipeline** - Automatic testing on every commit
4. **Security Scanning** - Secret detection + SQL injection checks
5. **Code Quality Gates** - Multi-dimensional quality scoring
6. **Architecture Guard** - Spec drift detection
7. **Gap Analysis** - Completeness validation before push
8. **Governance Enforcement** - Policy validation

### Tier 2: Background Services (Auto-Active)
8. **Telemetry (Datadog)** - Metrics and tracing (if DD_API_KEY set)
9. **Persistence Layer** - SQLite metrics database
10. **Error Tracking** - Cross-session error persistence
11. **PRD System** - PROJECT_SPEC.md management
12. **Debug Logging** - ./clog wrapper and session logging

### Tier 3: Available On-Demand
13. **Model Routing** - AI model selection and cost optimization
14. **Parallel Orchestration** - Multi-session coordination
15. **Agent System** - Claude agent orchestration
16. **Design System** - Industry profiles and Tailwind generation
17. **Self-Service** - Auto-detect required services
18. **Build Orchestrator** - Advanced task coordination
19. **AI Context Management** - Context optimization
20. **Feature Discovery** - Auto-discover existing features
21. **Adaptive Planning** - Result-based planning

## 🚀 Quick Start

### Every Commit
When you run `git commit`, these systems run automatically:
- Secret detection
- SQL injection check
- Auto-debug (quick checks)
- Code quality (changed files)
- Architecture validation
- Governance rules

### Every Push
When you run `git push`, these run automatically:
- Full test suite (deep checks)
- Gap analysis (completeness)
- Full security scan
- Complete quality analysis

### Every Deployment
**IMPORTANT:** To enforce checks before deployment, use these commands:

```bash
# Supabase functions
source .buildrunner/scripts/br3-aliases.sh
supabase-deploy <function-name>

# Or wrap any deploy command
br-deploy <your-deploy-command>
```

This ensures NO CODE gets deployed without passing:
- Security scanning
- Auto-debug tests
- Quality checks

**Without the wrapper**, you can still deploy directly but you bypass all enforcement.

### Manual Commands
```bash
# Check all systems status
br doctor

# Run specific checks
br security check
br quality check
br gaps analyze
br autodebug run

# Telemetry
br telemetry summary
br telemetry events

# Model routing
br routing estimate "implement user auth"
br routing costs

# Parallel builds
br parallel start my-build
br parallel status

# Agents
br agent list
br agent health
```

## 📊 Monitoring

### Debug Logging
```bash
# Quick logging wrapper
./clog pytest tests/

# Show errors
source .buildrunner/scripts/debug-aliases.sh
show-errors

# View full log
show-log
```

### Telemetry (Datadog)
If DD_API_KEY is set, all metrics are automatically exported:
- Task duration
- Error rates  
- Token usage
- API latency

Dashboard: https://app.datadoghq.com/

## 🔧 Configuration

### Governance Rules
Edit: `.buildrunner/governance/governance.yaml`

### Quality Standards
Edit: `.buildrunner/quality-standards.yaml`

### Telemetry
Edit: `.buildrunner/telemetry-config.yaml`

## 📚 Documentation

- Architecture Guard: Run `br guard validate --help`
- Gap Analysis: Run `br gaps analyze --help`
- Auto-Debug: Run `br autodebug --help`
- Full CLI: Run `br --help`

## ⚠️ Important Notes

1. **Hooks Cannot Be Bypassed**: `--no-verify` is prohibited by governance
2. **All Checks Must Pass**: Commits/pushes blocked if checks fail
3. **Telemetry Requires Setup**: Set DD_API_KEY to enable Datadog
4. **Database Auto-Creates**: SQLite database created on first use

---

**BuildRunner Version:** 3.2.0  
**Activation Date:** $(date +"%Y-%m-%d")  
**Systems Active:** 21/21 ✅
