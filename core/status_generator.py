"""STATUS.md Generator for BuildRunner 3.0

Auto-generates STATUS.md from features.json data with markdown formatting.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class StatusGenerator:
    """Generates STATUS.md from features.json"""

    def __init__(self, project_root: str = "."):
        """Initialize status generator

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.features_file = self.project_root / ".buildrunner" / "features.json"
        self.status_file = self.project_root / "STATUS.md"

    def generate(self) -> str:
        """Generate STATUS.md content

        Returns:
            Markdown formatted status content
        """
        if not self.features_file.exists():
            return self._generate_empty_status()

        with open(self.features_file, 'r') as f:
            data = json.load(f)

        return self._format_status(data)

    def save(self):
        """Generate and save STATUS.md"""
        content = self.generate()
        self.status_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.status_file, 'w') as f:
            f.write(content)

    def _generate_empty_status(self) -> str:
        """Generate status for empty project

        Returns:
            Empty status markdown
        """
        return """# Project Status

**Status:** No features.json found

Run `br init` to initialize this project.
"""

    def _format_status(self, data: Dict[str, Any]) -> str:
        """Format features data as markdown

        Args:
            data: Features.json data

        Returns:
            Markdown formatted status
        """
        project = data.get('project', 'Unknown Project')
        version = data.get('version', '1.0.0')
        status = data.get('status', 'unknown').replace('_', ' ').title()
        description = data.get('description', '')
        metrics = data.get('metrics', {})
        features = data.get('features', [])

        # Header
        lines = [
            f"# {project} - Status Report",
            "",
            f"**Version:** {version}",
            f"**Status:** {status}",
            f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}",
            f"**Completion:** {metrics.get('completion_percentage', 0)}%",
            ""
        ]

        # Metrics
        lines.extend([
            "## Progress",
            "",
            f"- ✅ {metrics.get('features_complete', 0)} features complete",
            f"- 🚧 {metrics.get('features_in_progress', 0)} features in progress",
            f"- 📋 {metrics.get('features_planned', 0)} features planned",
            ""
        ])

        # Description
        if description:
            lines.extend([
                "## Description",
                "",
                description,
                ""
            ])

        # Group features by status
        complete_features = [f for f in features if f.get('status') == 'complete']
        in_progress_features = [f for f in features if f.get('status') == 'in_progress']
        planned_features = [f for f in features if f.get('status') == 'planned']

        # Complete features
        if complete_features:
            lines.extend([
                "---",
                "",
                "## ✅ Complete Features",
                ""
            ])
            for feature in complete_features:
                lines.extend(self._format_feature(feature))

        # In progress features
        if in_progress_features:
            lines.extend([
                "---",
                "",
                "## 🚧 In Progress Features",
                ""
            ])
            for feature in in_progress_features:
                lines.extend(self._format_feature(feature))

        # Planned features
        if planned_features:
            lines.extend([
                "---",
                "",
                "## 📋 Planned Features",
                ""
            ])
            for feature in planned_features:
                lines.extend(self._format_feature(feature))

        # Footer
        lines.extend([
            "---",
            "",
            f"*Generated from `.buildrunner/features.json` on {datetime.now().isoformat()}*",
            f"*Generator: `core/status_generator.py`*",
            ""
        ])

        return "\n".join(lines)

    def _format_feature(self, feature: Dict[str, Any]) -> List[str]:
        """Format a single feature as markdown

        Args:
            feature: Feature dictionary

        Returns:
            List of markdown lines
        """
        name = feature.get('name', 'Unnamed Feature')
        feature_id = feature.get('id', '')
        priority = feature.get('priority', 'medium').upper()
        description = feature.get('description', '')
        week = feature.get('week')
        build = feature.get('build')

        lines = [
            f"### {name}",
        ]

        # Metadata line
        meta_parts = [f"**ID:** {feature_id}"]
        if priority:
            meta_parts.append(f"**Priority:** {priority}")
        if week:
            meta_parts.append(f"**Week:** {week}")
        if build:
            meta_parts.append(f"**Build:** {build}")

        lines.append(" | ".join(meta_parts))
        lines.append("")

        if description:
            lines.append(description)
            lines.append("")

        return lines
