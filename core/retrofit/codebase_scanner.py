"""Codebase scanner - analyzes project structure and extracts code artifacts"""

import ast
import time
import logging
from pathlib import Path
from typing import List, Set, Optional
from dataclasses import dataclass

from .models import CodeArtifact, ArtifactType, ScanResult

logger = logging.getLogger(__name__)


# Directories to skip
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.pytest_cache', '.mypy_cache',
    'venv', '.venv', 'env', '.env', 'build', 'dist', '.tox', 'htmlcov',
    '.eggs', '*.egg-info', '.next', 'out', 'coverage', '.nyc_output'
}

# File patterns to skip
SKIP_PATTERNS = {
    '.pyc', '.pyo', '.so', '.dylib', '.dll', '.log', '.lock',
    'package-lock.json', 'yarn.lock', 'poetry.lock'
}


class PythonAnalyzer(ast.NodeVisitor):
    """AST visitor to extract Python code artifacts"""

    def __init__(self, file_path: Path, source: str):
        self.file_path = file_path
        self.source = source
        self.artifacts: List[CodeArtifact] = []
        self.current_class: Optional[str] = None
        self.imports: List[str] = []

    def visit_Import(self, node: ast.Import):
        """Track imports"""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports"""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function definitions"""
        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]

        # Check if it's a route
        is_route = any(d in ['app.get', 'app.post', 'app.put', 'app.delete',
                             'router.get', 'router.post', 'router.put', 'router.delete',
                             'route', 'api_route'] for d in decorators)

        # Check if it's a test
        is_test = (node.name.startswith('test_') or
                   self.file_path.name.startswith('test_') or
                   'test' in str(self.file_path).lower())

        # Determine artifact type
        if is_route:
            artifact_type = ArtifactType.ROUTE
        elif is_test:
            artifact_type = ArtifactType.TEST
        elif self.current_class:
            artifact_type = ArtifactType.METHOD
        else:
            artifact_type = ArtifactType.FUNCTION

        # Get docstring
        docstring = ast.get_docstring(node)

        # Create artifact
        artifact = CodeArtifact(
            type=artifact_type,
            name=f"{self.current_class}.{node.name}" if self.current_class else node.name,
            file_path=self.file_path,
            line_number=node.lineno,
            docstring=docstring,
            decorators=decorators,
            imports=self.imports.copy(),
            metadata={
                'args': [arg.arg for arg in node.args.args],
                'is_async': isinstance(node, ast.AsyncFunctionDef),
            }
        )

        self.artifacts.append(artifact)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Handle async functions"""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class definitions"""
        # Get docstring
        docstring = ast.get_docstring(node)

        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]

        # Get base classes
        bases = [self._get_name(base) for base in node.bases]

        # Determine if it's a model (database model)
        is_model = any(base in ['Base', 'Model', 'Document', 'BaseModel']
                       for base in bases)

        # Create artifact
        artifact = CodeArtifact(
            type=ArtifactType.MODEL if is_model else ArtifactType.CLASS,
            name=node.name,
            file_path=self.file_path,
            line_number=node.lineno,
            docstring=docstring,
            decorators=decorators,
            metadata={
                'bases': bases,
                'is_model': is_model,
            }
        )

        self.artifacts.append(artifact)

        # Visit methods within this class
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_name(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return str(decorator)

    def _get_name(self, node) -> str:
        """Extract name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)


class CodebaseScanner:
    """
    Scans codebase and extracts code artifacts

    Currently supports:
    - Python (via AST)
    - JavaScript/TypeScript (basic, extensible)
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.artifacts: List[CodeArtifact] = []
        self.total_files = 0
        self.total_lines = 0
        self.languages: Set[str] = set()
        self.frameworks: Set[str] = set()

    def scan(self) -> ScanResult:
        """
        Scan the codebase and extract artifacts

        Returns:
            ScanResult with all extracted artifacts
        """
        logger.info(f"Scanning codebase at {self.project_root}")
        start_time = time.time()

        # Detect languages and frameworks
        self._detect_languages()
        self._detect_frameworks()

        # Scan files
        if 'python' in self.languages:
            self._scan_python_files()

        # More languages can be added here
        # if 'javascript' in self.languages:
        #     self._scan_js_files()

        duration = time.time() - start_time

        result = ScanResult(
            project_root=self.project_root,
            project_name=self.project_root.name,
            languages=list(self.languages),
            frameworks=list(self.frameworks),
            artifacts=self.artifacts,
            total_files=self.total_files,
            total_lines=self.total_lines,
            scan_duration_seconds=duration
        )

        logger.info(f"Scan complete: {result.summary}")
        return result

    def _detect_languages(self):
        """Detect programming languages in the project"""
        for ext in ['.py', '.js', '.ts', '.tsx', '.go', '.java', '.rb']:
            if list(self.project_root.rglob(f'*{ext}')):
                if ext == '.py':
                    self.languages.add('python')
                elif ext in ['.js', '.ts', '.tsx']:
                    self.languages.add('javascript')
                elif ext == '.go':
                    self.languages.add('go')
                elif ext == '.java':
                    self.languages.add('java')
                elif ext == '.rb':
                    self.languages.add('ruby')

        logger.info(f"Detected languages: {self.languages}")

    def _detect_frameworks(self):
        """Detect frameworks used in the project"""
        # Check for framework indicators
        if (self.project_root / 'requirements.txt').exists():
            req_text = (self.project_root / 'requirements.txt').read_text()
            if 'fastapi' in req_text.lower():
                self.frameworks.add('FastAPI')
            if 'flask' in req_text.lower():
                self.frameworks.add('Flask')
            if 'django' in req_text.lower():
                self.frameworks.add('Django')

        if (self.project_root / 'package.json').exists():
            pkg_text = (self.project_root / 'package.json').read_text()
            if 'react' in pkg_text.lower():
                self.frameworks.add('React')
            if 'next' in pkg_text.lower():
                self.frameworks.add('Next.js')
            if 'express' in pkg_text.lower():
                self.frameworks.add('Express')
            if 'vue' in pkg_text.lower():
                self.frameworks.add('Vue')

        logger.info(f"Detected frameworks: {self.frameworks}")

    def _scan_python_files(self):
        """Scan all Python files in the project"""
        logger.info("Scanning Python files...")

        for py_file in self._iter_source_files('*.py'):
            try:
                self._analyze_python_file(py_file)
            except Exception as e:
                logger.warning(f"Error analyzing {py_file}: {e}")

        logger.info(f"Found {len(self.artifacts)} Python artifacts")

    def _analyze_python_file(self, file_path: Path):
        """Analyze a single Python file"""
        try:
            source = file_path.read_text(encoding='utf-8')
            self.total_files += 1
            self.total_lines += len(source.splitlines())

            # Parse AST
            tree = ast.parse(source, filename=str(file_path))

            # Extract artifacts
            analyzer = PythonAnalyzer(file_path, source)
            analyzer.visit(tree)

            self.artifacts.extend(analyzer.artifacts)

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

    def _iter_source_files(self, pattern: str):
        """Iterate over source files matching pattern, skipping ignored dirs"""
        for file_path in self.project_root.rglob(pattern):
            # Check if any part of the path is in skip dirs
            if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
                continue

            # Check if file suffix matches skip patterns
            if any(file_path.name.endswith(pattern) for pattern in SKIP_PATTERNS):
                continue

            # Skip hidden files
            if any(part.startswith('.') for part in file_path.parts[len(self.project_root.parts):]):
                continue

            yield file_path
