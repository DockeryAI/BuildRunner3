# Quality Gates Tutorial

Learn to set up and enforce code quality standards using BuildRunner's quality gate system for consistent, maintainable code.

## Table of Contents

- [Introduction](#introduction)
- [Understanding Quality Gates](#understanding-quality-gates)
- [Setting Up Quality Standards](#setting-up-quality-standards)
- [Configuring Thresholds](#configuring-thresholds)
- [Local Quality Checks](#local-quality-checks)
- [CI/CD Integration](#cicd-integration)
- [Auto-fix Workflows](#auto-fix-workflows)
- [Team Adoption Strategies](#team-adoption-strategies)
- [Progressive Enforcement](#progressive-enforcement)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Introduction

Quality gates are automated checkpoints that enforce code quality standards before code is merged or deployed. BuildRunner's quality gate system analyzes your code across four dimensions:

- **Structure** (complexity, type hints, formatting)
- **Security** (vulnerabilities, unsafe patterns)
- **Testing** (coverage, test count)
- **Documentation** (docstrings, README)

This tutorial shows you how to implement quality gates in your development workflow.

## Understanding Quality Gates

### What is a Quality Gate?

A quality gate is a pass/fail check based on quality metrics:

```
Code → Analyze → Check Thresholds → Pass/Fail
```

**Example:**
```bash
# Run quality check
br quality check --threshold 80

# If overall score >= 80: Exit code 0 (Pass)
# If overall score < 80:  Exit code 1 (Fail)
```

### Why Use Quality Gates?

**Without Quality Gates:**
- Inconsistent code quality
- Technical debt accumulates
- Hard to review PRs
- Security vulnerabilities slip through

**With Quality Gates:**
- ✅ Consistent quality standards
- ✅ Technical debt prevented
- ✅ Automated code review
- ✅ Security issues caught early

### Quality Metrics Explained

**Structure Score (25% weight)**
- Cyclomatic complexity (simpler is better)
- Type hint coverage
- Code formatting (black compliance)

**Security Score (30% weight)**
- High/medium/low severity vulnerabilities
- Unsafe patterns (SQL injection, XSS, etc.)
- Uses bandit security scanner

**Testing Score (25% weight)**
- Test coverage percentage
- Test count vs source files
- Assertion count

**Documentation Score (20% weight)**
- Docstring coverage
- Comment ratio
- README quality

**Overall Score**
```
overall = (structure * 0.25) + (security * 0.30) +
          (testing * 0.25) + (docs * 0.20)
```

## Setting Up Quality Standards

### Step 1: Assess Current Quality

First, see where you stand:

```bash
# Run quality check without enforcement
br quality check
```

Output:
```
📊 Code Quality Report

Quality Scores:
Component       Score  Status
Structure       72.0   ⚠ Fair
Security        95.0   ✓ Excellent
Testing         65.0   ✗ Poor
Documentation   58.0   ✗ Poor
OVERALL         72.5   ⚠ Fair

📈 Metrics:
  Avg Complexity: 8.5
  Type Hint Coverage: 45.0%
  Test Coverage: 65.0%
  Docstring Coverage: 40.0%

💡 Suggestions:
  • Test coverage is 65.0% (target: 80%+)
  • Docstring coverage is 40.0% (target: 70%+)
  • Add type hints to improve structure score
```

### Step 2: Set Realistic Initial Thresholds

Don't start too high. Set thresholds slightly above current:

```bash
# Current overall: 72.5
# Set initial threshold: 70
br quality check --threshold 70 --strict

# ✅ Should pass initially
```

### Step 3: Create Quality Config

Create `.buildrunner/quality.yaml`:

```yaml
# Quality gate configuration

thresholds:
  overall: 70      # Minimum overall score
  structure: 65
  security: 90     # High bar for security
  testing: 65
  docs: 60

targets:
  # Long-term goals
  overall: 85
  structure: 80
  security: 95
  testing: 85
  docs: 75

auto_fix:
  enabled: true
  tools:
    - black        # Code formatting
    - isort        # Import sorting

progressive:
  enabled: true
  increment: 5     # Raise threshold by 5 every month
  max: 85          # Stop at target

exclusions:
  # Paths to exclude from analysis
  - tests/fixtures/
  - legacy/old_code/
```

### Step 4: Install Quality Tools

```bash
# Install analysis tools
pip install black bandit pytest pytest-cov

# Verify installation
black --version
bandit --version
pytest --version
```

## Configuring Thresholds

### Default Thresholds

BuildRunner's defaults (strict):

```python
DEFAULT_THRESHOLDS = {
    'overall': 80.0,
    'structure': 75.0,
    'security': 90.0,
    'testing': 80.0,
    'docs': 70.0,
}
```

### Component-Specific Thresholds

Adjust per component:

```yaml
# .buildrunner/quality.yaml
thresholds:
  overall: 75
  structure: 70
  security: 95     # Higher for security
  testing: 80      # Higher for testing
  docs: 60         # Lower for docs (for now)
```

### Per-Environment Thresholds

Different standards for different environments:

```yaml
# .buildrunner/quality.yaml
environments:
  development:
    thresholds:
      overall: 70    # More lenient
      testing: 65

  staging:
    thresholds:
      overall: 80
      testing: 80

  production:
    thresholds:
      overall: 85    # Strictest
      testing: 90
      security: 95
```

Usage:
```bash
# Development
br quality check --env development

# Production
br quality check --env production
```

### File-Specific Thresholds

Different rules for different file types:

```yaml
# .buildrunner/quality.yaml
file_rules:
  - pattern: "api/*.py"
    thresholds:
      security: 95    # API files need high security

  - pattern: "tests/*.py"
    thresholds:
      docs: 50        # Tests need less documentation

  - pattern: "core/*.py"
    thresholds:
      testing: 90     # Core needs high test coverage
```

## Local Quality Checks

### Pre-Commit Checks

Prevent bad commits:

```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Quality gate pre-commit hook

echo "Running quality checks..."
br quality check --threshold 70 --strict

if [ $? -ne 0 ]; then
    echo "❌ Quality gate failed. Commit blocked."
    echo "Run 'br quality check' to see details."
    exit 1
fi

echo "✅ Quality gate passed"
exit 0
EOF

# Make executable
chmod +x .git/hooks/pre-commit
```

Now commits are blocked if quality fails:

```bash
git commit -m "Add feature"
# Running quality checks...
# ❌ Quality gate failed. Commit blocked.
# Error: Overall score 68.0 < 70.0
```

### Pre-Push Checks

More comprehensive check before push:

```bash
# .git/hooks/pre-push
#!/bin/bash

echo "Running full quality check..."

# Run tests with coverage
pytest --cov=. --cov-report=json

# Run quality check
br quality check --threshold 75 --strict

if [ $? -ne 0 ]; then
    echo "❌ Quality gate failed. Push blocked."
    exit 1
fi

echo "✅ Quality gate passed. Pushing..."
exit 0
```

### IDE Integration

#### VS Code

Install BuildRunner extension and configure:

```json
// .vscode/settings.json
{
  "buildrunner.qualityCheck.onSave": true,
  "buildrunner.qualityCheck.threshold": 70,
  "buildrunner.autoFix.onSave": true,
  "buildrunner.autoFix.tools": ["black", "isort"]
}
```

#### PyCharm

Configure external tool:

```
Settings → Tools → External Tools → Add

Name: BuildRunner Quality Check
Program: br
Arguments: quality check --threshold 70
Working Directory: $ProjectFileDir$
```

Bind to keyboard shortcut: `Cmd+Shift+Q`

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/quality.yml`:

```yaml
name: Quality Gate

on:
  pull_request:
  push:
    branches: [main, develop]

jobs:
  quality:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install buildrunner
          pip install -r requirements.txt

      - name: Install quality tools
        run: |
          pip install black bandit pytest pytest-cov

      - name: Run tests with coverage
        run: |
          pytest --cov=. --cov-report=json

      - name: Run quality gate
        run: |
          br quality check --threshold 75 --strict

      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const output = fs.readFileSync('quality_report.txt', 'utf8');

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Quality Gate Report\n\n${output}`
            });
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - quality

quality_check:
  stage: quality
  image: python:3.11

  before_script:
    - pip install buildrunner
    - pip install black bandit pytest pytest-cov
    - pip install -r requirements.txt

  script:
    - pytest --cov=. --cov-report=json
    - br quality check --threshold 75 --strict

  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'

  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### CircleCI

Create `.circleci/config.yml`:

```yaml
version: 2.1

jobs:
  quality_gate:
    docker:
      - image: cimg/python:3.11

    steps:
      - checkout

      - run:
          name: Install dependencies
          command: |
            pip install buildrunner
            pip install -r requirements.txt
            pip install black bandit pytest pytest-cov

      - run:
          name: Run tests
          command: pytest --cov=. --cov-report=json

      - run:
          name: Quality gate
          command: br quality check --threshold 75 --strict

      - store_artifacts:
          path: coverage.json

workflows:
  quality:
    jobs:
      - quality_gate
```

### PR Status Checks

Make quality gate required:

**GitHub:**
```
Settings → Branches → Branch protection rules
→ Require status checks: "Quality Gate"
```

**GitLab:**
```
Settings → Repository → Merge request approvals
→ Require pipeline to succeed
```

## Auto-fix Workflows

### Local Auto-fix

```bash
# Auto-fix formatting issues
br quality check --fix

# What it fixes:
# - Code formatting (black)
# - Import sorting (isort)
# - Trailing whitespace
# - Line endings
```

### Automated PR Auto-fix

GitHub Action that auto-fixes and commits:

```yaml
# .github/workflows/auto-fix.yml
name: Auto-fix Quality Issues

on:
  pull_request:

jobs:
  auto_fix:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.head_ref }}

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install tools
        run: |
          pip install buildrunner black isort

      - name: Auto-fix issues
        run: |
          br quality check --fix

      - name: Commit fixes
        run: |
          git config user.name "BuildRunner Bot"
          git config user.email "bot@buildrunner.dev"
          git add -A
          git diff --quiet && git diff --staged --quiet || \
            git commit -m "style: auto-fix quality issues"
          git push
```

### Pre-commit Auto-fix

Using pre-commit framework:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: buildrunner-format
        name: BuildRunner Auto-fix
        entry: br quality check --fix
        language: system
        pass_filenames: false

      - id: buildrunner-check
        name: BuildRunner Quality Gate
        entry: br quality check --threshold 70 --strict
        language: system
        pass_filenames: false
```

Install:
```bash
pip install pre-commit
pre-commit install
```

## Team Adoption Strategies

### Phase 1: Measurement (Week 1-2)

Don't enforce yet, just measure:

```bash
# Run checks but don't block
br quality check

# Generate weekly reports
br quality check --output weekly_report.md
```

Share reports in team meetings.

### Phase 2: Opt-in (Week 3-4)

Make it optional:

```bash
# Developers can opt-in
git config --local quality.enabled true

# Pre-commit only runs if opted-in
if git config --get quality.enabled; then
    br quality check --threshold 70 --strict
fi
```

Encourage early adopters.

### Phase 3: Soft Enforcement (Month 2)

Warn but don't block:

```bash
# Pre-commit warns but allows commit
br quality check --threshold 70 || echo "⚠️ Quality below threshold"

# CI fails but doesn't block merge
- br quality check --threshold 70 || true
```

### Phase 4: Hard Enforcement (Month 3+)

Full enforcement:

```bash
# Pre-commit blocks
br quality check --threshold 70 --strict

# CI blocks merge
br quality check --threshold 75 --strict
```

### Training & Support

**Documentation:**
- Share this tutorial
- Create internal quality guidelines
- Record walkthrough videos

**Office Hours:**
```
Weekly "Quality Hour"
- Review quality reports
- Fix issues together
- Answer questions
```

**Champions:**
- Assign quality champions per team
- They help teammates improve
- Share best practices

### Incentives

**Gamification:**
```bash
# Generate leaderboard
br quality leaderboard

# Output:
# Top Contributors by Quality Improvement:
# 1. Alice  (+15 points this month)
# 2. Bob    (+12 points this month)
# 3. Carol  (+8 points this month)
```

**Recognition:**
- Quality improvement awards
- Highlight in team meetings
- Internal blog posts

## Progressive Enforcement

Gradually raise standards:

### Month 1: Baseline

```yaml
thresholds:
  overall: 70
  testing: 65
  docs: 60
```

### Month 2: Increment

```yaml
thresholds:
  overall: 75    # +5
  testing: 70    # +5
  docs: 65       # +5
```

### Month 3: Target

```yaml
thresholds:
  overall: 80    # +5
  testing: 75    # +5
  docs: 70       # +5
```

### Automated Progression

```yaml
# .buildrunner/quality.yaml
progressive:
  enabled: true
  start_date: "2024-01-01"
  increment: 5
  interval: "monthly"
  max:
    overall: 85
    structure: 80
    security: 95
    testing: 85
    docs: 75
```

BuildRunner automatically raises thresholds monthly.

## Common Patterns

### Pattern 1: Security-First

High security bar, moderate others:

```yaml
thresholds:
  overall: 75
  structure: 70
  security: 95    # High
  testing: 75
  docs: 65
```

### Pattern 2: Test-Driven

Emphasize testing:

```yaml
thresholds:
  overall: 75
  structure: 70
  security: 85
  testing: 90     # High
  docs: 65
```

### Pattern 3: Balanced

Equal emphasis:

```yaml
thresholds:
  overall: 80
  structure: 80
  security: 80
  testing: 80
  docs: 80
```

### Pattern 4: Legacy Modernization

Start low, increase gradually:

```yaml
# Month 1
thresholds:
  overall: 60
  structure: 55
  security: 85    # Security always high
  testing: 50
  docs: 45

# Auto-increment monthly to:
targets:
  overall: 80
  structure: 75
  security: 95
  testing: 85
  docs: 70
```

## Troubleshooting

### Issue: Quality check too slow

**Cause:** Analyzing too many files

**Solution:**
```yaml
# Exclude unnecessary paths
exclusions:
  - tests/fixtures/
  - vendor/
  - .venv/
```

### Issue: Team pushback

**Cause:** Too strict too fast

**Solution:**
- Start with measurement only
- Gradual enforcement
- Provide training
- Celebrate improvements

### Issue: Flaky quality scores

**Cause:** External tool availability

**Solution:**
```yaml
# Fallback scores if tools unavailable
fallbacks:
  black_unavailable: 50  # Neutral score
  bandit_unavailable: 50
```

### Issue: Different scores locally vs CI

**Cause:** Different tool versions

**Solution:**
```bash
# Pin tool versions in requirements.txt
black==23.0.1
bandit==1.7.5
```

### Issue: Can't meet security threshold

**Cause:** Legacy vulnerabilities

**Solution:**
```yaml
# Temporary exceptions (with expiry)
exceptions:
  - path: "legacy/old_api.py"
    reason: "Scheduled for refactor Q2 2024"
    expires: "2024-06-30"
    thresholds:
      security: 70  # Lower bar temporarily
```

## Summary

You've learned:

✅ What quality gates are and why they matter
✅ How to assess current quality
✅ How to configure thresholds appropriately
✅ How to implement local quality checks
✅ How to integrate with CI/CD pipelines
✅ How to set up auto-fix workflows
✅ How to drive team adoption
✅ How to use progressive enforcement
✅ Common patterns and troubleshooting

## Next Steps

- Read [PARALLEL_BUILDS.md](PARALLEL_BUILDS.md) - Work on multiple features
- Read [COMPLETION_ASSURANCE.md](COMPLETION_ASSURANCE.md) - Use gap analysis
- See [../CODE_QUALITY.md](../CODE_QUALITY.md) - Deep dive into quality metrics

Start enforcing quality standards in your projects today!
