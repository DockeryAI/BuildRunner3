"""
Spec Parser - Parse PROJECT_SPEC.md into structured features

Extracts:
- Features with metadata (name, description, requirements)
- Technical requirements
- Dependencies between features
- Acceptance criteria

Returns structured dictionary for downstream processing.
"""
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Feature:
    """Represents a single feature from spec"""
    id: str
    name: str
    description: str
    requirements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    technical_details: List[str] = field(default_factory=list)
    complexity: str = "medium"  # simple, medium, complex


class SpecParser:
    """
    Parse PROJECT_SPEC.md into structured features

    Features:
    - Extract features from markdown
    - Identify dependencies
    - Parse acceptance criteria
    - Validate spec structure
    """

    def __init__(self):
        """Initialize SpecParser"""
        self.required_sections = [
            'overview', 'features', 'technical requirements'
        ]

    def parse_spec(self, spec_path: Path) -> Dict[str, Any]:
        """
        Parse PROJECT_SPEC.md file into structured format

        Args:
            spec_path: Path to PROJECT_SPEC.md file

        Returns:
            Dict with:
                - features: List of Feature objects
                - technical_requirements: List of technical requirements
                - overview: Project overview text
                - metadata: Additional metadata

        Raises:
            FileNotFoundError: If spec file doesn't exist
            ValueError: If spec is missing required sections
        """
        spec_path = Path(spec_path)

        if not spec_path.exists():
            raise FileNotFoundError(f"Spec file not found: {spec_path}")

        # Read spec content
        content = spec_path.read_text()

        # Validate structure
        if not self.validate_spec(content):
            raise ValueError("Spec missing required sections")

        # Extract sections
        overview = self._extract_overview(content)
        features = self.extract_features(content)
        tech_requirements = self._extract_tech_requirements(content)
        dependencies = self.extract_dependencies(content)

        # Apply dependencies to features
        self._apply_dependencies(features, dependencies)

        return {
            "features": [self._feature_to_dict(f) for f in features],
            "technical_requirements": tech_requirements,
            "overview": overview,
            "metadata": {
                "source_file": str(spec_path),
                "feature_count": len(features),
                "has_dependencies": len(dependencies) > 0
            }
        }

    def extract_features(self, content: str) -> List[Feature]:
        """
        Parse markdown for ## Features sections

        Args:
            content: Markdown content

        Returns:
            List of Feature objects
        """
        features = []

        # Find Features section (greedy match until next ## heading or end)
        features_match = re.search(
            r'##\s+Features\s*\n(.*?)(?=\n##\s|\Z)',
            content,
            re.IGNORECASE | re.DOTALL
        )

        if not features_match:
            return features

        features_section = features_match.group(1)

        # Extract individual features (###)
        # Split by ### headers first
        feature_sections = re.split(r'\n###\s+', '\n' + features_section)
        # Remove empty first element
        feature_sections = [s for s in feature_sections if s.strip()]

        for section in feature_sections:
            # First line is the feature name
            lines = section.split('\n', 1)
            if not lines:
                continue

            feature_name = lines[0].strip()
            feature_body = lines[1] if len(lines) > 1 else ""

            # Generate ID from name
            feature_id = self._generate_feature_id(feature_name)

            # Extract description (first paragraph)
            description = self._extract_description(feature_body)

            # Extract requirements
            requirements = self._extract_requirements(feature_body)

            # Extract acceptance criteria
            acceptance_criteria = self._extract_acceptance_criteria(feature_body)

            # Extract technical details
            technical_details = self._extract_technical_details(feature_body)

            # Estimate complexity
            complexity = self._estimate_complexity(feature_body)

            feature = Feature(
                id=feature_id,
                name=feature_name,
                description=description,
                requirements=requirements,
                acceptance_criteria=acceptance_criteria,
                technical_details=technical_details,
                complexity=complexity
            )

            features.append(feature)

        return features

    def extract_dependencies(self, content: str) -> Dict[str, List[str]]:
        """
        Identify feature dependencies from content

        Args:
            content: Markdown content

        Returns:
            Dict mapping feature_id to list of dependency IDs
        """
        dependencies = {}

        # Look for "depends on", "requires", "needs" patterns
        dependency_patterns = [
            r'depends on:?\s*(.+?)(?:\n|$)',
            r'requires:?\s*(.+?)(?:\n|$)',
            r'needs:?\s*(.+?)(?:\n|$)',
            r'after:?\s*(.+?)(?:\n|$)'
        ]

        # Find all feature sections
        feature_pattern = r'###\s+(.+?)\n(.*?)(?=\n###|\Z)'
        matches = re.finditer(feature_pattern, content, re.DOTALL)

        for match in matches:
            feature_name = match.group(1).strip()
            feature_body = match.group(2).strip()
            feature_id = self._generate_feature_id(feature_name)

            deps = []

            # Check for dependency patterns
            for pattern in dependency_patterns:
                dep_matches = re.finditer(pattern, feature_body, re.IGNORECASE)
                for dep_match in dep_matches:
                    dep_text = dep_match.group(1).strip()

                    # Split by comma or "and"
                    dep_names = re.split(r',|\s+and\s+', dep_text)

                    for dep_name in dep_names:
                        dep_name = dep_name.strip()
                        if dep_name:
                            # Try to match to feature ID
                            dep_id = self._generate_feature_id(dep_name)
                            if dep_id not in deps:
                                deps.append(dep_id)

            if deps:
                dependencies[feature_id] = deps

        return dependencies

    def validate_spec(self, content: str) -> bool:
        """
        Ensure spec has all required sections

        Args:
            content: Markdown content

        Returns:
            True if valid, False otherwise
        """
        content_lower = content.lower()

        for section in self.required_sections:
            # Check for section heading
            pattern = rf'##\s+{re.escape(section)}'
            if not re.search(pattern, content_lower):
                return False

        return True

    def _extract_overview(self, content: str) -> str:
        """Extract project overview section"""
        overview_match = re.search(
            r'##\s+Overview\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.IGNORECASE | re.DOTALL
        )

        if overview_match:
            return overview_match.group(1).strip()

        return ""

    def _extract_tech_requirements(self, content: str) -> List[str]:
        """Extract technical requirements list"""
        tech_match = re.search(
            r'##\s+Technical Requirements\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.IGNORECASE | re.DOTALL
        )

        if not tech_match:
            return []

        tech_section = tech_match.group(1)

        # Extract bullet points
        requirements = []
        bullet_pattern = r'[-*]\s+(.+?)(?:\n|$)'
        matches = re.finditer(bullet_pattern, tech_section)

        for match in matches:
            req = match.group(1).strip()
            if req:
                requirements.append(req)

        return requirements

    def _generate_feature_id(self, feature_name: str) -> str:
        """Generate feature ID from name"""
        # Convert to lowercase, replace spaces/special chars with underscore
        feature_id = re.sub(r'[^a-z0-9]+', '_', feature_name.lower())
        feature_id = feature_id.strip('_')
        return feature_id

    def _extract_description(self, feature_body: str) -> str:
        """Extract feature description (first paragraph)"""
        # Get first non-empty paragraph
        paragraphs = feature_body.split('\n\n')

        for para in paragraphs:
            para = para.strip()
            # Skip headings and lists
            if para and not para.startswith('#') and not para.startswith('-') and not para.startswith('*'):
                return para

        return ""

    def _extract_requirements(self, feature_body: str) -> List[str]:
        """Extract requirements from feature body"""
        requirements = []

        # Look for Requirements section
        req_match = re.search(
            r'Requirements?:?\s*\n(.*?)(?=\n[A-Z]|\Z)',
            feature_body,
            re.IGNORECASE | re.DOTALL
        )

        if req_match:
            req_section = req_match.group(1)

            # Extract bullet points
            bullet_pattern = r'[-*]\s+(.+?)(?:\n|$)'
            matches = re.finditer(bullet_pattern, req_section)

            for match in matches:
                req = match.group(1).strip()
                if req:
                    requirements.append(req)

        return requirements

    def _extract_acceptance_criteria(self, feature_body: str) -> List[str]:
        """Extract acceptance criteria from feature body"""
        criteria = []

        # Look for Acceptance Criteria section
        ac_match = re.search(
            r'Acceptance Criteria:?\s*\n(.*?)(?=\n[A-Z]|\Z)',
            feature_body,
            re.IGNORECASE | re.DOTALL
        )

        if ac_match:
            ac_section = ac_match.group(1)

            # Extract bullet points or checkboxes
            bullet_pattern = r'[-*]\s*\[?\s*\]?\s*(.+?)(?:\n|$)'
            matches = re.finditer(bullet_pattern, ac_section)

            for match in matches:
                criterion = match.group(1).strip()
                if criterion:
                    criteria.append(criterion)

        return criteria

    def _extract_technical_details(self, feature_body: str) -> List[str]:
        """Extract technical details from feature body"""
        details = []

        # Look for Technical Details or Implementation section
        tech_match = re.search(
            r'(?:Technical Details?|Implementation):?\s*\n(.*?)(?=\n[A-Z]|\Z)',
            feature_body,
            re.IGNORECASE | re.DOTALL
        )

        if tech_match:
            tech_section = tech_match.group(1)

            # Extract bullet points
            bullet_pattern = r'[-*]\s+(.+?)(?:\n|$)'
            matches = re.finditer(bullet_pattern, tech_section)

            for match in matches:
                detail = match.group(1).strip()
                if detail:
                    details.append(detail)

        return details

    def _estimate_complexity(self, feature_body: str) -> str:
        """Estimate feature complexity based on content"""
        # Simple heuristics
        word_count = len(feature_body.split())
        requirement_count = len(self._extract_requirements(feature_body))

        if word_count < 100 and requirement_count < 3:
            return "simple"
        elif word_count > 300 or requirement_count > 7:
            return "complex"
        else:
            return "medium"

    def _apply_dependencies(self, features: List[Feature], dependencies: Dict[str, List[str]]):
        """Apply dependency mapping to features"""
        feature_map = {f.id: f for f in features}

        for feature_id, deps in dependencies.items():
            if feature_id in feature_map:
                # Verify dependencies exist
                valid_deps = [d for d in deps if d in feature_map]
                feature_map[feature_id].dependencies = valid_deps

    def _feature_to_dict(self, feature: Feature) -> Dict:
        """Convert Feature object to dictionary"""
        return {
            "id": feature.id,
            "name": feature.name,
            "description": feature.description,
            "requirements": feature.requirements,
            "dependencies": feature.dependencies,
            "acceptance_criteria": feature.acceptance_criteria,
            "technical_details": feature.technical_details,
            "complexity": feature.complexity
        }


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python spec_parser.py <spec_path>")
        sys.exit(1)

    spec_path = sys.argv[1]

    parser = SpecParser()
    result = parser.parse_spec(Path(spec_path))

    print(f"\n=== Spec Analysis ===")
    print(f"Features: {result['metadata']['feature_count']}")
    print(f"\nFeatures found:")

    for feature in result['features']:
        print(f"\n  • {feature['name']} ({feature['id']})")
        print(f"    Complexity: {feature['complexity']}")
        print(f"    Requirements: {len(feature['requirements'])}")
        print(f"    Dependencies: {', '.join(feature['dependencies']) if feature['dependencies'] else 'None'}")


if __name__ == "__main__":
    main()
