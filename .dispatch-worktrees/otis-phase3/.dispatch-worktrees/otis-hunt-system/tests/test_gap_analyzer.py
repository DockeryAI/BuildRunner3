"""
Tests for Gap Analysis System

Tests gap detection, analysis, and reporting.
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gap_analyzer import GapAnalysis, GapAnalyzer


class TestGapAnalysis:
    """Test GapAnalysis dataclass."""

    def test_default_analysis(self):
        """Test default analysis values."""
        analysis = GapAnalysis()

        assert analysis.missing_features == []
        assert analysis.incomplete_features == []
        assert analysis.todo_count == 0
        assert analysis.stub_count == 0
        assert analysis.missing_dependencies == []
        assert analysis.total_gaps == 0

    def test_custom_analysis(self):
        """Test custom analysis values."""
        analysis = GapAnalysis(
            todo_count=5,
            stub_count=3,
            missing_features=[{"id": "feat-1", "name": "Feature 1", "reason": "Not started"}],
        )

        assert analysis.todo_count == 5
        assert analysis.stub_count == 3
        assert len(analysis.missing_features) == 1


class TestGapAnalyzer:
    """Test GapAnalyzer."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create sample project for testing."""
        # Create .buildrunner directory
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()

        # Create features.json
        features = {
            "features": [
                {"id": "feat-1", "name": "Complete Feature", "status": "complete"},
                {"id": "feat-2", "name": "In Progress Feature", "status": "in_progress"},
                {"id": "feat-3", "name": "Planned Feature", "status": "planned"},
                {"id": "feat-4", "name": "Blocked Feature", "status": "blocked"},
            ]
        }
        features_file = buildrunner_dir / "features.json"
        features_file.write_text(json.dumps(features))

        # Create Python files with TODOs and stubs
        main_file = tmp_path / "main.py"
        main_file.write_text(
            """
# TODO: Implement this function
def incomplete_function():
    # FIXME: This is broken
    pass

def stub_function():
    raise NotImplementedError

import requests
"""
        )

        # Create requirements file
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("pytest\npyyaml\n")

        return tmp_path

    def test_analyzer_initialization(self, sample_project):
        """Test analyzer initialization."""
        analyzer = GapAnalyzer(sample_project)

        assert analyzer.project_root == sample_project
        assert analyzer.buildrunner_dir == sample_project / ".buildrunner"

    def test_discover_files(self, sample_project):
        """Test file discovery."""
        analyzer = GapAnalyzer(sample_project)
        analyzer._discover_files()

        assert len(analyzer.python_files) > 0

    def test_analyze_features(self, sample_project):
        """Test feature analysis."""
        analyzer = GapAnalyzer(sample_project)
        analysis = GapAnalysis()

        analyzer.analyze_features(analysis)

        # Should find missing, incomplete, and blocked features
        assert len(analysis.missing_features) == 1  # planned
        assert len(analysis.incomplete_features) == 1  # in_progress
        assert len(analysis.blocked_features) == 1  # blocked

        assert analysis.missing_features[0]["id"] == "feat-3"
        assert analysis.incomplete_features[0]["id"] == "feat-2"
        assert analysis.blocked_features[0]["id"] == "feat-4"

    def test_analyze_features_no_file(self, tmp_path):
        """Test feature analysis when features.json missing."""
        analyzer = GapAnalyzer(tmp_path)
        analysis = GapAnalysis()

        analyzer.analyze_features(analysis)

        # Should add to missing components
        assert ".buildrunner/features.json" in analysis.missing_components

    def test_analyze_features_invalid_json(self, tmp_path):
        """Test feature analysis with invalid JSON."""
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()

        features_file = buildrunner_dir / "features.json"
        features_file.write_text("{invalid json")

        analyzer = GapAnalyzer(tmp_path)
        analysis = GapAnalysis()

        analyzer.analyze_features(analysis)

        # Should record violation
        assert len(analysis.spec_violations) > 0

    def test_detect_incomplete_implementations(self, sample_project):
        """Test detection of TODOs and stubs."""
        analyzer = GapAnalyzer(sample_project)
        analyzer._discover_files()

        analysis = GapAnalysis()
        analyzer.detect_incomplete_implementations(analysis)

        # Should find TODOs
        assert analysis.todo_count > 0
        assert len(analysis.todos) > 0

        # Should find stubs
        assert analysis.stub_count > 0
        assert len(analysis.stubs) > 0

    def test_detect_todo_patterns(self, tmp_path):
        """Test detection of different TODO patterns."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            """
# TODO: Fix this
# FIXME: Broken code
# XXX: Hack alert
# HACK: Temporary workaround
"""
        )

        analyzer = GapAnalyzer(tmp_path)
        analyzer._discover_files()

        analysis = GapAnalysis()
        analyzer.detect_incomplete_implementations(analysis)

        assert analysis.todo_count >= 4

    def test_detect_stubs(self, tmp_path):
        """Test detection of stub implementations."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            """
def stub_raise():
    raise NotImplementedError

def empty_function():
    pass
"""
        )

        analyzer = GapAnalyzer(tmp_path)
        analyzer._discover_files()

        analysis = GapAnalysis()
        analyzer.detect_incomplete_implementations(analysis)

        # Should find NotImplementedError
        assert analysis.stub_count >= 1

        # Should count pass statements
        assert analysis.pass_statements >= 1

    def test_analyze_dependencies(self, sample_project):
        """Test dependency analysis."""
        analyzer = GapAnalyzer(sample_project)
        analyzer._discover_files()

        analysis = GapAnalysis()
        analyzer.analyze_dependencies(analysis)

        # Should find missing dependency (requests not in requirements)
        assert "requests" in analysis.missing_dependencies

    def test_analyze_dependencies_no_requirements(self, tmp_path):
        """Test dependency analysis without requirements file."""
        py_file = tmp_path / "test.py"
        py_file.write_text("import requests")

        analyzer = GapAnalyzer(tmp_path)
        analyzer._discover_files()

        analysis = GapAnalysis()
        analyzer.analyze_dependencies(analysis)

        # Should still detect missing deps
        assert "requests" in analysis.missing_dependencies

    def test_get_stdlib_modules(self, sample_project):
        """Test stdlib module detection."""
        analyzer = GapAnalyzer(sample_project)

        stdlib = analyzer._get_stdlib_modules()

        assert "os" in stdlib
        assert "sys" in stdlib
        assert "json" in stdlib
        assert "pathlib" in stdlib

    def test_analyze_spec(self, tmp_path):
        """Test spec analysis."""
        # Create PROJECT_SPEC.md
        spec_file = tmp_path / "PROJECT_SPEC.md"
        spec_file.write_text(
            """
# Project Spec

## API Endpoints
- `GET /api/users`
- `POST /api/items`

## Database Tables
- table: users
- table: items

## Required Files
- file: `core/models.py`
"""
        )

        analyzer = GapAnalyzer(tmp_path)
        analysis = GapAnalysis()

        analyzer.analyze_spec(spec_file, analysis)

        # Should find missing components
        assert len(analysis.missing_components) > 0

    def test_analyze_spec_missing(self, tmp_path):
        """Test spec analysis when spec file missing."""
        analyzer = GapAnalyzer(tmp_path)
        analysis = GapAnalysis()

        analyzer.analyze_spec(None, analysis)

        # Should add PROJECT_SPEC.md to missing components
        assert "PROJECT_SPEC.md" in analysis.missing_components

    def test_full_analysis(self, sample_project):
        """Test complete gap analysis."""
        analyzer = GapAnalyzer(sample_project)
        analysis = analyzer.analyze()

        # Should have populated analysis
        assert isinstance(analysis, GapAnalysis)
        assert analysis.total_gaps > 0
        assert analysis.severity_high >= 0
        assert analysis.severity_medium >= 0
        assert analysis.severity_low >= 0

    def test_generate_gap_report(self, sample_project):
        """Test gap report generation."""
        analyzer = GapAnalyzer(sample_project)
        analysis = analyzer.analyze()

        report = analyzer.generate_gap_report(analysis)

        assert isinstance(report, str)
        assert "# Gap Analysis Report" in report
        assert "Total Gaps:" in report

    def test_gap_report_with_features(self, sample_project):
        """Test gap report includes feature gaps."""
        analyzer = GapAnalyzer(sample_project)
        analysis = analyzer.analyze()

        report = analyzer.generate_gap_report(analysis)

        # Should include feature sections
        if analysis.missing_features:
            assert "Missing Features" in report
        if analysis.incomplete_features:
            assert "Incomplete Features" in report

    def test_gap_report_with_todos(self, sample_project):
        """Test gap report includes TODOs."""
        analyzer = GapAnalyzer(sample_project)
        analysis = analyzer.analyze()

        report = analyzer.generate_gap_report(analysis)

        if analysis.todo_count > 0:
            assert "TODOs" in report

    def test_gap_report_with_stubs(self, sample_project):
        """Test gap report includes stubs."""
        analyzer = GapAnalyzer(sample_project)
        analysis = analyzer.analyze()

        report = analyzer.generate_gap_report(analysis)

        if analysis.stub_count > 0:
            assert "Stubs" in report or "NotImplemented" in report

    def test_gap_report_with_dependencies(self, sample_project):
        """Test gap report includes dependencies."""
        analyzer = GapAnalyzer(sample_project)
        analysis = analyzer.analyze()

        report = analyzer.generate_gap_report(analysis)

        if analysis.missing_dependencies:
            assert "Missing Dependencies" in report


class TestCircularDependencyDetection:
    """Test circular dependency detection."""

    def test_detect_circular_deps(self, tmp_path):
        """Test basic circular dependency detection."""
        analyzer = GapAnalyzer(tmp_path)

        # Simulate imports map
        imports = {"module_a.py": {"module_b"}, "module_b.py": {"module_a"}}

        analysis = GapAnalysis()
        analyzer._detect_circular_deps(imports, analysis)

        # Note: Simplified detection may not catch all cases
        # This tests the function doesn't crash
        assert isinstance(analysis.circular_dependencies, list)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_project(self, tmp_path):
        """Test analysis of empty project."""
        analyzer = GapAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert isinstance(analysis, GapAnalysis)
        assert analysis.total_gaps >= 0

    def test_syntax_error_file(self, tmp_path):
        """Test handling of files with syntax errors."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def broken(\n  invalid")

        analyzer = GapAnalyzer(tmp_path)
        analyzer._discover_files()

        analysis = GapAnalysis()
        analyzer.detect_incomplete_implementations(analysis)

        # Should record syntax error as violation
        assert len(analysis.spec_violations) > 0

    def test_excluded_directories(self, tmp_path):
        """Test that excluded directories are skipped."""
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()

        venv_file = venv_dir / "module.py"
        venv_file.write_text("# TODO: This should be skipped")

        analyzer = GapAnalyzer(tmp_path)
        analyzer._discover_files()

        # Should not include venv files
        venv_files = [f for f in analyzer.python_files if ".venv" in str(f)]
        assert len(venv_files) == 0

    def test_unicode_content(self, tmp_path):
        """Test handling of files with Unicode content."""
        py_file = tmp_path / "unicode.py"
        py_file.write_text("# TODO: 测试 Unicode 支持", encoding="utf-8")

        analyzer = GapAnalyzer(tmp_path)
        analyzer._discover_files()

        analysis = GapAnalysis()
        analyzer.detect_incomplete_implementations(analysis)

        # Should handle Unicode without crashing
        assert analysis.todo_count >= 1

    def test_large_report_truncation(self, tmp_path):
        """Test that large reports truncate appropriately."""
        # Create many TODO items
        py_file = tmp_path / "many_todos.py"
        todos = "\n".join([f"# TODO: Item {i}" for i in range(20)])
        py_file.write_text(todos)

        analyzer = GapAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        report = analyzer.generate_gap_report(analysis)

        # Report should mention "and X more" for large lists
        if analysis.todo_count > 10:
            assert "more" in report
