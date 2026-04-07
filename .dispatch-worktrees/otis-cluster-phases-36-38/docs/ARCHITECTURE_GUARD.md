# Architecture Guard System

> Prevent architectural drift by validating code against PROJECT_SPEC.md

## Overview

The Architecture Guard System ensures your codebase remains aligned with architectural specifications by automatically detecting violations in:

- **Tech Stack Compliance**: Unauthorized libraries and frameworks
- **Component Structure**: Directory organization and file placement
- **API Design Patterns**: Endpoint naming and REST/GraphQL conventions
- **Naming Conventions**: Code style and identifier standards

**Key Benefits:**
- 🛡️ Prevents architectural drift before it happens
- 📋 Validates code against PROJECT_SPEC.md automatically
- 🔍 Detects unauthorized dependencies early
- 🎯 Enforces design patterns consistently
- 🔗 Integrates with git hooks for pre-commit validation

## How It Works

### 1. Specification Parsing

The system parses your `PROJECT_SPEC.md` to extract architectural requirements:

```markdown
## Tech Stack

### Backend
- FastAPI
- Pydantic
- SQLAlchemy

### Frontend
- React
- TypeScript
- Tailwind

## Architecture

Directory structure:
\`\`\`
project/
├── backend/
│   ├── core/
│   ├── api/
│   └── db/
├── frontend/
│   ├── components/
│   └── pages/
└── tests/
\`\`\`

## API Design

RESTful endpoints:
- GET /api/v1/resources
- POST /api/v1/resources
- PUT /api/v1/resources/{id}
- DELETE /api/v1/resources/{id}

## Naming Conventions

- Files: snake_case
- Classes: PascalCase
- Functions: snake_case
- Constants: UPPER_CASE
```

### 2. Code Analysis

Using Python's AST (Abstract Syntax Tree), the guard analyzes your codebase to detect:

**Import Analysis:**
```python
import fastapi  # ✅ Allowed (in tech stack)
import unauthorized_lib  # ❌ Violation - not in spec
```

**Naming Analysis:**
```python
class UserModel:  # ✅ Correct PascalCase
    pass

class badClassName:  # ❌ Violation - should be PascalCase
    pass

def process_data():  # ✅ Correct snake_case
    pass

def BadFunction():  # ❌ Violation - should be snake_case
    pass
```

**API Pattern Analysis:**
```python
@app.get("/api/v1/users")  # ✅ Follows RESTful pattern
def get_users():
    pass

@app.post("missing_slash")  # ❌ Violation - should start with /
def bad_endpoint():
    pass
```

### 3. Violation Detection

Violations are categorized by severity:

- **Critical**: Major architectural deviations (unauthorized tech stack additions)
- **Warning**: Design pattern violations (API inconsistencies, component misplacement)
- **Info**: Style violations (naming conventions)

### 4. Report Generation

Generates detailed reports in multiple formats:
- **Markdown**: Human-readable with emojis and formatting
- **JSON**: Machine-readable for CI/CD integration
- **Text**: Plain text for simple parsing

## CLI Usage

### Basic Check

Validate your entire codebase:

```bash
br guard check
```

**Output:**
```
✅ Loaded architectural specifications
Analyzing codebase...

# Architecture Violation Report

**Total Violations:** 3

## 🟡 Warning (2)

### Tech Stack
**File:** `core/models.py` (line 5)

Unauthorized library 'pydantic-extra' not in tech stack specification

- **Expected:** Libraries from approved tech stack
- **Actual:** pydantic-extra
- **Suggestion:** Consider using approved alternatives or add 'pydantic-extra' to PROJECT_SPEC

### API Design
**File:** `api/routes.py` (line 42)

Route 'users/profile' should start with '/'

- **Expected:** Routes starting with '/'
- **Actual:** users/profile

## 🔵 Info (1)

### Naming
**File:** `core/utils.py` (line 15)

Function 'ProcessData' should use snake_case

- **Expected:** snake_case
- **Actual:** ProcessData

Found 3 violations
  Critical: 0, Warnings: 2
```

### Strict Mode

Include info-level violations:

```bash
br guard check --strict
```

### Custom Spec Location

Specify PROJECT_SPEC.md location:

```bash
br guard check --spec docs/architecture.md
```

### JSON Output

For CI/CD integration:

```bash
br guard check --output json > violations.json
```

**Output:**
```json
[
  {
    "type": "tech_stack",
    "severity": "warning",
    "file": "core/models.py",
    "line": 5,
    "description": "Unauthorized library 'pydantic-extra' not in tech stack specification",
    "expected": "Libraries from approved tech stack",
    "actual": "pydantic-extra",
    "suggestion": "Consider using approved alternatives or add 'pydantic-extra' to PROJECT_SPEC"
  }
]
```

### Text Output

Simple text format:

```bash
br guard check --output text
```

## Git Hook Integration

### Pre-Commit Hook

Automatically validate architecture before commits:

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running architecture validation..."
br guard check

if [ $? -ne 0 ]; then
    echo "❌ Architecture violations detected!"
    echo "Fix violations or use --no-verify to skip (not recommended)"
    exit 1
fi

echo "✅ Architecture validation passed"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

### Pre-Push Hook

Validate before pushing:

```bash
# .git/hooks/pre-push
#!/bin/bash

echo "Running architecture validation before push..."
br guard check --strict

if [ $? -ne 0 ]; then
    echo "❌ Architecture violations detected!"
    echo "Cannot push with violations in strict mode"
    exit 1
fi
```

### Using BuildRunner Governance

Integrate with BuildRunner's built-in governance:

```yaml
# .buildrunner/behavior.yaml
governance:
  pre_commit_checks:
    - type: architecture_guard
      strict: false
      block_on_violations: true

  pre_push_checks:
    - type: architecture_guard
      strict: true
      block_on_violations: true
```

## Example Violation Reports

### Tech Stack Violation

```markdown
## 🔴 Critical

### Tech Stack
**File:** `backend/services/payment.py` (line 3)

Unauthorized library 'stripe-unofficial' not in tech stack specification

- **Expected:** Use approved 'stripe' library from tech stack
- **Actual:** stripe-unofficial
- **Suggestion:** Replace with official 'stripe' library or add to PROJECT_SPEC if approved by architecture team
```

### Component Structure Violation

```markdown
## 🟡 Warning

### Component Structure
**File:** `/`

Expected directory 'tests/' not found

- **Expected:** tests/
- **Actual:** missing
- **Suggestion:** Create tests/ directory to match specified architecture
```

### API Design Violation

```markdown
## 🟡 Warning

### API Design
**File:** `api/v2/endpoints.py` (line 28)

Endpoint '/api/users/list' doesn't follow RESTful convention

- **Expected:** GET /api/v1/users (resource-based, not action-based)
- **Actual:** /api/users/list
- **Suggestion:** Use GET /api/v1/users instead of /api/users/list
```

### Naming Convention Violation

```markdown
## 🔵 Info

### Naming
**File:** `core/models/UserModel.py` (line 1)

File 'UserModel.py' should use snake_case

- **Expected:** user_model.py
- **Actual:** UserModel.py
- **Suggestion:** Rename file to user_model.py
```

## Best Practices

### 1. Keep PROJECT_SPEC.md Updated

Your spec is the source of truth:

```markdown
## Tech Stack Updates

When adding new libraries:
1. Document in PROJECT_SPEC.md first
2. Run `br guard check` to ensure compatibility
3. Update team on architectural changes
```

### 2. Use Strict Mode in CI/CD

```yaml
# .github/workflows/ci.yml
- name: Architecture Validation
  run: br guard check --strict --output json
```

### 3. Review Violations Regularly

Weekly architecture review:
```bash
# Generate violation report
br guard check --strict --output markdown > arch_review.md

# Review in team meeting
cat arch_review.md
```

### 4. Gradual Adoption

For existing codebases:

**Step 1: Baseline**
```bash
# Generate current violations
br guard check --strict > baseline.txt
```

**Step 2: Track Progress**
```bash
# Week 1: Fix critical violations
br guard check --output json | jq '[.[] | select(.severity=="critical")]'

# Week 2: Fix warnings
br guard check --output json | jq '[.[] | select(.severity=="warning")]'

# Week 3: Fix info violations
br guard check --strict
```

**Step 3: Enforce**
```bash
# Enable git hook when baseline is clean
cp .buildrunner/templates/pre-commit .git/hooks/
```

### 5. Document Exceptions

Sometimes violations are intentional:

```python
# This import is intentionally not in PROJECT_SPEC
# Reason: Legacy code migration in progress
# Approved by: Architecture team
# Ticket: ARCH-123
import legacy_library
```

Add to PROJECT_SPEC temporarily:
```markdown
## Tech Stack

### Temporary Exceptions

- `legacy_library` - Migration in progress (remove by Q2 2024)
```

### 6. Customize Severity Levels

Adjust violation severity in your spec:

```markdown
## Architecture Rules

### Severity Overrides

- Naming conventions: INFO (don't block commits)
- Tech stack additions: CRITICAL (block commits)
- API patterns: WARNING (warn but allow)
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Architecture Guard

on: [push, pull_request]

jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install BuildRunner
        run: pip install buildrunner

      - name: Validate Architecture
        run: |
          br guard check --strict --output json > violations.json

      - name: Upload violations
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: architecture-violations
          path: violations.json

      - name: Comment PR
        if: failure() && github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const violations = JSON.parse(fs.readFileSync('violations.json'));
            const body = `## Architecture Violations\n\nFound ${violations.length} violations:\n\n${violations.map(v => `- **${v.type}** in \`${v.file}\`: ${v.description}`).join('\n')}`;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

### GitLab CI

```yaml
architecture_guard:
  stage: quality
  script:
    - pip install buildrunner
    - br guard check --strict
  only:
    - merge_requests
    - main
  artifacts:
    when: on_failure
    paths:
      - violations.json
```

### Jenkins

```groovy
stage('Architecture Guard') {
    steps {
        sh 'pip install buildrunner'
        sh 'br guard check --strict --output json > violations.json'
    }
    post {
        failure {
            archiveArtifacts artifacts: 'violations.json'
            emailext body: 'Architecture violations detected. See attached report.',
                     subject: 'Architecture Guard Failed',
                     attachmentsPattern: 'violations.json'
        }
    }
}
```

## Troubleshooting

### No Spec Found

**Error:**
```
❌ PROJECT_SPEC.md not found in /project/root
```

**Solution:**
Create PROJECT_SPEC.md or specify custom location:
```bash
br guard check --spec docs/architecture.md
```

### False Positives

**Issue:** Standard library imports flagged as violations

**Solution:** Standard library is automatically allowed. If still flagged, check import spelling:
```python
import sys  # ✅ Allowed
import unknown  # ❌ Flagged if not in spec or stdlib
```

### Performance on Large Codebases

**Issue:** Slow analysis on 10,000+ files

**Optimization:**
1. Analyze specific directories:
   ```bash
   br guard check  # Analyzes core/, api/, cli/ by default
   ```

2. Exclude directories in `.gitignore`
3. Run in parallel in CI/CD

## Advanced Usage

### Custom Violation Handlers

Process violations programmatically:

```python
from core.architecture_guard import ArchitectureGuard

guard = ArchitectureGuard('/project/path')
guard.load_spec()
violations = guard.detect_violations()

# Custom filtering
critical_only = [v for v in violations if v.severity == 'critical']

# Custom reporting
for violation in critical_only:
    send_to_monitoring_system(violation)
```

### Integration with Code Review Tools

```python
# PR comment generator
def generate_pr_comment(violations):
    comment = "## Architecture Review\n\n"
    for v in violations:
        comment += f"- [{v.severity}] **{v.file}:{v.line}**: {v.description}\n"
    return comment
```

## See Also

- [Feature Registry](FEATURES.md) - Feature tracking system
- [Git Governance](GOVERNANCE.md) - Branch protection and automation
- [Self-Service Setup](SELF_SERVICE.md) - Service dependency management
- [BUILD_PLAN_MISSING_SYSTEMS.md](../.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md) - Implementation plan
