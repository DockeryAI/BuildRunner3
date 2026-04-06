"""
Code Smell Detector - Detect common code smells and anti-patterns

Analyzes code for:
- Long methods
- Long parameter lists
- Duplicate code patterns
- Dead code (unused variables, unused imports)
- Magic numbers
- God classes
- Deep nesting
- Commented-out code
"""

import ast
import re
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CodeSmell:
    """Represents a detected code smell"""

    smell_type: str
    location: str
    severity: str  # 'high', 'medium', 'low'
    description: str
    recommendation: str
    metric_value: Optional[float] = None


class CodeSmellDetector:
    """
    Detect common code smells and anti-patterns

    Features:
    - Long method detection
    - Long parameter list detection
    - Magic number detection
    - Dead code detection
    - God class detection
    - Deep nesting detection
    - Commented-out code detection
    """

    # Thresholds
    MAX_METHOD_LINES = 50
    MAX_PARAMETERS = 5
    MAX_CLASS_METHODS = 20
    MAX_NESTING_DEPTH = 4

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize CodeSmellDetector

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Comprehensive code smell analysis of a file

        Args:
            file_path: Path to file to analyze

        Returns:
            Dict with:
                - long_methods: List of methods that are too long
                - long_parameter_lists: List of functions with too many parameters
                - magic_numbers: List of magic number occurrences
                - dead_code: List of dead code issues
                - god_classes: List of classes with too many methods
                - deep_nesting: List of deeply nested code
                - commented_code: List of commented-out code
                - smell_score: Score 0-100 (higher is better)
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

        # Run detections
        long_methods = self.detect_long_methods(tree, code)
        long_params = self.detect_long_parameter_lists(tree)
        magic_numbers = self.detect_magic_numbers(tree, code)
        dead_code = self.detect_dead_code(tree, code)
        god_classes = self.detect_god_classes(tree)
        deep_nesting = self.detect_deep_nesting(tree)
        commented_code = self.detect_commented_code(code)

        # Calculate smell score
        smell_score = self.calculate_smell_score(
            long_methods,
            long_params,
            magic_numbers,
            dead_code,
            god_classes,
            deep_nesting,
            commented_code,
        )

        # Generate recommendations
        recommendations = self.generate_recommendations(
            long_methods,
            long_params,
            magic_numbers,
            dead_code,
            god_classes,
            deep_nesting,
            commented_code,
        )

        return {
            "long_methods": [vars(s) for s in long_methods],
            "long_parameter_lists": [vars(s) for s in long_params],
            "magic_numbers": [vars(s) for s in magic_numbers],
            "dead_code": [vars(s) for s in dead_code],
            "god_classes": [vars(s) for s in god_classes],
            "deep_nesting": [vars(s) for s in deep_nesting],
            "commented_code": [vars(s) for s in commented_code],
            "smell_score": smell_score,
            "recommendations": recommendations,
        }

    def detect_long_methods(self, tree: ast.AST, code: str) -> List[CodeSmell]:
        """
        Detect methods that are too long

        Args:
            tree: AST of the code
            code: Source code

        Returns:
            List of long method smells
        """
        smells = []
        code_lines = code.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Calculate method length
                start_line = node.lineno - 1
                end_line = node.end_lineno if node.end_lineno else start_line + 1
                method_lines = end_line - start_line

                if method_lines > self.MAX_METHOD_LINES:
                    severity = "high" if method_lines > self.MAX_METHOD_LINES * 2 else "medium"
                    smells.append(
                        CodeSmell(
                            smell_type="long_method",
                            location=f"Function {node.name} (line {node.lineno})",
                            severity=severity,
                            description=f"Method is {method_lines} lines long (max: {self.MAX_METHOD_LINES})",
                            recommendation="Break into smaller, focused functions",
                            metric_value=float(method_lines),
                        )
                    )

        return smells

    def detect_long_parameter_lists(self, tree: ast.AST) -> List[CodeSmell]:
        """
        Detect functions with too many parameters

        Args:
            tree: AST of the code

        Returns:
            List of long parameter list smells
        """
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Count parameters (excluding self/cls)
                param_count = len(node.args.args)
                if param_count > 0:
                    first_param = node.args.args[0].arg
                    if first_param in ["self", "cls"]:
                        param_count -= 1

                if param_count > self.MAX_PARAMETERS:
                    severity = "high" if param_count > self.MAX_PARAMETERS * 2 else "medium"
                    smells.append(
                        CodeSmell(
                            smell_type="long_parameter_list",
                            location=f"Function {node.name} (line {node.lineno})",
                            severity=severity,
                            description=f"Function has {param_count} parameters (max: {self.MAX_PARAMETERS})",
                            recommendation="Consider using parameter objects or builder pattern",
                            metric_value=float(param_count),
                        )
                    )

        return smells

    def detect_magic_numbers(self, tree: ast.AST, code: str) -> List[CodeSmell]:
        """
        Detect magic numbers in code

        Args:
            tree: AST of the code
            code: Source code

        Returns:
            List of magic number smells
        """
        smells = []
        seen_locations = set()

        # Common non-magic numbers
        ALLOWED_NUMBERS = {0, 1, -1, 2, 10, 100, 1000}

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    # Skip allowed numbers
                    if node.value in ALLOWED_NUMBERS:
                        continue

                    # Skip if in a constant assignment
                    if self._is_constant_definition(node, tree):
                        continue

                    location = f"Line {node.lineno}"
                    if location not in seen_locations:
                        seen_locations.add(location)
                        smells.append(
                            CodeSmell(
                                smell_type="magic_number",
                                location=location,
                                severity="low",
                                description=f"Magic number '{node.value}' used in code",
                                recommendation="Replace with named constant",
                                metric_value=float(node.value),
                            )
                        )

        return smells

    def detect_dead_code(self, tree: ast.AST, code: str) -> List[CodeSmell]:
        """
        Detect dead code (unused variables, unused imports)

        Args:
            tree: AST of the code
            code: Source code

        Returns:
            List of dead code smells
        """
        smells = []

        # Detect unused variables
        assigned_vars = set()
        used_vars = set()

        for node in ast.walk(tree):
            # Track assignments
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned_vars.add(target.id)
            # Track usage
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_vars.add(node.id)

        unused_vars = assigned_vars - used_vars
        for var in unused_vars:
            # Skip private variables (likely intentional)
            if not var.startswith("_"):
                smells.append(
                    CodeSmell(
                        smell_type="unused_variable",
                        location=f"Variable '{var}'",
                        severity="low",
                        description=f"Variable '{var}' is assigned but never used",
                        recommendation="Remove unused variable or use it",
                    )
                )

        # Detect unused imports
        imported_names = set()
        used_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.asname if alias.asname else alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname if alias.asname else alias.name)
            elif isinstance(node, ast.Name):
                used_names.add(node.id)

        unused_imports = imported_names - used_names
        for imp in unused_imports:
            smells.append(
                CodeSmell(
                    smell_type="unused_import",
                    location=f"Import '{imp}'",
                    severity="low",
                    description=f"Import '{imp}' is not used",
                    recommendation="Remove unused import",
                )
            )

        return smells

    def detect_god_classes(self, tree: ast.AST) -> List[CodeSmell]:
        """
        Detect god classes (classes with too many methods)

        Args:
            tree: AST of the code

        Returns:
            List of god class smells
        """
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count methods
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                method_count = len(methods)

                if method_count > self.MAX_CLASS_METHODS:
                    severity = "high" if method_count > self.MAX_CLASS_METHODS * 2 else "medium"
                    smells.append(
                        CodeSmell(
                            smell_type="god_class",
                            location=f"Class {node.name} (line {node.lineno})",
                            severity=severity,
                            description=f"Class has {method_count} methods (max: {self.MAX_CLASS_METHODS})",
                            recommendation="Split into smaller, focused classes",
                            metric_value=float(method_count),
                        )
                    )

        return smells

    def detect_deep_nesting(self, tree: ast.AST) -> List[CodeSmell]:
        """
        Detect deeply nested code

        Args:
            tree: AST of the code

        Returns:
            List of deep nesting smells
        """
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                max_depth = self._calculate_nesting_depth(node)

                if max_depth > self.MAX_NESTING_DEPTH:
                    severity = "high" if max_depth > self.MAX_NESTING_DEPTH * 2 else "medium"
                    smells.append(
                        CodeSmell(
                            smell_type="deep_nesting",
                            location=f"Function {node.name} (line {node.lineno})",
                            severity=severity,
                            description=f"Nesting depth is {max_depth} (max: {self.MAX_NESTING_DEPTH})",
                            recommendation="Reduce nesting with early returns or extraction",
                            metric_value=float(max_depth),
                        )
                    )

        return smells

    def detect_commented_code(self, code: str) -> List[CodeSmell]:
        """
        Detect commented-out code

        Args:
            code: Source code

        Returns:
            List of commented code smells
        """
        smells = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check if line is a comment
            if stripped.startswith("#"):
                # Remove the # and check if it looks like code
                comment_content = stripped[1:].strip()

                # Heuristics for code: contains =, (), def, class, if, for, etc.
                code_indicators = [
                    "=",
                    "def ",
                    "class ",
                    "if ",
                    "for ",
                    "while ",
                    "return ",
                    "import ",
                ]

                if any(indicator in comment_content for indicator in code_indicators):
                    # Skip docstrings and normal comments
                    if not any(
                        word in comment_content.lower()
                        for word in ["note:", "todo:", "fixme:", "hack:"]
                    ):
                        smells.append(
                            CodeSmell(
                                smell_type="commented_code",
                                location=f"Line {i}",
                                severity="low",
                                description="Commented-out code detected",
                                recommendation="Remove commented code or uncomment if needed",
                            )
                        )

        return smells

    def calculate_smell_score(
        self,
        long_methods: List[CodeSmell],
        long_params: List[CodeSmell],
        magic_numbers: List[CodeSmell],
        dead_code: List[CodeSmell],
        god_classes: List[CodeSmell],
        deep_nesting: List[CodeSmell],
        commented_code: List[CodeSmell],
    ) -> int:
        """
        Calculate overall code smell score

        Args:
            Various smell lists

        Returns:
            Score from 0-100 (higher is better)
        """
        score = 100

        # Penalties
        score -= len([s for s in long_methods if s.severity == "high"]) * 15
        score -= len([s for s in long_methods if s.severity == "medium"]) * 8
        score -= len([s for s in long_params if s.severity == "high"]) * 12
        score -= len([s for s in long_params if s.severity == "medium"]) * 6
        score -= len(magic_numbers) * 2
        score -= len(dead_code) * 3
        score -= len([s for s in god_classes if s.severity == "high"]) * 20
        score -= len([s for s in god_classes if s.severity == "medium"]) * 10
        score -= len([s for s in deep_nesting if s.severity == "high"]) * 15
        score -= len([s for s in deep_nesting if s.severity == "medium"]) * 8
        score -= len(commented_code) * 2

        return max(0, min(100, score))

    def generate_recommendations(
        self,
        long_methods: List[CodeSmell],
        long_params: List[CodeSmell],
        magic_numbers: List[CodeSmell],
        dead_code: List[CodeSmell],
        god_classes: List[CodeSmell],
        deep_nesting: List[CodeSmell],
        commented_code: List[CodeSmell],
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if long_methods:
            recommendations.append(
                f"Refactor {len(long_methods)} long method(s) into smaller functions"
            )

        if long_params:
            recommendations.append(f"Reduce parameter count in {len(long_params)} function(s)")

        if magic_numbers:
            recommendations.append(
                f"Replace {len(magic_numbers)} magic number(s) with named constants"
            )

        if dead_code:
            recommendations.append(f"Remove {len(dead_code)} piece(s) of dead code")

        if god_classes:
            recommendations.append(f"Split {len(god_classes)} god class(es) into smaller classes")

        if deep_nesting:
            recommendations.append(f"Reduce nesting in {len(deep_nesting)} function(s)")

        if commented_code:
            recommendations.append(
                f"Remove or uncomment {len(commented_code)} commented code block(s)"
            )

        if not recommendations:
            recommendations.append("Code is clean with no major smells detected")

        return recommendations

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Return error result"""
        return {
            "long_methods": [],
            "long_parameter_lists": [],
            "magic_numbers": [],
            "dead_code": [],
            "god_classes": [],
            "deep_nesting": [],
            "commented_code": [],
            "smell_score": 0,
            "recommendations": [error_msg],
        }

    def _is_constant_definition(self, node: ast.Constant, tree: ast.AST) -> bool:
        """Check if constant is being used in a constant definition"""
        # Simple heuristic: check if assigned to uppercase variable
        for parent in ast.walk(tree):
            if isinstance(parent, ast.Assign):
                for target in parent.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        if node in ast.walk(parent):
                            return True
        return False

    def _calculate_nesting_depth(self, node: ast.AST, depth: int = 0) -> int:
        """Calculate maximum nesting depth"""
        max_depth = depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)

        return max_depth


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python code_smell_detector.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    detector = CodeSmellDetector()
    result = detector.analyze_file(file_path)

    print(f"\n=== Code Smell Analysis for {file_path} ===\n")
    print(f"Smell Score: {result['smell_score']}/100\n")

    if result["long_methods"]:
        print("Long Methods:")
        for smell in result["long_methods"]:
            print(f"  - [{smell['severity'].upper()}] {smell['description']}")
            print(f"    Location: {smell['location']}")

    if result["long_parameter_lists"]:
        print("\nLong Parameter Lists:")
        for smell in result["long_parameter_lists"]:
            print(f"  - [{smell['severity'].upper()}] {smell['description']}")

    if result["magic_numbers"]:
        print(f"\nMagic Numbers: {len(result['magic_numbers'])} detected")

    if result["dead_code"]:
        print(f"\nDead Code: {len(result['dead_code'])} issue(s)")

    if result["god_classes"]:
        print("\nGod Classes:")
        for smell in result["god_classes"]:
            print(f"  - [{smell['severity'].upper()}] {smell['description']}")

    if result["deep_nesting"]:
        print("\nDeep Nesting:")
        for smell in result["deep_nesting"]:
            print(f"  - [{smell['severity'].upper()}] {smell['description']}")

    if result["commented_code"]:
        print(f"\nCommented Code: {len(result['commented_code'])} occurrence(s)")

    print("\nRecommendations:")
    for rec in result["recommendations"]:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()
