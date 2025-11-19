"""
Codebase Analyzer - Scans existing projects to extract structure and features.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json


@dataclass
class AnalysisResult:
    """Results from codebase analysis"""
    project_root: str
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    architecture: str = "unknown"
    features: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    api_endpoints: List[Dict[str, str]] = field(default_factory=list)
    database: Optional[str] = None
    test_coverage: float = 0.0
    file_count: int = 0
    lines_of_code: int = 0


class CodebaseAnalyzer:
    """Analyze existing codebases to extract project information"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.ignore_dirs = {
            'node_modules', 'venv', '.venv', 'env', '__pycache__',
            '.git', 'dist', 'build', '.next', '.nuxt', 'target'
        }

    def scan_project(self) -> AnalysisResult:
        """Comprehensive project scan"""
        result = AnalysisResult(project_root=str(self.project_root))

        # Detect languages
        result.languages = self._detect_languages()

        # Detect frameworks
        result.frameworks = self._detect_frameworks()

        # Detect architecture
        result.architecture = self._detect_architecture()

        # Extract features
        result.features = self._extract_features()

        # Scan dependencies
        result.dependencies = self._scan_dependencies()

        # Find API endpoints
        result.api_endpoints = self._find_api_endpoints()

        # Detect database
        result.database = self._detect_database()

        # Calculate stats
        result.file_count, result.lines_of_code = self._calculate_stats()

        # Test coverage (basic estimation)
        result.test_coverage = self._estimate_test_coverage()

        return result

    def _detect_languages(self) -> List[str]:
        """Detect programming languages used"""
        extensions = {}

        for file_path in self._walk_files():
            ext = file_path.suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1

        # Map extensions to languages
        lang_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.jsx': 'JavaScript',
            '.go': 'Go',
            '.rs': 'Rust',
            '.java': 'Java',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.cs': 'C#',
            '.cpp': 'C++',
            '.c': 'C',
            '.swift': 'Swift',
            '.kt': 'Kotlin'
        }

        languages = []
        for ext, lang in lang_map.items():
            if ext in extensions and extensions[ext] >= 3:  # At least 3 files
                languages.append(lang)

        return sorted(languages)

    def _detect_frameworks(self) -> List[str]:
        """Detect frameworks and libraries"""
        frameworks = []

        # Python frameworks
        if (self.project_root / 'requirements.txt').exists():
            content = (self.project_root / 'requirements.txt').read_text()
            if 'django' in content.lower():
                frameworks.append('Django')
            if 'flask' in content.lower():
                frameworks.append('Flask')
            if 'fastapi' in content.lower():
                frameworks.append('FastAPI')

        if (self.project_root / 'pyproject.toml').exists():
            content = (self.project_root / 'pyproject.toml').read_text()
            if 'fastapi' in content.lower():
                frameworks.append('FastAPI')
            if 'typer' in content.lower():
                frameworks.append('Typer')

        # JavaScript/TypeScript frameworks
        if (self.project_root / 'package.json').exists():
            try:
                pkg = json.loads((self.project_root / 'package.json').read_text())
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

                if 'react' in deps:
                    frameworks.append('React')
                if 'vue' in deps:
                    frameworks.append('Vue')
                if 'next' in deps:
                    frameworks.append('Next.js')
                if 'express' in deps:
                    frameworks.append('Express')
                if 'nest' in deps or '@nestjs/core' in deps:
                    frameworks.append('NestJS')
            except:
                pass

        # Go frameworks
        if (self.project_root / 'go.mod').exists():
            content = (self.project_root / 'go.mod').read_text()
            if 'gin-gonic' in content:
                frameworks.append('Gin')
            if 'echo' in content:
                frameworks.append('Echo')

        return sorted(set(frameworks))

    def _detect_architecture(self) -> str:
        """Detect architectural pattern"""
        dirs = {d.name for d in self.project_root.iterdir() if d.is_dir()}

        # MVC pattern
        if {'models', 'views', 'controllers'}.issubset(dirs):
            return 'MVC'

        # Clean Architecture
        if {'core', 'api', 'infrastructure'}.issubset(dirs):
            return 'Clean Architecture'

        # Microservices
        if 'services' in dirs:
            service_dir = self.project_root / 'services'
            if service_dir.is_dir():
                services = [d for d in service_dir.iterdir() if d.is_dir()]
                if len(services) >= 2:
                    return 'Microservices'

        # Monolith with modules
        if {'cli', 'core', 'api'}.issubset(dirs):
            return 'Modular Monolith'

        return 'Standard'

    def _extract_features(self) -> List[Dict[str, Any]]:
        """Extract features from code structure"""
        features = []

        # Python: Find classes and functions
        if 'Python' in self._detect_languages():
            features.extend(self._extract_python_features())

        # JavaScript/TypeScript: Find components and routes
        if 'JavaScript' in self._detect_languages() or 'TypeScript' in self._detect_languages():
            features.extend(self._extract_js_features())

        return features

    def _extract_python_features(self) -> List[Dict[str, Any]]:
        """Extract features from Python codebase"""
        features = []

        # Look for FastAPI/Flask routes
        for file_path in self._walk_files(['.py']):
            try:
                content = file_path.read_text()

                # FastAPI routes
                routes = re.findall(r'@\w+\.(?:get|post|put|delete|patch)\(["\']([^"\']+)', content)
                for route in routes:
                    features.append({
                        'name': f'API Endpoint: {route}',
                        'type': 'api',
                        'file': str(file_path.relative_to(self.project_root)),
                        'confidence': 0.9
                    })

                # CLI commands (Typer/Click)
                commands = re.findall(r'@\w+\.command\(["\']?([^"\'\)]*)', content)
                for cmd in commands:
                    if cmd:
                        features.append({
                            'name': f'CLI Command: {cmd}',
                            'type': 'cli',
                            'file': str(file_path.relative_to(self.project_root)),
                            'confidence': 0.8
                        })
            except:
                pass

        return features

    def _extract_js_features(self) -> List[Dict[str, Any]]:
        """Extract features from JavaScript/TypeScript codebase"""
        features = []

        # Look for React components
        for file_path in self._walk_files(['.tsx', '.jsx', '.ts', '.js']):
            try:
                content = file_path.read_text()

                # React components
                components = re.findall(r'(?:export\s+)?(?:function|const)\s+(\w+)\s*(?:\(|=)', content)
                if 'return' in content and '<' in content:  # Likely JSX
                    for comp in components[:1]:  # First component per file
                        features.append({
                            'name': f'Component: {comp}',
                            'type': 'ui',
                            'file': str(file_path.relative_to(self.project_root)),
                            'confidence': 0.7
                        })
            except:
                pass

        return features

    def _find_api_endpoints(self) -> List[Dict[str, str]]:
        """Find API endpoints"""
        endpoints = []

        for file_path in self._walk_files(['.py', '.js', '.ts']):
            try:
                content = file_path.read_text()

                # FastAPI/Flask
                for method in ['get', 'post', 'put', 'delete', 'patch']:
                    pattern = rf'@\w+\.{method}\(["\']([^"\']+)'
                    for route in re.findall(pattern, content):
                        endpoints.append({
                            'method': method.upper(),
                            'path': route,
                            'file': str(file_path.relative_to(self.project_root))
                        })
            except:
                pass

        return endpoints

    def _scan_dependencies(self) -> Dict[str, List[str]]:
        """Scan project dependencies"""
        deps = {}

        # Python
        if (self.project_root / 'requirements.txt').exists():
            deps['python'] = []
            for line in (self.project_root / 'requirements.txt').read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    pkg = line.split('>=')[0].split('==')[0].strip()
                    deps['python'].append(pkg)

        # Node
        if (self.project_root / 'package.json').exists():
            try:
                pkg = json.loads((self.project_root / 'package.json').read_text())
                deps['node'] = list(pkg.get('dependencies', {}).keys())
            except:
                pass

        return deps

    def _detect_database(self) -> Optional[str]:
        """Detect database usage"""
        # Check for database-related files/dependencies
        if (self.project_root / 'requirements.txt').exists():
            content = (self.project_root / 'requirements.txt').read_text().lower()
            if 'psycopg' in content or 'postgresql' in content:
                return 'PostgreSQL'
            if 'mysql' in content:
                return 'MySQL'
            if 'sqlite' in content:
                return 'SQLite'
            if 'mongodb' in content or 'pymongo' in content:
                return 'MongoDB'

        return None

    def _calculate_stats(self) -> tuple[int, int]:
        """Calculate file count and lines of code"""
        file_count = 0
        total_lines = 0

        for file_path in self._walk_files():
            file_count += 1
            try:
                total_lines += len(file_path.read_text().splitlines())
            except:
                pass

        return file_count, total_lines

    def _estimate_test_coverage(self) -> float:
        """Estimate test coverage based on test files"""
        test_files = 0
        source_files = 0

        for file_path in self._walk_files(['.py', '.js', '.ts']):
            if 'test' in file_path.name.lower() or file_path.parent.name == 'tests':
                test_files += 1
            else:
                source_files += 1

        if source_files == 0:
            return 0.0

        # Rough estimate: if 1 test file per 3 source files, ~30% coverage
        return min((test_files / source_files) * 100, 100.0) if source_files > 0 else 0.0

    def _walk_files(self, extensions: Optional[List[str]] = None) -> List[Path]:
        """Walk all files in project, respecting ignore rules"""
        files = []

        for root, dirs, filenames in os.walk(self.project_root):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

            for filename in filenames:
                file_path = Path(root) / filename

                if extensions:
                    if file_path.suffix in extensions:
                        files.append(file_path)
                else:
                    files.append(file_path)

        return files
