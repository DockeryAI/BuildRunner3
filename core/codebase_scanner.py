"""
Codebase Scanner - Analyze actual implementation against spec

Scans codebase to identify:
- Implemented files
- Functions and classes
- API endpoints
- UI components
- Test coverage
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field


@dataclass
class FileInfo:
    """Information about a scanned file"""
    path: str
    exists: bool
    line_count: int = 0
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    has_tests: bool = False
    has_docstrings: bool = False


@dataclass
class EndpointInfo:
    """Information about an API endpoint"""
    path: str
    method: str
    file: str
    line: int
    has_tests: bool = False


@dataclass
class ComponentInfo:
    """Information about a UI component"""
    name: str
    file: str
    has_tests: bool = False
    is_connected: bool = False  # Connected to backend


class CodebaseScanner:
    """
    Scan codebase to analyze implementation.

    Features:
    - File existence checking
    - Python code analysis (functions, classes)
    - API endpoint detection
    - Test coverage analysis
    - Import dependency analysis
    """

    def __init__(self, project_root: Path):
        """
        Initialize CodebaseScanner.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root)

    def scan_file(self, file_path: str) -> FileInfo:
        """
        Scan a single file for implementation details.

        Args:
            file_path: Relative file path from project root

        Returns:
            FileInfo with scan results
        """
        full_path = self.project_root / file_path

        if not full_path.exists():
            return FileInfo(path=file_path, exists=False)

        # Get line count
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                line_count = len(content.splitlines())
        except Exception:
            return FileInfo(path=file_path, exists=True, line_count=0)

        # Parse Python files
        if file_path.endswith('.py'):
            return self._scan_python_file(file_path, content)

        # For other files, just return basic info
        return FileInfo(
            path=file_path,
            exists=True,
            line_count=line_count
        )

    def scan_files(self, file_paths: List[str]) -> Dict[str, FileInfo]:
        """
        Scan multiple files.

        Args:
            file_paths: List of file paths to scan

        Returns:
            Dict mapping file path to FileInfo
        """
        results = {}
        for file_path in file_paths:
            results[file_path] = self.scan_file(file_path)
        return results

    def find_api_endpoints(self) -> List[EndpointInfo]:
        """
        Find all API endpoints in the codebase.

        Returns:
            List of EndpointInfo for all endpoints
        """
        endpoints = []
        api_dir = self.project_root / "api"

        if not api_dir.exists():
            return endpoints

        # Scan all Python files in api/
        for py_file in api_dir.rglob("*.py"):
            if py_file.name.startswith('_'):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for FastAPI route decorators
                endpoint_patterns = [
                    r'@app\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                    r'@router\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                ]

                for pattern in endpoint_patterns:
                    for match in re.finditer(pattern, content):
                        method = match.group(1).upper()
                        path = match.group(2)

                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1

                        # Check if has tests
                        has_tests = self._endpoint_has_tests(path, method)

                        endpoints.append(EndpointInfo(
                            path=path,
                            method=method,
                            file=str(py_file.relative_to(self.project_root)),
                            line=line_num,
                            has_tests=has_tests
                        ))

            except Exception:
                continue

        return endpoints

    def find_components(self) -> List[ComponentInfo]:
        """
        Find all UI components in the codebase.

        Returns:
            List of ComponentInfo for all components
        """
        components = []
        # This is a placeholder - would need to scan frontend files
        # based on the project's frontend framework
        return components

    def check_test_coverage(self, file_path: str) -> bool:
        """
        Check if file has corresponding test file.

        Args:
            file_path: File path to check

        Returns:
            True if test file exists
        """
        # Convert file path to test path
        if file_path.startswith('core/') or file_path.startswith('cli/'):
            test_path = f"tests/test_{Path(file_path).name}"
        elif file_path.startswith('api/'):
            test_path = f"tests/test_api_{Path(file_path).stem}.py"
        else:
            test_path = f"tests/test_{Path(file_path).stem}.py"

        test_file = self.project_root / test_path
        return test_file.exists()

    def get_missing_files(self, expected_files: List[str]) -> List[str]:
        """
        Get list of expected files that don't exist.

        Args:
            expected_files: List of expected file paths

        Returns:
            List of missing file paths
        """
        missing = []
        for file_path in expected_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing.append(file_path)
        return missing

    def get_implemented_files(self, file_paths: List[str]) -> List[str]:
        """
        Get list of files that exist.

        Args:
            file_paths: List of file paths to check

        Returns:
            List of existing file paths
        """
        implemented = []
        for file_path in file_paths:
            full_path = self.project_root / file_path
            if full_path.exists():
                implemented.append(file_path)
        return implemented

    def _scan_python_file(self, file_path: str, content: str) -> FileInfo:
        """Scan Python file with AST"""
        info = FileInfo(
            path=file_path,
            exists=True,
            line_count=len(content.splitlines())
        )

        try:
            tree = ast.parse(content)

            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    info.functions.append(node.name)
                    # Check for docstring
                    if ast.get_docstring(node):
                        info.has_docstrings = True

                elif isinstance(node, ast.ClassDef):
                    info.classes.append(node.name)
                    # Check for docstring
                    if ast.get_docstring(node):
                        info.has_docstrings = True

                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        info.imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        info.imports.append(node.module)

            # Check for module docstring
            if ast.get_docstring(tree):
                info.has_docstrings = True

        except SyntaxError:
            # File has syntax errors, mark as exists but empty
            pass

        # Check if has tests
        info.has_tests = self.check_test_coverage(file_path)

        return info

    def _endpoint_has_tests(self, path: str, method: str) -> bool:
        """Check if endpoint has tests"""
        # Look for test files that might test this endpoint
        tests_dir = self.project_root / "tests"

        if not tests_dir.exists():
            return False

        # Simple heuristic: check if test files mention the endpoint path
        for test_file in tests_dir.glob("test_api*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if path in content and method.lower() in content.lower():
                        return True
            except Exception:
                continue

        return False

    def analyze_dependencies(self) -> Dict[str, List[str]]:
        """
        Analyze import dependencies across codebase.

        Returns:
            Dict mapping file path to list of imported modules
        """
        dependencies = {}

        for py_file in self.project_root.rglob("*.py"):
            if py_file.is_dir() or py_file.name.startswith('_'):
                continue

            try:
                relative_path = str(py_file.relative_to(self.project_root))
                info = self.scan_file(relative_path)
                dependencies[relative_path] = info.imports
            except Exception:
                continue

        return dependencies
