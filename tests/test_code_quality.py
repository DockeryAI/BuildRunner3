"""
Tests for Code Quality System

Tests quality metrics calculation, analysis, and enforcement.
"""

import sys
import ast
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.code_quality import (
    QualityMetrics,
    FileQualityMetrics,
    CodeQualityAnalyzer,
    QualityGate,
    QualityGateError,
)


class TestQualityMetrics:
    """Test QualityMetrics dataclass."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = QualityMetrics()

        assert metrics.structure_score == 0.0
        assert metrics.security_score == 0.0
        assert metrics.testing_score == 0.0
        assert metrics.docs_score == 0.0
        assert metrics.overall_score == 0.0
        assert metrics.issues == []
        assert metrics.warnings == []

    def test_custom_metrics(self):
        """Test custom metric values."""
        metrics = QualityMetrics(
            structure_score=85.0,
            security_score=95.0,
            testing_score=80.0,
            docs_score=75.0
        )

        assert metrics.structure_score == 85.0
        assert metrics.security_score == 95.0
        assert metrics.testing_score == 80.0
        assert metrics.docs_score == 75.0


class TestFileQualityMetrics:
    """Test FileQualityMetrics dataclass."""

    def test_file_metrics(self):
        """Test file-level metrics."""
        metrics = FileQualityMetrics(
            file_path="test.py",
            complexity=5,
            has_type_hints=True,
            has_docstrings=True,
            line_count=100
        )

        assert metrics.file_path == "test.py"
        assert metrics.complexity == 5
        assert metrics.has_type_hints == True
        assert metrics.has_docstrings == True
        assert metrics.line_count == 100


class TestCodeQualityAnalyzer:
    """Test CodeQualityAnalyzer."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project for testing."""
        # Create a simple Python file
        main_file = tmp_path / "main.py"
        main_file.write_text('''
"""Main module with docstring."""

def simple_function(x: int, y: int) -> int:
    """Add two numbers."""
    if x > 0:
        return x + y
    return y

class TestClass:
    """Test class."""
    pass
''')

        # Create a test file
        test_dir = tmp_path / "tests"
        test_dir.mkdir()

        test_file = test_dir / "test_main.py"
        test_file.write_text('''
def test_simple():
    """Test simple function."""
    assert 1 + 1 == 2

def test_another():
    assert True
''')

        # Create README
        readme = tmp_path / "README.md"
        readme.write_text("# Test Project\n\nThis is a test project.")

        return tmp_path

    def test_analyzer_initialization(self, sample_project):
        """Test analyzer initialization."""
        analyzer = CodeQualityAnalyzer(sample_project)

        assert analyzer.project_root == sample_project
        assert analyzer.python_files == []
        assert analyzer.test_files == []

    def test_discover_files(self, sample_project):
        """Test file discovery."""
        analyzer = CodeQualityAnalyzer(sample_project)
        analyzer._discover_files()

        assert len(analyzer.python_files) > 0
        assert len(analyzer.test_files) > 0

        # Check that main.py is found
        main_files = [f for f in analyzer.python_files if f.name == 'main.py']
        assert len(main_files) == 1

        # Check that test file is found
        test_files = [f for f in analyzer.test_files if 'test_' in f.name]
        assert len(test_files) > 0

    def test_calculate_complexity(self, sample_project):
        """Test complexity calculation."""
        analyzer = CodeQualityAnalyzer(sample_project)

        code = '''
def complex_function(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                pass
    return x
'''
        tree = ast.parse(code)
        func_node = tree.body[0]

        complexity = analyzer._calculate_complexity(func_node)

        assert complexity > 1  # Should have some complexity

    def test_analyze_project(self, sample_project):
        """Test full project analysis."""
        analyzer = CodeQualityAnalyzer(sample_project)

        with patch.object(analyzer, '_check_formatting', return_value=100.0):
            with patch('subprocess.run'):  # Mock security scan
                metrics = analyzer.analyze_project()

        assert metrics.structure_score >= 0
        assert metrics.overall_score >= 0
        assert isinstance(metrics, QualityMetrics)

    def test_structure_score_calculation(self, sample_project):
        """Test structure score calculation."""
        analyzer = CodeQualityAnalyzer(sample_project)
        analyzer._discover_files()

        metrics = QualityMetrics()

        with patch.object(analyzer, '_check_formatting', return_value=100.0):
            score = analyzer.calculate_structure_score(metrics)

        assert 0 <= score <= 100
        assert metrics.avg_complexity >= 0

    def test_check_formatting(self, sample_project):
        """Test formatting check."""
        analyzer = CodeQualityAnalyzer(sample_project)

        with patch('subprocess.run') as mock_run:
            # Mock black returning success
            mock_run.return_value = Mock(returncode=0)

            score = analyzer._check_formatting()

            assert score == 100.0

    def test_check_formatting_black_not_found(self, sample_project):
        """Test formatting check when black not installed."""
        analyzer = CodeQualityAnalyzer(sample_project)

        with patch('subprocess.run', side_effect=FileNotFoundError()):
            score = analyzer._check_formatting()

            # Should return default score
            assert score == 50.0

    def test_security_score_calculation(self, sample_project):
        """Test security score calculation."""
        analyzer = CodeQualityAnalyzer(sample_project)

        metrics = QualityMetrics()

        with patch('subprocess.run') as mock_run:
            # Mock bandit output
            mock_run.return_value = Mock(
                stdout='{"results": [{"issue_severity": "HIGH"}]}',
                returncode=0
            )

            score = analyzer.calculate_security_score(metrics)

            assert 0 <= score <= 100
            assert metrics.vulnerabilities_high >= 0

    def test_security_score_no_bandit(self, sample_project):
        """Test security score when bandit not available."""
        analyzer = CodeQualityAnalyzer(sample_project)

        metrics = QualityMetrics()

        with patch('subprocess.run', side_effect=FileNotFoundError()):
            score = analyzer.calculate_security_score(metrics)

            # Should return neutral score
            assert score == 50.0
            assert len(metrics.warnings) > 0

    def test_testing_score_calculation(self, sample_project):
        """Test testing score calculation."""
        analyzer = CodeQualityAnalyzer(sample_project)
        analyzer._discover_files()

        metrics = QualityMetrics()
        score = analyzer.calculate_testing_score(metrics)

        assert 0 <= score <= 100
        assert metrics.test_count >= 0

    def test_testing_score_with_coverage(self, sample_project):
        """Test testing score with coverage data."""
        analyzer = CodeQualityAnalyzer(sample_project)
        analyzer._discover_files()

        # Create coverage file
        coverage_file = sample_project / "coverage.json"
        coverage_data = {
            "totals": {
                "percent_covered": 85.5
            }
        }
        coverage_file.write_text(json.dumps(coverage_data))

        metrics = QualityMetrics()
        score = analyzer.calculate_testing_score(metrics)

        assert metrics.test_coverage == 85.5
        assert score > 0

    def test_docs_score_calculation(self, sample_project):
        """Test documentation score calculation."""
        analyzer = CodeQualityAnalyzer(sample_project)
        analyzer._discover_files()

        metrics = QualityMetrics()
        score = analyzer.calculate_docs_score(metrics)

        assert 0 <= score <= 100
        assert metrics.docstring_coverage >= 0
        assert metrics.readme_score > 0  # README exists

    def test_docs_score_no_readme(self, tmp_path):
        """Test docs score without README."""
        # Create project without README
        py_file = tmp_path / "test.py"
        py_file.write_text("def foo(): pass")

        analyzer = CodeQualityAnalyzer(tmp_path)
        analyzer._discover_files()

        metrics = QualityMetrics()
        score = analyzer.calculate_docs_score(metrics)

        assert metrics.readme_score == 0
        assert any("README.md" in issue for issue in metrics.issues)

    def test_overall_score_calculation(self, sample_project):
        """Test overall score calculation."""
        analyzer = CodeQualityAnalyzer(sample_project)

        metrics = QualityMetrics(
            structure_score=80.0,
            security_score=90.0,
            testing_score=85.0,
            docs_score=75.0
        )

        overall = analyzer.get_overall_score(metrics)

        assert 0 <= overall <= 100
        # Should be weighted average
        assert overall > 0


class TestQualityGate:
    """Test QualityGate."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        gate = QualityGate()

        assert gate.thresholds['overall'] == 80.0
        assert gate.thresholds['structure'] == 75.0
        assert gate.thresholds['security'] == 90.0
        assert gate.thresholds['testing'] == 80.0
        assert gate.thresholds['docs'] == 70.0

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        gate = QualityGate({'overall': 90.0, 'security': 95.0})

        assert gate.thresholds['overall'] == 90.0
        assert gate.thresholds['security'] == 95.0

    def test_check_passing(self):
        """Test quality gate check passing."""
        gate = QualityGate()

        metrics = QualityMetrics(
            overall_score=85.0,
            structure_score=80.0,
            security_score=95.0,
            testing_score=85.0,
            docs_score=75.0
        )

        passed, failures = gate.check(metrics)

        assert passed == True
        assert len(failures) == 0

    def test_check_failing(self):
        """Test quality gate check failing."""
        gate = QualityGate()

        metrics = QualityMetrics(
            overall_score=70.0,  # Below threshold
            structure_score=80.0,
            security_score=95.0,
            testing_score=85.0,
            docs_score=75.0
        )

        passed, failures = gate.check(metrics)

        assert passed == False
        assert len(failures) > 0
        assert any("Overall score" in f for f in failures)

    def test_check_multiple_failures(self):
        """Test quality gate with multiple failures."""
        gate = QualityGate()

        metrics = QualityMetrics(
            overall_score=70.0,
            structure_score=60.0,  # Below threshold
            security_score=85.0,   # Below threshold
            testing_score=75.0,    # Below threshold
            docs_score=65.0        # Below threshold
        )

        passed, failures = gate.check(metrics)

        assert passed == False
        assert len(failures) >= 4  # Multiple failures

    def test_enforce_passing(self):
        """Test enforce with passing metrics."""
        gate = QualityGate()

        metrics = QualityMetrics(
            overall_score=85.0,
            structure_score=80.0,
            security_score=95.0,
            testing_score=85.0,
            docs_score=75.0
        )

        # Should not raise
        gate.enforce(metrics, strict=True)

    def test_enforce_failing_non_strict(self):
        """Test enforce with failing metrics (non-strict)."""
        gate = QualityGate()

        metrics = QualityMetrics(
            overall_score=70.0,
            structure_score=60.0,
            security_score=85.0,
            testing_score=75.0,
            docs_score=65.0
        )

        # Should not raise in non-strict mode
        gate.enforce(metrics, strict=False)

    def test_enforce_failing_strict(self):
        """Test enforce with failing metrics (strict)."""
        gate = QualityGate()

        metrics = QualityMetrics(
            overall_score=70.0,
            structure_score=60.0,
            security_score=85.0,
            testing_score=75.0,
            docs_score=65.0
        )

        # Should raise in strict mode
        with pytest.raises(QualityGateError):
            gate.enforce(metrics, strict=True)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_project(self, tmp_path):
        """Test analysis of empty project."""
        analyzer = CodeQualityAnalyzer(tmp_path)
        metrics = analyzer.analyze_project()

        # Should still return valid metrics
        assert isinstance(metrics, QualityMetrics)
        assert metrics.overall_score >= 0

    def test_syntax_error_file(self, tmp_path):
        """Test handling of files with syntax errors."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def broken(\n  invalid syntax")

        analyzer = CodeQualityAnalyzer(tmp_path)
        analyzer._discover_files()

        metrics = QualityMetrics()

        # Should not crash
        score = analyzer.calculate_structure_score(metrics)

        assert len(metrics.warnings) > 0

    def test_excluded_directories(self, tmp_path):
        """Test that excluded directories are skipped."""
        # Create venv directory
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()

        venv_file = venv_dir / "module.py"
        venv_file.write_text("def foo(): pass")

        analyzer = CodeQualityAnalyzer(tmp_path)
        analyzer._discover_files()

        # Should not include venv files
        venv_files = [f for f in analyzer.python_files if '.venv' in str(f)]
        assert len(venv_files) == 0
