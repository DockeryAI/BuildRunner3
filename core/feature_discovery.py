"""
Feature Discovery - Automatically discover features from codebase

Scans codebase to identify:
- Core features and capabilities
- API endpoints and their purposes
- UI components and user flows
- CLI commands and functionality
- Data models and schemas
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DiscoveredFeature:
    """A feature discovered from the codebase"""
    title: str
    description: str
    component: str  # File or module path
    priority: str = "medium"  # high, medium, low
    status: str = "implemented"  # implemented, partial, planned
    version: str = "1.0"
    endpoints: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class FeatureDiscovery:
    """
    Discover features from codebase automatically.

    Strategies:
    1. API Routes → Backend Features
    2. CLI Commands → Command-Line Features
    3. UI Components → Frontend Features
    4. Core Modules → System Features
    5. Database Models → Data Features
    """

    def __init__(self, project_root: Path):
        """Initialize feature discovery"""
        self.project_root = Path(project_root)
        self.features: List[DiscoveredFeature] = []

    def discover_all(self) -> List[DiscoveredFeature]:
        """
        Run all discovery strategies.

        Returns:
            List of discovered features
        """
        self.features = []

        # Run discovery strategies
        self._discover_from_api()
        self._discover_from_cli()
        self._discover_from_ui()
        self._discover_from_core()
        self._discover_from_models()

        return self.features

    def _discover_from_api(self):
        """Discover features from API routes"""
        api_dir = self.project_root / "api"
        if not api_dir.exists():
            return

        # Group endpoints by route file
        route_files = list(api_dir.glob("**/routes/*.py")) + list(api_dir.glob("**/*_api.py"))

        for route_file in route_files:
            if route_file.name.startswith('_'):
                continue

            try:
                with open(route_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract module docstring for feature description
                tree = ast.parse(content)
                module_doc = ast.get_docstring(tree) or ""

                # Find all endpoints
                endpoints = self._extract_endpoints(content)

                if endpoints:
                    # Create feature from API routes
                    feature_name = route_file.stem.replace('_', ' ').replace('routes', '').strip().title()
                    if not feature_name:
                        feature_name = "API Endpoints"

                    # Generate description from docstring or endpoints
                    if module_doc:
                        description = module_doc.split('\n')[0]
                    else:
                        description = f"API endpoints for {feature_name.lower()}"

                    # Extract acceptance criteria from docstrings
                    criteria = self._extract_acceptance_criteria_from_code(content)

                    feature = DiscoveredFeature(
                        title=feature_name,
                        description=description,
                        component=str(route_file.relative_to(self.project_root)),
                        priority="high",
                        endpoints=[f"{ep['method']} {ep['path']}" for ep in endpoints],
                        files=[str(route_file.relative_to(self.project_root))],
                        acceptance_criteria=criteria,
                        version="1.0"
                    )

                    self.features.append(feature)

            except Exception as e:
                print(f"Error scanning {route_file}: {e}")
                continue

    def _discover_from_cli(self):
        """Discover features from CLI commands"""
        cli_dir = self.project_root / "cli"
        if not cli_dir.exists():
            return

        for cli_file in cli_dir.glob("*.py"):
            if cli_file.name.startswith('_') or cli_file.name == 'main.py':
                continue

            try:
                with open(cli_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for typer/click commands
                commands = self._extract_cli_commands(content)

                if commands:
                    feature_name = cli_file.stem.replace('_commands', '').replace('_', ' ').title()

                    # Get module docstring
                    tree = ast.parse(content)
                    module_doc = ast.get_docstring(tree) or f"{feature_name} command-line interface"

                    feature = DiscoveredFeature(
                        title=f"CLI: {feature_name}",
                        description=module_doc.split('\n')[0],
                        component=str(cli_file.relative_to(self.project_root)),
                        priority="medium",
                        functions=[cmd['name'] for cmd in commands],
                        files=[str(cli_file.relative_to(self.project_root))],
                        acceptance_criteria=[f"Command '{cmd['name']}' executes successfully" for cmd in commands],
                        version="1.0"
                    )

                    self.features.append(feature)

            except Exception:
                continue

    def _discover_from_ui(self):
        """Discover features from UI components"""
        ui_dir = self.project_root / "ui" / "src" / "components"
        if not ui_dir.exists():
            return

        for ui_file in ui_dir.glob("*.tsx"):
            if ui_file.name.startswith('_'):
                continue

            try:
                with open(ui_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract component name and description from comments
                component_name = ui_file.stem

                # Look for JSDoc or leading comments
                doc_match = re.search(r'/\*\*\s*\n\s*\*\s*(.*?)\n', content)
                description = doc_match.group(1).strip() if doc_match else f"{component_name} UI component"

                # Check if it's a major feature (not a util component)
                if any(keyword in component_name.lower() for keyword in ['workspace', 'editor', 'builder', 'wizard', 'picker', 'modal']):
                    feature = DiscoveredFeature(
                        title=f"UI: {component_name.replace('UI', '').replace('Component', '')}",
                        description=description,
                        component=str(ui_file.relative_to(self.project_root)),
                        priority="high",
                        files=[str(ui_file.relative_to(self.project_root))],
                        version="1.0"
                    )

                    self.features.append(feature)

            except Exception:
                continue

    def _discover_from_core(self):
        """Discover features from core modules"""
        core_dir = self.project_root / "core"
        if not core_dir.exists():
            return

        # Look for major subsystems
        for subdir in core_dir.iterdir():
            if not subdir.is_dir() or subdir.name.startswith('_'):
                continue

            # Check for __init__.py with exports
            init_file = subdir / "__init__.py"
            if init_file.exists():
                try:
                    with open(init_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    tree = ast.parse(content)
                    module_doc = ast.get_docstring(tree) or ""

                    # Find all exported classes
                    exports = self._extract_exports(content)

                    if exports:
                        feature_name = subdir.name.replace('_', ' ').title()

                        feature = DiscoveredFeature(
                            title=f"Core: {feature_name}",
                            description=module_doc.split('\n')[0] if module_doc else f"{feature_name} system",
                            component=str(subdir.relative_to(self.project_root)),
                            priority="high",
                            classes=exports,
                            files=[str(f.relative_to(self.project_root)) for f in subdir.glob("*.py")],
                            version="1.0"
                        )

                        self.features.append(feature)

                except Exception:
                    continue

    def _discover_from_models(self):
        """Discover features from data models"""
        # Look for Pydantic models or database schemas
        model_patterns = [
            self.project_root / "models",
            self.project_root / "core" / "models",
            self.project_root / "api" / "models"
        ]

        for model_dir in model_patterns:
            if not model_dir.exists():
                continue

            for model_file in model_dir.glob("*.py"):
                if model_file.name.startswith('_'):
                    continue

                try:
                    with open(model_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    tree = ast.parse(content)
                    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

                    if classes:
                        feature = DiscoveredFeature(
                            title=f"Data: {model_file.stem.replace('_', ' ').title()}",
                            description=f"Data models for {model_file.stem.replace('_', ' ')}",
                            component=str(model_file.relative_to(self.project_root)),
                            priority="medium",
                            classes=classes,
                            files=[str(model_file.relative_to(self.project_root))],
                            version="1.0"
                        )

                        self.features.append(feature)

                except Exception:
                    continue

    def _extract_endpoints(self, content: str) -> List[Dict]:
        """Extract API endpoints from file content"""
        endpoints = []

        patterns = [
            r'@(?:app|router)\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                endpoints.append({
                    'method': match.group(1).upper(),
                    'path': match.group(2)
                })

        return endpoints

    def _extract_cli_commands(self, content: str) -> List[Dict]:
        """Extract CLI commands from file content"""
        commands = []

        # Look for function definitions with @app.command() decorator
        pattern = r'@(?:app|cli)\.command\(\)\s*\ndef\s+(\w+)'

        for match in re.finditer(pattern, content):
            commands.append({
                'name': match.group(1)
            })

        # Also look for plain function definitions in CLI files
        if not commands:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    commands.append({'name': node.name})

        return commands

    def _extract_exports(self, content: str) -> List[str]:
        """Extract __all__ exports from module"""
        exports = []

        # Look for __all__ = [...]
        match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            exports_str = match.group(1)
            # Extract quoted strings
            for export_match in re.finditer(r'["\']([^"\']+)["\']', exports_str):
                exports.append(export_match.group(1))

        return exports

    def _extract_acceptance_criteria_from_code(self, content: str) -> List[str]:
        """Extract acceptance criteria from comments and docstrings"""
        criteria = []

        # Look for test functions
        if 'def test_' in content:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    test_name = node.name.replace('test_', '').replace('_', ' ').capitalize()
                    criteria.append(f"{test_name}")

        return criteria[:5]  # Limit to first 5

    def generate_prd_markdown(self, project_name: str, version: str = "1.0.0") -> str:
        """
        Generate PROJECT_SPEC.md from discovered features.

        Args:
            project_name: Project name
            version: Current version

        Returns:
            Markdown content for PROJECT_SPEC.md
        """
        md = f"""# {project_name} - Product Requirements Document

**Version:** {version}
**Generated:** {datetime.now().strftime('%Y-%m-%d')}
**Auto-discovered from codebase**

## Project Overview

{project_name} is a software project with {len(self.features)} discovered features and capabilities.

## Core Capabilities

"""

        # Group features by category
        categories = {
            'API': [],
            'CLI': [],
            'UI': [],
            'Core': [],
            'Data': []
        }

        for feature in self.features:
            for category in categories:
                if feature.title.startswith(f"{category}:"):
                    categories[category].append(feature)
                    break
            else:
                categories['Core'].append(feature)

        # List capabilities by category
        for category, features in categories.items():
            if features:
                md += f"\n### {category} Features\n\n"
                for feature in features:
                    md += f"- **{feature.title.split(':', 1)[-1].strip()}**: {feature.description}\n"

        md += "\n\n---\n\n"

        # Add detailed features
        for i, feature in enumerate(self.features, 1):
            md += f"""## Feature {i}: {feature.title}

**Priority:** {feature.priority.title()}
**Component:** {feature.component}
**Status:** {feature.status.title()}
**Version:** {feature.version}

### Description

{feature.description}

"""

            if feature.endpoints:
                md += "### API Endpoints\n\n"
                for endpoint in feature.endpoints:
                    md += f"- `{endpoint}`\n"
                md += "\n"

            if feature.functions:
                md += "### Functions\n\n"
                for func in feature.functions[:10]:  # Limit to 10
                    md += f"- `{func}()`\n"
                md += "\n"

            if feature.classes:
                md += "### Classes\n\n"
                for cls in feature.classes[:10]:  # Limit to 10
                    md += f"- `{cls}`\n"
                md += "\n"

            if feature.files:
                md += "### Implementation Files\n\n"
                for file_path in feature.files[:5]:  # Limit to 5
                    md += f"- `{file_path}`\n"
                md += "\n"

            if feature.acceptance_criteria:
                md += "### Acceptance Criteria\n\n"
                for criterion in feature.acceptance_criteria:
                    md += f"- [ ] {criterion}\n"
                md += "\n"

            md += "---\n\n"

        # Add version planning sections
        md += self._generate_version_planning(version)

        md += """
---

*This document was automatically generated by BuildRunner 3 Feature Discovery*
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

        return md

    def _generate_version_planning(self, current_version: str) -> str:
        """Generate version planning sections"""

        # Parse version
        parts = current_version.split('.')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        next_patch = f"{major}.{minor}.{patch + 1}"
        next_minor = f"{major}.{minor + 1}.0"
        next_major = f"{major + 1}.0.0"

        md = f"""## Version Roadmap

### Current Version: {current_version}

All features listed above are part of the current release.

### Next Patch Release: {next_patch}

**Focus:** Bug fixes and minor improvements

- [ ] Fix critical bugs discovered in {current_version}
- [ ] Performance optimizations
- [ ] Documentation updates
- [ ] Test coverage improvements

### Next Minor Release: {next_minor}

**Focus:** New features and enhancements

- [ ] Additional features based on user feedback
- [ ] Enhanced existing capabilities
- [ ] New integrations
- [ ] UX improvements

### Next Major Release: {next_major}

**Focus:** Breaking changes and major features

- [ ] Architectural improvements
- [ ] Breaking API changes (if needed)
- [ ] Major new capabilities
- [ ] Platform expansion

## Feature Requests

*To add new features to the roadmap, update this section*

### Planned Features

- [ ] Feature request 1
- [ ] Feature request 2
- [ ] Feature request 3

### Under Consideration

- [ ] Proposed feature 1
- [ ] Proposed feature 2

"""

        return md
