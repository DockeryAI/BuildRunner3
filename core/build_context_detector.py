"""
Build Context Detector
Analyzes changed files to determine tech stack and build type
"""

import subprocess
from pathlib import Path
from typing import List, Set, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import yaml
import fnmatch


class BuildType(Enum):
    """Type of build detected"""
    PYTHON_ONLY = "python"
    TYPESCRIPT_ONLY = "typescript"
    REACT = "react"
    FULL_STACK = "fullstack"
    DATABASE = "database"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    MIXED = "mixed"


class TechStack(Enum):
    """Technologies detected in the build"""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    REACT = "react"
    FASTAPI = "fastapi"
    FLASK = "flask"
    SQLALCHEMY = "sqlalchemy"
    PYTEST = "pytest"
    JEST = "jest"


@dataclass
class BuildContext:
    """Context information about a build"""
    build_type: BuildType
    tech_stack: Set[TechStack]
    changed_files: List[Path]
    python_files: List[Path]
    typescript_files: List[Path]
    react_files: List[Path]
    test_files: List[Path]
    config_files: List[Path]
    has_backend_changes: bool
    has_frontend_changes: bool
    has_database_changes: bool
    has_test_changes: bool
    project_root: Path


class BuildContextDetector:
    """Detects build context from file changes"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.exclude_patterns = self._load_exclude_patterns()

    def _load_exclude_patterns(self) -> List[str]:
        """Load exclude patterns from autodebug.yaml"""
        autodebug_file = self.project_root / '.buildrunner' / 'autodebug.yaml'
        if not autodebug_file.exists():
            return []

        try:
            with open(autodebug_file) as f:
                config = yaml.safe_load(f)
                return config.get('exclude', [])
        except Exception:
            return []

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file matches any exclude pattern"""
        try:
            rel_path = file_path.relative_to(self.project_root)
            rel_path_str = str(rel_path)
        except ValueError:
            rel_path_str = str(file_path)

        for pattern in self.exclude_patterns:
            # Handle directory patterns (ending with /**)
            if pattern.endswith('/**'):
                dir_pattern = pattern.rstrip('/**')
                if any(part == dir_pattern for part in file_path.parts):
                    return True

            # Handle glob patterns
            if fnmatch.fnmatch(rel_path_str, pattern):
                return True

            # Handle ** patterns (match any directory depth)
            if '**' in pattern:
                # Simplify: just check if any part matches the non-** portion
                base_pattern = pattern.replace('/**', '').replace('**/', '')
                if base_pattern in file_path.parts:
                    return True

        return False

    def detect_from_git(self, base_branch: str = "HEAD~1") -> BuildContext:
        """Detect context from git changes since base_branch"""
        changed_files = self._get_changed_files(base_branch)
        return self._analyze_files(changed_files)

    def detect_from_files(self, files: List[str]) -> BuildContext:
        """Detect context from explicit list of files"""
        changed_files = [Path(f) for f in files]
        return self._analyze_files(changed_files)

    def _get_changed_files(self, base: str) -> List[Path]:
        """Get list of changed files from git"""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                files = [
                    self.project_root / f.strip()
                    for f in result.stdout.split('\n')
                    if f.strip()
                ]
                return files

        except Exception as e:
            print(f"Warning: Could not get git changes: {e}")

        return []

    def _analyze_files(self, files: List[Path]) -> BuildContext:
        """Analyze files to determine build context"""

        # Filter out excluded files first
        files = [f for f in files if not self._should_exclude(f)]

        # Categorize files by type
        python_files = [f for f in files if f.suffix == '.py']
        typescript_files = [f for f in files if f.suffix in {'.ts', '.tsx'}]
        javascript_files = [f for f in files if f.suffix in {'.js', '.jsx'}]
        test_files = [
            f for f in files
            if 'test' in f.name.lower() or f.parts and 'tests' in f.parts
        ]
        config_files = [
            f for f in files
            if f.suffix in {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'}
            or f.name in {'Dockerfile', 'docker-compose.yml', 'requirements.txt', 'package.json'}
        ]

        # Identify React files
        react_files = []
        for f in typescript_files + javascript_files:
            if self._is_react_file(f):
                react_files.append(f)

        # Determine tech stack
        tech_stack = set()
        if python_files:
            tech_stack.add(TechStack.PYTHON)
            if self._has_fastapi(python_files):
                tech_stack.add(TechStack.FASTAPI)
            if self._has_flask(python_files):
                tech_stack.add(TechStack.FLASK)
            if self._has_sqlalchemy(python_files):
                tech_stack.add(TechStack.SQLALCHEMY)

        if typescript_files:
            tech_stack.add(TechStack.TYPESCRIPT)

        if javascript_files:
            tech_stack.add(TechStack.JAVASCRIPT)

        if react_files:
            tech_stack.add(TechStack.REACT)

        if test_files:
            if any(f.suffix == '.py' for f in test_files):
                tech_stack.add(TechStack.PYTEST)
            if any(f.suffix in {'.ts', '.tsx', '.js', '.jsx'} for f in test_files):
                tech_stack.add(TechStack.JEST)

        # Determine build type
        has_backend = bool(python_files) and any(
            'api' in str(f) or 'core' in str(f) or 'cli' in str(f)
            for f in python_files
        )
        has_frontend = bool(typescript_files or javascript_files or react_files)
        has_database = any(
            'models' in str(f) or 'migrations' in str(f) or 'schema' in str(f)
            for f in files
        )

        # Determine primary build type
        if has_backend and has_frontend:
            build_type = BuildType.FULL_STACK
        elif react_files:
            build_type = BuildType.REACT
        elif typescript_files and not python_files:
            build_type = BuildType.TYPESCRIPT_ONLY
        elif python_files and not typescript_files and not javascript_files:
            build_type = BuildType.PYTHON_ONLY
        elif has_database:
            build_type = BuildType.DATABASE
        elif config_files and len(config_files) == len(files):
            build_type = BuildType.CONFIG
        elif all(f.suffix in {'.md', '.txt', '.rst'} for f in files):
            build_type = BuildType.DOCUMENTATION
        else:
            build_type = BuildType.MIXED

        return BuildContext(
            build_type=build_type,
            tech_stack=tech_stack,
            changed_files=files,
            python_files=python_files,
            typescript_files=typescript_files,
            react_files=react_files,
            test_files=test_files,
            config_files=config_files,
            has_backend_changes=has_backend,
            has_frontend_changes=has_frontend,
            has_database_changes=has_database,
            has_test_changes=bool(test_files),
            project_root=self.project_root
        )

    def _is_react_file(self, file_path: Path) -> bool:
        """Check if file is a React component"""
        if file_path.suffix not in {'.tsx', '.jsx', '.ts', '.js'}:
            return False

        try:
            content = file_path.read_text()
            # Simple heuristic: check for React imports or JSX syntax
            return (
                'import React' in content or
                'from "react"' in content or
                'from \'react\'' in content or
                '</' in content  # JSX closing tags
            )
        except Exception:
            return False

    def _has_fastapi(self, python_files: List[Path]) -> bool:
        """Check if FastAPI is used"""
        for f in python_files:
            try:
                content = f.read_text()
                if 'from fastapi' in content or 'import fastapi' in content:
                    return True
            except Exception:
                continue
        return False

    def _has_flask(self, python_files: List[Path]) -> bool:
        """Check if Flask is used"""
        for f in python_files:
            try:
                content = f.read_text()
                if 'from flask' in content or 'import flask' in content:
                    return True
            except Exception:
                continue
        return False

    def _has_sqlalchemy(self, python_files: List[Path]) -> bool:
        """Check if SQLAlchemy is used"""
        for f in python_files:
            try:
                content = f.read_text()
                if 'from sqlalchemy' in content or 'import sqlalchemy' in content:
                    return True
            except Exception:
                continue
        return False
