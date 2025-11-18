"""
Code Quality System for BuildRunner 3.0

Analyzes codebase quality across multiple dimensions:
- Structure: complexity, formatting, type hints
- Security: vulnerability scanning, unsafe patterns
- Testing: coverage, test count, test quality
- Documentation: docstrings, README, comments
"""

import ast
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re

from core.security import SecretDetector, SQLInjectionDetector


@dataclass
class QualityMetrics:
    """Quality metrics for a codebase."""

    # Structure metrics
    structure_score: float = 0.0
    avg_complexity: float = 0.0
    type_hint_coverage: float = 0.0
    formatting_compliance: float = 0.0

    # Security metrics
    security_score: float = 0.0
    vulnerabilities_high: int = 0
    vulnerabilities_medium: int = 0
    vulnerabilities_low: int = 0

    # Testing metrics
    testing_score: float = 0.0
    test_coverage: float = 0.0
    test_count: int = 0
    assertions_count: int = 0

    # Documentation metrics
    docs_score: float = 0.0
    docstring_coverage: float = 0.0
    comment_ratio: float = 0.0
    readme_score: float = 0.0

    # Overall
    overall_score: float = 0.0

    # Details
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class FileQualityMetrics:
    """Quality metrics for a single file."""

    file_path: str
    complexity: int = 0
    has_type_hints: bool = False
    has_docstrings: bool = False
    line_count: int = 0
    comment_count: int = 0
    function_count: int = 0
    class_count: int = 0
    issues: List[str] = field(default_factory=list)


class CodeQualityAnalyzer:
    """Analyzes code quality across multiple dimensions."""

    # Weights for overall score calculation
    WEIGHTS = {
        'structure': 0.25,
        'security': 0.30,
        'testing': 0.25,
        'docs': 0.20,
    }

    # Complexity thresholds
    COMPLEXITY_THRESHOLDS = {
        'low': 5,
        'medium': 10,
        'high': 15,
    }

    def __init__(self, project_root: Path):
        """
        Initialize analyzer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.python_files: List[Path] = []
        self.test_files: List[Path] = []

    def analyze_project(self) -> QualityMetrics:
        """
        Analyze entire project.

        Returns:
            QualityMetrics object with all scores
        """
        # Find Python files
        self._discover_files()

        metrics = QualityMetrics()

        # Calculate each component
        metrics.structure_score = self.calculate_structure_score(metrics)
        metrics.security_score = self.calculate_security_score(metrics)
        metrics.testing_score = self.calculate_testing_score(metrics)
        metrics.docs_score = self.calculate_docs_score(metrics)

        # Calculate overall score
        metrics.overall_score = self.get_overall_score(metrics)

        return metrics

    def _discover_files(self):
        """Discover Python files in the project."""
        self.python_files = []
        self.test_files = []

        # Exclude common non-source directories
        exclude_dirs = {'.venv', 'venv', '__pycache__', '.git', 'node_modules', '.pytest_cache'}

        for py_file in self.project_root.rglob('*.py'):
            # Skip if in excluded directory
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue

            # Only check direct parent folder name 'tests' or filename starting with 'test_'
            parent_name = py_file.parent.name
            if py_file.stem.startswith('test_') or parent_name == 'tests':
                self.test_files.append(py_file)
            else:
                self.python_files.append(py_file)

    def calculate_structure_score(self, metrics: QualityMetrics) -> float:
        """
        Calculate structure quality score.

        Considers:
        - Cyclomatic complexity
        - Code formatting (via black/ruff)
        - Type hint coverage

        Args:
            metrics: Metrics object to populate

        Returns:
            Structure score (0-100)
        """
        if not self.python_files:
            return 0.0

        # Analyze complexity
        complexities = []
        type_hint_counts = {'with': 0, 'without': 0}

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    code = f.read()

                # Parse AST
                tree = ast.parse(code)

                # Calculate complexity for functions
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        complexity = self._calculate_complexity(node)
                        complexities.append(complexity)

                        # Check type hints
                        has_hints = (
                            node.returns is not None or
                            any(arg.annotation is not None for arg in node.args.args)
                        )
                        if has_hints:
                            type_hint_counts['with'] += 1
                        else:
                            type_hint_counts['without'] += 1

            except Exception as e:
                metrics.warnings.append(f"Failed to analyze {py_file}: {str(e)}")

        # Calculate average complexity
        if complexities:
            metrics.avg_complexity = sum(complexities) / len(complexities)

        # Calculate type hint coverage
        total_functions = type_hint_counts['with'] + type_hint_counts['without']
        if total_functions > 0:
            metrics.type_hint_coverage = (type_hint_counts['with'] / total_functions) * 100

        # Check formatting compliance
        metrics.formatting_compliance = self._check_formatting()

        # Calculate structure score
        # Lower complexity is better
        complexity_score = max(0, 100 - (metrics.avg_complexity * 5))

        # Combine scores
        structure_score = (
            complexity_score * 0.4 +
            metrics.type_hint_coverage * 0.3 +
            metrics.formatting_compliance * 0.3
        )

        return min(100.0, max(0.0, structure_score))

    def _calculate_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity for a function.

        Simplified complexity calculation based on decision points.

        Args:
            node: AST node (FunctionDef or AsyncFunctionDef)

        Returns:
            Complexity score
        """
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1

        return complexity

    def _check_formatting(self) -> float:
        """
        Check code formatting compliance.

        Uses black to check if code is properly formatted.

        Returns:
            Formatting compliance percentage (0-100)
        """
        try:
            # Check if black is available
            result = subprocess.run(
                ['black', '--check', '--quiet', str(self.project_root)],
                capture_output=True,
                timeout=30
            )

            # black returns 0 if all files are formatted correctly
            if result.returncode == 0:
                return 100.0
            else:
                # Estimate compliance based on output
                # This is a simplified heuristic
                return 70.0

        except (FileNotFoundError, subprocess.TimeoutExpired):
            # black not installed or timeout
            return 50.0  # Assume moderate compliance

    def calculate_security_score(self, metrics: QualityMetrics) -> float:
        """
        Calculate security quality score.

        Tier 1 Checks (non-negotiable):
        - Secret detection (API keys, tokens, credentials)
        - SQL injection vulnerabilities

        Additional Checks:
        - Bandit security scanner (general vulnerabilities)

        Args:
            metrics: Metrics object to populate

        Returns:
            Security score (0-100)
        """
        # Tier 1: Secret Detection
        try:
            secret_detector = SecretDetector(self.project_root)
            secret_results = secret_detector.scan_directory(str(self.project_root))

            secret_count = sum(len(matches) for matches in secret_results.values())
            if secret_count > 0:
                metrics.vulnerabilities_high += secret_count
                metrics.issues.append(
                    f"Found {secret_count} exposed secret(s) in codebase - "
                    f"run 'br security check' for details"
                )
        except Exception as e:
            metrics.warnings.append(f"Secret detection failed: {str(e)}")

        # Tier 1: SQL Injection Detection
        try:
            sql_detector = SQLInjectionDetector(self.project_root)
            sql_results = sql_detector.scan_directory(str(self.project_root))

            for matches in sql_results.values():
                for match in matches:
                    if match.severity == 'high':
                        metrics.vulnerabilities_high += 1
                    elif match.severity == 'medium':
                        metrics.vulnerabilities_medium += 1
                    else:
                        metrics.vulnerabilities_low += 1

            sql_count = sum(len(matches) for matches in sql_results.values())
            if sql_count > 0:
                metrics.issues.append(
                    f"Found {sql_count} SQL injection risk(s) - "
                    f"run 'br security check' for details"
                )
        except Exception as e:
            metrics.warnings.append(f"SQL injection detection failed: {str(e)}")

        # Additional: Bandit scanner
        try:
            result = subprocess.run(
                ['bandit', '-r', str(self.project_root), '-f', 'json', '-q'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.stdout:
                import json
                report = json.loads(result.stdout)

                # Count vulnerabilities by severity
                for issue in report.get('results', []):
                    severity = issue.get('issue_severity', 'LOW').upper()
                    if severity == 'HIGH':
                        metrics.vulnerabilities_high += 1
                    elif severity == 'MEDIUM':
                        metrics.vulnerabilities_medium += 1
                    else:
                        metrics.vulnerabilities_low += 1

        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            metrics.warnings.append(f"Bandit scan skipped: {str(e)}")

        # Calculate security score
        # Penalize high-severity issues more (Tier 1 checks are critical)
        penalty = (
            metrics.vulnerabilities_high * 20 +
            metrics.vulnerabilities_medium * 10 +
            metrics.vulnerabilities_low * 5
        )

        security_score = max(0, 100 - penalty)

        if metrics.vulnerabilities_high > 0:
            metrics.issues.append(
                f"Total: {metrics.vulnerabilities_high} high-severity security issues detected"
            )

        return security_score

    def calculate_testing_score(self, metrics: QualityMetrics) -> float:
        """
        Calculate testing quality score.

        Considers:
        - Test coverage percentage
        - Number of tests
        - Number of assertions

        Args:
            metrics: Metrics object to populate

        Returns:
            Testing score (0-100)
        """
        # Check for coverage report
        coverage_file = self.project_root / 'coverage.json'

        if coverage_file.exists():
            try:
                import json
                with open(coverage_file) as f:
                    coverage_data = json.load(f)

                # Extract coverage percentage
                totals = coverage_data.get('totals', {})
                metrics.test_coverage = totals.get('percent_covered', 0.0)

            except Exception as e:
                metrics.warnings.append(f"Failed to read coverage data: {str(e)}")

        # Count tests and assertions
        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    code = f.read()

                tree = ast.parse(code)

                for node in ast.walk(tree):
                    # Count test functions
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        metrics.test_count += 1

                    # Count assertions
                    if isinstance(node, ast.Assert):
                        metrics.assertions_count += 1

                    # Count pytest-style assertions (assert calls)
                    if isinstance(node, ast.Compare):
                        metrics.assertions_count += 1

            except Exception as e:
                metrics.warnings.append(f"Failed to analyze test file {test_file}: {str(e)}")

        # Calculate testing score
        coverage_score = metrics.test_coverage

        # Bonus for having tests
        test_score = min(100, (metrics.test_count / max(1, len(self.python_files))) * 100)

        # Combine scores
        testing_score = (coverage_score * 0.7 + test_score * 0.3)

        if metrics.test_coverage < 80:
            metrics.suggestions.append(f"Test coverage is {metrics.test_coverage:.1f}% (target: 80%+)")

        return min(100.0, max(0.0, testing_score))

    def calculate_docs_score(self, metrics: QualityMetrics) -> float:
        """
        Calculate documentation quality score.

        Considers:
        - Docstring coverage
        - Comment ratio
        - README quality

        Args:
            metrics: Metrics object to populate

        Returns:
            Documentation score (0-100)
        """
        docstring_counts = {'with': 0, 'without': 0}
        total_lines = 0
        comment_lines = 0

        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                    lines = code.split('\n')

                total_lines += len(lines)

                # Count comment lines
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        comment_lines += 1

                # Parse AST for docstrings
                tree = ast.parse(code)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        docstring = ast.get_docstring(node)
                        if docstring:
                            docstring_counts['with'] += 1
                        else:
                            docstring_counts['without'] += 1

            except Exception as e:
                metrics.warnings.append(f"Failed to analyze docs in {py_file}: {str(e)}")

        # Calculate docstring coverage
        total_documented = docstring_counts['with'] + docstring_counts['without']
        if total_documented > 0:
            metrics.docstring_coverage = (docstring_counts['with'] / total_documented) * 100

        # Calculate comment ratio
        if total_lines > 0:
            metrics.comment_ratio = (comment_lines / total_lines) * 100

        # Check README
        readme_path = self.project_root / 'README.md'
        if readme_path.exists():
            try:
                readme_content = readme_path.read_text()
                # Simple scoring based on length and sections
                metrics.readme_score = min(100, len(readme_content) / 20)  # 2000 chars = 100 score
            except Exception:
                metrics.readme_score = 0
        else:
            metrics.readme_score = 0
            metrics.issues.append("No README.md found")

        # Calculate docs score
        docs_score = (
            metrics.docstring_coverage * 0.5 +
            min(20, metrics.comment_ratio * 2) * 0.2 +  # Cap comment contribution
            metrics.readme_score * 0.3
        )

        if metrics.docstring_coverage < 70:
            metrics.suggestions.append(f"Docstring coverage is {metrics.docstring_coverage:.1f}% (target: 70%+)")

        return min(100.0, max(0.0, docs_score))

    def get_overall_score(self, metrics: QualityMetrics) -> float:
        """
        Calculate weighted overall quality score.

        Args:
            metrics: QualityMetrics with component scores

        Returns:
            Overall quality score (0-100)
        """
        overall = (
            metrics.structure_score * self.WEIGHTS['structure'] +
            metrics.security_score * self.WEIGHTS['security'] +
            metrics.testing_score * self.WEIGHTS['testing'] +
            metrics.docs_score * self.WEIGHTS['docs']
        )

        return min(100.0, max(0.0, overall))


class QualityGate:
    """Enforces quality thresholds."""

    DEFAULT_THRESHOLDS = {
        'overall': 80.0,
        'structure': 75.0,
        'security': 90.0,
        'testing': 80.0,
        'docs': 70.0,
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize quality gate.

        Args:
            thresholds: Custom thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()

    def check(self, metrics: QualityMetrics) -> Tuple[bool, List[str]]:
        """
        Check if metrics meet quality thresholds.

        Args:
            metrics: Quality metrics to check

        Returns:
            Tuple of (passed, list of failures)
        """
        failures = []

        # Check overall score
        if metrics.overall_score < self.thresholds['overall']:
            failures.append(
                f"Overall score {metrics.overall_score:.1f} < {self.thresholds['overall']}"
            )

        # Check component scores
        if metrics.structure_score < self.thresholds['structure']:
            failures.append(
                f"Structure score {metrics.structure_score:.1f} < {self.thresholds['structure']}"
            )

        if metrics.security_score < self.thresholds['security']:
            failures.append(
                f"Security score {metrics.security_score:.1f} < {self.thresholds['security']}"
            )

        if metrics.testing_score < self.thresholds['testing']:
            failures.append(
                f"Testing score {metrics.testing_score:.1f} < {self.thresholds['testing']}"
            )

        if metrics.docs_score < self.thresholds['docs']:
            failures.append(
                f"Documentation score {metrics.docs_score:.1f} < {self.thresholds['docs']}"
            )

        passed = len(failures) == 0
        return (passed, failures)

    def enforce(self, metrics: QualityMetrics, strict: bool = False):
        """
        Enforce quality gate.

        Args:
            metrics: Quality metrics to check
            strict: If True, raise exception on failure

        Raises:
            QualityGateError: If strict=True and quality gate fails
        """
        passed, failures = self.check(metrics)

        if not passed and strict:
            raise QualityGateError(f"Quality gate failed:\n" + "\n".join(f"  - {f}" for f in failures))


class QualityGateError(Exception):
    """Raised when quality gate enforcement fails."""
    pass
