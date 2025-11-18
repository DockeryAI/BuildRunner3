"""
Performance Analyzer - Detect performance issues and complexity

Analyzes code for:
- Cyclomatic complexity (using radon)
- N+1 query patterns
- Memory leak indicators
- Big-O complexity analysis
- Performance anti-patterns
"""
import ast
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from radon.complexity import cc_visit, cc_rank
from radon.metrics import h_visit, mi_visit


@dataclass
class ComplexityIssue:
    """Represents a complexity issue"""
    issue_type: str
    location: str
    severity: str  # 'high', 'medium', 'low'
    description: str
    metric_value: Optional[float] = None
    recommendation: str = ""


class PerformanceAnalyzer:
    """
    Analyze code for performance issues and complexity

    Features:
    - Cyclomatic complexity analysis (using radon)
    - N+1 query detection
    - Memory leak pattern detection
    - Big-O complexity hints
    - Performance anti-pattern detection
    """

    # Complexity thresholds
    COMPLEXITY_THRESHOLDS = {
        'A': (1, 5, 'low'),      # Simple
        'B': (6, 10, 'low'),     # Well structured
        'C': (11, 20, 'medium'), # Complex
        'D': (21, 30, 'high'),   # Too complex
        'F': (31, 999, 'high')   # Extremely complex
    }

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize PerformanceAnalyzer

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Comprehensive performance analysis of a file

        Args:
            file_path: Path to file to analyze

        Returns:
            Dict with:
                - complexity_issues: List of complexity problems
                - n_plus_one_queries: List of potential N+1 queries
                - memory_leaks: List of memory leak indicators
                - big_o_warnings: List of Big-O complexity warnings
                - performance_score: Score 0-100
                - recommendations: List of recommendations
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file
        try:
            code = file_path.read_text()
        except Exception as e:
            return self._error_result(f"Failed to read file: {e}")

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return self._error_result(f"Syntax error: {e}")

        # Run analyses
        complexity_issues = self.analyze_complexity(code, file_path.name)
        n_plus_one = self.detect_n_plus_one_queries(tree)
        memory_leaks = self.detect_memory_leaks(tree, code)
        big_o_warnings = self.analyze_big_o(tree)

        # Calculate performance score
        performance_score = self.calculate_performance_score(
            complexity_issues, n_plus_one, memory_leaks, big_o_warnings
        )

        # Generate recommendations
        recommendations = self.generate_recommendations(
            complexity_issues, n_plus_one, memory_leaks, big_o_warnings
        )

        return {
            "complexity_issues": [vars(i) for i in complexity_issues],
            "n_plus_one_queries": [vars(i) for i in n_plus_one],
            "memory_leaks": [vars(i) for i in memory_leaks],
            "big_o_warnings": [vars(i) for i in big_o_warnings],
            "performance_score": performance_score,
            "recommendations": recommendations
        }

    def analyze_complexity(self, code: str, filename: str) -> List[ComplexityIssue]:
        """
        Analyze cyclomatic complexity using radon

        Args:
            code: Source code
            filename: Name of file

        Returns:
            List of complexity issues
        """
        issues = []

        try:
            # Get complexity metrics
            complexity_results = cc_visit(code)

            for result in complexity_results:
                rank = cc_rank(result.complexity)
                _, _, severity = self.COMPLEXITY_THRESHOLDS.get(rank, (0, 0, 'low'))

                if rank in ['C', 'D', 'F']:  # Only report complex functions
                    issues.append(ComplexityIssue(
                        issue_type='high_complexity',
                        location=f"{result.name} (line {result.lineno})",
                        severity=severity,
                        description=f"Cyclomatic complexity of {result.complexity} (rank {rank})",
                        metric_value=float(result.complexity),
                        recommendation=self._get_complexity_recommendation(rank, result.complexity)
                    ))

        except Exception:
            # Radon analysis failed, skip
            pass

        return issues

    def detect_n_plus_one_queries(self, tree: ast.AST) -> List[ComplexityIssue]:
        """
        Detect potential N+1 query patterns

        Args:
            tree: AST of the code

        Returns:
            List of N+1 query issues
        """
        issues = []

        # Look for loops containing database queries
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check if loop body contains query-like calls
                for child in ast.walk(node):
                    if self._is_database_query(child):
                        issues.append(ComplexityIssue(
                            issue_type='n_plus_one_query',
                            location=f"Line {node.lineno}",
                            severity='high',
                            description="Potential N+1 query: database query inside loop",
                            recommendation="Consider using bulk queries or eager loading"
                        ))
                        break  # One issue per loop

        return issues

    def detect_memory_leaks(self, tree: ast.AST, code: str) -> List[ComplexityIssue]:
        """
        Detect potential memory leak patterns

        Args:
            tree: AST of the code
            code: Source code

        Returns:
            List of memory leak indicators
        """
        issues = []

        # Check for global mutable structures
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check if assigning to global list/dict without clearing
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Check if it's a list or dict append/update in a function
                        if self._is_potential_memory_leak(node, tree):
                            issues.append(ComplexityIssue(
                                issue_type='memory_leak',
                                location=f"Line {node.lineno}",
                                severity='medium',
                                description="Potential memory leak: growing global collection",
                                recommendation="Consider clearing collection or using local scope"
                            ))

        # Check for unclosed resources (file handles, connections)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if self._is_resource_open(node) and not self._has_close_or_with(node, tree):
                    issues.append(ComplexityIssue(
                        issue_type='unclosed_resource',
                        location=f"Line {node.lineno}",
                        severity='high',
                        description="Resource opened but not explicitly closed",
                        recommendation="Use context manager (with statement) for resource management"
                    ))

        return issues

    def analyze_big_o(self, tree: ast.AST) -> List[ComplexityIssue]:
        """
        Analyze Big-O complexity patterns

        Args:
            tree: AST of the code

        Returns:
            List of Big-O warnings
        """
        issues = []

        # Detect nested loops (O(n²) or worse)
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                nested_loops = self._count_nested_loops(node)

                if nested_loops >= 1:
                    complexity = f"O(n^{nested_loops + 1})"
                    issues.append(ComplexityIssue(
                        issue_type='high_time_complexity',
                        location=f"Line {node.lineno}",
                        severity='medium' if nested_loops == 1 else 'high',
                        description=f"Nested loops detected: {complexity} time complexity",
                        recommendation="Consider optimizing with hash maps or better algorithm"
                    ))

        return issues

    def calculate_performance_score(
        self,
        complexity_issues: List[ComplexityIssue],
        n_plus_one: List[ComplexityIssue],
        memory_leaks: List[ComplexityIssue],
        big_o_warnings: List[ComplexityIssue]
    ) -> int:
        """
        Calculate overall performance score

        Args:
            complexity_issues: Complexity problems
            n_plus_one: N+1 query issues
            memory_leaks: Memory leak indicators
            big_o_warnings: Big-O warnings

        Returns:
            Score from 0-100
        """
        score = 100

        # Penalties
        score -= len([i for i in complexity_issues if i.severity == 'high']) * 15
        score -= len([i for i in complexity_issues if i.severity == 'medium']) * 8
        score -= len(n_plus_one) * 20  # N+1 queries are serious
        score -= len([i for i in memory_leaks if i.severity == 'high']) * 18
        score -= len([i for i in memory_leaks if i.severity == 'medium']) * 10
        score -= len([i for i in big_o_warnings if i.severity == 'high']) * 12
        score -= len([i for i in big_o_warnings if i.severity == 'medium']) * 6

        return max(0, min(100, score))

    def generate_recommendations(
        self,
        complexity_issues: List[ComplexityIssue],
        n_plus_one: List[ComplexityIssue],
        memory_leaks: List[ComplexityIssue],
        big_o_warnings: List[ComplexityIssue]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Complexity recommendations
        if complexity_issues:
            high_complexity = [i for i in complexity_issues if i.severity == 'high']
            if high_complexity:
                recommendations.append(
                    f"Refactor {len(high_complexity)} function(s) with high cyclomatic complexity"
                )

        # N+1 query recommendations
        if n_plus_one:
            recommendations.append(
                f"Fix {len(n_plus_one)} potential N+1 query issue(s) using bulk operations"
            )

        # Memory leak recommendations
        if memory_leaks:
            recommendations.append(
                f"Address {len(memory_leaks)} potential memory leak(s)"
            )

        # Big-O recommendations
        if big_o_warnings:
            high_complexity_algo = [w for w in big_o_warnings if w.severity == 'high']
            if high_complexity_algo:
                recommendations.append(
                    f"Optimize {len(high_complexity_algo)} algorithm(s) with poor time complexity"
                )

        if not recommendations:
            recommendations.append("Code shows good performance characteristics")

        return recommendations

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Return error result"""
        return {
            "complexity_issues": [],
            "n_plus_one_queries": [],
            "memory_leaks": [],
            "big_o_warnings": [],
            "performance_score": 0,
            "recommendations": [error_msg]
        }

    def _get_complexity_recommendation(self, rank: str, complexity: int) -> str:
        """Get recommendation for complexity level"""
        if rank == 'F':
            return f"Extremely complex ({complexity}). Break into smaller functions immediately."
        elif rank == 'D':
            return f"Too complex ({complexity}). Consider refactoring into smaller, focused functions."
        elif rank == 'C':
            return f"Complex ({complexity}). Look for opportunities to simplify logic."
        return ""

    def _is_database_query(self, node: ast.AST) -> bool:
        """Check if node looks like a database query"""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr.lower()
                # Common ORM/query methods
                if any(keyword in method_name for keyword in [
                    'query', 'filter', 'get', 'find', 'select', 'execute', 'fetch'
                ]):
                    return True
        return False

    def _is_potential_memory_leak(self, node: ast.Assign, tree: ast.AST) -> bool:
        """Check if assignment could be a memory leak"""
        # Simple heuristic: assignment to list/dict in a function that modifies global
        for target in node.targets:
            if isinstance(target, ast.Subscript) or isinstance(target, ast.Attribute):
                # Modifying a collection
                return True
        return False

    def _is_resource_open(self, node: ast.Call) -> bool:
        """Check if call opens a resource"""
        if isinstance(node.func, ast.Name):
            if node.func.id in ['open', 'connect', 'socket']:
                return True
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in ['open', 'connect', 'create_connection']:
                return True
        return False

    def _has_close_or_with(self, node: ast.Call, tree: ast.AST) -> bool:
        """Check if resource is properly closed or in with statement"""
        # Simple check: look for parent with statement
        for parent in ast.walk(tree):
            if isinstance(parent, ast.With):
                for item in parent.items:
                    if item.context_expr == node:
                        return True
        return False

    def _count_nested_loops(self, node: ast.AST, depth: int = 0) -> int:
        """Count nested loop depth"""
        max_depth = depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                nested_depth = self._count_nested_loops(child, depth + 1)
                max_depth = max(max_depth, nested_depth)

        return max_depth


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python performance_analyzer.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze_file(file_path)

    print(f"\n=== Performance Analysis for {file_path} ===\n")
    print(f"Performance Score: {result['performance_score']}/100")

    if result['complexity_issues']:
        print("\nComplexity Issues:")
        for issue in result['complexity_issues']:
            print(f"  - [{issue['severity'].upper()}] {issue['description']}")
            print(f"    Location: {issue['location']}")

    if result['n_plus_one_queries']:
        print("\nN+1 Query Issues:")
        for issue in result['n_plus_one_queries']:
            print(f"  - {issue['description']}")
            print(f"    Location: {issue['location']}")

    if result['memory_leaks']:
        print("\nMemory Leak Indicators:")
        for issue in result['memory_leaks']:
            print(f"  - {issue['description']}")

    if result['big_o_warnings']:
        print("\nBig-O Complexity Warnings:")
        for issue in result['big_o_warnings']:
            print(f"  - {issue['description']}")

    print("\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()
