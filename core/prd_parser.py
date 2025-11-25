"""
PRD Parser - Parse and Validate PROJECT_SPEC.md

Extracts structured data from PROJECT_SPEC.md including features, phases,
dependencies, and credentials. Validates completeness and tracks deltas.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class Feature:
    """Extracted feature from PRD"""

    name: str
    description: str
    priority: str = "medium"
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Phase:
    """Implementation phase from PRD"""

    number: int
    name: str
    features: List[str] = field(default_factory=list)
    duration: Optional[str] = None


@dataclass
class Credential:
    """API credential or service key"""

    service: str
    required: bool = True
    deferred: bool = False


@dataclass
class ParsedSpec:
    """Parsed PROJECT_SPEC data"""

    status: Optional[str] = None
    industry: Optional[str] = None
    use_case: Optional[str] = None
    tech_stack: Optional[str] = None
    features: List[Feature] = field(default_factory=list)
    phases: List[Phase] = field(default_factory=list)
    credentials: List[Credential] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    raw_sections: Dict[str, str] = field(default_factory=dict)


class PRDParser:
    """
    Parse PROJECT_SPEC.md and extract structured data.

    Features:
    - Extract metadata (status, industry, use case, tech stack)
    - Parse features and user stories
    - Extract implementation phases
    - Identify dependencies and credentials
    - Validate completeness
    - Track deltas for incremental updates
    """

    def __init__(self, spec_path: str):
        self.spec_path = Path(spec_path)
        self.previous_parse: Optional[ParsedSpec] = None

    def parse(self) -> ParsedSpec:
        """Parse PROJECT_SPEC.md and return structured data"""
        if not self.spec_path.exists():
            raise FileNotFoundError(f"PROJECT_SPEC not found: {self.spec_path}")

        with open(self.spec_path, "r") as f:
            content = f.read()

        spec = ParsedSpec()

        # Parse metadata
        spec.status = self._extract_metadata(content, "Status")
        spec.industry = self._extract_metadata(content, "Industry")
        spec.use_case = self._extract_metadata(content, "Use Case")
        spec.tech_stack = self._extract_metadata(content, "Tech Stack")

        # Parse sections
        sections = self._split_sections(content)
        spec.raw_sections = sections

        # Extract features from user stories
        if "Product Requirements" in sections:
            spec.features = self._extract_features(sections["Product Requirements"])

        # Extract phases from implementation section
        if "Technical Architecture" in sections:
            spec.phases = self._extract_phases(sections["Technical Architecture"])
            spec.dependencies = self._extract_dependencies(sections["Technical Architecture"])

        # Extract credentials
        if "Product Requirements" in sections:
            spec.credentials = self._extract_credentials(sections["Product Requirements"])

        return spec

    def _extract_metadata(self, content: str, key: str) -> Optional[str]:
        """Extract metadata value from header"""
        pattern = rf"\*\*{key}\*\*:\s*(.+)"
        match = re.search(pattern, content)
        return match.group(1).strip() if match else None

    def _split_sections(self, content: str) -> Dict[str, str]:
        """Split content into sections"""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split("\n"):
            # Check if this is a section header (# followed by text)
            if line.startswith("# ") and not line.startswith("# PROJECT_SPEC"):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content)

                # Start new section
                current_section = line[2:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _extract_features(self, prd_content: str) -> List[Feature]:
        """Extract features from user stories"""
        features = []

        # Look for user stories pattern
        story_pattern = r"- As a (.+?), I want (.+?) so that (.+)"
        matches = re.finditer(story_pattern, prd_content)

        for i, match in enumerate(matches):
            user_type, goal, benefit = match.groups()

            feature = Feature(
                name=f"feature_{i+1}",
                description=f"{goal.strip()} ({benefit.strip()})",
                priority="high" if i < 3 else "medium",
            )
            features.append(feature)

        return features

    def _extract_phases(self, tech_content: str) -> List[Phase]:
        """Extract implementation phases"""
        phases = []

        # Look for phase patterns like "Phase 1:", "Week 1:", etc.
        phase_pattern = r"(?:Phase|Week)\s+(\d+)(?::|,)\s*(.+?)(?:\n|$)"
        matches = re.finditer(phase_pattern, tech_content, re.MULTILINE)

        for match in matches:
            number, name = match.groups()

            phase = Phase(number=int(number), name=name.strip())
            phases.append(phase)

        return phases

    def _extract_dependencies(self, tech_content: str) -> Set[str]:
        """Extract technology dependencies"""
        dependencies = set()

        # Common dependency patterns
        dep_patterns = [
            r"(?:using|with|built on)\s+([A-Z][a-zA-Z0-9]+)",
            r"([A-Z][a-zA-Z0-9]+)\s+(?:framework|library)",
            r"- \*\*Frontend\*\*:\s*(.+)",
            r"- \*\*Backend\*\*:\s*(.+)",
            r"- \*\*Database\*\*:\s*(.+)",
        ]

        for pattern in dep_patterns:
            matches = re.finditer(pattern, tech_content)
            for match in matches:
                dep = match.group(1).strip()
                # Clean up common words
                if dep and len(dep) > 2 and dep.lower() not in ["the", "and", "for", "with"]:
                    dependencies.add(dep)

        return dependencies

    def _extract_credentials(self, prd_content: str) -> List[Credential]:
        """Extract required credentials/API keys"""
        credentials = []

        # Look for mentions of API keys, services
        service_keywords = ["API", "OAuth", "Auth0", "Stripe", "AWS", "Google", "Facebook"]

        for keyword in service_keywords:
            if keyword in prd_content:
                credentials.append(Credential(service=keyword, required=True, deferred=False))

        return credentials

    def validate_completeness(self, spec: ParsedSpec) -> Dict[str, List[str]]:
        """
        Validate spec completeness and return issues.

        Returns:
            Dictionary of section names to list of issues
        """
        issues = {}

        # Check required metadata
        if not spec.status:
            issues.setdefault("metadata", []).append("Missing status")
        if not spec.industry:
            issues.setdefault("metadata", []).append("Missing industry")
        if not spec.use_case:
            issues.setdefault("metadata", []).append("Missing use case")

        # Check required sections
        required_sections = [
            "Product Requirements",
            "Technical Architecture",
            "Design Architecture",
        ]
        for section in required_sections:
            if section not in spec.raw_sections or not spec.raw_sections[section].strip():
                issues.setdefault("sections", []).append(f"Missing or empty: {section}")

        # Check features
        if not spec.features:
            issues.setdefault("features", []).append("No features or user stories found")

        # Check phases
        if not spec.phases:
            issues.setdefault("phases", []).append("No implementation phases defined")

        return issues

    def calculate_delta(self, new_spec: ParsedSpec) -> Dict[str, List[str]]:
        """
        Calculate changes between previous parse and new parse.

        Returns:
            Dictionary of change types to list of changes
        """
        if not self.previous_parse:
            return {"status": ["Initial parse - no previous version"]}

        delta = {}

        # Check metadata changes
        if new_spec.status != self.previous_parse.status:
            delta.setdefault("metadata", []).append(
                f"Status: {self.previous_parse.status} → {new_spec.status}"
            )

        # Check feature changes
        old_feature_names = {f.name for f in self.previous_parse.features}
        new_feature_names = {f.name for f in new_spec.features}

        added_features = new_feature_names - old_feature_names
        removed_features = old_feature_names - new_feature_names

        if added_features:
            delta.setdefault("features", []).append(f"Added: {', '.join(added_features)}")
        if removed_features:
            delta.setdefault("features", []).append(f"Removed: {', '.join(removed_features)}")

        # Check phase changes
        if len(new_spec.phases) != len(self.previous_parse.phases):
            delta.setdefault("phases", []).append(
                f"Phase count changed: {len(self.previous_parse.phases)} → {len(new_spec.phases)}"
            )

        # Store new parse as previous for next delta
        self.previous_parse = new_spec

        return delta if delta else {"status": ["No changes detected"]}


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python prd_parser.py <spec_path>")
        sys.exit(1)

    spec_path = sys.argv[1]

    parser = PRDParser(spec_path)
    spec = parser.parse()

    print(f"\nParsed PROJECT_SPEC:")
    print(f"  Status: {spec.status}")
    print(f"  Industry: {spec.industry}")
    print(f"  Use Case: {spec.use_case}")
    print(f"  Tech Stack: {spec.tech_stack}")
    print(f"  Features: {len(spec.features)}")
    print(f"  Phases: {len(spec.phases)}")
    print(f"  Dependencies: {len(spec.dependencies)}")
    print(f"  Credentials: {len(spec.credentials)}")

    # Validate
    issues = parser.validate_completeness(spec)
    if issues:
        print(f"\nValidation Issues:")
        for section, section_issues in issues.items():
            print(f"  {section}:")
            for issue in section_issues:
                print(f"    - {issue}")
    else:
        print(f"\n✓ Spec is complete")


if __name__ == "__main__":
    main()
