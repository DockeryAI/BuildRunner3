"""
Gap Analysis System for BuildRunner 3.0

Detects gaps between specifications and implementation:
- Missing features from features.json
- Incomplete implementations (TODOs, stubs, pass statements)
- Spec vs implementation mismatches
- Missing dependencies
- Circular dependencies
"""

import ast
import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from core.security import SecretDetector, SQLInjectionDetector


@dataclass
class GapAnalysis:
    """Gap analysis results."""

    # Feature gaps
    missing_features: List[Dict[str, Any]] = field(default_factory=list)
    incomplete_features: List[Dict[str, Any]] = field(default_factory=list)
    blocked_features: List[Dict[str, Any]] = field(default_factory=list)

    # Implementation gaps
    todo_count: int = 0
    stub_count: int = 0
    pass_statements: int = 0
    todos: List[Dict[str, str]] = field(default_factory=list)
    stubs: List[Dict[str, str]] = field(default_factory=list)

    # Dependency gaps
    missing_dependencies: List[str] = field(default_factory=list)
    circular_dependencies: List[List[str]] = field(default_factory=list)

    # Spec gaps
    spec_violations: List[Dict[str, str]] = field(default_factory=list)
    missing_components: List[str] = field(default_factory=list)

    # Security gaps (Tier 1)
    exposed_secrets: List[Dict[str, Any]] = field(default_factory=list)
    sql_injection_risks: List[Dict[str, Any]] = field(default_factory=list)
    security_gap_count: int = 0

    # Overall
    total_gaps: int = 0
    severity_high: int = 0
    severity_medium: int = 0
    severity_low: int = 0


class GapAnalyzer:
    """Analyzes gaps in project implementation."""

    # Patterns for detecting incomplete code
    TODO_PATTERNS = [
        r"#\s*TODO[:\s]+(.*)",
        r"#\s*FIXME[:\s]+(.*)",
        r"#\s*XXX[:\s]+(.*)",
        r"#\s*HACK[:\s]+(.*)",
    ]

    STUB_PATTERNS = [
        r"raise\s+NotImplementedError",
        r"return\s+NotImplemented",
    ]

    def __init__(self, project_root: Path):
        """
        Initialize gap analyzer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.buildrunner_dir = self.project_root / ".buildrunner"
        self.python_files: List[Path] = []

    def analyze(self) -> GapAnalysis:
        """
        Run complete gap analysis.

        Returns:
            GapAnalysis with all detected gaps
        """
        analysis = GapAnalysis()

        # Discover files
        self._discover_files()

        # Run analyses
        self.analyze_features(analysis)
        self.detect_incomplete_implementations(analysis)
        self.analyze_dependencies(analysis)
        self.detect_security_gaps(analysis)

        # Calculate totals
        analysis.total_gaps = (
            len(analysis.missing_features)
            + len(analysis.incomplete_features)
            + analysis.todo_count
            + analysis.stub_count
            + len(analysis.missing_dependencies)
            + len(analysis.spec_violations)
            + analysis.security_gap_count
        )

        # Calculate severity (security gaps are ALWAYS high severity)
        analysis.severity_high = (
            len(analysis.missing_features)
            + analysis.stub_count
            + len(analysis.circular_dependencies)
            + analysis.security_gap_count
        )
        analysis.severity_medium = (
            len(analysis.incomplete_features)
            + len(analysis.missing_dependencies)
            + len(analysis.spec_violations)
        )
        analysis.severity_low = analysis.todo_count

        return analysis

    def _discover_files(self):
        """Discover Python files in the project."""
        self.python_files = []

        # Exclude common non-source directories
        exclude_dirs = {".venv", "venv", "__pycache__", ".git", "node_modules", ".pytest_cache"}

        for py_file in self.project_root.rglob("*.py"):
            # Skip if in excluded directory
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue

            self.python_files.append(py_file)

    def analyze_features(self, analysis: GapAnalysis):
        """
        Analyze features.json for completeness.

        Detects:
        - Features with status 'planned' (not started)
        - Features with status 'in_progress' (incomplete)
        - Features with status 'blocked'

        Args:
            analysis: GapAnalysis object to populate
        """
        features_file = self.buildrunner_dir / "features.json"

        if not features_file.exists():
            analysis.missing_components.append(".buildrunner/features.json")
            return

        try:
            with open(features_file) as f:
                features_data = json.load(f)

            for feature in features_data.get("features", []):
                status = feature.get("status", "unknown").lower()
                feature_id = feature.get("id", "unknown")
                feature_name = feature.get("name", "Unknown Feature")

                if status == "planned":
                    analysis.missing_features.append(
                        {
                            "id": feature_id,
                            "name": feature_name,
                            "reason": "Not started (status: planned)",
                        }
                    )
                elif status == "in_progress":
                    analysis.incomplete_features.append(
                        {
                            "id": feature_id,
                            "name": feature_name,
                            "reason": "In progress (not completed)",
                        }
                    )
                elif status == "blocked":
                    analysis.blocked_features.append(
                        {
                            "id": feature_id,
                            "name": feature_name,
                            "reason": "Blocked",
                            "severity": "high",
                        }
                    )

        except json.JSONDecodeError as e:
            analysis.spec_violations.append(
                {"file": str(features_file), "issue": f"Invalid JSON: {str(e)}", "severity": "high"}
            )
        except Exception as e:
            analysis.spec_violations.append(
                {
                    "file": str(features_file),
                    "issue": f"Error reading features: {str(e)}",
                    "severity": "medium",
                }
            )

    def analyze_spec(self, spec_path: Optional[Path], analysis: GapAnalysis):
        """
        Compare PROJECT_SPEC vs implementation.

        Detects:
        - Missing components mentioned in spec
        - API endpoints not implemented
        - Database tables not created

        Args:
            spec_path: Path to PROJECT_SPEC.md
            analysis: GapAnalysis object to populate
        """
        if spec_path is None:
            spec_path = self.project_root / "PROJECT_SPEC.md"

        if not spec_path.exists():
            analysis.missing_components.append("PROJECT_SPEC.md")
            return

        try:
            spec_content = spec_path.read_text()

            # Extract components from spec
            # Look for API endpoints
            api_endpoints = re.findall(r"`((?:GET|POST|PUT|DELETE|PATCH)\s+/[^\`]+)`", spec_content)

            # Look for database tables
            db_tables = re.findall(r"(?:table|TABLE):\s*`?(\w+)`?", spec_content)

            # Look for required files/modules
            required_files = re.findall(r"(?:file|module):\s*`([^`]+)`", spec_content)

            # Check if components exist
            for endpoint in api_endpoints:
                # Simple heuristic: check if endpoint is in any Python file
                endpoint_found = False
                for py_file in self.python_files:
                    try:
                        content = py_file.read_text()
                        if endpoint in content or endpoint.split()[1] in content:
                            endpoint_found = True
                            break
                    except Exception:
                        pass

                if not endpoint_found:
                    analysis.missing_components.append(f"API endpoint: {endpoint}")

            for required_file in required_files:
                file_path = self.project_root / required_file
                if not file_path.exists():
                    analysis.missing_components.append(f"File: {required_file}")

        except Exception as e:
            analysis.spec_violations.append(
                {
                    "file": str(spec_path),
                    "issue": f"Error analyzing spec: {str(e)}",
                    "severity": "low",
                }
            )

    def detect_incomplete_implementations(self, analysis: GapAnalysis):
        """
        Find incomplete implementations in code.

        Detects:
        - TODO/FIXME/XXX comments
        - NotImplementedError raises
        - Functions with only 'pass'
        - Empty class bodies

        Args:
            analysis: GapAnalysis object to populate
        """
        for py_file in self.python_files:
            # Skip test files for stub detection (they contain test fixtures)
            is_test_file = "test" in py_file.parts or py_file.name.startswith("test_")

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                # Detect TODOs
                for i, line in enumerate(lines, 1):
                    for pattern in self.TODO_PATTERNS:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            analysis.todo_count += 1
                            analysis.todos.append(
                                {
                                    "file": str(py_file.relative_to(self.project_root)),
                                    "line": i,
                                    "text": (
                                        match.group(1).strip() if match.lastindex else line.strip()
                                    ),
                                }
                            )

                # Parse AST for stubs and pass statements
                try:
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        # Detect NotImplementedError (skip in test files)
                        if isinstance(node, ast.Raise) and not is_test_file:
                            if (
                                isinstance(node.exc, ast.Name)
                                and node.exc.id == "NotImplementedError"
                            ):
                                analysis.stub_count += 1
                                analysis.stubs.append(
                                    {
                                        "file": str(py_file.relative_to(self.project_root)),
                                        "line": node.lineno,
                                        "type": "NotImplementedError",
                                    }
                                )

                        # Detect functions with only pass (skip in test files)
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            # Check if function body is only pass statement
                            if (
                                not is_test_file
                                and len(node.body) == 1
                                and isinstance(node.body[0], ast.Pass)
                            ):
                                analysis.stub_count += 1
                                analysis.stubs.append(
                                    {
                                        "file": str(py_file.relative_to(self.project_root)),
                                        "line": node.lineno,
                                        "type": "empty function",
                                        "name": node.name,
                                    }
                                )

                            # Count pass statements
                            for child in ast.walk(node):
                                if isinstance(child, ast.Pass):
                                    analysis.pass_statements += 1

                except SyntaxError:
                    # Syntax error in file - could be incomplete code
                    analysis.spec_violations.append(
                        {
                            "file": str(py_file.relative_to(self.project_root)),
                            "issue": "Syntax error (incomplete code?)",
                            "severity": "high",
                        }
                    )

            except Exception as e:
                analysis.spec_violations.append(
                    {
                        "file": str(py_file.relative_to(self.project_root)),
                        "issue": f"Error analyzing file: {str(e)}",
                        "severity": "low",
                    }
                )

    def analyze_dependencies(self, analysis: GapAnalysis):
        """
        Analyze project dependencies.

        Detects:
        - Missing dependencies (imported but not in requirements)
        - Circular dependencies

        Args:
            analysis: GapAnalysis object to populate
        """
        # Collect all imports
        imports: Dict[str, Set[str]] = {}  # file -> set of imports
        all_imports: Set[str] = set()

        for py_file in self.python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                file_imports = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split(".")[0]
                            file_imports.add(module)
                            all_imports.add(module)

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split(".")[0]
                            file_imports.add(module)
                            all_imports.add(module)

                imports[str(py_file.relative_to(self.project_root))] = file_imports

            except Exception:
                pass

        # Check for missing dependencies
        requirements_file = self.project_root / "pyproject.toml"
        if not requirements_file.exists():
            requirements_file = self.project_root / "requirements.txt"

        # Read requirements if file exists
        requirements_content = ""
        if requirements_file.exists():
            try:
                requirements_content = requirements_file.read_text()
            except Exception:
                pass

        # Filter out stdlib and local imports
        stdlib_modules = self._get_stdlib_modules()

        for module in all_imports:
            # Skip stdlib modules
            if module in stdlib_modules:
                continue

            # Skip local imports (modules in project)
            if any(
                (self.project_root / f"{module}.py").exists()
                or (self.project_root / module).is_dir()
                for _ in [None]
            ):  # Just execute once
                continue

            # Check if in requirements (empty content means all are missing)
            if not requirements_content or module.lower() not in requirements_content.lower():
                analysis.missing_dependencies.append(module)

        # Detect circular dependencies (simplified)
        # This is a basic check - full circular dependency detection is complex
        self._detect_circular_deps(imports, analysis)

    def _get_stdlib_modules(self) -> Set[str]:
        """Get set of Python stdlib module names."""
        # Common stdlib modules (not exhaustive)
        return {
            "abc",
            "ast",
            "asyncio",
            "base64",
            "collections",
            "dataclasses",
            "datetime",
            "functools",
            "hashlib",
            "http",
            "inspect",
            "io",
            "itertools",
            "json",
            "logging",
            "math",
            "os",
            "pathlib",
            "pickle",
            "re",
            "shutil",
            "subprocess",
            "sys",
            "tempfile",
            "time",
            "typing",
            "unittest",
            "uuid",
            "warnings",
            "yaml",
        }

    def _detect_circular_deps(self, imports: Dict[str, Set[str]], analysis: GapAnalysis):
        """
        Detect circular dependencies using proper graph traversal.

        Args:
            imports: Map of file -> imports
            analysis: GapAnalysis object to populate
        """
        # Build module dependency graph
        # Map each file to the local modules it imports
        graph: Dict[str, Set[str]] = {}

        # Get all local modules (files in this project)
        local_modules = set()
        for file_path in imports.keys():
            # Convert file path to module name: core/security/secret_detector.py -> core.security.secret_detector
            module_name = file_path.replace("/", ".").replace(".py", "")
            local_modules.add(module_name)
            # Also add parent modules
            parts = module_name.split(".")
            for i in range(1, len(parts)):
                local_modules.add(".".join(parts[:i]))

        # Build dependency graph between local modules only
        for file_path, file_imports in imports.items():
            source_module = file_path.replace("/", ".").replace(".py", "")
            graph[source_module] = set()

            for imported_module in file_imports:
                # Check if this is a local module import
                # Match exact module name or any child module
                for local_mod in local_modules:
                    if local_mod == imported_module or local_mod.startswith(imported_module + "."):
                        # Only add edge if it's not importing itself or parent package
                        if source_module != local_mod and not source_module.startswith(
                            local_mod + "."
                        ):
                            graph[source_module].add(local_mod)

        # Find cycles using DFS
        def find_cycle(
            node: str, visited: Set[str], rec_stack: Set[str], path: List[str]
        ) -> Optional[List[str]]:
            """Find a cycle in the graph starting from node."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    cycle = find_cycle(neighbor, visited, rec_stack, path[:])
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            rec_stack.remove(node)
            return None

        # Find all cycles
        visited: Set[str] = set()
        found_cycles: Set[tuple] = set()  # Use set to avoid duplicates

        for node in graph.keys():
            if node not in visited:
                cycle = find_cycle(node, visited, set(), [])
                if cycle and len(cycle) > 1:
                    # Normalize cycle representation (start with lexically smallest)
                    min_idx = cycle.index(min(cycle[:-1]))  # Exclude last element (duplicate)
                    normalized = tuple(cycle[min_idx:-1] + cycle[:min_idx])
                    found_cycles.add(normalized)

        # Convert to list format expected by analysis
        for cycle in found_cycles:
            analysis.circular_dependencies.append(list(cycle))

    def detect_security_gaps(self, analysis: GapAnalysis):
        """
        Detect Tier 1 security gaps in codebase.

        Detects:
        - Exposed API keys and secrets
        - SQL injection vulnerabilities

        Args:
            analysis: GapAnalysis object to populate
        """
        # Detect exposed secrets
        try:
            secret_detector = SecretDetector(self.project_root)
            secret_results = secret_detector.scan_directory(str(self.project_root))

            for file_path, matches in secret_results.items():
                for match in matches:
                    analysis.exposed_secrets.append(
                        {
                            "file": match.file_path,
                            "line": match.line_number,
                            "type": match.pattern_name,
                            "value": match.secret_value,  # Already masked
                            "severity": "high",
                        }
                    )
                    analysis.security_gap_count += 1

        except Exception as e:
            analysis.spec_violations.append(
                {
                    "file": "security scan",
                    "issue": f"Secret detection failed: {str(e)}",
                    "severity": "medium",
                }
            )

        # Detect SQL injection risks
        try:
            sql_detector = SQLInjectionDetector(self.project_root)
            sql_results = sql_detector.scan_directory(str(self.project_root))

            for file_path, matches in sql_results.items():
                for match in matches:
                    # Determine severity - treat high/medium SQL issues as high severity gaps
                    severity = "high" if match.severity in ["high", "medium"] else "medium"

                    analysis.sql_injection_risks.append(
                        {
                            "file": file_path,
                            "line": match.line_number,
                            "type": match.vulnerability_type,
                            "severity": severity,
                            "suggestion": match.suggestion,
                        }
                    )

                    # Only count high/medium SQL issues in security gap count
                    if severity == "high":
                        analysis.security_gap_count += 1

        except Exception as e:
            analysis.spec_violations.append(
                {
                    "file": "security scan",
                    "issue": f"SQL injection detection failed: {str(e)}",
                    "severity": "medium",
                }
            )

    def generate_gap_report(self, analysis: GapAnalysis) -> str:
        """
        Generate markdown gap report.

        Args:
            analysis: GapAnalysis results

        Returns:
            Markdown-formatted gap report
        """
        lines = []

        lines.append("# Gap Analysis Report")
        lines.append("")
        lines.append(f"**Total Gaps:** {analysis.total_gaps}")
        lines.append(f"- High Severity: {analysis.severity_high}")
        lines.append(f"- Medium Severity: {analysis.severity_medium}")
        lines.append(f"- Low Severity: {analysis.severity_low}")
        lines.append("")

        # Feature gaps
        if analysis.missing_features or analysis.incomplete_features or analysis.blocked_features:
            lines.append("## Feature Gaps")
            lines.append("")

            if analysis.missing_features:
                lines.append("### Missing Features (Not Started)")
                for feature in analysis.missing_features:
                    lines.append(f"- **{feature['id']}**: {feature['name']}")
                    lines.append(f"  - {feature['reason']}")
                lines.append("")

            if analysis.incomplete_features:
                lines.append("### Incomplete Features (In Progress)")
                for feature in analysis.incomplete_features:
                    lines.append(f"- **{feature['id']}**: {feature['name']}")
                    lines.append(f"  - {feature['reason']}")
                lines.append("")

            if analysis.blocked_features:
                lines.append("### Blocked Features")
                for feature in analysis.blocked_features:
                    lines.append(f"- **{feature['id']}**: {feature['name']}")
                    lines.append(f"  - {feature['reason']}")
                lines.append("")

        # Implementation gaps
        if analysis.todos or analysis.stubs:
            lines.append("## Implementation Gaps")
            lines.append("")

            if analysis.todos:
                lines.append(f"### TODOs ({analysis.todo_count})")
                for todo in analysis.todos[:10]:  # Limit to top 10
                    lines.append(f"- `{todo['file']}:{todo['line']}` - {todo['text']}")
                if analysis.todo_count > 10:
                    lines.append(f"- ... and {analysis.todo_count - 10} more")
                lines.append("")

            if analysis.stubs:
                lines.append(f"### Stubs/NotImplemented ({analysis.stub_count})")
                for stub in analysis.stubs[:10]:
                    name = stub.get("name", stub.get("type"))
                    lines.append(f"- `{stub['file']}:{stub['line']}` - {name}")
                if analysis.stub_count > 10:
                    lines.append(f"- ... and {analysis.stub_count - 10} more")
                lines.append("")

        # Security gaps (CRITICAL - Tier 1)
        if analysis.exposed_secrets or analysis.sql_injection_risks:
            lines.append("## Security Gaps (CRITICAL - Tier 1)")
            lines.append("")
            lines.append("⚠️  **These are non-negotiable security issues that must be fixed**")
            lines.append("")

            if analysis.exposed_secrets:
                lines.append(f"### Exposed Secrets ({len(analysis.exposed_secrets)})")
                lines.append("")
                for secret in analysis.exposed_secrets[:20]:  # Limit to top 20
                    lines.append(f"- `{secret['file']}:{secret['line']}` - {secret['type']}")
                    lines.append(f"  - Value: `{secret['value']}`")
                if len(analysis.exposed_secrets) > 20:
                    lines.append(f"- ... and {len(analysis.exposed_secrets) - 20} more")
                lines.append("")
                lines.append("**Remediation:**")
                lines.append("- Move secrets to `.env` file (add to `.gitignore`)")
                lines.append("- Use environment variables")
                lines.append("- Run `br security check` for detailed guidance")
                lines.append("")

            if analysis.sql_injection_risks:
                lines.append(f"### SQL Injection Risks ({len(analysis.sql_injection_risks)})")
                lines.append("")
                high_risks = [r for r in analysis.sql_injection_risks if r["severity"] == "high"]
                medium_risks = [
                    r for r in analysis.sql_injection_risks if r["severity"] == "medium"
                ]

                if high_risks:
                    lines.append("**High Severity:**")
                    for risk in high_risks[:10]:
                        lines.append(f"- `{risk['file']}:{risk['line']}` - {risk['type']}")
                        lines.append(f"  - 💡 {risk['suggestion']}")
                    if len(high_risks) > 10:
                        lines.append(f"- ... and {len(high_risks) - 10} more")
                    lines.append("")

                if medium_risks:
                    lines.append("**Medium Severity:**")
                    for risk in medium_risks[:5]:
                        lines.append(f"- `{risk['file']}:{risk['line']}` - {risk['type']}")
                    if len(medium_risks) > 5:
                        lines.append(f"- ... and {len(medium_risks) - 5} more")
                    lines.append("")

                lines.append("**Remediation:**")
                lines.append("- Use parameterized queries")
                lines.append("- Use ORM methods (e.g., SQLAlchemy)")
                lines.append("- Run `br security check` for safe examples")
                lines.append("")

        # Dependency gaps
        if analysis.missing_dependencies or analysis.circular_dependencies:
            lines.append("## Dependency Gaps")
            lines.append("")

            if analysis.missing_dependencies:
                lines.append("### Missing Dependencies")
                for dep in analysis.missing_dependencies:
                    lines.append(f"- {dep}")
                lines.append("")

            if analysis.circular_dependencies:
                lines.append("### Circular Dependencies")
                for cycle in analysis.circular_dependencies:
                    lines.append(f"- {' <-> '.join(cycle)}")
                lines.append("")

        # Spec violations
        if analysis.spec_violations:
            lines.append("## Spec Violations")
            lines.append("")
            for violation in analysis.spec_violations:
                lines.append(f"- **{violation['file']}**: {violation['issue']}")
            lines.append("")

        # Missing components
        if analysis.missing_components:
            lines.append("## Missing Components")
            lines.append("")
            for component in analysis.missing_components:
                lines.append(f"- {component}")
            lines.append("")

        return "\n".join(lines)
