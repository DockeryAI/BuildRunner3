# PROJECT_SPEC - Build 4E: Multi-Model Routing + Security Foundation + Telemetry

**Version:** 4E (v3.1.0-alpha.9)
**Duration:** 5-7 days
**Goal:** Add intelligent multi-model routing for cost/speed optimization + essential security/quality safeguards + lightweight telemetry with threshold-based alerts

---

## Overview

Build 4E implements the high-value components of v3.1 plus essential security safeguards:

**1. Security Foundation (Tier 1 - Critical)** 🔴
- Secret detection and prevention (prevents token leaks)
- SQL injection detection (prevents security vulnerabilities)
- Test coverage enforcement (prevents regressions)

**2. Multi-Model Routing**
- Route tasks to appropriate Claude model (Haiku/Sonnet/Opus)
- 70% cost reduction through intelligent model selection
- 3x speed improvement on simple tasks

**3. Telemetry Foundation**
- Passive event collection for future learning
- Threshold alerts when enough data exists for next learning phase
- Privacy-first design (no secrets logged)

**Immediate Value:**
- Security: Prevent token leaks and vulnerabilities (learned from Synapse incident)
- Cost: 60%+ savings through model routing
- Speed: 2-3x faster execution on simple tasks
- Foundation: Data collection enables future learning

**Delayed Value:**
- Data collection enables analytics at 30+ features
- Alert system guides when to build advanced learning features

---

## Features

### Feature 1: Multi-Model Router

**Description:** Intelligent routing of tasks to optimal Claude model based on complexity and task type

**Files to Create:**
1. `core/model_router.py` (400+ lines)
   - `TaskComplexity` enum (simple, medium, complex, planning)
   - `ModelRouter` class
   - Complexity estimation from task description
   - Cost tracking per model
   - Model selection logic
   - Fallback handling

**Implementation Details:**
```python
class ModelRouter:
    """Route tasks to optimal Claude model"""

    MODELS = {
        'haiku': {
            'cost_per_mtok': 0.25,
            'speed_multiplier': 3.0,
            'max_complexity': 'simple'
        },
        'sonnet': {
            'cost_per_mtok': 3.00,
            'speed_multiplier': 1.0,
            'max_complexity': 'complex'
        },
        'opus': {
            'cost_per_mtok': 15.00,
            'speed_multiplier': 0.7,
            'max_complexity': 'planning'
        }
    }

    def estimate_complexity(self, task: str, context: dict) -> str:
        """Estimate task complexity from description and context"""
        # Simple: formatting, TODOs, simple refactors
        # Medium: feature implementation, bug fixes
        # Complex: architecture decisions, multi-file refactors
        # Planning: PRD creation, system design

    def select_model(self, task: str, context: dict = None) -> str:
        """Select optimal model for task"""

    def track_usage(self, model: str, tokens: int, duration: float):
        """Track model usage for cost analysis"""
```

**Routing Rules:**
- **Haiku** - Formatting, linting, TODO extraction, simple file edits
- **Sonnet** - Feature implementation, tests, bug fixes, refactoring
- **Opus** - Architecture planning, PRD creation, complex design decisions

**Acceptance Criteria:**
- ✅ Routes simple tasks to Haiku
- ✅ Routes medium tasks to Sonnet
- ✅ Routes planning tasks to Opus
- ✅ Tracks cost savings vs always-Sonnet baseline
- ✅ Provides model override flag for user control
- ✅ Falls back gracefully if model unavailable

---

### Feature 2: Lightweight Telemetry System

**Description:** Passive event collection for future learning without heavy infrastructure

**Files to Create:**
2. `core/telemetry/__init__.py`
3. `core/telemetry/event_schema.py` (200+ lines)
   - `TelemetryEvent` base class
   - Event types (BuildEvent, FeatureEvent, QualityEvent, ModelEvent)
   - JSON serialization
   - Event validation

4. `core/telemetry/collector.py` (300+ lines)
   - `TelemetryCollector` class
   - Event logging to `.buildrunner/telemetry/events.jsonl`
   - Async/non-blocking collection
   - Automatic metadata (timestamp, git hash, user)
   - Privacy controls (opt-in/opt-out)

5. `core/telemetry/analyzer.py` (250+ lines)
   - `TelemetryAnalyzer` class
   - Query events by type/date range
   - Calculate metrics (feature count, build count, model usage)
   - Threshold checking
   - Simple statistics (counts, averages, trends)

**Event Types:**
```python
# Build events
{
    "event_type": "build",
    "command": "br quality check",
    "duration_ms": 2345,
    "success": true,
    "timestamp": "2025-01-17T22:00:00Z"
}

# Feature events
{
    "event_type": "feature",
    "action": "completed",
    "feature_id": "auth-system",
    "complexity": "medium",
    "duration_hours": 8.5
}

# Model usage events
{
    "event_type": "model_usage",
    "model": "haiku",
    "task_type": "formatting",
    "tokens": 1500,
    "cost": 0.000375,
    "duration_ms": 800
}

# Quality events
{
    "event_type": "quality",
    "score": 78.5,
    "coverage": 87.2,
    "violations": 3
}
```

**Storage:**
- Append-only JSONL file: `.buildrunner/telemetry/events.jsonl`
- One event per line
- Human-readable for debugging
- Easy to migrate to database later

**Acceptance Criteria:**
- ✅ All CLI commands emit events
- ✅ Events logged asynchronously (non-blocking)
- ✅ File size stays reasonable (<50KB per project initially)
- ✅ Privacy: no code content, no secrets
- ✅ Opt-out mechanism in config
- ✅ Query interface works for threshold checking

---

### Feature 3: Threshold Monitoring & Alert System

**Description:** Monitor collected data and alert user when enough exists for next learning phase

**Files to Create:**
6. `core/telemetry/threshold_monitor.py` (300+ lines)
   - `ThresholdMonitor` class
   - Define thresholds for each learning phase
   - Check current data against thresholds
   - Generate actionable alerts
   - Track alert history (don't spam user)

**Thresholds:**
```python
LEARNING_THRESHOLDS = {
    'analytics_dashboard': {
        'min_features': 30,
        'min_builds': 20,
        'min_days': 14,
        'value': 'Trend analysis, velocity tracking, quality trends',
        'build_time': '1 week',
        'message': '🎯 Ready for Analytics Dashboard! You have {features} features...'
    },
    'pattern_recognition': {
        'min_features': 100,
        'min_builds': 50,
        'min_projects': 3,
        'min_days': 60,
        'value': 'Architecture recommendations, pattern detection',
        'build_time': '2 weeks'
    },
    'predictive_intelligence': {
        'min_features': 500,
        'min_builds': 200,
        'min_projects': 10,
        'min_days': 180,
        'value': 'Bug prediction, performance forecasting, auto-optimization',
        'build_time': '3 weeks'
    }
}
```

**Alert Mechanisms:**
1. **CLI Output** - Show banner on `br status` when threshold met
2. **Notification File** - Write to `.buildrunner/alerts/learning_ready.md`
3. **Optional Slack/Email** - If user configures integrations

**Alert Format:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 LEARNING PHASE READY: Analytics Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You've collected enough data for valuable insights!

Current Stats:
  • 32 features completed (threshold: 30) ✅
  • 45 builds executed (threshold: 20) ✅
  • 21 days of data (threshold: 14) ✅

What You'll Gain:
  • Trend analysis (quality over time)
  • Velocity tracking (features/week)
  • Pattern identification (what works for you)

Estimated Build Time: 1 week

Next Steps:
  1. Run: br telemetry ready analytics_dashboard
  2. Review capabilities and decide
  3. Run: br build start analytics_dashboard (auto-generates spec)

Dismiss this alert: br telemetry dismiss analytics_dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Acceptance Criteria:**
- ✅ Monitors telemetry data on every `br` command
- ✅ Calculates current stats vs thresholds
- ✅ Shows alert when threshold reached (once)
- ✅ Doesn't spam (tracks dismissed alerts)
- ✅ Provides clear value proposition
- ✅ Gives actionable next steps
- ✅ User can dismiss alerts

---

### Feature 4: CLI Integration

**Description:** Integrate routing, telemetry, and alerts into existing CLI

**Files to Modify:**
7. `cli/main.py` - Add telemetry commands and initialization
8. All command files - Add event emission

**New Commands:**
```bash
# Telemetry management
br telemetry status          # Show collection stats
br telemetry ready [phase]   # Check if ready for learning phase
br telemetry export [file]   # Export events for analysis
br telemetry clear           # Clear all events (confirm prompt)
br telemetry disable         # Opt out of collection
br telemetry enable          # Opt in to collection

# Alert management
br telemetry alerts          # Show all active alerts
br telemetry dismiss <alert> # Dismiss specific alert

# Model routing
br config set model.routing auto|manual
br config set model.default haiku|sonnet|opus
br model stats               # Show usage stats and cost savings
```

**Command Modifications:**
- Every CLI command emits start/end events
- Capture success/failure
- Track duration
- Log to telemetry if enabled

**Acceptance Criteria:**
- ✅ All existing commands emit telemetry events
- ✅ New telemetry commands work
- ✅ Model routing respected in all AI calls
- ✅ Cost tracking shows savings
- ✅ Alerts display on relevant commands

---

### Feature 5: Cost Tracking Dashboard

**Description:** Show user actual cost savings from multi-model routing

**Files to Create:**
9. `cli/model_commands.py` (200+ lines)
   - `br model stats` command
   - Cost comparison (actual vs baseline)
   - Model usage breakdown
   - Savings over time

**Output Example:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Multi-Model Cost Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Period: Last 30 days

Model Usage:
  • Haiku:  145 tasks (65%) - $2.18
  • Sonnet:  70 tasks (30%) - $12.45
  • Opus:    12 tasks (5%)  - $18.90

Total Cost: $33.53

If All Sonnet (baseline): $87.25
Savings: $53.72 (62% reduction) 🎉

Average Task Cost:
  • Haiku:  $0.015
  • Sonnet: $0.178
  • Opus:   $1.575

Fastest Model: Haiku (avg 800ms)
Slowest Model: Opus (avg 3200ms)

Recommendations:
  • Consider using Haiku more for formatting (100% success rate)
  • Opus usage optimal (only complex planning tasks)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Acceptance Criteria:**
- ✅ Tracks cost per model
- ✅ Compares to baseline (all-Sonnet)
- ✅ Shows percentage savings
- ✅ Displays usage patterns
- ✅ Provides optimization suggestions

---

### Feature 6: Core Security & Quality Safeguards (Tier 1 Only)

**Description:** Three essential checks to prevent disasters - secrets, SQL injection, test coverage

**Background:** Based on real incidents and BuildRunnerSaaS best practices:
1. User experienced token leaks (Synapse incident)
2. SQL injection is a common security vulnerability
3. Test coverage prevents regressions
4. These 3 checks prevent 80% of critical issues without slowing developers down

**Principle:** Start minimal, expand gradually based on user feedback

**Files to Create:**
10. `core/security/__init__.py`
11. `core/security/secret_masker.py` (200+ lines - streamlined)
    - `SecretMasker` class
    - Pattern detection (API keys, JWT tokens, passwords)
    - Sensitive key detection (api_key, secret, token, password)
    - Masking logic (show first/last 4 chars)
    - Integration with CLI output

12. `core/security/secret_detector.py` (250+ lines - focused)
    - `SecretDetector` class
    - Regex patterns for common API keys (Anthropic, OpenAI, OpenRouter, JWT, generic)
    - Scan staged files only (not entire history - too slow)
    - Simple whitelist mechanism

13. `core/security/sql_injection_detector.py` (150+ lines - new)
    - `SQLInjectionDetector` class
    - Detect string concatenation with user input in SQL queries
    - Suggest parameterized queries
    - Language-specific patterns (Python, JS/TS, etc.)

14. `core/hooks/tier1_hook.py` (200+ lines - new)
    - Pre-commit hook for Tier 1 checks only
    - Check 1: Secrets in staged files
    - Check 2: SQL injection patterns
    - Check 3: Test coverage minimum (if tests exist)
    - Fast execution (<2 seconds)
    - Clear error messages with fix suggestions

**Implementation Details:**

```python
# core/security/secret_masker.py
class SecretMasker:
    """Mask sensitive values in terminal output"""

    SENSITIVE_PATTERNS = {
        'anthropic_key': r'sk-ant-[a-zA-Z0-9]{32,}',
        'openai_key': r'sk-[a-zA-Z0-9]{32,}',
        'openrouter_key': r'sk-or-v1-[a-f0-9]{64}',
        'jwt_token': r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',
        'notion_secret': r'ntn_[a-zA-Z0-9]+',
        'apify_key': r'apify_api_[a-zA-Z0-9]+',
        'bearer_token': r'Bearer [a-zA-Z0-9_-]+',
    }

    SENSITIVE_KEYS = {
        'api_key', 'secret', 'token', 'password', 'key',
        'auth', 'credential', 'private', 'jwt',
    }

    @staticmethod
    def mask_value(value: str, show_chars: int = 4) -> str:
        """Mask sensitive value, showing only first/last chars"""
        if not value or len(value) < 8:
            return "****"
        return f"{value[:show_chars]}...{value[-show_chars:]}"

    @staticmethod
    def mask_config_value(key: str, value: str) -> str:
        """Mask value if key is sensitive"""
        if SecretMasker.is_sensitive_key(key):
            return SecretMasker.mask_value(value)
        return value

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Replace all detected secrets in text with masked versions"""
        for pattern_name, pattern in SecretMasker.SENSITIVE_PATTERNS.items():
            text = re.sub(pattern, lambda m: SecretMasker.mask_value(m.group(0)), text)
        return text
```

```python
# core/security/secret_detector.py
class SecretDetector:
    """Detect secrets in files, git history, and diffs"""

    def scan_file(self, file_path: str) -> List[SecretMatch]:
        """Scan a single file for secrets"""

    def scan_directory(self, directory: str, exclude: List[str] = None) -> Dict[str, List[SecretMatch]]:
        """Recursively scan directory"""

    def scan_git_diff(self, staged_only: bool = True) -> Dict[str, List[SecretMatch]]:
        """Scan git staged changes for secrets"""

    def scan_git_history(self, file_path: str = None) -> Dict[str, List[SecretMatch]]:
        """Scan git history for committed secrets"""
```

```bash
# Pre-commit hook (.buildrunner/hooks/pre-commit-secrets)
#!/bin/bash
# Auto-generated by BuildRunner
# Scans staged files for secrets before allowing commit

br security check --staged
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ SECRET DETECTED in staged files!"
    echo ""
    echo "⚠️  Commit blocked to prevent secret exposure"
    echo ""
    echo "Options:"
    echo "  1. Remove the secret from staged files"
    echo "  2. Move secret to .env (gitignored)"
    echo "  3. If false positive: br security whitelist <file>:<line>"
    echo ""
    exit 1
fi

exit 0
```

**CLI Integration:**

Update CLI commands to mask secrets:
```python
# cli/config_commands.py (BEFORE)
console.print(f"✅ Set {key} = {value} (local)")

# cli/config_commands.py (AFTER)
from core.security.secret_masker import SecretMasker
masked = SecretMasker.mask_config_value(key, value)
console.print(f"✅ Set {key} = {masked} (local)")
```

**Quality Gate Integration:**

```python
# core/quality/quality_gate.py
from core.security.secret_detector import SecretDetector

class QualityGate:
    def check_security(self) -> QualityResult:
        """Check for exposed secrets in codebase"""
        detector = SecretDetector()
        secrets = detector.scan_directory(
            self.project_root,
            exclude=['.env', '.git', 'node_modules', 'venv']
        )

        if secrets:
            return QualityResult(
                passed=False,
                score=0,
                violations=[
                    f"Secret found in {file}:{line}"
                    for file, matches in secrets.items()
                    for match in matches
                ]
            )
        return QualityResult(passed=True, score=100)
```

**Gap Analyzer Integration:**

```python
# core/gaps/gap_analyzer.py
from core.security.secret_detector import SecretDetector

class GapAnalyzer:
    def analyze_security_gaps(self) -> List[Gap]:
        """Detect security-related gaps"""
        gaps = []

        # Check for hardcoded secrets
        detector = SecretDetector()
        secrets = detector.scan_directory(self.project_root)
        if secrets:
            gaps.append(Gap(
                type='security',
                severity='critical',
                description='Hardcoded secrets detected',
                suggestion='Move secrets to environment variables',
                files=list(secrets.keys())
            ))

        # Check for missing .env in .gitignore
        gitignore_path = self.project_root / '.gitignore'
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if '.env' not in content:
                gaps.append(Gap(
                    type='security',
                    severity='high',
                    description='.env not in .gitignore',
                    suggestion='Add .env to .gitignore to prevent secret commits'
                ))

        # Check for committed .env in git history
        if self._check_git_history_for_env():
            gaps.append(Gap(
                type='security',
                severity='critical',
                description='.env file found in git history',
                suggestion='Clean git history with git-filter-repo'
            ))

        return gaps
```

**Telemetry Privacy:**

Ensure telemetry NEVER logs secrets:
```python
# core/telemetry/collector.py
from core.security.secret_masker import SecretMasker

class TelemetryCollector:
    def collect_event(self, event: TelemetryEvent):
        """Collect event with privacy protection"""
        # Sanitize all text fields
        if hasattr(event, 'command'):
            event.command = SecretMasker.sanitize_text(event.command)
        if hasattr(event, 'output'):
            event.output = SecretMasker.sanitize_text(event.output)
        if hasattr(event, 'error'):
            event.error = SecretMasker.sanitize_text(event.error)

        # Never log file paths that might contain secrets
        if hasattr(event, 'file_path'):
            if '.env' in event.file_path:
                event.file_path = '<redacted .env file>'

        self._write_event(event)
```

**Acceptance Criteria (Streamlined):**
- ✅ Pre-commit hook blocks commits with secrets (< 2s execution)
- ✅ Pre-commit hook detects SQL injection patterns
- ✅ Pre-commit hook checks test coverage minimum (if tests exist)
- ✅ CLI commands mask secrets in output (br config, br status)
- ✅ `br quality check` includes all 3 Tier 1 checks
- ✅ Telemetry never logs secret values
- ✅ False positives can be whitelisted (simple .buildrunner/whitelist.txt)
- ✅ Clear error messages with fix suggestions
- ✅ No slowdown for developers (fast checks only)

---

### Feature 7: Parallel Build Orchestration System

**Description:** Semi-automated system for managing parallel builds across multiple Claude Code instances

**Files to Create:**
15. `core/orchestration/session_manager.py` (400+ lines)
    - Session state management for parallel streams
    - Command file generation for workers
    - Status tracking across streams
    - Merge coordination

16. `core/orchestration/dashboard.py` (300+ lines)
    - Flask-based dashboard at localhost:8080
    - Real-time stream progress display
    - Shared decision tracking
    - Conflict visualization

17. `core/orchestration/context_sync.py` (250+ lines)
    - Cross-stream context synchronization
    - Shared decisions file management
    - Dependency tracking between streams
    - Merge conflict detection

18. `cli/session_commands.py` (200+ lines)
    - `br orchestrate --parallel` - Start orchestrator
    - `br worker --stream [name]` - Start worker
    - `br session [stream]` - Copy prompt to clipboard
    - `br merge --streams` - Coordinate merge

**Implementation Details:**

Worker watches `.buildrunner/commands/[stream].json`:
```json
{
  "batch_id": "batch_1",
  "tasks": [
    {"id": "task_1", "description": "...", "files": ["..."]},
    {"id": "task_2", "description": "...", "files": ["..."]}
  ],
  "context": {
    "completed": ["previous_task_1"],
    "shared_decisions": {...}
  }
}
```

Worker writes `.buildrunner/status/[stream].json`:
```json
{
  "stream": "frontend",
  "status": "complete",
  "batch_id": "batch_1",
  "completed_tasks": ["task_1", "task_2"],
  "branch": "stream/frontend",
  "commit": "abc123"
}
```

**User Workflow:**
1. Terminal 1: `br orchestrate --parallel` (orchestrator)
2. Terminal 2: `br worker --stream frontend`
3. Terminal 3: `br worker --stream backend`
4. Terminal 4: `br worker --stream database`
5. Workers prompt: "Found batch. Type 'continue'"
6. User types "continue" in each worker
7. Workers complete, say "Done. Type 'check' for more"
8. User tells orchestrator: "merge"
9. Orchestrator merges, prepares next batch
10. User tells workers: "check"
11. Cycle repeats

**Acceptance Criteria:**
- ✅ Orchestrator generates parallel plan
- ✅ Workers detect command files
- ✅ Dashboard shows real-time progress
- ✅ Merge automation works
- ✅ Context syncs between batches
- ✅ User only types short commands

---

### Feature 8: Testing & Documentation

**Description:** Comprehensive tests and user documentation

**Files to Create:**
19. `tests/test_security.py` (350+ lines)
    - Test secret detection patterns
    - Test masking logic
    - Test pre-commit hook
    - Test CLI integration
    - Test false positive handling

20. `tests/test_model_router.py` (200+ lines)
    - Test complexity estimation
    - Test model selection logic
    - Test cost tracking
    - Mock API calls

21. `tests/test_telemetry.py` (250+ lines)
    - Test event collection
    - Test event querying
    - Test threshold monitoring
    - Test alert generation
    - Test privacy (no secrets in events)

22. `tests/test_orchestration.py` (300+ lines)
    - Test session management
    - Test worker coordination
    - Test merge automation
    - Test context synchronization
    - Test conflict detection

23. `docs/SECURITY.md` (500+ lines)
    - Secret detection system
    - Pre-commit hook setup
    - CLI secret masking
    - Git history cleanup guide
    - Best practices
    - Incident response

24. `docs/MULTI_MODEL_ROUTING.md` (300+ lines)
    - How routing works
    - Cost comparison examples
    - How to override
    - Troubleshooting

25. `docs/TELEMETRY.md` (400+ lines)
    - What data is collected
    - Privacy policy
    - How to opt out
    - Learning phase thresholds
    - Alert system

26. `docs/PARALLEL_BUILDS.md` (600+ lines)
    - How parallel orchestration works
    - User workflow guide
    - Dashboard usage
    - Troubleshooting
    - Best practices for parallel development

**Acceptance Criteria:**
- ✅ 85%+ test coverage for new code
- ✅ All tests passing
- ✅ Security documentation complete
- ✅ Privacy clearly explained
- ✅ Incident response playbook provided

---

## Implementation Plan

### Phase 1: Core Security Safeguards (Day 1-2) 🔴 PRIORITY
**Rationale:** Prevent disasters before adding features. Learned from Synapse incident.

1. Create `core/security/secret_masker.py` - Mask secrets in CLI output
2. Create `core/security/secret_detector.py` - Detect secrets in files
3. Create `core/security/sql_injection_detector.py` - Detect SQL injection patterns
4. Create `core/hooks/tier1_hook.py` - Fast pre-commit hook (<2s)
5. Write tests for all 3 checks
6. Test with real secrets (verify detection + masking)
7. Verify no false positives on sample projects

**Success Metric:** Hook runs in <2s, catches real secrets, no false alarms

### Phase 2: Multi-Model Router (Day 3)
1. Create `core/model_router.py`
2. Implement complexity estimation (simple heuristics)
3. Implement model selection logic
4. Add cost tracking
5. Write tests
6. Test with real API calls (verify routing works)

### Phase 3: Telemetry Foundation (Day 4)
1. Create telemetry module structure
2. Define event schemas (with secret sanitization)
3. Implement collector (async logging, non-blocking)
4. Implement analyzer (basic query interface)
5. Write tests (including privacy - no secrets logged)

### Phase 4: Threshold Monitoring (Day 5)
1. Create threshold monitor (simple check: count features)
2. Define threshold for analytics dashboard (30 features)
3. Implement alert generation (console banner)
4. Write tests

### Phase 5: CLI Integration (Day 6)
1. Update CLI commands to mask secrets (br config, br status)
2. Add telemetry to all existing commands (emit events)
3. Create model commands (br model stats)
4. Integrate Tier 1 hook into br init
5. Test end-to-end
6. Verify performance (<2s for hook, <50ms for telemetry)

### Phase 6: Quality & Gap Integration (Day 7)
1. Integrate 3 Tier 1 checks into quality gates
2. Add security/SQL gaps to gap analyzer
3. Test quality checks fail appropriately
4. Verify gap detection works
5. Test remediation suggestions are clear

### Phase 7: Parallel Orchestration System (Days 7-8)
1. Create session manager (command file generation, status tracking)
2. Create dashboard (Flask app, real-time display)
3. Create context sync system (shared decisions, conflict detection)
4. Implement CLI commands (orchestrate, worker, merge)
5. Write tests for orchestration
6. Test full parallel workflow (4 instances)
7. Verify merge automation works

### Phase 8: Documentation & Polish (Day 9)
1. Write SECURITY.md (Tier 1 checks explained, incident response)
2. Write TELEMETRY.md (what's collected, privacy policy, opt-out)
3. Write MULTI_MODEL_ROUTING.md (how it works, cost savings)
4. Write PARALLEL_BUILDS.md (workflow guide, troubleshooting)
5. Add inline help text (br --help improvements)
6. Test on fresh environment
7. Tag release v3.1.0-alpha.9

---

## Acceptance Criteria

### Functional Requirements:
- ✅ Multi-model routing works (Haiku/Sonnet/Opus)
- ✅ Cost tracking shows accurate savings
- ✅ Telemetry collects events passively
- ✅ Threshold monitoring detects readiness
- ✅ Alerts display when thresholds met
- ✅ User can opt out of telemetry
- ✅ No performance degradation (<50ms overhead)

### Security Requirements (Tier 1 Only): 🔴 NEW
- ✅ Pre-commit hook blocks commits with secrets (3 checks run in <2s)
- ✅ Pre-commit hook blocks SQL injection patterns
- ✅ Pre-commit hook enforces minimum test coverage (if tests exist)
- ✅ CLI commands mask secrets in output (br config, br status)
- ✅ Quality gates fail on Tier 1 violations
- ✅ Gap analyzer identifies security issues (secrets, SQL injection)
- ✅ Telemetry sanitizes all events (no secrets ever logged)
- ✅ False positives whitelistable (.buildrunner/whitelist.txt)
- ✅ Clear error messages with fix suggestions
- ✅ Hook runs fast enough not to annoy developers

### Quality Requirements:
- ✅ 85%+ test coverage
- ✅ All tests passing
- ✅ Security tests verify masking works with real API key patterns
- ✅ Documentation complete
- ✅ Privacy policy clear
- ✅ Secure (no secrets logged anywhere)
- ✅ Incident response playbook provided

### User Experience:
- ✅ Cost savings visible immediately
- ✅ Alerts are helpful, not annoying
- ✅ Clear value proposition
- ✅ Easy to disable if unwanted
- ✅ Security warnings are clear and actionable
- ✅ Secret detection doesn't cause false alarm fatigue

---

## Success Metrics

**Immediate (Week 1):**
- Multi-model routing saves 60%+ on costs
- Tasks execute 2-3x faster with Haiku
- Zero API errors from routing
- Telemetry collection working

**Short-term (Month 1):**
- User hits 30 features → analytics alert triggers
- Cost savings documented ($$$ saved)
- Telemetry data validates routing decisions

**Long-term (Month 6):**
- User benefits from learning phases
- System has data to build predictive features
- ROI proven (cost + time savings)

---

## Dependencies

**Python Packages:**
- Python 3.11+
- anthropic (Claude API)
- aiofiles (async file I/O)
- pytest (testing)
- rich (console UI)

**External:**
- Claude API access (Haiku, Sonnet, Opus)
- Git (for metadata)

---

## Risks & Mitigations

**Risk 1: Model availability**
- Mitigation: Fallback to Sonnet if preferred model unavailable

**Risk 2: Telemetry performance impact**
- Mitigation: Async logging, non-blocking writes

**Risk 3: Privacy concerns**
- Mitigation: Clear opt-out, no code content logged, documented

**Risk 4: Alert fatigue**
- Mitigation: Show each alert once, easy to dismiss

**Risk 5: Routing accuracy**
- Mitigation: User can override, monitor success rates

---

## Deliverables

**Code Files (20+ files):**

**Security Module:** 🔴 NEW
1. `core/security/__init__.py`
2. `core/security/secret_masker.py`
3. `core/security/secret_detector.py`
4. `core/security/git_hooks.py`
5. `cli/security_commands.py`
6. `tests/test_security.py`

**Model Routing:**
7. `core/model_router.py`
8. `tests/test_model_router.py`

**Telemetry:**
9. `core/telemetry/__init__.py`
10. `core/telemetry/event_schema.py`
11. `core/telemetry/collector.py` (with secret sanitization)
12. `core/telemetry/analyzer.py`
13. `core/telemetry/threshold_monitor.py`
14. `tests/test_telemetry.py`

**CLI:**
15. `cli/main.py` (modified - add security and telemetry commands)
16. `cli/model_commands.py`
17. All existing CLI command files (modified for secret masking + event emission)

**Documentation:**
18. `docs/SECURITY.md` (500+ lines) 🔴 NEW
19. `docs/MULTI_MODEL_ROUTING.md` (300+ lines)
20. `docs/TELEMETRY.md` (400+ lines with privacy policy)

**Configuration:**
- `.buildrunner/config.yaml` - Add telemetry and security settings
- `.buildrunner/telemetry/` - Event storage directory
- `.buildrunner/security/` - Secret detection whitelist
- `.buildrunner/hooks/pre-commit-secrets` - Git hook

**Documentation:**
- Security incident response playbook
- User guides for routing and telemetry
- Privacy policy (no secrets logged)
- Learning phase roadmap
- Secret detection best practices

---

## Post-Build Validation

After Build 4E completion:
1. Run `br model stats` - Should show $0 cost (no usage yet)
2. Run `br quality check` - Should emit telemetry event
3. Check `.buildrunner/telemetry/events.jsonl` - Should have events
4. Run `br telemetry status` - Should show collection stats
5. Run `br telemetry ready analytics_dashboard` - Should show progress toward 30 features
6. Create 30+ test features - Should trigger alert
7. Measure cost savings over 1 week of real usage

---

## Future Enhancements (Not in Build 4E)

- Analytics dashboard (at 30+ features)
- Pattern recognition (at 100+ features)
- Predictive intelligence (at 500+ features)
- Central telemetry database (multi-project)
- Team analytics (shared insights)
- Cloud sync (optional)

---

**Build 4E provides immediate value (cost/speed) while laying foundation for future learning capabilities.**
