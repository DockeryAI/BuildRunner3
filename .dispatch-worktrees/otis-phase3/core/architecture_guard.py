"""
Architecture Guard System for BuildRunner 3.0

Prevents architectural drift by validating code against PROJECT_SPEC.md.
Detects violations in tech stack, component structure, and API design.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import json


@dataclass
class ArchitectureViolation:
    """Represents a violation of architectural specifications"""

    type: str  # tech_stack, component_structure, api_design, naming
    severity: str  # critical, warning, info
    file: str
    line: Optional[int]
    description: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ArchitectureSpec:
    """Parsed architecture specification from PROJECT_SPEC.md"""

    tech_stack: Dict[str, List[str]] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    api_patterns: List[str] = field(default_factory=list)
    naming_conventions: Dict[str, str] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)


class ArchitectureGuard:
    """
    Validates codebase against architectural specifications.

    Prevents drift by detecting:
    - Unauthorized tech stack additions
    - Component structure violations
    - API design pattern violations
    - Naming convention violations
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Architecture Guard.

        Args:
            project_root: Root directory of project (default: current directory)
        """
        self.project_root = Path(project_root or Path.cwd())
        self.spec = ArchitectureSpec()
        self.violations: List[ArchitectureViolation] = []

    def load_spec(self, spec_path: Optional[str] = None) -> ArchitectureSpec:
        """
        Parse PROJECT_SPEC.md to extract architectural specifications.

        Args:
            spec_path: Path to PROJECT_SPEC.md (default: project_root/PROJECT_SPEC.md)

        Returns:
            Parsed ArchitectureSpec object
        """
        spec_file = Path(spec_path) if spec_path else self.project_root / "PROJECT_SPEC.md"

        if not spec_file.exists():
            # Try alternate locations
            for alt_path in [
                self.project_root / "docs" / "PROJECT_SPEC.md",
                self.project_root / ".buildrunner" / "PROJECT_SPEC.md",
            ]:
                if alt_path.exists():
                    spec_file = alt_path
                    break

        if not spec_file.exists():
            raise FileNotFoundError(f"PROJECT_SPEC.md not found in {self.project_root}")

        content = spec_file.read_text()
        self.spec = self._parse_spec_content(content)
        return self.spec

    def _parse_spec_content(self, content: str) -> ArchitectureSpec:
        """Parse specification content from markdown"""
        spec = ArchitectureSpec()

        # Extract tech stack section
        tech_stack_match = re.search(
            r"## Tech Stack\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE
        )
        if tech_stack_match:
            tech_stack_text = tech_stack_match.group(1)
            spec.tech_stack = self._parse_tech_stack(tech_stack_text)

        # Extract components/architecture section
        arch_match = re.search(
            r"## (?:Architecture|Components|Structure)\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if arch_match:
            spec.components = self._parse_components(arch_match.group(1))

        # Extract API patterns
        api_match = re.search(
            r"## API (?:Design|Patterns|Endpoints)\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if api_match:
            spec.api_patterns = self._parse_api_patterns(api_match.group(1))

        # Extract naming conventions
        naming_match = re.search(
            r"## Naming Conventions?\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE
        )
        if naming_match:
            spec.naming_conventions = self._parse_naming_conventions(naming_match.group(1))

        return spec

    def _parse_tech_stack(self, text: str) -> Dict[str, List[str]]:
        """Parse tech stack from markdown"""
        tech_stack = {
            "frontend": [],
            "backend": [],
            "database": [],
            "infrastructure": [],
            "libraries": [],
        }

        # Find libraries/frameworks mentioned
        lines = text.split("\n")
        current_category = "libraries"

        for line in lines:
            line = line.strip()

            # Check for category headers
            if "frontend" in line.lower():
                current_category = "frontend"
            elif "backend" in line.lower():
                current_category = "backend"
            elif "database" in line.lower():
                current_category = "database"
            elif "infrastructure" in line.lower():
                current_category = "infrastructure"

            # Extract library names from bullet points or code blocks
            lib_match = re.search(r"[-*]\s*(?:`)?(\w+(?:-\w+)*)(?:`)?", line)
            if lib_match:
                lib_name = lib_match.group(1).lower()
                if lib_name not in tech_stack[current_category]:
                    tech_stack[current_category].append(lib_name)

        return tech_stack

    def _parse_components(self, text: str) -> Dict[str, Any]:
        """Parse component structure from markdown"""
        components = {}

        # Look for directory structure in code blocks
        code_block_match = re.search(r"```(?:bash|text|)?\n(.*?)```", text, re.DOTALL)
        if code_block_match:
            structure_text = code_block_match.group(1)
            components["expected_structure"] = [
                line.strip()
                for line in structure_text.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]

        # Look for component descriptions
        component_pattern = r"[-*]\s*`?([\w/]+)`?:?\s*(.*)"
        for match in re.finditer(component_pattern, text):
            comp_name = match.group(1)
            comp_desc = match.group(2)
            if "/" in comp_name:
                components[comp_name] = comp_desc

        return components

    def _parse_api_patterns(self, text: str) -> List[str]:
        """Parse API endpoint patterns from markdown"""
        patterns = []

        # Find endpoint patterns
        endpoint_pattern = r"(?:GET|POST|PUT|DELETE|PATCH)\s+(/\S+)"
        for match in re.finditer(endpoint_pattern, text):
            patterns.append(match.group(1))

        # Also look for route patterns in code blocks
        code_block_match = re.search(r"```(?:python|)?\n(.*?)```", text, re.DOTALL)
        if code_block_match:
            code = code_block_match.group(1)
            for match in re.finditer(r'@app\.(?:get|post|put|delete|patch)\("([^"]+)"', code):
                patterns.append(match.group(1))

        return patterns

    def _parse_naming_conventions(self, text: str) -> Dict[str, str]:
        """Parse naming conventions from markdown"""
        conventions = {}

        # Common naming patterns
        patterns = {
            "files": r"files?:\s*`?(\w+)`?",
            "classes": r"classes?:\s*`?(\w+)`?",
            "functions": r"functions?:\s*`?(\w+)`?",
            "variables": r"variables?:\s*`?(\w+)`?",
            "constants": r"constants?:\s*`?(\w+)`?",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                conventions[key] = match.group(1)

        return conventions

    def analyze_codebase(
        self, directories: Optional[List[str]] = None
    ) -> List[ArchitectureViolation]:
        """
        Scan codebase for architectural violations.

        Args:
            directories: List of directories to scan (default: ['core', 'api', 'cli'])

        Returns:
            List of detected violations
        """
        self.violations = []

        if directories is None:
            directories = ["core", "api", "cli", "plugins"]

        for dir_name in directories:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                self._analyze_file(py_file)

        return self.violations

    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file for violations"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            # Check imports for tech stack compliance
            self._check_imports(tree, file_path)

            # Check class/function naming
            self._check_naming(tree, file_path)

            # Check for FastAPI route patterns if API file
            if "api" in str(file_path):
                self._check_api_patterns(tree, file_path)

        except SyntaxError as e:
            self.violations.append(
                ArchitectureViolation(
                    type="syntax_error",
                    severity="critical",
                    file=str(file_path.relative_to(self.project_root)),
                    line=e.lineno,
                    description=f"Syntax error: {e.msg}",
                )
            )
        except Exception as e:
            # Gracefully handle other parsing errors
            pass

    def _check_imports(self, tree: ast.AST, file_path: Path):
        """Check if imports comply with tech stack specifications"""
        if not self.spec.tech_stack:
            return

        allowed_libs = set()
        for libs in self.spec.tech_stack.values():
            allowed_libs.update(libs)

        # Also allow standard library and common utilities
        allowed_libs.update(
            [
                "os",
                "sys",
                "json",
                "pathlib",
                "typing",
                "dataclasses",
                "datetime",
                "re",
                "ast",
                "collections",
                "itertools",
                "functools",
                "asyncio",
                "unittest",
                "pytest",
                "click",
            ]
        )

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._check_library(alias.name, node.lineno, file_path, allowed_libs)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self._check_library(node.module, node.lineno, file_path, allowed_libs)

    def _check_library(self, lib_name: str, lineno: int, file_path: Path, allowed_libs: Set[str]):
        """Check if a library is allowed"""
        # Get root package name
        root_lib = lib_name.split(".")[0]

        # Skip local imports
        if root_lib in ["core", "api", "cli", "plugins", "tests"]:
            return

        if root_lib not in allowed_libs and not any(
            allowed in lib_name for allowed in allowed_libs
        ):
            self.violations.append(
                ArchitectureViolation(
                    type="tech_stack",
                    severity="warning",
                    file=str(file_path.relative_to(self.project_root)),
                    line=lineno,
                    description=f"Unauthorized library '{lib_name}' not in tech stack specification",
                    expected="Libraries from approved tech stack",
                    actual=lib_name,
                    suggestion=f"Consider using approved alternatives or add '{root_lib}' to PROJECT_SPEC",
                )
            )

    def _check_naming(self, tree: ast.AST, file_path: Path):
        """Check naming conventions"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Classes should be PascalCase
                if not node.name[0].isupper():
                    self.violations.append(
                        ArchitectureViolation(
                            type="naming",
                            severity="info",
                            file=str(file_path.relative_to(self.project_root)),
                            line=node.lineno,
                            description=f"Class '{node.name}' should use PascalCase",
                            expected="PascalCase",
                            actual=node.name,
                        )
                    )

            elif isinstance(node, ast.FunctionDef):
                # Functions should be snake_case
                if not node.name.islower() and "_" not in node.name:
                    # Skip special methods
                    if not (node.name.startswith("__") and node.name.endswith("__")):
                        self.violations.append(
                            ArchitectureViolation(
                                type="naming",
                                severity="info",
                                file=str(file_path.relative_to(self.project_root)),
                                line=node.lineno,
                                description=f"Function '{node.name}' should use snake_case",
                                expected="snake_case",
                                actual=node.name,
                            )
                        )

    def _check_api_patterns(self, tree: ast.AST, file_path: Path):
        """Check FastAPI route patterns"""
        if not self.spec.api_patterns:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Look for FastAPI route decorators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, "attr") and decorator.func.attr in [
                            "get",
                            "post",
                            "put",
                            "delete",
                            "patch",
                        ]:
                            # Extract route path
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                route_path = decorator.args[0].value
                                self._validate_route_pattern(route_path, node.lineno, file_path)

    def _validate_route_pattern(self, route_path: str, lineno: int, file_path: Path):
        """Validate route path against specified patterns"""
        # Check if route follows RESTful patterns
        if not route_path.startswith("/"):
            self.violations.append(
                ArchitectureViolation(
                    type="api_design",
                    severity="warning",
                    file=str(file_path.relative_to(self.project_root)),
                    line=lineno,
                    description=f"Route '{route_path}' should start with '/'",
                    expected="Routes starting with '/'",
                    actual=route_path,
                )
            )

    def check_tech_stack_compliance(self) -> List[ArchitectureViolation]:
        """
        Check if codebase only uses approved technologies.

        Returns:
            List of tech stack violations
        """
        tech_violations = [v for v in self.violations if v.type == "tech_stack"]
        return tech_violations

    def check_component_structure(self) -> List[ArchitectureViolation]:
        """
        Verify component/directory structure matches specification.

        Returns:
            List of structure violations
        """
        violations = []

        if "expected_structure" in self.spec.components:
            expected_dirs = []
            for item in self.spec.components["expected_structure"]:
                # Extract directory names from structure
                match = re.search(r"(\w+)/", item)
                if match:
                    expected_dirs.append(match.group(1))

            # Check if expected directories exist
            for dir_name in expected_dirs:
                dir_path = self.project_root / dir_name
                if not dir_path.exists():
                    violations.append(
                        ArchitectureViolation(
                            type="component_structure",
                            severity="warning",
                            file=str(self.project_root),
                            line=None,
                            description=f"Expected directory '{dir_name}' not found",
                            expected=dir_name,
                            actual="missing",
                        )
                    )

        return violations

    def check_api_design(self) -> List[ArchitectureViolation]:
        """
        Verify API endpoints match design patterns.

        Returns:
            List of API design violations
        """
        api_violations = [v for v in self.violations if v.type == "api_design"]
        return api_violations

    def detect_violations(self, strict: bool = False) -> List[ArchitectureViolation]:
        """
        Run all violation checks.

        Args:
            strict: If True, include info-level violations

        Returns:
            List of all detected violations
        """
        # Analyze codebase
        self.analyze_codebase()

        # Add component structure violations
        self.violations.extend(self.check_component_structure())

        # Filter by severity if not strict
        if not strict:
            self.violations = [v for v in self.violations if v.severity != "info"]

        return self.violations

    def generate_violation_report(self, output_format: str = "markdown") -> str:
        """
        Generate detailed violation report.

        Args:
            output_format: Report format ("markdown", "json", "text")

        Returns:
            Formatted violation report
        """
        if output_format == "json":
            return json.dumps(
                [
                    {
                        "type": v.type,
                        "severity": v.severity,
                        "file": v.file,
                        "line": v.line,
                        "description": v.description,
                        "expected": v.expected,
                        "actual": v.actual,
                        "suggestion": v.suggestion,
                    }
                    for v in self.violations
                ],
                indent=2,
            )

        elif output_format == "markdown":
            return self._generate_markdown_report()

        else:  # text
            return self._generate_text_report()

    def _generate_markdown_report(self) -> str:
        """Generate markdown formatted report"""
        if not self.violations:
            return "# Architecture Validation Report\n\n✅ **No violations detected**\n\nCodebase complies with PROJECT_SPEC architecture."

        report = ["# Architecture Violation Report\n"]
        report.append(f"**Total Violations:** {len(self.violations)}\n")

        # Group by severity
        by_severity = {"critical": [], "warning": [], "info": []}
        for v in self.violations:
            by_severity[v.severity].append(v)

        for severity in ["critical", "warning", "info"]:
            violations = by_severity[severity]
            if not violations:
                continue

            emoji = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🔵"
            report.append(f"\n## {emoji} {severity.title()} ({len(violations)})\n")

            for v in violations:
                report.append(f"\n### {v.type.replace('_', ' ').title()}")
                report.append(f"\n**File:** `{v.file}`")
                if v.line:
                    report.append(f" (line {v.line})")
                report.append(f"\n\n{v.description}\n")

                if v.expected:
                    report.append(f"- **Expected:** {v.expected}\n")
                if v.actual:
                    report.append(f"- **Actual:** {v.actual}\n")
                if v.suggestion:
                    report.append(f"- **Suggestion:** {v.suggestion}\n")

        return "\n".join(report)

    def _generate_text_report(self) -> str:
        """Generate plain text report"""
        if not self.violations:
            return "Architecture Validation: PASSED\nNo violations detected."

        report = [f"Architecture Violations: {len(self.violations)} found\n"]

        for i, v in enumerate(self.violations, 1):
            report.append(f"\n{i}. [{v.severity.upper()}] {v.type}")
            report.append(f"   File: {v.file}" + (f":{v.line}" if v.line else ""))
            report.append(f"   {v.description}")
            if v.suggestion:
                report.append(f"   Suggestion: {v.suggestion}")

        return "\n".join(report)
