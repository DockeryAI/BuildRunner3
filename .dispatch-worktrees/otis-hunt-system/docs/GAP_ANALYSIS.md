# Gap Analysis System

The BuildRunner 3.0 Gap Analysis System detects gaps between project specifications and actual implementation, helping identify incomplete work, missing features, and technical debt.

## Overview

Gap analysis bridges the gap between what's planned and what's implemented. It scans your codebase, features, specifications, and dependencies to find:

- Missing or incomplete features
- TODOs, FIXMEs, and stub implementations
- Missing dependencies
- Circular dependencies
- Spec violations
- Incomplete documentation

### Key Features

- **Feature Tracking**: Analyzes `.buildrunner/features.json` for incomplete work
- **Spec Comparison**: Compares PROJECT_SPEC.md with actual implementation
- **Code Analysis**: Detects TODOs, stubs, NotImplementedError patterns
- **Dependency Analysis**: Finds missing imports and circular dependencies
- **Severity Classification**: Categorizes gaps by impact (high/medium/low)
- **Markdown Reports**: Generates actionable reports for teams

## Gap Types

### Feature Gaps

Detected from `.buildrunner/features.json`:

#### Missing Features (Status: planned)

Features defined but not started:

```json
{
  "id": "auth-sso",
  "name": "SSO Authentication",
  "status": "planned",
  "priority": "high"
}
```

**Impact**: High - Planned functionality not delivered

#### Incomplete Features (Status: in_progress)

Features started but not finished:

```json
{
  "id": "api-pagination",
  "name": "API Pagination",
  "status": "in_progress",
  "completion": "60%"
}
```

**Impact**: Medium - Work in progress, may block other features

#### Blocked Features (Status: blocked)

Features waiting on dependencies:

```json
{
  "id": "payment-gateway",
  "name": "Payment Integration",
  "status": "blocked",
  "blocked_by": ["ssl-cert", "compliance-review"]
}
```

**Impact**: High - Blockers prevent progress

### Implementation Gaps

Detected from code analysis:

#### TODO Comments

Markers for incomplete work:

```python
# TODO: Implement retry logic
# FIXME: This breaks on edge case
# XXX: Hack - replace with proper solution
# HACK: Temporary workaround for issue #123
```

**Patterns Detected**:
- `TODO:` - Work to be done
- `FIXME:` - Broken code needing fixes
- `XXX:` - Code smells or hacks
- `HACK:` - Temporary workarounds

**Impact**: Varies - Review each TODO for context

#### Stub Implementations

Functions that raise NotImplementedError:

```python
def process_payment(amount: float):
    raise NotImplementedError("Payment processing not yet implemented")
```

**Impact**: High - Functionality appears to exist but fails at runtime

#### Empty Functions

Functions with only `pass`:

```python
def validate_input(data: dict):
    pass  # Validation not implemented
```

**Impact**: Medium - May cause logic errors

### Dependency Gaps

Detected from import analysis:

#### Missing Dependencies

Imports not in requirements.txt:

```python
import requests  # Not in requirements.txt
import pandas    # Not in requirements.txt
```

**Impact**: High - Code fails in fresh environments

#### Circular Dependencies

Modules importing each other:

```
module_a.py imports module_b
module_b.py imports module_a
```

**Impact**: Medium - Can cause import errors, indicates design issue

### Spec Violations

Detected by comparing PROJECT_SPEC.md with implementation:

#### Missing Components

Spec defines components not in codebase:

```markdown
## Required Files
- file: `core/auth.py`  # Missing
- file: `api/routes.py`  # Missing
```

**Impact**: High - Spec promises unfulfilled

#### Missing API Endpoints

Endpoints documented but not implemented:

```markdown
## API Endpoints
- `GET /api/users` - List users  # Not found
```

**Impact**: High - API contract broken

#### Missing Database Tables

Tables specified but not created:

```markdown
## Database Schema
- table: users    # Exists
- table: sessions # Missing
```

**Impact**: High - Data model incomplete

## CLI Usage

### Basic Gap Analysis

Analyze current project:

```bash
br gaps analyze
```

Output includes:
- Gap summary (total, by severity)
- Feature gaps (missing, incomplete, blocked)
- Implementation gaps (TODOs, stubs)
- Dependency gaps
- Recommendations

### With Custom Spec

Specify custom spec file:

```bash
br gaps analyze --spec ./REQUIREMENTS.md
```

### Save Report

Generate markdown report:

```bash
br gaps analyze --output gaps_report.md
```

Report includes:
- Executive summary
- Detailed gap listings
- Severity breakdown
- Actionable recommendations

### Verbose Output

Show all details:

```bash
br gaps analyze --verbose
```

Includes:
- File paths and line numbers
- Full TODO text
- Dependency trees
- Spec diffs

## Configuration

### Features File Format

`.buildrunner/features.json`:

```json
{
  "features": [
    {
      "id": "feat-001",
      "name": "User Authentication",
      "description": "Login and session management",
      "status": "complete",
      "priority": "high"
    },
    {
      "id": "feat-002",
      "name": "API Documentation",
      "status": "in_progress",
      "completion": "75%",
      "assignee": "dev-team",
      "priority": "medium"
    },
    {
      "id": "feat-003",
      "name": "Analytics Dashboard",
      "status": "planned",
      "priority": "low",
      "depends_on": ["feat-001"]
    },
    {
      "id": "feat-004",
      "name": "Payment Processing",
      "status": "blocked",
      "blocked_by": ["compliance", "ssl-cert"],
      "priority": "high"
    }
  ]
}
```

**Status Values**:
- `complete` - Feature finished and tested
- `in_progress` - Currently being worked on
- `planned` - Scheduled but not started
- `blocked` - Waiting on dependencies

### Spec File Format

`PROJECT_SPEC.md`:

```markdown
# Project Specification

## API Endpoints

- `GET /api/users` - List all users
- `POST /api/users` - Create new user
- `PUT /api/users/:id` - Update user

## Database Tables

- table: users
  - id (primary key)
  - email (unique)
  - created_at

- table: sessions
  - id (primary key)
  - user_id (foreign key)
  - expires_at

## Required Files

- file: `core/models.py` - Data models
- file: `core/auth.py` - Authentication logic
- file: `api/routes.py` - API endpoints

## External Dependencies

- service: PostgreSQL 14+
- service: Redis 6+
- service: SendGrid (email)
```

## Understanding Results

### Gap Analysis Summary

```
=== Gap Analysis Summary ===

Total Gaps: 47

By Severity:
  🔴 High:   12 gaps
  🟡 Medium: 23 gaps
  🟢 Low:    12 gaps

By Category:
  Features:       8 gaps
  Implementation: 28 gaps
  Dependencies:   7 gaps
  Spec:           4 gaps
```

### Severity Levels

#### High Severity (🔴)

- Missing features (status: planned)
- Blocked features
- Stub implementations (NotImplementedError)
- Missing critical dependencies
- Spec violations for required components

**Action**: Address immediately, may block releases

#### Medium Severity (🟡)

- Incomplete features (status: in_progress)
- TODO/FIXME comments
- Empty function implementations
- Circular dependencies
- Missing non-critical components

**Action**: Prioritize in sprint planning

#### Low Severity (🟢)

- HACK/XXX comments (if documented)
- Missing optional dependencies
- Documentation gaps
- Minor spec deviations

**Action**: Address during refactoring cycles

## Integration Examples

### CI/CD Pipeline

GitHub Actions (.github/workflows/gaps.yml):

```yaml
name: Gap Analysis

on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  workflow_dispatch:

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install BuildRunner
        run: pip install -e .

      - name: Run gap analysis
        run: |
          br gaps analyze --output gaps_report.md

      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: gap-analysis-report
          path: gaps_report.md

      - name: Comment on PR (if PR)
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('gaps_report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Gap Analysis Report\n\n${report}`
            });
```

### Pre-release Checklist

```bash
#!/bin/bash
# pre-release.sh - Run before creating release

echo "Running gap analysis..."
br gaps analyze --output release_gaps.md

# Check for high-severity gaps
high_gaps=$(grep -c "🔴 High" release_gaps.md || true)

if [ "$high_gaps" -gt 0 ]; then
    echo "❌ Found $high_gaps high-severity gaps!"
    echo "Review release_gaps.md before proceeding."
    cat release_gaps.md
    exit 1
fi

echo "✅ No high-severity gaps found"
```

### Project Status Dashboard

Generate weekly status:

```bash
#!/bin/bash
# status.sh - Weekly status report

br gaps analyze --output gaps_$(date +%Y%m%d).md

# Extract metrics
total=$(grep "Total Gaps:" gaps_$(date +%Y%m%d).md | awk '{print $3}')
high=$(grep "High:" gaps_$(date +%Y%m%d).md | awk '{print $2}')

echo "Weekly Status Report - $(date +%Y-%m-%d)"
echo "Total Gaps: $total"
echo "High Severity: $high"

# Compare with last week
if [ -f gaps_last_week.md ]; then
    echo ""
    echo "Trend:"
    diff -u gaps_last_week.md gaps_$(date +%Y%m%d).md | grep -E '^\+|^\-' | head -20
fi

cp gaps_$(date +%Y%m%d).md gaps_last_week.md
```

## Programmatic Usage

### Basic Analysis

```python
from pathlib import Path
from core.gap_analyzer import GapAnalyzer

analyzer = GapAnalyzer(Path.cwd())
analysis = analyzer.analyze()

print(f"Total Gaps: {analysis.total_gaps}")
print(f"High Severity: {analysis.severity_high}")
print(f"TODOs: {analysis.todo_count}")
print(f"Stubs: {analysis.stub_count}")
```

### Feature-Specific Analysis

```python
analyzer = GapAnalyzer(Path.cwd())
analysis = analyzer.analyze()

# Check missing features
if analysis.missing_features:
    print("Missing Features:")
    for feature in analysis.missing_features:
        print(f"  - {feature['name']} (priority: {feature.get('priority', 'unknown')})")

# Check blocked features
if analysis.blocked_features:
    print("\nBlocked Features:")
    for feature in analysis.blocked_features:
        blockers = feature.get('blocked_by', [])
        print(f"  - {feature['name']} (blocked by: {', '.join(blockers)})")
```

### Dependency Analysis

```python
from core.gap_analyzer import GapAnalyzer

analyzer = GapAnalyzer(Path.cwd())
analyzer._discover_files()

from core.gap_analyzer import GapAnalysis
analysis = GapAnalysis()

analyzer.analyze_dependencies(analysis)

print(f"Missing Dependencies: {', '.join(analysis.missing_dependencies)}")
print(f"Circular Dependencies: {len(analysis.circular_dependencies)}")
```

### Generate Custom Report

```python
from pathlib import Path
from core.gap_analyzer import GapAnalyzer

analyzer = GapAnalyzer(Path.cwd())
analysis = analyzer.analyze()

# Custom report with filtering
report_lines = [
    "# Critical Gaps Only",
    "",
    f"High Severity Gaps: {analysis.severity_high}",
    "",
]

# Add high-priority missing features
high_priority_missing = [
    f for f in analysis.missing_features
    if f.get('priority') == 'high'
]

if high_priority_missing:
    report_lines.append("## High Priority Missing Features")
    for feature in high_priority_missing:
        report_lines.append(f"- **{feature['name']}**")
        if 'description' in feature:
            report_lines.append(f"  {feature['description']}")

# Add stubs
if analysis.stubs:
    report_lines.append("\n## Stub Implementations")
    for stub in analysis.stubs[:10]:  # Top 10
        report_lines.append(f"- {stub['file']}:{stub['line']} - `{stub['name']}`")

report = "\n".join(report_lines)
Path("critical_gaps.md").write_text(report)
```

## Best Practices

### Maintain Feature Tracking

1. **Update features.json regularly**: Keep status current
2. **Document blockers**: List what's preventing progress
3. **Set priorities**: Help team focus on important gaps
4. **Track completion**: Use percentage for in-progress features

### Manage TODOs

1. **Be specific**: `TODO: Add retry logic with exponential backoff` not `TODO: Fix`
2. **Add issue numbers**: `TODO(#123): Implement caching`
3. **Set deadlines**: `TODO(by 2024-03): Migrate to new API`
4. **Avoid permanent TODOs**: Either do it or remove it
5. **Review regularly**: Weekly TODO sweep

### Address Gaps Systematically

1. **High severity first**: Fix blocking issues immediately
2. **Group related gaps**: Fix all TODOs in one module together
3. **Update features.json**: Mark progress as you go
4. **Communicate blockers**: Escalate blocked features
5. **Track trends**: Monitor if gaps increasing or decreasing

### Spec Maintenance

1. **Keep spec updated**: Reflect actual requirements
2. **Version the spec**: Track changes over time
3. **Link to issues**: Reference issue tracker
4. **Remove obsolete items**: Clean up outdated requirements
5. **Review in planning**: Make spec part of sprint planning

## Interpreting Reports

### Sample Report Structure

```markdown
# Gap Analysis Report

Generated: 2024-01-15 14:30:00

## Summary

Total Gaps: 34
- 🔴 High: 8 gaps
- 🟡 Medium: 18 gaps
- 🟢 Low: 8 gaps

## Feature Gaps

### Missing Features (3)

1. **SSO Authentication** (Priority: high)
   - Status: planned
   - Impact: Blocks enterprise customers

2. **API Rate Limiting** (Priority: medium)
   - Status: planned
   - Impact: Performance and security

### Incomplete Features (2)

1. **Export to PDF** (Priority: medium)
   - Status: in_progress (60% complete)
   - Assignee: dev-team

### Blocked Features (1)

1. **Payment Processing** (Priority: high)
   - Status: blocked
   - Blocked by: ssl-cert, compliance-review
   - Impact: Cannot launch paid tiers

## Implementation Gaps

### TODOs (15 found)

Top 10 shown:

1. `core/auth.py:45` - TODO: Add password strength validation
2. `api/routes.py:123` - FIXME: Handle concurrent requests
3. `core/db.py:78` - TODO: Implement connection pooling

... and 5 more

### Stub Implementations (4 found)

1. `core/payments.py:34` - `process_refund()`
2. `core/exports.py:56` - `generate_pdf()`

## Dependency Gaps

### Missing Dependencies (3)

- `redis` (imported in core/cache.py)
- `celery` (imported in tasks/worker.py)
- `pillow` (imported in utils/images.py)

Action: Add to requirements.txt

## Recommendations

1. **Unblock payment processing** - Escalate ssl-cert and compliance
2. **Add missing dependencies** - Update requirements.txt
3. **Address stub implementations** - Implement or remove
4. **Review TODOs** - Convert to issues or fix inline
```

## Troubleshooting

### "No .buildrunner/features.json found"

Create features file:

```bash
mkdir -p .buildrunner
cat > .buildrunner/features.json << 'EOF'
{
  "features": []
}
EOF
```

Then add your features manually or via CLI.

### "Invalid JSON in features.json"

Validate JSON:

```bash
python -m json.tool .buildrunner/features.json
```

Fix syntax errors reported.

### "PROJECT_SPEC.md not found"

Create spec file:

```bash
cat > PROJECT_SPEC.md << 'EOF'
# Project Specification

## Overview
Brief project description

## Features
List of features

## Technical Requirements
System requirements
EOF
```

### Too many TODOs reported

Filter by pattern:

```python
# In custom script
analysis = analyzer.analyze()
critical_todos = [
    todo for todo in analysis.todos
    if 'FIXME' in todo['text'] or 'URGENT' in todo['text']
]
```

Or use git pre-commit hooks to prevent adding TODOs.

### Circular dependency false positives

May occur with:
- Type checking imports (`if TYPE_CHECKING:`)
- Dynamic imports

Review manually and add to ignore list if needed.

## Related Documentation

- [Code Quality](CODE_QUALITY.md) - Quality metrics and enforcement
- [Feature Tracking](FEATURE_TRACKING.md) - Managing features.json
- [Specifications](SPEC_WRITING.md) - Writing effective specs
- [Technical Debt](TECH_DEBT.md) - Managing and reducing debt
