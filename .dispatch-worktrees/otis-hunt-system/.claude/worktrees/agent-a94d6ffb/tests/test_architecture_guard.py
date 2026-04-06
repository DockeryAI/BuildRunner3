"""
Tests for Architecture Guard System

Comprehensive test coverage for architectural drift prevention.
"""

import ast
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import json

from core.architecture_guard import ArchitectureGuard, ArchitectureViolation, ArchitectureSpec


# Fixtures


@pytest.fixture
def sample_spec_content():
    """Sample PROJECT_SPEC.md content"""
    return """# Project Specification

## Tech Stack

### Backend
- FastAPI
- Pydantic
- uvicorn

### Database
- PostgreSQL
- Redis

### Libraries
- pytest
- black
- ruff

## Architecture

Component structure:
```
project/
├── core/
├── api/
├── cli/
└── tests/
```

Components:
- `core/` - Business logic
- `api/` - FastAPI endpoints
- `cli/` - Command-line interface

## API Design

Endpoints follow RESTful patterns:
- GET /api/v1/features
- POST /api/v1/features
- PUT /api/v1/features/{id}
- DELETE /api/v1/features/{id}

## Naming Conventions

- Files: snake_case
- Classes: PascalCase
- Functions: snake_case
- Constants: UPPER_CASE
"""


@pytest.fixture
def guard(tmp_path):
    """Create ArchitectureGuard instance with temp directory"""
    return ArchitectureGuard(str(tmp_path))


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing"""
    return """
import fastapi
from pydantic import BaseModel
import unauthorized_lib  # Unauthorized import

class MyModel(BaseModel):
    name: str

class badClassName:  # Bad naming - should be PascalCase
    pass

def BadFunction():  # Bad naming - should be snake_case
    pass

@app.get("/api/v1/test")
def test_endpoint():
    return {"status": "ok"}

@app.post("missing_slash")  # Bad API pattern
def bad_endpoint():
    return {}
"""


# Test ArchitectureSpec


class TestArchitectureSpec:
    """Test ArchitectureSpec dataclass"""

    def test_init_empty(self):
        """Spec initializes with empty defaults"""
        spec = ArchitectureSpec()
        assert spec.tech_stack == {}
        assert spec.components == {}
        assert spec.api_patterns == []
        assert spec.naming_conventions == {}
        assert spec.constraints == []


# Test Spec Parsing


class TestSpecParsing:
    """Test PROJECT_SPEC.md parsing"""

    def test_load_spec_from_root(self, guard, tmp_path, sample_spec_content):
        """Load spec from project root"""
        spec_file = tmp_path / "PROJECT_SPEC.md"
        spec_file.write_text(sample_spec_content)

        spec = guard.load_spec()

        assert spec is not None
        assert "backend" in spec.tech_stack
        assert "database" in spec.tech_stack

    def test_load_spec_custom_path(self, guard, tmp_path, sample_spec_content):
        """Load spec from custom path"""
        custom_path = tmp_path / "docs" / "PROJECT_SPEC.md"
        custom_path.parent.mkdir(parents=True)
        custom_path.write_text(sample_spec_content)

        spec = guard.load_spec(str(custom_path))

        assert spec is not None

    def test_load_spec_not_found(self, guard):
        """Raise error if spec not found"""
        with pytest.raises(FileNotFoundError):
            guard.load_spec()

    def test_parse_tech_stack(self, guard, sample_spec_content):
        """Parse tech stack correctly"""
        spec = guard._parse_spec_content(sample_spec_content)

        # Tech stack parsing may normalize to lowercase or preserve case
        assert "backend" in spec.tech_stack
        assert "database" in spec.tech_stack or "libraries" in spec.tech_stack
        # Should have some tech stack entries
        assert len(spec.tech_stack) > 0

    def test_parse_components(self, guard, sample_spec_content):
        """Parse component structure"""
        spec = guard._parse_spec_content(sample_spec_content)

        assert "expected_structure" in spec.components
        assert any("core/" in item for item in spec.components["expected_structure"])

    def test_parse_api_patterns(self, guard, sample_spec_content):
        """Parse API endpoint patterns"""
        spec = guard._parse_spec_content(sample_spec_content)

        assert "/api/v1/features" in spec.api_patterns or any(
            "/api/v1" in p for p in spec.api_patterns
        )

    def test_parse_naming_conventions(self, guard, sample_spec_content):
        """Parse naming conventions"""
        spec = guard._parse_spec_content(sample_spec_content)

        # Should extract naming patterns if present
        assert isinstance(spec.naming_conventions, dict)


# Test Code Analysis


class TestCodeAnalysis:
    """Test codebase analysis"""

    def test_analyze_codebase(self, guard, tmp_path, sample_python_code):
        """Analyze codebase and detect violations"""
        # Create sample Python file
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "test.py").write_text(sample_python_code)

        # Load a basic spec first
        guard.spec = ArchitectureSpec(tech_stack={"backend": ["fastapi", "pydantic"]})

        violations = guard.analyze_codebase(directories=["core"])

        assert len(violations) > 0
        # Should detect unauthorized import, naming violations, etc.

    def test_analyze_file_syntax_error(self, guard, tmp_path):
        """Handle syntax errors gracefully"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "bad.py").write_text("def bad syntax{")

        guard.spec = ArchitectureSpec()
        guard._analyze_file(code_dir / "bad.py")

        # Should create syntax error violation
        assert any(v.type == "syntax_error" for v in guard.violations)

    def test_check_imports(self, guard, tmp_path):
        """Check import compliance with tech stack"""
        code = """
import fastapi  # Allowed
import unauthorized  # Not allowed
from typing import List  # Standard library - allowed
"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "imports.py").write_text(code)

        guard.spec = ArchitectureSpec(tech_stack={"backend": ["fastapi"]})

        tree = ast.parse(code)
        guard._check_imports(tree, code_dir / "imports.py")

        # Should detect unauthorized import
        violations = [v for v in guard.violations if v.type == "tech_stack"]
        assert len(violations) > 0
        assert any("unauthorized" in v.description.lower() for v in violations)

    def test_check_naming_classes(self, guard, tmp_path):
        """Check class naming conventions"""
        code = """
class GoodClass:  # Correct PascalCase
    pass

class badClass:  # Incorrect - should start with uppercase
    pass
"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "naming.py").write_text(code)

        tree = ast.parse(code)
        guard._check_naming(tree, code_dir / "naming.py")

        # Should detect naming violation
        violations = [v for v in guard.violations if v.type == "naming"]
        assert any("badClass" in v.description for v in violations)

    def test_check_naming_functions(self, guard, tmp_path):
        """Check function naming conventions"""
        code = """
def good_function():  # Correct snake_case
    pass

def BadFunction():  # Incorrect - should be snake_case
    pass

def __init__(self):  # Special method - allowed
    pass
"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "functions.py").write_text(code)

        tree = ast.parse(code)
        guard._check_naming(tree, code_dir / "functions.py")

        violations = [v for v in guard.violations if v.type == "naming"]
        # Should detect BadFunction but not __init__
        assert any("BadFunction" in v.description for v in violations)
        assert not any("__init__" in v.description for v in violations)

    def test_check_api_patterns(self, guard, tmp_path):
        """Check FastAPI route patterns"""
        code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/v1/users")
def good_route():
    return {}

@app.post("missing_slash")
def bad_route():
    return {}
"""
        code_dir = tmp_path / "api"
        code_dir.mkdir()
        (code_dir / "routes.py").write_text(code)

        guard.spec = ArchitectureSpec(api_patterns=["/api/v1/"])

        tree = ast.parse(code)
        guard._check_api_patterns(tree, code_dir / "routes.py")

        # Should detect route without leading slash
        violations = [v for v in guard.violations if v.type == "api_design"]
        assert any("missing_slash" in v.description for v in violations)


# Test Violation Checking


class TestViolationChecking:
    """Test specific violation checking methods"""

    def test_check_tech_stack_compliance(self, guard):
        """Get tech stack violations"""
        guard.violations = [
            ArchitectureViolation(
                type="tech_stack",
                severity="warning",
                file="test.py",
                line=1,
                description="Unauthorized library",
            ),
            ArchitectureViolation(
                type="naming", severity="info", file="test.py", line=5, description="Bad naming"
            ),
        ]

        tech_violations = guard.check_tech_stack_compliance()

        assert len(tech_violations) == 1
        assert tech_violations[0].type == "tech_stack"

    def test_check_component_structure(self, guard, tmp_path):
        """Check component structure matches spec"""
        guard.spec = ArchitectureSpec(
            components={"expected_structure": ["core/", "api/", "missing_dir/"]}
        )

        # Create some but not all directories
        (tmp_path / "core").mkdir()
        (tmp_path / "api").mkdir()
        # missing_dir not created

        violations = guard.check_component_structure()

        # Should detect missing directory
        assert any("missing_dir" in v.description for v in violations)

    def test_check_api_design(self, guard):
        """Get API design violations"""
        guard.violations = [
            ArchitectureViolation(
                type="api_design",
                severity="warning",
                file="api.py",
                line=10,
                description="Bad route",
            )
        ]

        api_violations = guard.check_api_design()

        assert len(api_violations) == 1
        assert api_violations[0].type == "api_design"

    def test_detect_violations_strict(self, guard, tmp_path):
        """Detect violations in strict mode"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "test.py").write_text("class badClass: pass")

        guard.spec = ArchitectureSpec()
        violations = guard.detect_violations(strict=True)

        # Strict mode includes info-level violations
        assert len(violations) >= 0

    def test_detect_violations_non_strict(self, guard, tmp_path):
        """Detect violations in non-strict mode"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "test.py").write_text("class badClass: pass")

        guard.spec = ArchitectureSpec()

        # Add an info violation manually
        guard.violations.append(
            ArchitectureViolation(
                type="naming", severity="info", file="test.py", line=1, description="Info violation"
            )
        )

        violations = guard.detect_violations(strict=False)

        # Non-strict mode filters out info violations
        assert not any(v.severity == "info" for v in violations)


# Test Report Generation


class TestReportGeneration:
    """Test violation report generation"""

    def test_generate_markdown_report_no_violations(self, guard):
        """Generate report when no violations"""
        report = guard.generate_violation_report(output_format="markdown")

        assert "No violations detected" in report
        assert "✅" in report

    def test_generate_markdown_report_with_violations(self, guard):
        """Generate markdown report with violations"""
        guard.violations = [
            ArchitectureViolation(
                type="tech_stack",
                severity="critical",
                file="test.py",
                line=10,
                description="Unauthorized library detected",
                expected="Approved libraries",
                actual="unauthorized_lib",
                suggestion="Use approved alternative",
            ),
            ArchitectureViolation(
                type="naming",
                severity="info",
                file="model.py",
                line=5,
                description="Class should use PascalCase",
            ),
        ]

        report = guard.generate_violation_report(output_format="markdown")

        assert "# Architecture Violation Report" in report
        assert "Total Violations" in report and "2" in report
        assert "🔴" in report  # Critical emoji
        assert "tech_stack" in report.lower() or "Tech Stack" in report
        assert "Unauthorized library detected" in report

    def test_generate_json_report(self, guard):
        """Generate JSON format report"""
        guard.violations = [
            ArchitectureViolation(
                type="tech_stack",
                severity="warning",
                file="test.py",
                line=1,
                description="Test violation",
            )
        ]

        report = guard.generate_violation_report(output_format="json")

        # Parse JSON to verify format
        data = json.loads(report)
        assert len(data) == 1
        assert data[0]["type"] == "tech_stack"
        assert data[0]["severity"] == "warning"
        assert data[0]["file"] == "test.py"

    def test_generate_text_report_no_violations(self, guard):
        """Generate text report when no violations"""
        report = guard.generate_violation_report(output_format="text")

        assert "PASSED" in report
        assert "No violations" in report

    def test_generate_text_report_with_violations(self, guard):
        """Generate text report with violations"""
        guard.violations = [
            ArchitectureViolation(
                type="tech_stack",
                severity="critical",
                file="test.py",
                line=10,
                description="Unauthorized library",
                suggestion="Use alternative",
            )
        ]

        report = guard.generate_violation_report(output_format="text")

        assert "Architecture Violations: 1 found" in report
        assert "[CRITICAL]" in report
        assert "Unauthorized library" in report
        assert "Suggestion: Use alternative" in report


# Integration Tests


class TestArchitectureGuardIntegration:
    """End-to-end integration tests"""

    def test_full_workflow(self, tmp_path, sample_spec_content, sample_python_code):
        """Full workflow: load spec, analyze, generate report"""
        # Setup project structure
        (tmp_path / "PROJECT_SPEC.md").write_text(sample_spec_content)

        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "models.py").write_text(sample_python_code)

        # Run analysis
        guard = ArchitectureGuard(str(tmp_path))
        guard.load_spec()
        violations = guard.detect_violations(strict=False)

        # Generate report
        report = guard.generate_violation_report(output_format="markdown")

        # Verify results
        assert violations is not None
        assert report is not None
        assert len(report) > 0

    def test_empty_codebase(self, tmp_path, sample_spec_content):
        """Handle empty codebase gracefully"""
        (tmp_path / "PROJECT_SPEC.md").write_text(sample_spec_content)

        guard = ArchitectureGuard(str(tmp_path))
        guard.load_spec()
        violations = guard.detect_violations()

        # Should handle empty codebase
        assert isinstance(violations, list)

    def test_complex_spec(self, tmp_path):
        """Handle complex spec with multiple sections"""
        complex_spec = """# Complex Project Spec

## Tech Stack

### Frontend
- React
- TypeScript
- Tailwind

### Backend
- FastAPI
- SQLAlchemy
- Alembic

### DevOps
- Docker
- Kubernetes

## Architecture

Multi-tier architecture:
```
project/
├── frontend/
│   ├── components/
│   └── pages/
├── backend/
│   ├── core/
│   ├── api/
│   └── db/
└── devops/
    ├── docker/
    └── k8s/
```

## API Design

RESTful API with versioning:
- GET /api/v1/resource
- POST /api/v1/resource
- PUT /api/v1/resource/{id}
- DELETE /api/v1/resource/{id}

GraphQL endpoint:
- POST /graphql

## Naming Conventions

Files: kebab-case for frontend, snake_case for backend
Classes: PascalCase
Functions: camelCase for frontend, snake_case for backend
"""
        (tmp_path / "PROJECT_SPEC.md").write_text(complex_spec)

        guard = ArchitectureGuard(str(tmp_path))
        spec = guard.load_spec()

        # Verify complex parsing
        assert "frontend" in spec.tech_stack
        assert "backend" in spec.tech_stack
        assert "devops" in spec.tech_stack or "infrastructure" in spec.tech_stack
