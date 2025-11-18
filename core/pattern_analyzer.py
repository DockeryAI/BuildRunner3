"""
Pattern Analyzer - Detect design patterns and architecture violations

Analyzes code for common design patterns and architectural best practices:
- MVC (Model-View-Controller)
- Repository pattern
- Factory pattern
- Singleton pattern
- Layer violations
- Separation of concerns
"""
import ast
import re
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class PatternMatch:
    """Represents a detected pattern"""
    pattern_type: str
    confidence: float  # 0.0 - 1.0
    location: str
    description: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class LayerViolation:
    """Represents a layer violation"""
    from_layer: str
    to_layer: str
    location: str
    description: str
    severity: str  # 'high', 'medium', 'low'


class PatternAnalyzer:
    """
    Analyze code for design patterns and architectural violations

    Features:
    - Detect common design patterns (MVC, Repository, Factory, Singleton)
    - Identify layer violations
    - Verify separation of concerns
    - Analyze dependency flow
    """

    # Layer hierarchy (higher layers can depend on lower layers only)
    LAYER_HIERARCHY = {
        'presentation': 4,  # UI/Views
        'controller': 3,    # Controllers
        'service': 2,       # Business logic
        'repository': 1,    # Data access
        'model': 0          # Data models
    }

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize PatternAnalyzer

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Comprehensive pattern analysis of a file

        Args:
            file_path: Path to file to analyze

        Returns:
            Dict with:
                - patterns: List of detected patterns
                - violations: List of layer violations
                - separation_score: Score 0-100 for separation of concerns
                - recommendations: List of recommendations
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read and parse file
        try:
            code = file_path.read_text()
            tree = ast.parse(code)
        except Exception as e:
            return {
                "patterns": [],
                "violations": [],
                "separation_score": 0,
                "recommendations": [f"Failed to parse file: {e}"]
            }

        # Detect patterns
        patterns = self.detect_patterns(tree, code)

        # Check for layer violations
        violations = self.check_layer_violations(tree, file_path)

        # Calculate separation of concerns score
        separation_score = self.calculate_separation_score(tree, patterns, violations)

        # Generate recommendations
        recommendations = self.generate_recommendations(patterns, violations, separation_score)

        return {
            "patterns": [vars(p) for p in patterns],
            "violations": [vars(v) for v in violations],
            "separation_score": separation_score,
            "recommendations": recommendations
        }

    def detect_patterns(self, tree: ast.AST, code: str) -> List[PatternMatch]:
        """
        Detect design patterns in code

        Args:
            tree: AST of the code
            code: Source code string

        Returns:
            List of detected patterns
        """
        patterns = []

        # Detect MVC pattern
        patterns.extend(self._detect_mvc_pattern(tree, code))

        # Detect Repository pattern
        patterns.extend(self._detect_repository_pattern(tree, code))

        # Detect Factory pattern
        patterns.extend(self._detect_factory_pattern(tree, code))

        # Detect Singleton pattern
        patterns.extend(self._detect_singleton_pattern(tree, code))

        return patterns

    def check_layer_violations(self, tree: ast.AST, file_path: Path) -> List[LayerViolation]:
        """
        Check for architectural layer violations

        Args:
            tree: AST of the code
            file_path: Path to the file

        Returns:
            List of layer violations
        """
        violations = []

        # Determine the layer of current file
        current_layer = self._determine_layer(file_path)

        if not current_layer:
            return violations  # Unknown layer, skip checks

        # Analyze imports
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported_modules = self._get_imported_modules(node)

                for module in imported_modules:
                    imported_layer = self._determine_layer_from_import(module)

                    if imported_layer and self._is_layer_violation(current_layer, imported_layer):
                        violations.append(LayerViolation(
                            from_layer=current_layer,
                            to_layer=imported_layer,
                            location=f"{file_path.name}:line {node.lineno}",
                            description=f"Layer '{current_layer}' should not import from '{imported_layer}'",
                            severity=self._calculate_violation_severity(current_layer, imported_layer)
                        ))

        return violations

    def calculate_separation_score(
        self,
        tree: ast.AST,
        patterns: List[PatternMatch],
        violations: List[LayerViolation]
    ) -> int:
        """
        Calculate separation of concerns score

        Args:
            tree: AST of the code
            patterns: Detected patterns
            violations: Layer violations

        Returns:
            Score from 0-100
        """
        score = 100

        # Penalty for violations
        high_severity_count = sum(1 for v in violations if v.severity == 'high')
        medium_severity_count = sum(1 for v in violations if v.severity == 'medium')
        low_severity_count = sum(1 for v in violations if v.severity == 'low')

        score -= high_severity_count * 20
        score -= medium_severity_count * 10
        score -= low_severity_count * 5

        # Bonus for good patterns
        score += len([p for p in patterns if p.confidence > 0.8]) * 5

        # Check for mixed responsibilities
        class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        function_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))

        # Penalize files with too many classes (likely mixed concerns)
        if class_count > 5:
            score -= (class_count - 5) * 3

        # Penalize files with too many top-level functions
        if function_count > 10:
            score -= (function_count - 10) * 2

        return max(0, min(100, score))

    def generate_recommendations(
        self,
        patterns: List[PatternMatch],
        violations: List[LayerViolation],
        score: int
    ) -> List[str]:
        """
        Generate recommendations based on analysis

        Args:
            patterns: Detected patterns
            violations: Layer violations
            score: Separation score

        Returns:
            List of recommendations
        """
        recommendations = []

        # Recommendations for violations
        if violations:
            recommendations.append(
                f"Fix {len(violations)} layer violation(s) to improve architecture"
            )

            high_severity = [v for v in violations if v.severity == 'high']
            if high_severity:
                recommendations.append(
                    f"Address {len(high_severity)} high-severity layer violation(s) immediately"
                )

        # Recommendations for patterns
        if not any(p.pattern_type == 'Repository' for p in patterns):
            # Check if this looks like it should use repository pattern
            if any('query' in str(p.location).lower() or 'db' in str(p.location).lower() for p in patterns):
                recommendations.append(
                    "Consider using Repository pattern for data access"
                )

        # Recommendations based on score
        if score < 50:
            recommendations.append(
                "Code has significant separation of concerns issues - consider refactoring"
            )
        elif score < 70:
            recommendations.append(
                "Code could benefit from better separation of concerns"
            )

        if not recommendations:
            recommendations.append("Code follows good architectural practices")

        return recommendations

    def _detect_mvc_pattern(self, tree: ast.AST, code: str) -> List[PatternMatch]:
        """Detect MVC pattern indicators"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check for Model
                if 'model' in class_name or any(
                    base.id.endswith('Model') for base in node.bases if isinstance(base, ast.Name)
                ):
                    patterns.append(PatternMatch(
                        pattern_type='MVC-Model',
                        confidence=0.8,
                        location=f"Class {node.name}",
                        description="Model class detected",
                        evidence=[f"Class name: {node.name}"]
                    ))

                # Check for View
                if 'view' in class_name or any(
                    base.id.endswith('View') for base in node.bases if isinstance(base, ast.Name)
                ):
                    patterns.append(PatternMatch(
                        pattern_type='MVC-View',
                        confidence=0.8,
                        location=f"Class {node.name}",
                        description="View class detected",
                        evidence=[f"Class name: {node.name}"]
                    ))

                # Check for Controller
                if 'controller' in class_name or any(
                    base.id.endswith('Controller') for base in node.bases if isinstance(base, ast.Name)
                ):
                    patterns.append(PatternMatch(
                        pattern_type='MVC-Controller',
                        confidence=0.9,
                        location=f"Class {node.name}",
                        description="Controller class detected",
                        evidence=[f"Class name: {node.name}"]
                    ))

        return patterns

    def _detect_repository_pattern(self, tree: ast.AST, code: str) -> List[PatternMatch]:
        """Detect Repository pattern"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                if 'repository' in class_name or any(
                    base.id.endswith('Repository') for base in node.bases if isinstance(base, ast.Name)
                ):
                    # Check for data access methods
                    methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                    data_access_methods = [
                        m for m in methods
                        if any(keyword in m.lower() for keyword in ['find', 'get', 'save', 'delete', 'update', 'query'])
                    ]

                    if data_access_methods:
                        confidence = 0.9
                    else:
                        confidence = 0.6

                    patterns.append(PatternMatch(
                        pattern_type='Repository',
                        confidence=confidence,
                        location=f"Class {node.name}",
                        description="Repository pattern detected",
                        evidence=[
                            f"Class name: {node.name}",
                            f"Data access methods: {', '.join(data_access_methods)}"
                        ]
                    ))

        return patterns

    def _detect_factory_pattern(self, tree: ast.AST, code: str) -> List[PatternMatch]:
        """Detect Factory pattern"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                if 'factory' in class_name:
                    # Check for create methods
                    methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                    create_methods = [m for m in methods if 'create' in m.lower()]

                    confidence = 0.9 if create_methods else 0.6

                    patterns.append(PatternMatch(
                        pattern_type='Factory',
                        confidence=confidence,
                        location=f"Class {node.name}",
                        description="Factory pattern detected",
                        evidence=[
                            f"Class name: {node.name}",
                            f"Create methods: {', '.join(create_methods)}" if create_methods else "Factory naming convention"
                        ]
                    ))

            elif isinstance(node, ast.FunctionDef):
                # Check for factory functions
                if 'create_' in node.name.lower() or 'make_' in node.name.lower():
                    patterns.append(PatternMatch(
                        pattern_type='Factory',
                        confidence=0.7,
                        location=f"Function {node.name}",
                        description="Factory function detected",
                        evidence=[f"Function name: {node.name}"]
                    ))

        return patterns

    def _detect_singleton_pattern(self, tree: ast.AST, code: str) -> List[PatternMatch]:
        """Detect Singleton pattern"""
        patterns = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for __new__ method override (classic singleton)
                has_new = any(
                    isinstance(m, ast.FunctionDef) and m.name == '__new__'
                    for m in node.body
                )

                # Check for _instance class variable
                has_instance_var = any(
                    isinstance(m, ast.Assign) and
                    any(isinstance(t, ast.Name) and t.id.startswith('_instance') for t in m.targets)
                    for m in node.body
                )

                if has_new or has_instance_var:
                    confidence = 0.9 if has_new else 0.7

                    patterns.append(PatternMatch(
                        pattern_type='Singleton',
                        confidence=confidence,
                        location=f"Class {node.name}",
                        description="Singleton pattern detected",
                        evidence=[
                            "__new__ method override" if has_new else "_instance class variable"
                        ]
                    ))

        return patterns

    def _determine_layer(self, file_path: Path) -> Optional[str]:
        """Determine the architectural layer from file path"""
        path_str = str(file_path).lower()

        if 'view' in path_str or 'template' in path_str or 'ui' in path_str:
            return 'presentation'
        elif 'controller' in path_str:
            return 'controller'
        elif 'service' in path_str or 'business' in path_str:
            return 'service'
        elif 'repository' in path_str or 'dao' in path_str:
            return 'repository'
        elif 'model' in path_str or 'entity' in path_str:
            return 'model'

        return None

    def _determine_layer_from_import(self, module: str) -> Optional[str]:
        """Determine layer from import statement"""
        module_lower = module.lower()

        if 'view' in module_lower or 'template' in module_lower:
            return 'presentation'
        elif 'controller' in module_lower:
            return 'controller'
        elif 'service' in module_lower:
            return 'service'
        elif 'repository' in module_lower or 'dao' in module_lower:
            return 'repository'
        elif 'model' in module_lower or 'entity' in module_lower:
            return 'model'

        return None

    def _is_layer_violation(self, from_layer: str, to_layer: str) -> bool:
        """Check if importing from one layer to another is a violation"""
        from_level = self.LAYER_HIERARCHY.get(from_layer, 0)
        to_level = self.LAYER_HIERARCHY.get(to_layer, 0)

        # Lower layers should not import from higher layers
        return from_level < to_level

    def _calculate_violation_severity(self, from_layer: str, to_layer: str) -> str:
        """Calculate severity of layer violation"""
        from_level = self.LAYER_HIERARCHY.get(from_layer, 0)
        to_level = self.LAYER_HIERARCHY.get(to_layer, 0)

        level_diff = to_level - from_level

        if level_diff >= 3:
            return 'high'
        elif level_diff >= 2:
            return 'medium'
        else:
            return 'low'

    def _get_imported_modules(self, node: ast.AST) -> List[str]:
        """Extract imported module names from import statement"""
        modules = []

        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)

        return modules


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pattern_analyzer.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    analyzer = PatternAnalyzer()
    result = analyzer.analyze_file(file_path)

    print(f"\n=== Pattern Analysis for {file_path} ===\n")
    print(f"Separation Score: {result['separation_score']}/100")

    if result['patterns']:
        print("\nDetected Patterns:")
        for pattern in result['patterns']:
            print(f"  - {pattern['pattern_type']}: {pattern['description']}")
            print(f"    Confidence: {pattern['confidence']:.0%}")

    if result['violations']:
        print("\nLayer Violations:")
        for violation in result['violations']:
            print(f"  - [{violation['severity'].upper()}] {violation['description']}")
            print(f"    Location: {violation['location']}")

    if result['recommendations']:
        print("\nRecommendations:")
        for rec in result['recommendations']:
            print(f"  - {rec}")


if __name__ == "__main__":
    main()
