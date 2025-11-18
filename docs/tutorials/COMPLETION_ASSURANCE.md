# Completion Assurance Tutorial

Learn to use BuildRunner's gap analysis system to ensure nothing is missed before release, combining quality checks with completeness verification.

## Table of Contents

- [Introduction](#introduction)
- [Understanding Gap Analysis](#understanding-gap-analysis)
- [Running Gap Analysis](#running-gap-analysis)
- [Interpreting Gap Reports](#interpreting-gap-reports)
- [Fixing Incomplete Implementations](#fixing-incomplete-implementations)
- [Pre-Release Checklists](#pre-release-checklists)
- [Quality + Gaps Workflow](#quality--gaps-workflow)
- [Automated Gap Detection](#automated-gap-detection)
- [Common Gap Patterns](#common-gap-patterns)
- [Real-World Examples](#real-world-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

Gap analysis answers the critical question: **"Are we done?"**

Before releasing, you need to ensure:
- ✅ All planned features are complete
- ✅ No TODO comments left behind
- ✅ No stub implementations (NotImplementedError)
- ✅ All dependencies declared
- ✅ Spec matches implementation
- ✅ Documentation is complete

BuildRunner's gap analyzer automatically detects these issues.

## Understanding Gap Analysis

### What is Gap Analysis?

Gap analysis compares what you **planned** vs what you **implemented**:

```
PROJECT_SPEC.md (Plan)     ←→     Codebase (Reality)
features.json (Plan)       ←→     Implementation (Reality)
```

Gaps found:
- Missing features
- Incomplete implementations
- TODO/FIXME comments
- Stub functions
- Missing dependencies
- Spec violations

### Gap Severity Levels

**High Severity (🔴)**
- Missing planned features
- Blocked features
- Stub implementations (NotImplementedError)
- Missing critical dependencies
- Spec violations for required features

**Medium Severity (🟡)**
- Incomplete features (in_progress)
- TODO/FIXME comments
- Empty functions (just `pass`)
- Missing non-critical components

**Low Severity (🟢)**
- HACK/XXX comments (documented workarounds)
- Missing optional dependencies
- Documentation gaps

### Gap Categories

1. **Feature Gaps** - Features not implemented
2. **Implementation Gaps** - TODOs, stubs, empty functions
3. **Dependency Gaps** - Missing imports, circular dependencies
4. **Spec Gaps** - Code doesn't match PROJECT_SPEC.md

## Running Gap Analysis

### Basic Gap Analysis

```bash
# Run gap analysis on current project
br gaps analyze

# Output:
# === Gap Analysis Summary ===
#
# Total Gaps: 15
#
# By Severity:
#   🔴 High:   3 gaps
#   🟡 Medium: 8 gaps
#   🟢 Low:    4 gaps
#
# By Category:
#   Features:       3 gaps
#   Implementation: 8 gaps
#   Dependencies:   2 gaps
#   Spec:           2 gaps
```

### Generate Detailed Report

```bash
# Save full report to markdown
br gaps analyze --output gap_report.md

# Opens in editor
code gap_report.md
```

### Analyze Specific Areas

```bash
# Only check features
br gaps analyze --category features

# Only check dependencies
br gaps analyze --category dependencies

# Check specific severity
br gaps analyze --severity high

# Check specific paths
br gaps analyze --path src/api/
```

### Compare with Spec

```bash
# Provide custom spec location
br gaps analyze --spec docs/REQUIREMENTS.md

# Analyze multiple specs
br gaps analyze --spec PROJECT_SPEC.md,docs/API_SPEC.md
```

## Interpreting Gap Reports

### Sample Gap Report

```markdown
# Gap Analysis Report

Generated: 2024-01-15 14:30:00

## Summary

Total Gaps: 15
- 🔴 High: 3 gaps
- 🟡 Medium: 8 gaps
- 🟢 Low: 4 gaps

## Feature Gaps

### Missing Features (2)

1. **Payment Processing** (Priority: high)
   - Status: planned
   - Location: .buildrunner/features.json
   - Impact: Cannot process transactions
   - Action: Implement payment gateway integration

2. **Email Notifications** (Priority: medium)
   - Status: planned
   - Location: .buildrunner/features.json
   - Impact: Users don't receive updates
   - Action: Set up email service

### Blocked Features (1)

1. **Advanced Analytics** (Priority: low)
   - Status: blocked
   - Blocked by: data-pipeline, permissions-system
   - Location: .buildrunner/features.json
   - Action: Unblock dependencies first

## Implementation Gaps

### TODO Comments (6 found)

1. `src/api/users.py:45`
   - `TODO: Add password strength validation`
   - Severity: Medium
   - Age: 14 days

2. `src/db/models.py:123`
   - `FIXME: This query is slow, needs optimization`
   - Severity: High
   - Age: 30 days

... and 4 more

### Stub Implementations (2 found)

1. `src/payments/gateway.py:78` - `process_refund()`
   ```python
   def process_refund(transaction_id):
       raise NotImplementedError("Refund processing not implemented")
   ```
   - Severity: High
   - Action: Implement refund logic

2. `src/exports/pdf.py:34` - `generate_invoice()`
   - Severity: Medium
   - Action: Add PDF generation

## Dependency Gaps

### Missing Dependencies (2)

- `stripe` (imported in src/payments/gateway.py)
  - Action: Add to requirements.txt

- `celery` (imported in src/tasks/worker.py)
  - Action: Add to requirements.txt

## Spec Violations

### Missing Components (2)

1. API Endpoint: `POST /api/invoices`
   - Defined in: PROJECT_SPEC.md:145
   - Status: Not implemented
   - Action: Implement invoice creation endpoint

2. Database Table: `notifications`
   - Defined in: PROJECT_SPEC.md:89
   - Status: Not created
   - Action: Create notifications table migration

## Recommendations

1. **High Priority**: Implement payment refund functionality
2. **High Priority**: Fix slow database query in models.py:123
3. **Medium Priority**: Resolve 6 TODO comments
4. **Low Priority**: Complete blocked feature dependencies

## Progress Tracking

- Features: 12/15 complete (80%)
- High-priority gaps: 3 remaining
- Medium-priority gaps: 8 remaining
- Target completion: 2024-01-30
```

### Understanding the Report Sections

**Summary**
- Quick overview of gap count and severity
- Use to track progress over time

**Feature Gaps**
- From `.buildrunner/features.json`
- Shows planned but not started features
- Shows blocked features

**Implementation Gaps**
- From code analysis
- TODOs, FIXMEs, stubs
- Age helps prioritize

**Dependency Gaps**
- Missing imports
- Circular dependencies
- Version mismatches

**Spec Violations**
- PROJECT_SPEC.md vs reality
- Missing endpoints
- Missing database tables
- Missing required files

## Fixing Incomplete Implementations

### Fixing TODOs

**Step 1: Inventory TODOs**

```bash
# Generate TODO report
br gaps analyze --category implementation --severity medium > todos.md
```

**Step 2: Categorize**

```bash
# Group by age
br gaps analyze --todo-age 30  # Older than 30 days

# Group by author
git blame src/api/users.py | grep TODO
```

**Step 3: Create Issues**

```bash
# Convert TODOs to GitHub issues
br gaps export --format github-issues --category implementation

# Creates issues automatically
```

**Step 4: Fix or Remove**

```python
# Bad: Permanent TODO
# TODO: Optimize this later
def slow_function():
    ...

# Good: Issue reference
# TODO(#123): Optimize query performance
def slow_function():
    ...

# Better: Just fix it
def optimized_function():
    # Optimized implementation
    ...
```

### Fixing Stubs

**Step 1: Find All Stubs**

```bash
# List stub implementations
br gaps analyze --stub-only
```

**Step 2: Implement or Remove**

```python
# Bad: Stub that never gets implemented
def process_payment(amount):
    raise NotImplementedError()

# Option 1: Implement it
def process_payment(amount):
    response = stripe.Charge.create(
        amount=amount,
        currency='usd',
        source=request.token
    )
    return response

# Option 2: Remove if not needed
# Just delete the function if it's not in spec
```

**Step 3: Update Feature Status**

```bash
# Mark feature complete
br features update feat-payment --status complete
```

### Fixing Dependency Gaps

**Step 1: Find Missing Dependencies**

```bash
# Analyze dependencies
br gaps analyze --category dependencies

# Output:
# Missing Dependencies:
# - requests (imported in src/api/client.py)
# - celery (imported in src/tasks/worker.py)
```

**Step 2: Add to Requirements**

```bash
# Add missing dependencies
echo "requests>=2.28.0" >> requirements.txt
echo "celery>=5.2.0" >> requirements.txt

# Install
pip install -r requirements.txt
```

**Step 3: Verify**

```bash
# Re-run analysis
br gaps analyze --category dependencies

# Should show:
# Missing Dependencies: 0
```

### Fixing Spec Violations

**Step 1: Identify Violations**

```bash
# Find spec mismatches
br gaps analyze --category spec
```

**Step 2: Implement Missing Components**

```python
# PROJECT_SPEC.md says:
# - POST /api/invoices - Create invoice

# Implement it:
@app.post("/api/invoices", status_code=201)
def create_invoice(invoice: InvoiceCreate):
    """Create a new invoice."""
    # Implementation
    ...
```

**Step 3: Update Spec if Needed**

```markdown
# If implementation differs from spec:
# Update PROJECT_SPEC.md to match reality

## API Endpoints

- POST /api/invoices/generate - Create and send invoice
  (Updated from POST /api/invoices based on implementation)
```

## Pre-Release Checklists

### Automated Pre-Release Check

```bash
# Run comprehensive pre-release check
br release check

# Runs:
# 1. Gap analysis
# 2. Quality check
# 3. Test suite
# 4. Architecture guard
# 5. Security scan
```

### Pre-Release Checklist Template

Create `.buildrunner/release-checklist.yaml`:

```yaml
name: "v3.0.0 Release Checklist"
version: "3.0.0"
target_date: "2024-02-01"

checks:
  - name: "Gap Analysis"
    command: "br gaps analyze --severity high"
    threshold: "0 high-severity gaps"
    blocking: true

  - name: "Quality Gate"
    command: "br quality check --threshold 85 --strict"
    threshold: "85% overall quality"
    blocking: true

  - name: "Test Coverage"
    command: "pytest --cov=. --cov-fail-under=85"
    threshold: "85% coverage"
    blocking: true

  - name: "All Features Complete"
    command: "br features status"
    threshold: "100% complete"
    blocking: true

  - name: "No TODOs"
    command: "br gaps analyze --category implementation"
    threshold: "0 TODO/FIXME comments"
    blocking: false

  - name: "Documentation Updated"
    command: "br docs check"
    threshold: "All docs current"
    blocking: true

manual_checks:
  - "Review CHANGELOG.md"
  - "Update version in pyproject.toml"
  - "Create git tag"
  - "Build distribution packages"
  - "Test installation from package"
```

Run checklist:

```bash
# Run release checklist
br release checklist

# Output:
# Running Release Checklist for v3.0.0
#
# ✅ Gap Analysis: 0 high-severity gaps (PASS)
# ✅ Quality Gate: 87.5% overall (PASS)
# ✅ Test Coverage: 92% coverage (PASS)
# ✅ All Features Complete: 15/15 complete (PASS)
# ⚠️  No TODOs: 3 TODO comments found (WARN - non-blocking)
# ✅ Documentation Updated: All docs current (PASS)
#
# Manual Checks:
# [ ] Review CHANGELOG.md
# [ ] Update version in pyproject.toml
# [ ] Create git tag
# [ ] Build distribution packages
# [ ] Test installation from package
#
# Ready for release? 5/6 automated checks passed
```

## Quality + Gaps Workflow

### Combined Analysis

```bash
# Run both quality and gap analysis
br check-all

# Equivalent to:
br quality check --threshold 85
br gaps analyze --severity high
```

### Integrated Workflow

**Daily Development:**

```bash
# During development
br quality check           # Quick quality check
br gaps analyze --quick    # Quick gap scan
```

**Before Commit:**

```bash
# Pre-commit hook
br quality check --threshold 75 --strict
br gaps analyze --severity high --strict
```

**Before PR:**

```bash
# Full analysis
br quality check --threshold 80 --strict
br gaps analyze --output pr_gaps.md
br test coverage --min 80
```

**Before Release:**

```bash
# Comprehensive check
br release checklist
br quality check --threshold 85 --strict
br gaps analyze --strict  # Zero tolerance
```

### CI/CD Pipeline

```yaml
# .github/workflows/complete.yml
name: Completeness Check

on: [pull_request]

jobs:
  completeness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install BuildRunner
        run: pip install buildrunner

      - name: Quality Check
        run: br quality check --threshold 80 --strict

      - name: Gap Analysis
        run: br gaps analyze --severity high --strict

      - name: Generate Report
        if: failure()
        run: |
          br gaps analyze --output gaps.md
          br quality check --output quality.md

      - name: Comment on PR
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const gaps = fs.readFileSync('gaps.md', 'utf8');
            const quality = fs.readFileSync('quality.md', 'utf8');

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Quality & Gaps Report\n\n${quality}\n\n${gaps}`
            });
```

## Automated Gap Detection

### Continuous Monitoring

```bash
# Set up weekly gap analysis
crontab -e

# Add:
0 9 * * MON cd /path/to/project && br gaps analyze --output weekly_gaps_$(date +\%Y\%m\%d).md
```

### Gap Trend Tracking

```bash
# Track gaps over time
br gaps trend

# Output:
# Gap Trend (Last 30 Days)
#
# Date       Total  High  Medium  Low
# 2024-01-15   15     3      8     4
# 2024-01-08   18     5     10     3  ↓
# 2024-01-01   22     7     12     3  ↓
#
# Trend: Improving (7 fewer gaps in 2 weeks)
```

### Alerts

```yaml
# .buildrunner/alerts.yaml
gap_alerts:
  - condition: "high_severity > 0"
    action: "block_merge"
    message: "Cannot merge with high-severity gaps"

  - condition: "total_gaps > 20"
    action: "notify_team"
    slack_channel: "#tech-debt"

  - condition: "todo_age > 60"
    action: "create_issue"
    assignee: "tech-lead"
```

## Common Gap Patterns

### Pattern 1: MVP Launch

**Goal:** Ship minimum viable product

**Strategy:**
```yaml
# .buildrunner/gap-tolerance.yaml
mvp:
  allow:
    - medium_severity: 10   # Some TODOs okay
    - low_severity: 20      # Lots of polish items okay
  block:
    - high_severity: 0      # No critical gaps
    - missing_features: 0   # All MVP features must be complete
```

### Pattern 2: Incremental Improvement

**Goal:** Gradually reduce technical debt

**Strategy:**
```bash
# Month 1: Baseline
br gaps analyze > baseline.md
# Total gaps: 50

# Month 2: Target 20% reduction
# Total gaps: 40 (10 fixed)

# Month 3: Target 20% reduction
# Total gaps: 32 (8 fixed)

# Track progress
br gaps compare baseline.md current.md
```

### Pattern 3: Zero-Gap Policy

**Goal:** No gaps ever

**Strategy:**
```yaml
# Strict enforcement
thresholds:
  high_severity: 0
  medium_severity: 0
  low_severity: 0
  todos: 0
  stubs: 0

# Auto-block PRs with any gaps
ci:
  gap_tolerance: zero
```

## Real-World Examples

### Example 1: Healthcare App Release

```bash
# Pre-release check
br gaps analyze

# Found:
# 🔴 High: HIPAA compliance form (missing)
# 🔴 High: Patient data encryption (stub)
# 🟡 Medium: 5 TODO comments
# 🟢 Low: Missing audit log for admin actions

# Actions taken:
# 1. Implemented HIPAA compliance form
# 2. Implemented encryption
# 3. Fixed 3 critical TODOs, documented others
# 4. Deferred audit log to v1.1

# Final check:
br gaps analyze --severity high
# 🎉 0 high-severity gaps - Ready for release!
```

### Example 2: API Service

```bash
# Gap analysis found:
# - 3 API endpoints in spec but not implemented
# - 2 database migrations missing
# - Rate limiting stub implementation

# Generated issues:
br gaps export --format github-issues

# Created:
# - Issue #45: Implement POST /api/webhooks
# - Issue #46: Implement GET /api/analytics
# - Issue #47: Implement DELETE /api/sessions
# - Issue #48: Add user_sessions table migration
# - Issue #49: Add webhook_logs table migration
# - Issue #50: Implement rate limiting
```

## Best Practices

### 1. Run Gaps Early and Often

```bash
# Don't wait until release
# Run during development

# Daily:
br gaps analyze --quick

# Weekly:
br gaps analyze --output gaps_weekly.md

# Before release:
br gaps analyze --strict
```

### 2. Track Gap Trends

```bash
# Save reports with timestamps
br gaps analyze --output reports/gaps_$(date +%Y%m%d).md

# Compare over time
br gaps trend --since 30days
```

### 3. Prioritize High-Severity Gaps

```bash
# Focus on what matters
br gaps analyze --severity high

# Fix these first, defer others
```

### 4. Document Acceptable Gaps

```yaml
# .buildrunner/accepted-gaps.yaml
accepted:
  - type: todo
    location: "src/legacy/old_api.py:45"
    reason: "Legacy code, will be removed in v4.0"
    expires: "2024-12-31"

  - type: feature
    id: "feat-advanced-analytics"
    reason: "Deferred to v2.0 due to low priority"
    expires: "2024-06-30"
```

### 5. Integrate with Project Management

```bash
# Sync gaps with Jira
br gaps export --format jira --project PROJ

# Sync with Linear
br gaps export --format linear --team ENG

# Sync with GitHub Projects
br gaps export --format github-project --project 5
```

## Troubleshooting

### Issue: Too Many False Positives

**Cause:** Overly strict analysis

**Solution:**
```yaml
# .buildrunner/gaps-config.yaml
exclusions:
  - tests/fixtures/  # Test data
  - docs/examples/   # Example code
  - vendor/          # Third-party code

ignore_patterns:
  - "TODO(example):"  # Documentation TODOs
  - "# XXX: Known issue #123"  # Documented hacks
```

### Issue: Gap Count Not Decreasing

**Cause:** New gaps added as fast as old ones fixed

**Solution:**
```bash
# Freeze new gaps during cleanup
git config hooks.pre-commit "br gaps analyze --no-new-gaps"

# Only allow gap reduction
```

### Issue: Spec Out of Sync with Code

**Cause:** Spec not updated when implementation changed

**Solution:**
```bash
# Make spec review part of PR process
# .github/pull_request_template.md

## Checklist
- [ ] PROJECT_SPEC.md updated if needed
- [ ] Gap analysis shows no spec violations
```

## Summary

You've learned:

✅ What gap analysis is and why it matters
✅ How to run gap analysis
✅ How to interpret gap reports
✅ How to fix different types of gaps
✅ Pre-release checklist creation
✅ Quality + gaps combined workflow
✅ Common gap patterns
✅ Real-world examples

## Next Steps

- Review [QUALITY_GATES.md](QUALITY_GATES.md) - Enforce quality standards
- Read [../GAP_ANALYSIS.md](../GAP_ANALYSIS.md) - Deep dive into gap analysis
- Create your first pre-release checklist

Never ship incomplete code again! 🎯
