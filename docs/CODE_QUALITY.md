# Code Quality System

The BuildRunner 3.0 Code Quality System provides comprehensive analysis of your codebase across multiple dimensions: structure, security, testing, and documentation.

## Overview

The quality system analyzes Python projects and generates actionable metrics to help maintain high code standards. It integrates with CI/CD pipelines to enforce quality gates and prevent regressions.

### Key Features

- **Multi-dimensional Analysis**: Structure, security, testing, and documentation scores
- **Quality Gate Enforcement**: Configurable thresholds with pass/fail criteria
- **Actionable Feedback**: Issues, warnings, and suggestions for improvement
- **CLI Integration**: Simple commands for local and CI/CD use
- **External Tool Integration**: Leverages black, bandit, and coverage tools

## Quality Metrics

### Structure Score (Weight: 25%)

Measures code organization and complexity:

- **Cyclomatic Complexity**: Decision point count (if, while, for, except, comprehensions)
  - Target: Average complexity < 10
  - High complexity (>15) indicates code that's hard to test and maintain

- **Type Hint Coverage**: Percentage of functions with type annotations
  - Target: 80%+ coverage
  - Improves IDE support, catches type errors, serves as documentation

- **Formatting Compliance**: Adherence to black code style
  - Target: 100% compliance
  - Ensures consistent, readable code across the project

**Score Calculation**:
```
structure_score = (
    complexity_score * 0.4 +      # Lower complexity is better
    type_hint_coverage * 0.3 +
    formatting_compliance * 0.3
)
```

### Security Score (Weight: 30%)

Identifies security vulnerabilities using bandit:

- **High Severity**: Critical security issues (20 point penalty each)
  - SQL injection, command injection, unsafe deserialization

- **Medium Severity**: Moderate security concerns (10 point penalty each)
  - Weak cryptography, insecure temp files, hardcoded passwords

- **Low Severity**: Minor security issues (5 point penalty each)
  - Assert usage, exec/eval calls, suspicious imports

**Score Calculation**:
```
penalty = (high * 20) + (medium * 10) + (low * 5)
security_score = max(0, 100 - penalty)
```

### Testing Score (Weight: 25%)

Evaluates test coverage and test count:

- **Test Coverage**: Percentage from coverage.json
  - Target: 80%+ coverage
  - Read from coverage.json in project root

- **Test Count**: Number of test functions vs source files
  - Target: At least 1 test per source file
  - Counts functions starting with `test_`

**Score Calculation**:
```
testing_score = (coverage * 0.7) + (test_ratio * 0.3)
```

### Documentation Score (Weight: 20%)

Measures documentation completeness:

- **Docstring Coverage**: Functions/classes with docstrings
  - Target: 70%+ coverage
  - Includes module, class, and function docstrings

- **Comment Ratio**: Percentage of lines that are comments
  - Target: 10-20% (capped contribution)
  - Too few or too many comments can indicate issues

- **README Quality**: README.md existence and length
  - Target: Comprehensive README (2000+ chars = 100 score)
  - Based on length as proxy for completeness

**Score Calculation**:
```
docs_score = (
    docstring_coverage * 0.5 +
    min(20, comment_ratio * 2) * 0.2 +
    readme_score * 0.3
)
```

### Overall Score

Weighted average of component scores:

```
overall_score = (
    structure_score * 0.25 +
    security_score * 0.30 +
    testing_score * 0.25 +
    docs_score * 0.20
)
```

## CLI Usage

### Basic Quality Check

Run analysis on current project:

```bash
br quality check
```

Output includes:
- Component scores (structure, security, testing, docs)
- Overall score
- Detailed metrics (complexity, coverage, vulnerabilities, etc.)
- Issues and suggestions

### Threshold Enforcement

Set minimum acceptable score:

```bash
br quality check --threshold 85
```

Non-zero exit code if score below threshold.

### Strict Mode

Fail fast with detailed error on threshold violation:

```bash
br quality check --threshold 80 --strict
```

Raises `QualityGateError` with all failures listed.

### Auto-fix (Future)

Automatically fix formatting and other auto-correctable issues:

```bash
br quality check --fix
```

Currently supported:
- Code formatting via black
- Import sorting (future)
- Type hint generation (future)

## Threshold Configuration

### Default Thresholds

```python
DEFAULT_THRESHOLDS = {
    'overall': 80.0,
    'structure': 75.0,
    'security': 90.0,    # Higher bar for security
    'testing': 80.0,
    'docs': 70.0,
}
```

### Custom Thresholds

Via Python API:

```python
from core.code_quality import CodeQualityAnalyzer, QualityGate

analyzer = CodeQualityAnalyzer(project_root)
metrics = analyzer.analyze_project()

# Custom thresholds
gate = QualityGate({
    'overall': 85.0,
    'security': 95.0,
    'testing': 90.0,
})

passed, failures = gate.check(metrics)
if not passed:
    for failure in failures:
        print(f"❌ {failure}")
```

## Integration Examples

### Local Development

Pre-commit hook (.git/hooks/pre-commit):

```bash
#!/bin/bash
br quality check --threshold 75 --strict
```

### CI/CD Pipeline

GitHub Actions (.github/workflows/quality.yml):

```yaml
name: Code Quality

on: [push, pull_request]

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
          pip install -e .
          pip install black bandit pytest pytest-cov

      - name: Run tests with coverage
        run: |
          pytest --cov=. --cov-report=json

      - name: Check code quality
        run: |
          br quality check --threshold 80 --strict
```

### GitLab CI

.gitlab-ci.yml:

```yaml
quality_check:
  stage: test
  script:
    - pip install -e .
    - pip install black bandit pytest pytest-cov
    - pytest --cov=. --cov-report=json
    - br quality check --threshold 80 --strict
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

## Understanding Results

### High Structure Score (75+)

- Low complexity functions
- Good type hint coverage
- Consistent formatting

**Actions**: Maintain current practices

### Low Structure Score (<75)

- High complexity functions
- Missing type hints
- Formatting issues

**Actions**:
- Refactor complex functions (complexity >10)
- Add type hints to function signatures
- Run `black .` to fix formatting

### High Security Score (90+)

- No critical vulnerabilities
- Safe coding practices

**Actions**: Maintain current practices

### Low Security Score (<90)

- Security vulnerabilities detected
- Unsafe patterns used

**Actions**:
- Review bandit output: `bandit -r . -f screen`
- Fix high-severity issues immediately
- Use parameterized queries, secure random, etc.

### High Testing Score (80+)

- Good test coverage
- Adequate test count

**Actions**: Maintain test quality

### Low Testing Score (<80)

- Low coverage
- Missing tests

**Actions**:
- Run `pytest --cov=. --cov-report=html`
- Add tests for uncovered code
- Aim for 80%+ coverage

### High Docs Score (70+)

- Good docstring coverage
- Quality README

**Actions**: Keep docs updated

### Low Docs Score (<70)

- Missing docstrings
- Inadequate README

**Actions**:
- Add docstrings to public APIs
- Enhance README with usage examples
- Document complex algorithms

## Auto-fix Capabilities

### Currently Supported

#### Code Formatting

Automatically format code to black style:

```bash
br quality check --fix
```

Runs: `black .`

### Future Capabilities

#### Import Sorting

```bash
br quality check --fix-imports
```

Will run: `isort .`

#### Type Hint Generation

```bash
br quality check --add-types
```

Will use monkeytype or similar to infer and add type hints.

#### Docstring Generation

```bash
br quality check --add-docs
```

Will generate basic docstrings for undocumented functions.

## Programmatic Usage

### Basic Analysis

```python
from pathlib import Path
from core.code_quality import CodeQualityAnalyzer

analyzer = CodeQualityAnalyzer(Path.cwd())
metrics = analyzer.analyze_project()

print(f"Overall Score: {metrics.overall_score:.1f}")
print(f"Security Score: {metrics.security_score:.1f}")
print(f"Test Coverage: {metrics.test_coverage:.1f}%")
```

### Component Analysis

```python
from core.code_quality import CodeQualityAnalyzer, QualityMetrics

analyzer = CodeQualityAnalyzer(Path.cwd())
analyzer._discover_files()

metrics = QualityMetrics()

# Analyze specific component
structure_score = analyzer.calculate_structure_score(metrics)
print(f"Structure: {structure_score:.1f}")
print(f"Avg Complexity: {metrics.avg_complexity:.1f}")
print(f"Type Hints: {metrics.type_hint_coverage:.1f}%")
```

### Quality Gate

```python
from core.code_quality import QualityGate, QualityGateError

gate = QualityGate({'overall': 85.0})

try:
    gate.enforce(metrics, strict=True)
    print("✅ Quality gate passed!")
except QualityGateError as e:
    print(f"❌ Quality gate failed:\n{e}")
    exit(1)
```

## Best Practices

### Maintain High Quality

1. **Run locally before commit**: `br quality check`
2. **Fix issues immediately**: Don't let quality debt accumulate
3. **Review metrics regularly**: Track trends over time
4. **Set realistic thresholds**: Start at current level, improve gradually
5. **Automate in CI/CD**: Prevent regressions

### Improving Scores

#### Structure

- Extract complex functions into smaller helpers
- Add type hints incrementally
- Run black on save (IDE integration)

#### Security

- Review bandit output carefully
- Use security linters in IDE
- Follow OWASP guidelines
- Keep dependencies updated

#### Testing

- Write tests alongside code
- Use TDD when appropriate
- Target critical paths first
- Aim for 80%+ coverage

#### Documentation

- Add docstrings to public APIs
- Document non-obvious logic
- Keep README current
- Use inline comments sparingly

### Quality Trends

Track quality over time:

```bash
# Save baseline
br quality check > quality_baseline.txt

# After changes, compare
br quality check > quality_current.txt
diff quality_baseline.txt quality_current.txt
```

For automated tracking, integrate with metrics platforms (Prometheus, DataDog, etc.).

## Troubleshooting

### "black not found" warning

Install black:
```bash
pip install black
```

### "bandit not found" warning

Install bandit:
```bash
pip install bandit
```

### "No coverage.json found"

Run tests with coverage first:
```bash
pytest --cov=. --cov-report=json
```

### Low complexity score despite simple code

Check for:
- Deeply nested loops
- Long if-elif chains
- Complex boolean expressions

Refactor into smaller functions.

### Type hints not detected

Ensure proper syntax:
```python
def func(x: int, y: str) -> bool:  # ✅ Detected
    ...

def func(x, y):  # ❌ Not detected
    ...
```

## Related Documentation

- [Gap Analysis](GAP_ANALYSIS.md) - Detect incomplete implementations
- [Testing Guide](../tests/README.md) - Writing effective tests
- [Contributing](../CONTRIBUTING.md) - Code standards and review process
