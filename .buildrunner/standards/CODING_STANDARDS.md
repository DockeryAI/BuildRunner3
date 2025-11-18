# Universal Coding Standards for BuildRunner 3.0 Projects

Version: 1.0
Last Updated: 2025-11-17

These standards apply to ALL projects using BuildRunner 3.0 governance system. They ensure consistency, maintainability, and AI-friendly codebases.

---

## Table of Contents

1. [Git Workflow](#git-workflow)
2. [Commit Standards](#commit-standards)
3. [Code Quality](#code-quality)
4. [Testing Practices](#testing-practices)
5. [Security Guidelines](#security-guidelines)
6. [Documentation Standards](#documentation-standards)
7. [AI Collaboration Guidelines](#ai-collaboration-guidelines)

---

## Git Workflow

### Branch Naming Convention

```
build/week{N}-{feature-name}     # For feature development
hotfix/{feature-id}-{description} # For urgent fixes
integration/week{N}               # For integration builds
```

**Examples:**
- `build/week1-governance`
- `hotfix/auth-token-expiry`
- `integration/week2`

### Branch Lifecycle

1. **Create worktree** for parallel development:
   ```bash
   git worktree add ../project-feature -b build/week1-feature
   ```

2. **Work in isolation** - Each feature gets its own worktree

3. **Push branch** when ready for review:
   ```bash
   git push origin build/week1-feature
   ```

4. **Create PR** - Never merge to main directly

5. **Cleanup after merge**:
   ```bash
   git worktree remove ../project-feature
   git branch -d build/week1-feature
   ```

---

## Commit Standards

### Semantic Versioning

**Format:** `<type>[(scope)]: <description>`

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code restructuring (no functionality change)
- `test:` - Adding or updating tests
- `docs:` - Documentation only
- `chore:` - Maintenance (dependencies, configs)
- `style:` - Formatting, whitespace (no code change)

**Examples:**
```bash
feat: Add governance checksum verification
fix: Correct state transition validation logic
refactor: Simplify GovernanceManager.load() method
test: Add comprehensive tests for governance_enforcer
docs: Update API documentation for enforcement policies
chore: Upgrade pyyaml to 6.0.3
style: Format code with black
```

### Commit Message Body

For non-trivial commits, add a body:

```
feat: Add governance checksum verification

Implements SHA256 checksum generation and verification for governance.yaml
to prevent unauthorized tampering. Checksums are stored in .governance.sha256
and automatically verified on load().

Addresses requirement: Security-001
```

### AI-Generated Commits

**Always include AI attribution:**

```
feat: Complete feature registry system

Implemented FeatureRegistry class with CRUD operations, JSON serialization,
and version-based progress tracking.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Code Quality

### Python Standards

**Version:** Python 3.11+

**Formatting:**
- Use `black` for code formatting (line length: 100)
- Use `ruff` for linting
- Sort imports with `isort` (if not using ruff)

**Type Hints:**
- Use type hints for all function signatures
- Use `from typing import` for complex types
- Use `Optional[]` for nullable types

**Example:**
```python
from typing import Dict, List, Optional, Any
from pathlib import Path

def validate_config(
    config_path: Path,
    strict: bool = True,
    allowed_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Validate configuration file.

    Args:
        config_path: Path to config file
        strict: Whether to enforce strict validation
        allowed_keys: List of allowed keys (None = allow all)

    Returns:
        Validated configuration dictionary

    Raises:
        ValidationError: If validation fails
    """
    pass
```

### Docstrings

**Style:** Google-style docstrings

**Requirements:**
- All public classes, methods, and functions MUST have docstrings
- Private methods (`_method`) should have docstrings for complex logic
- Include Args, Returns, Raises sections where applicable

**Example:**
```python
class GovernanceManager:
    """
    Manages governance rules for BuildRunner projects.

    Responsibilities:
    - Load and validate governance.yaml configuration
    - Verify checksums to prevent tampering
    - Provide rule query interface
    - Enforce workflow constraints

    Attributes:
        project_root: Root directory of the project
        config: Loaded governance configuration
    """

    def load(self, verify_checksum: bool = True) -> Dict[str, Any]:
        """
        Load governance configuration from YAML.

        Args:
            verify_checksum: Whether to verify checksum before loading

        Returns:
            The loaded governance configuration dictionary

        Raises:
            GovernanceError: If file doesn't exist or can't be loaded
            GovernanceChecksumError: If checksum verification fails
        """
        pass
```

### Error Handling

**Create specific exception classes:**
```python
class GovernanceError(Exception):
    """Base exception for governance-related errors."""
    pass

class GovernanceValidationError(GovernanceError):
    """Raised when governance configuration validation fails."""
    pass
```

**Use context managers:**
```python
with open(config_file, 'r') as f:
    data = yaml.safe_load(f)
```

**Fail fast with clear messages:**
```python
if not self.config_file.exists():
    raise GovernanceError(
        f"Governance config not found: {self.config_file}. "
        f"Run 'br init' to initialize governance."
    )
```

### Code Organization

**File structure:**
```
project/
├── core/               # Core business logic
│   ├── __init__.py
│   ├── governance.py
│   └── governance_enforcer.py
├── cli/                # Command-line interface
├── api/                # API endpoints
├── tests/              # Test files (mirrors src structure)
│   ├── test_governance.py
│   └── test_governance_enforcer.py
├── docs/               # Documentation
└── .buildrunner/       # BuildRunner governance files
```

---

## Testing Practices

### Coverage Requirements

- **Minimum:** 90% coverage for core modules
- **CLI/API:** 85% coverage minimum
- **Integration:** 80% coverage minimum

### Test Structure

**Use pytest** for all testing:

```python
import pytest
from core.governance import GovernanceManager, GovernanceError

class TestGovernanceManager:
    """Test suite for GovernanceManager class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir

    def test_load_missing_file(self, temp_project):
        """Test that loading raises error when file doesn't exist."""
        gm = GovernanceManager(temp_project)

        with pytest.raises(GovernanceError, match="Governance config not found"):
            gm.load()

    def test_checksum_verification(self, temp_project):
        """Test checksum generation and verification."""
        gm = GovernanceManager(temp_project)
        # Setup...
        checksum = gm.generate_checksum()
        assert len(checksum) == 64  # SHA256 hex length
        assert gm.verify_checksum() is True
```

### Test Naming

- Test files: `test_{module_name}.py`
- Test classes: `Test{ClassName}`
- Test methods: `test_{what_is_being_tested}_{expected_behavior}`

**Examples:**
- `test_load_success`
- `test_load_missing_file`
- `test_validate_invalid_structure`
- `test_checksum_mismatch_raises_error`

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov-report=term-missing

# Run specific test
pytest tests/test_governance.py::TestGovernanceManager::test_load_success

# Run with verbose output
pytest -v
```

---

## Security Guidelines

### Input Validation

**Always validate user input:**
```python
def load_feature_id(feature_id: str) -> str:
    """Validate and sanitize feature ID."""
    if not re.match(r'^[a-z0-9-]+$', feature_id):
        raise ValueError(f"Invalid feature ID: {feature_id}")
    return feature_id
```

### File Operations

**Use pathlib and validate paths:**
```python
from pathlib import Path

def read_config(config_path: Path) -> dict:
    """Read config file safely."""
    # Resolve to absolute path
    config_path = config_path.resolve()

    # Ensure it's within project root
    if not config_path.is_relative_to(self.project_root):
        raise SecurityError("Path outside project root")

    # Check file exists and is file
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    return yaml.safe_load(config_path.read_text())
```

### Secrets Management

**NEVER commit secrets:**
- Use `.env` files (gitignored)
- Use environment variables
- Use secret management tools (AWS Secrets Manager, etc.)

**Check for secrets in pre-commit:**
```python
SENSITIVE_PATTERNS = [
    r'api[_-]?key',
    r'password',
    r'secret',
    r'token',
    r'-----BEGIN .* PRIVATE KEY-----',
]
```

### Dependency Management

**Pin versions in production:**
```toml
[project]
dependencies = [
    "pyyaml==6.0.3",      # Exact version
    "GitPython>=3.1.0",   # Minimum version
]
```

**Audit dependencies:**
```bash
pip audit
safety check
```

---

## Documentation Standards

### README.md

**Every project MUST have:**
1. Project description
2. Installation instructions
3. Quick start guide
4. Usage examples
5. Development setup
6. Contributing guidelines

### API Documentation

**Use docstrings + auto-generation:**
- FastAPI: Auto-generates OpenAPI docs
- CLI: Use Click/Typer auto-help

### Architecture Documentation

**Maintain `.buildrunner/context/architecture.md`:**
```markdown
# Project Architecture

## Overview
Brief description of system architecture

## Components
- Core: Business logic
- API: RESTful endpoints
- CLI: Command-line interface

## Data Flow
[Diagram or description]

## Key Design Decisions
1. Why we chose X over Y
2. Trade-offs and rationale
```

---

## AI Collaboration Guidelines

### Context Management

**Maintain AI context files:**
```
.buildrunner/
├── CLAUDE.md              # Persistent AI memory
└── context/
    ├── architecture.md    # System architecture
    ├── current-work.md    # Current focus
    ├── blockers.md        # Known issues
    └── test-results.md    # Latest test output
```

### AI-Friendly Code

**Write clear, self-documenting code:**
- Use descriptive variable names
- Keep functions focused and small
- Add comments for complex logic
- Use type hints everywhere

**Example:**
```python
# ❌ Bad - unclear, no types, no docs
def proc(d, v):
    if v:
        return [x for x in d if x['s'] == 'c']
    return []

# ✅ Good - clear, typed, documented
def get_completed_features(
    features: List[Dict[str, Any]],
    validate: bool = True
) -> List[Dict[str, Any]]:
    """
    Filter features to return only completed ones.

    Args:
        features: List of feature dictionaries
        validate: Whether to validate feature structure

    Returns:
        List of features with status='complete'
    """
    if not validate:
        return []

    return [
        feature for feature in features
        if feature.get('status') == 'complete'
    ]
```

### Prompts for AI

**When asking AI for help, provide:**
1. Context (what you're building)
2. Current state (what exists)
3. Goal (what you want)
4. Constraints (requirements, limits)

**Example:**
```
Context: Building governance system for BuildRunner 3.0
Current: We have GovernanceManager that loads YAML configs
Goal: Add a method to check if a feature can transition states
Constraints: Must validate against governance.yaml rules,
             must return clear error messages if transition invalid
```

---

## Enforcement

These standards are enforced by:
- **Pre-commit hooks** - Format, lint, validate
- **Pre-push hooks** - Run tests, check coverage
- **PR checks** - GitHub Actions CI/CD
- **Governance system** - BuildRunner enforcement engine

**Override at your own risk.** Standards exist to prevent the inevitable 3 AM debugging session caused by "it was just a quick fix."

---

## Version History

- **1.0** (2025-11-17) - Initial standards for BuildRunner 3.0

---

**Remember:** Standards are like backups - everyone agrees they're important, but nobody wants to deal with them until it's too late.

Now go write some damn good code.
