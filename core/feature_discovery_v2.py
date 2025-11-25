"""
Enhanced Feature Discovery - V2
Improved automatic feature discovery with better grouping and naming

Key Improvements:
1. AST-based parsing for accurate code analysis
2. Smart feature grouping (related code → single feature)
3. Intelligent naming (code names → readable feature names)
4. Multi-language support prep (Python, TypeScript, JavaScript)
5. Confidence scoring for discoveries
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CodeArtifact:
    """A code artifact (function, class, endpoint, etc.)"""

    name: str
    type: str  # 'function', 'class', 'endpoint', 'component', 'model'
    file_path: str
    line_number: int = 0
    docstring: str = ""
    decorators: List[str] = field(default_factory=list)
    related_artifacts: Set[str] = field(default_factory=set)


@dataclass
class DiscoveredFeature:
    """Enhanced feature with grouping and confidence"""

    id: str
    title: str
    description: str
    priority: str = "medium"
    status: str = "implemented"
    version: str = "1.0"
    confidence: float = 0.8  # 0.0-1.0
    group: str = "Other"  # NEW: Feature group for organization
    artifacts: List[CodeArtifact] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    technical_details: Dict = field(default_factory=dict)


class EnhancedFeatureDiscovery:
    """
    Enhanced feature discovery with smart grouping and naming

    Discovery Strategy:
    1. Parse all Python files with AST
    2. Extract artifacts (functions, classes, endpoints, models)
    3. Group related artifacts into features
    4. Generate readable feature names
    5. Calculate confidence scores
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.artifacts: List[CodeArtifact] = []
        self.features: List[DiscoveredFeature] = []

        # Feature name mappings (technical → readable)
        self.name_mappings = {
            "auth": "Authentication",
            "user": "User Management",
            "prd": "PRD Management",
            "api": "API",
            "cli": "Command Line Interface",
            "ui": "User Interface",
            "db": "Database",
            "build": "Build System",
            "test": "Testing",
            "orchestrator": "Task Orchestration",
            "agent": "Agent System",
            "telemetry": "Telemetry & Analytics",
            "routing": "Routing",
            "security": "Security",
            "parallel": "Parallel Execution",
        }

    def discover_all(self) -> List[DiscoveredFeature]:
        """
        Run complete feature discovery

        Returns:
            List of discovered features with confidence scores
        """
        # Step 0: Try documentation-based discovery first (highest quality)
        doc_features = self._extract_features_from_documentation()

        if doc_features:
            # Documentation found - use these as primary features
            self.features = doc_features
            self._calculate_confidence_scores()
            return self.features

        # Fallback: Code-based discovery
        # Step 1: Extract all artifacts
        self._extract_artifacts_from_python()
        self._extract_artifacts_from_typescript()

        # Step 2: Group artifacts into features
        self._group_artifacts_into_features()

        # Step 3: Enhance feature descriptions
        self._enhance_feature_descriptions()

        # Step 4: Calculate confidence scores
        self._calculate_confidence_scores()

        return self.features

    def _extract_features_from_documentation(self) -> List[DiscoveredFeature]:
        """
        Extract features from markdown documentation files

        Parses documentation for feature lists like:
        - **Feature Name** - Description
        - 1. **Feature Name** - Description
        - ✅ **Feature Name** - Description

        Returns:
            List of discovered features from documentation
        """
        doc_features = []
        md_files = list(self.project_root.rglob("*.md"))

        # Skip common non-feature documentation
        skip_patterns = ["node_modules", ".venv", "venv", "CHANGELOG", "LICENSE", "CONTRIBUTING"]

        # Prioritize these file patterns (real feature documentation)
        priority_patterns = ["mvp", "overview", "roadmap", "feature", "prd", "spec", "project_spec"]

        # Deprioritize these (implementation/debug docs)
        low_priority_patterns = [
            "implementation",
            "handoff",
            "debug",
            "test",
            "gap_analysis",
            "session",
            "summary",
            "guide",
            "readme",
            "quickstart",
            "integration",
            "complete",
            "report",
            "migration",
            "fix",
            "checkpoint",
        ]

        # Sort files: priority files first, then others
        priority_files = []
        other_files = []

        for md_file in md_files:
            if any(skip in str(md_file) for skip in skip_patterns):
                continue

            filename_lower = md_file.name.lower()

            # Check if it's a priority file
            if any(p in filename_lower for p in priority_patterns):
                priority_files.append(md_file)
            elif not any(p in filename_lower for p in low_priority_patterns):
                other_files.append(md_file)
            # Low priority files are skipped entirely

        # Process priority files first
        for md_file in priority_files + other_files:
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract features from this file
                file_features = self._parse_markdown_for_features(content, str(md_file))
                doc_features.extend(file_features)

            except Exception:
                continue

        # Deduplicate by title (keep first occurrence - priority files win)
        seen_titles = set()
        unique_features = []
        for feature in doc_features:
            title_lower = feature.title.lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_features.append(feature)

        # Limit to reasonable number of features (max 50)
        # Priority: implemented features first, then planned
        implemented = [f for f in unique_features if f.status == "implemented"]
        planned = [f for f in unique_features if f.status == "planned"]
        in_progress = [f for f in unique_features if f.status == "in_progress"]

        # Return up to 50 features, balanced between implemented and planned
        result = []
        result.extend(implemented[:30])
        result.extend(in_progress[:5])
        result.extend(planned[:15])

        return result

    def _parse_markdown_for_features(self, content: str, file_path: str) -> List[DiscoveredFeature]:
        """
        Parse markdown content for feature definitions

        Supports formats:
        - 1. **Feature Name** - Description (numbered list required)
        - ✅ **Feature Name** - Description (implemented)
        - ❌ **Feature Name** - Description (planned)
        """
        features = []

        # Infer default group from filename
        default_group = self._infer_group_from_file(file_path)

        # Blacklist of common non-feature bold text
        non_feature_words = {
            "note",
            "warning",
            "important",
            "example",
            "usage",
            "tip",
            "info",
            "changed",
            "result",
            "solution",
            "after",
            "before",
            "features",
            "columns",
            "files",
            "rationale",
            "impact",
            "contents",
            "analysis",
            "status",
            "legend",
            "summary",
            "what",
            "why",
            "how",
            "when",
            "where",
            "services",
            "ui",
            "infrastructure",
            "database",
            "api",
            "deployment",
            "testing",
            "documentation",
            "configuration",
            "setup",
            "installation",
            "prerequisites",
            "requirements",
            "dependencies",
            "credits",
            "license",
            "authors",
            "contributors",
            "changelog",
            "release",
            "version",
            "verification",
            "validation",
            "claims",
            "actual",
            "expected",
            "output",
            "input",
            "parameters",
            "arguments",
            "returns",
            "errors",
            "exceptions",
            "issues",
            "bugs",
            "fixes",
            "updates",
            "improvements",
            "enhancements",
            "this means",
            "this adds",
            "review the comprehensive report",
            "implement immediate quick wins",
            "deploy edge functions",
            "start content calendar",
            "follow the roadmap",
            "next focus",
            "brand perception gap",
            "competitive intelligence",
            "customer understanding",
            "search visibility",
            "strong areas",
            "weak areas",
            "available but not wired",
            "new files",
            "modified files",
            "directories created",
            "reference files",
        }

        # Pattern for numbered list items with bold feature names
        # More strict: requires number prefix like "1. **Feature** - desc"
        pattern_numbered = r"(?:^|\n)\s*\d+\.\s*\*\*([^*]+)\*\*\s*[-–—]\s*(.+?)(?=\n|$)"

        # Pattern with status emoji (these are clearly features)
        # Matches: "✅ **Feature Name** - Description" in MVP_OVERVIEW style
        pattern_emoji = (
            r"(?:^|\n)\s*\d*\.?\s*([✅❌⏳🔄])\s*\*\*([^*]+)\*\*\s*[-–—]\s*(.+?)(?=\n|$)"
        )

        # Find emoji-prefixed features first (highest confidence)
        for match in re.finditer(pattern_emoji, content):
            emoji = match.group(1)
            title = match.group(2).strip()
            description = match.group(3).strip()

            # Skip if title is in blacklist
            if title.lower() in non_feature_words:
                continue

            # Skip if title looks like a status label
            if title.endswith(":") or len(title) < 3:
                continue

            # Determine status from emoji
            if emoji == "✅":
                status = "implemented"
            elif emoji == "❌":
                status = "planned"
            elif emoji in ["⏳", "🔄"]:
                status = "in_progress"
            else:
                status = "implemented"

            # Infer group from context near this feature
            group = self._infer_group_from_context(content, title, default_group)

            feature = DiscoveredFeature(
                id=f"doc-feature-{len(features) + 1}",
                title=title,
                description=description,
                priority=self._infer_priority_from_context(content, title),
                status=status,
                version="1.0",
                confidence=0.95,  # High confidence - from documentation
                group=group,
                acceptance_criteria=[],
                technical_details={"source_file": file_path, "source": "documentation"},
            )
            features.append(feature)

        # Find numbered list items (still good confidence)
        for match in re.finditer(pattern_numbered, content):
            title = match.group(1).strip()
            description = match.group(2).strip()

            # Skip if already found
            if any(f.title.lower() == title.lower() for f in features):
                continue

            # Skip blacklisted titles
            if title.lower() in non_feature_words:
                continue

            # Skip if title looks like a status/section label
            if title.endswith(":") or len(title) < 3:
                continue

            # Skip titles that are clearly not features
            if any(word in title.lower() for word in ["step", "fix", "bug", "issue", "error"]):
                continue

            # Infer status from context
            status = self._infer_status_from_context(content, title)

            # Infer group from context
            group = self._infer_group_from_context(content, title, default_group)

            feature = DiscoveredFeature(
                id=f"doc-feature-{len(features) + 1}",
                title=title,
                description=description,
                priority=self._infer_priority_from_context(content, title),
                status=status,
                version="1.0",
                confidence=0.85,  # Good confidence - from numbered list
                group=group,
                acceptance_criteria=[],
                technical_details={"source_file": file_path, "source": "documentation"},
            )
            features.append(feature)

        return features

    def _infer_group_from_file(self, file_path: str) -> str:
        """Infer feature group from the source file name"""
        filename = Path(file_path).stem.lower()

        # Map common file patterns to groups
        group_mappings = {
            "mvp": "MVP Features",
            "overview": "Core Features",
            "roadmap": "Roadmap",
            "phase_1": "Phase 1",
            "phase_2": "Phase 2",
            "phase_3": "Phase 3",
            "implementation": "Implementation",
            "mirror": "Mirror Diagnostics",
            "content": "Content Generation",
            "calendar": "Calendar & Scheduling",
            "brand": "Brand Intelligence",
            "competitive": "Competitive Analysis",
            "design": "Design Studio",
        }

        for pattern, group_name in group_mappings.items():
            if pattern in filename:
                return group_name

        return "Other"

    def _infer_group_from_context(self, content: str, title: str, default_group: str) -> str:
        """Infer feature group from context around the feature"""
        title_lower = title.lower()
        content_lower = content.lower()

        # Find the position of this feature in the document
        title_pos = content_lower.find(title_lower)
        if title_pos == -1:
            return default_group

        # Look back to find the most recent section header
        context_before = content[:title_pos]

        # Find the last ## or ### header before this feature
        header_pattern = r"##\s+([^\n]+)"
        headers = list(re.finditer(header_pattern, context_before))

        if headers:
            last_header = headers[-1].group(1).strip()

            # Map common header patterns to groups
            header_mappings = {
                "mvp": "MVP Features",
                "phase 1": "MVP Features",
                "phase 2": "Phase 2 - Future",
                "phase 3": "Phase 3 - Future",
                "content": "Content Generation",
                "calendar": "Calendar & Scheduling",
                "brand": "Brand Intelligence",
                "mirror": "Mirror Diagnostics",
                "intelligence": "Brand Intelligence",
                "scheduling": "Calendar & Scheduling",
                "competitive": "Competitive Analysis",
                "design": "Design Studio",
                "template": "Templates & Visual",
                "analytics": "Analytics & Reporting",
            }

            last_header_lower = last_header.lower()
            for pattern, group_name in header_mappings.items():
                if pattern in last_header_lower:
                    return group_name

            # If header doesn't match patterns, use it directly (cleaned up)
            if len(last_header) < 40:  # Reasonable header length
                return last_header.replace("✅", "").replace("❌", "").strip()

        return default_group

    def _infer_status_from_context(self, content: str, title: str) -> str:
        """Infer feature status from surrounding context"""
        title_lower = title.lower()
        content_lower = content.lower()

        # Look for context clues near the title
        title_pos = content_lower.find(title_lower)
        if title_pos == -1:
            return "implemented"

        # Check 200 chars before title for context
        context_start = max(0, title_pos - 200)
        context = content_lower[context_start : title_pos + len(title) + 200]

        # Context indicators for planned/not implemented
        planned_indicators = [
            "not in mvp",
            "phase 2",
            "phase 3",
            "coming soon",
            "planned",
            "not yet",
            "future",
            "roadmap",
            "todo",
            "backlog",
            "❌",
        ]

        # Context indicators for implemented
        implemented_indicators = [
            "in the mvp",
            "what you have",
            "implemented",
            "complete",
            "available",
            "current",
            "✅",
            "done",
            "shipped",
        ]

        for indicator in planned_indicators:
            if indicator in context:
                return "planned"

        for indicator in implemented_indicators:
            if indicator in context:
                return "implemented"

        return "implemented"  # Default

    def _infer_priority_from_context(self, content: str, title: str) -> str:
        """Infer feature priority from surrounding context"""
        title_lower = title.lower()
        content_lower = content.lower()

        # Check for priority indicators
        title_pos = content_lower.find(title_lower)
        if title_pos == -1:
            return "medium"

        context_start = max(0, title_pos - 300)
        context = content_lower[context_start : title_pos + len(title) + 100]

        high_priority = ["critical", "essential", "core", "must have", "p0", "p1", "high priority"]
        low_priority = ["nice to have", "optional", "low priority", "p3", "stretch"]

        for indicator in high_priority:
            if indicator in context:
                return "high"

        for indicator in low_priority:
            if indicator in context:
                return "low"

        return "medium"

    def _extract_artifacts_from_python(self):
        """Extract code artifacts from Python files using AST"""
        python_files = list(self.project_root.rglob("*.py"))

        for py_file in python_files:
            # Skip tests, migrations, and virtual envs
            if any(
                skip in str(py_file)
                for skip in ["test_", "__pycache__", ".venv", "venv", "migrations"]
            ):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                relative_path = str(py_file.relative_to(self.project_root))

                # Extract classes and functions
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        self._extract_function(node, relative_path)
                    elif isinstance(node, ast.ClassDef):
                        self._extract_class(node, relative_path)
                    elif isinstance(node, ast.AsyncFunctionDef):
                        self._extract_async_function(node, relative_path)

            except Exception as e:
                # Skip files that can't be parsed
                continue

    def _extract_function(self, node: ast.FunctionDef, file_path: str):
        """Extract function artifact"""
        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]

        # Detect endpoint decorators
        is_endpoint = any(
            d
            in [
                "app.get",
                "app.post",
                "app.put",
                "app.delete",
                "app.route",
                "router.get",
                "router.post",
                "router.put",
                "router.delete",
            ]
            for d in decorators
        )

        artifact_type = "endpoint" if is_endpoint else "function"

        artifact = CodeArtifact(
            name=node.name,
            type=artifact_type,
            file_path=file_path,
            line_number=node.lineno,
            docstring=ast.get_docstring(node) or "",
            decorators=decorators,
        )

        self.artifacts.append(artifact)

    def _extract_async_function(self, node: ast.AsyncFunctionDef, file_path: str):
        """Extract async function artifact"""
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]

        is_endpoint = any(
            d
            in [
                "app.get",
                "app.post",
                "app.put",
                "app.delete",
                "router.get",
                "router.post",
                "router.put",
                "router.delete",
            ]
            for d in decorators
        )

        artifact_type = "endpoint" if is_endpoint else "function"

        artifact = CodeArtifact(
            name=node.name,
            type=artifact_type,
            file_path=file_path,
            line_number=node.lineno,
            docstring=ast.get_docstring(node) or "",
            decorators=decorators,
        )

        self.artifacts.append(artifact)

    def _extract_class(self, node: ast.ClassDef, file_path: str):
        """Extract class artifact"""
        # Detect model classes (inherit from BaseModel, Base, etc.)
        is_model = any(
            isinstance(base, ast.Name) and base.id in ["BaseModel", "Base", "Model"]
            for base in node.bases
        )

        artifact_type = "model" if is_model else "class"

        artifact = CodeArtifact(
            name=node.name,
            type=artifact_type,
            file_path=file_path,
            line_number=node.lineno,
            docstring=ast.get_docstring(node) or "",
        )

        self.artifacts.append(artifact)

    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return f"{decorator.func.value.id}.{decorator.func.attr}"
            elif isinstance(decorator.func, ast.Name):
                return decorator.func.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}"
        return ""

    def _extract_artifacts_from_typescript(self):
        """Extract code artifacts from TypeScript/JavaScript files using regex"""
        # Find all TS/JS files, excluding node_modules
        ts_files = []
        for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
            ts_files.extend(self.project_root.rglob(ext))

        for ts_file in ts_files:
            # Skip node_modules, dist, build folders
            if any(
                skip in str(ts_file)
                for skip in ["node_modules", "dist", "build", ".next", "__tests__"]
            ):
                continue

            try:
                with open(ts_file, "r", encoding="utf-8") as f:
                    content = f.read()

                relative_path = str(ts_file.relative_to(self.project_root))

                # Extract React components (function and class)
                # Pattern: export function ComponentName or export const ComponentName =
                component_patterns = [
                    r"export\s+(?:default\s+)?function\s+([A-Z][a-zA-Z0-9]*)",
                    r"export\s+(?:const|let)\s+([A-Z][a-zA-Z0-9]*)\s*[=:]",
                    r"export\s+(?:default\s+)?class\s+([A-Z][a-zA-Z0-9]*)",
                    r"const\s+([A-Z][a-zA-Z0-9]*)\s*:\s*(?:React\.)?FC",
                ]

                for pattern in component_patterns:
                    for match in re.finditer(pattern, content):
                        name = match.group(1)
                        # Check if it's likely a component (starts with uppercase, has JSX nearby)
                        artifact = CodeArtifact(
                            name=name,
                            type="component",
                            file_path=relative_path,
                            line_number=content[: match.start()].count("\n") + 1,
                        )
                        self.artifacts.append(artifact)

                # Extract regular functions
                func_pattern = r"(?:export\s+)?(?:async\s+)?function\s+([a-z][a-zA-Z0-9]*)\s*\("
                for match in re.finditer(func_pattern, content):
                    name = match.group(1)
                    artifact = CodeArtifact(
                        name=name,
                        type="function",
                        file_path=relative_path,
                        line_number=content[: match.start()].count("\n") + 1,
                    )
                    self.artifacts.append(artifact)

                # Extract arrow function exports
                arrow_pattern = r"export\s+const\s+([a-z][a-zA-Z0-9]*)\s*=\s*(?:async\s+)?\("
                for match in re.finditer(arrow_pattern, content):
                    name = match.group(1)
                    artifact = CodeArtifact(
                        name=name,
                        type="function",
                        file_path=relative_path,
                        line_number=content[: match.start()].count("\n") + 1,
                    )
                    self.artifacts.append(artifact)

                # Extract classes
                class_pattern = r"(?:export\s+)?class\s+([a-zA-Z][a-zA-Z0-9]*)"
                for match in re.finditer(class_pattern, content):
                    name = match.group(1)
                    if not name[0].isupper():
                        continue
                    artifact = CodeArtifact(
                        name=name,
                        type="class",
                        file_path=relative_path,
                        line_number=content[: match.start()].count("\n") + 1,
                    )
                    self.artifacts.append(artifact)

                # Extract interfaces and types
                interface_pattern = r"(?:export\s+)?interface\s+([A-Z][a-zA-Z0-9]*)"
                for match in re.finditer(interface_pattern, content):
                    name = match.group(1)
                    artifact = CodeArtifact(
                        name=name,
                        type="model",
                        file_path=relative_path,
                        line_number=content[: match.start()].count("\n") + 1,
                    )
                    self.artifacts.append(artifact)

                type_pattern = r"(?:export\s+)?type\s+([A-Z][a-zA-Z0-9]*)\s*="
                for match in re.finditer(type_pattern, content):
                    name = match.group(1)
                    artifact = CodeArtifact(
                        name=name,
                        type="model",
                        file_path=relative_path,
                        line_number=content[: match.start()].count("\n") + 1,
                    )
                    self.artifacts.append(artifact)

                # Extract API routes (Next.js, Express patterns)
                route_patterns = [
                    r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)',
                    r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)\s*\(",
                ]

                for pattern in route_patterns:
                    for match in re.finditer(pattern, content):
                        name = (
                            match.group(1)
                            if len(match.groups()) == 1
                            else f"{match.group(1)}:{match.group(2)}"
                        )
                        artifact = CodeArtifact(
                            name=name,
                            type="endpoint",
                            file_path=relative_path,
                            line_number=content[: match.start()].count("\n") + 1,
                        )
                        self.artifacts.append(artifact)

            except Exception as e:
                # Skip files that can't be read
                continue

    def _group_artifacts_into_features(self):
        """Group related artifacts into logical features"""
        # Group by module/file path
        groups = defaultdict(list)

        for artifact in self.artifacts:
            # Extract feature identifier from path
            parts = Path(artifact.file_path).parts

            # Try to identify feature from path
            feature_key = self._extract_feature_key(parts, artifact)
            groups[feature_key].append(artifact)

        # Convert groups to features
        for feature_key, artifacts in groups.items():
            if not artifacts:
                continue

            feature = self._create_feature_from_group(feature_key, artifacts)
            self.features.append(feature)

    def _extract_feature_key(self, path_parts: Tuple[str, ...], artifact: CodeArtifact) -> str:
        """Extract feature identifier from file path"""
        # Priority order for feature identification:
        # 1. Main module name (api/routes/prd_builder.py → prd_builder)
        # 2. Directory name (core/agents/... → agents)
        # 3. First part of filename (user_service.py → user)

        if len(path_parts) >= 2:
            if path_parts[0] in ["api", "core", "cli"]:
                # Use second part (api/routes → routes, core/agents → agents)
                if len(path_parts) > 2:
                    return path_parts[1]
                # Or filename without extension
                return Path(path_parts[-1]).stem
            else:
                return path_parts[0]

        return Path(artifact.file_path).stem

    def _create_feature_from_group(
        self, feature_key: str, artifacts: List[CodeArtifact]
    ) -> DiscoveredFeature:
        """Create a feature from grouped artifacts"""
        # Generate readable feature name
        feature_title = self._generate_feature_name(feature_key, artifacts)

        # Generate description
        description = self._generate_feature_description(artifacts)

        # Extract endpoints
        endpoints = [a.name for a in artifacts if a.type == "endpoint"]

        # Extract classes and functions
        classes = [a.name for a in artifacts if a.type in ["class", "model"]]
        functions = [a.name for a in artifacts if a.type == "function"]

        # Determine priority based on artifact count
        priority = self._calculate_priority(artifacts)

        # Generate acceptance criteria from docstrings
        acceptance_criteria = self._generate_acceptance_criteria(artifacts)

        # Generate feature ID
        feature_id = f"feature-{len(self.features) + 1}"

        feature = DiscoveredFeature(
            id=feature_id,
            title=feature_title,
            description=description,
            priority=priority,
            status="implemented",
            version="1.0",
            artifacts=artifacts,
            acceptance_criteria=acceptance_criteria,
            technical_details={
                "endpoints": endpoints,
                "classes": classes,
                "functions": functions,
                "file_count": len(set(a.file_path for a in artifacts)),
                "artifact_count": len(artifacts),
            },
        )

        return feature

    def _generate_feature_name(self, feature_key: str, artifacts: List[CodeArtifact]) -> str:
        """Generate readable feature name from key and artifacts"""
        # Check if key matches known mappings
        key_lower = feature_key.lower()
        for tech_name, readable_name in self.name_mappings.items():
            if tech_name in key_lower:
                return readable_name

        # Try to extract from artifact names
        if artifacts:
            # Get most common word in artifact names
            words = []
            for artifact in artifacts:
                # Extract words from camelCase or snake_case
                artifact_words = re.findall(r"[A-Z][a-z]+|[a-z]+", artifact.name)
                words.extend(artifact_words)

            if words:
                # Find most common word
                from collections import Counter

                common_word = Counter(w.lower() for w in words).most_common(1)[0][0]

                # Check if it's in mappings
                if common_word in self.name_mappings:
                    return self.name_mappings[common_word]

                # Otherwise capitalize it
                return common_word.title() + " System"

        # Fallback: Clean up feature key
        return feature_key.replace("_", " ").title()

    def _generate_feature_description(self, artifacts: List[CodeArtifact]) -> str:
        """Generate feature description from artifacts"""
        # Try to use first artifact's docstring
        for artifact in artifacts:
            if artifact.docstring:
                # Use first line of docstring
                first_line = artifact.docstring.split("\n")[0].strip()
                if len(first_line) > 20:
                    return first_line

        # Generate from artifact types
        endpoint_count = sum(1 for a in artifacts if a.type == "endpoint")
        class_count = sum(1 for a in artifacts if a.type in ["class", "model"])

        if endpoint_count > 0:
            return f"Provides {endpoint_count} API endpoints for managing operations"
        elif class_count > 0:
            return f"Core functionality with {class_count} classes and components"
        else:
            return f"System functionality with {len(artifacts)} components"

    def _calculate_priority(self, artifacts: List[CodeArtifact]) -> str:
        """Calculate priority based on artifact characteristics"""
        # High priority if:
        # - Has many artifacts (>10)
        # - Has endpoints (user-facing)
        # - In core directories

        artifact_count = len(artifacts)
        has_endpoints = any(a.type == "endpoint" for a in artifacts)
        in_core = any("core" in a.file_path or "api" in a.file_path for a in artifacts)

        if artifact_count > 10 or (has_endpoints and in_core):
            return "high"
        elif artifact_count > 5 or has_endpoints:
            return "medium"
        else:
            return "low"

    def _generate_acceptance_criteria(self, artifacts: List[CodeArtifact]) -> List[str]:
        """Generate acceptance criteria from artifacts"""
        criteria = []

        # From endpoints
        endpoints = [a for a in artifacts if a.type == "endpoint"]
        if endpoints:
            criteria.append(f"All {len(endpoints)} endpoints should respond correctly")

        # From classes
        classes = [a for a in artifacts if a.type in ["class", "model"]]
        if classes:
            criteria.append(f"All {len(classes)} classes should be properly initialized")

        # From docstrings
        for artifact in artifacts[:3]:  # Top 3
            if artifact.docstring:
                # Extract any "should" or "must" statements
                for line in artifact.docstring.split("\n"):
                    line = line.strip()
                    if "should" in line.lower() or "must" in line.lower():
                        criteria.append(line)
                        if len(criteria) >= 5:
                            break

        return criteria[:5]  # Max 5 criteria

    def _enhance_feature_descriptions(self):
        """Enhance feature descriptions with additional context"""
        for feature in self.features:
            # Add implementation status
            if feature.technical_details.get("endpoints"):
                feature.description += (
                    f"\n\nProvides {len(feature.technical_details['endpoints'])} API endpoints."
                )

            # Add file count
            file_count = feature.technical_details.get("file_count", 0)
            if file_count > 1:
                feature.description += f" Implemented across {file_count} files."

    def _calculate_confidence_scores(self):
        """Calculate confidence scores for each feature"""
        for feature in self.features:
            score = 0.5  # Base score

            # Higher confidence if:
            # - Has docstrings (+0.2)
            # - Has multiple artifacts (+0.1)
            # - Has endpoints (+0.2)
            # - Has tests (+0.1)

            if any(a.docstring for a in feature.artifacts):
                score += 0.2

            if len(feature.artifacts) >= 3:
                score += 0.1

            if feature.technical_details.get("endpoints"):
                score += 0.2

            # Check for test files
            for artifact in feature.artifacts:
                if "test" in artifact.file_path:
                    score += 0.1
                    break

            feature.confidence = min(1.0, score)


def export_to_prd_format(features: List[DiscoveredFeature], project_name: str) -> Dict:
    """
    Export discovered features to PRD format compatible with UI

    Args:
        features: List of discovered features
        project_name: Name of the project

    Returns:
        PRD data structure
    """
    prd_features = []

    for i, feature in enumerate(features, 1):
        prd_feature = {
            "id": feature.id or f"feature-{i}",
            "title": feature.title,
            "description": feature.description,
            "priority": feature.priority,
            "status": feature.status,
            "version": f"v{feature.version}",
            "group": feature.group,  # Add group for organization
            "acceptance_criteria": "\n".join(f"- [ ] {c}" for c in feature.acceptance_criteria),
        }
        prd_features.append(prd_feature)

    # Calculate group metadata
    all_groups = list(set(f.group for f in features))
    group_counts = {g: sum(1 for f in features if f.group == g) for g in all_groups}

    return {
        "project_name": project_name,
        "features": prd_features,
        "overview": {
            "executive_summary": f"Automatically discovered {len(features)} features from codebase.",
            "goals": "Feature inventory generated from code analysis",
            "target_users": "",
        },
        "technical_requirements": {},
        "success_criteria": [],
        "metadata": {
            "groups": sorted(all_groups),  # List of all unique groups
            "group_counts": group_counts,  # Count of features per group
        },
    }
