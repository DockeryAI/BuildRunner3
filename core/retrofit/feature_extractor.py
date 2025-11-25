"""Feature extraction - groups code artifacts into logical features"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict

from .models import CodeArtifact, ExtractedFeature, ArtifactType, ScanResult

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Extracts features from code artifacts using multiple heuristics:
    - Route patterns (API endpoint grouping)
    - Directory structure
    - Import clustering
    - Test file mapping
    """

    def __init__(self):
        self.features: List[ExtractedFeature] = []
        self.artifact_to_feature: Dict[CodeArtifact, str] = {}

    def extract_features(self, scan_result: ScanResult) -> List[ExtractedFeature]:
        """
        Extract features from scan results

        Args:
            scan_result: Result from CodebaseScanner

        Returns:
            List of extracted features
        """
        logger.info(f"Extracting features from {len(scan_result.artifacts)} artifacts")

        # Group artifacts by different heuristics
        route_groups = self._group_by_routes(scan_result.artifacts)
        dir_groups = self._group_by_directory(scan_result.artifacts)
        test_groups = self._group_by_tests(scan_result.artifacts)

        # Merge groups intelligently
        feature_groups = self._merge_groups(route_groups, dir_groups, test_groups)

        # Create features from groups
        for feature_id, (name, artifacts, confidence) in feature_groups.items():
            feature = self._create_feature(feature_id, name, artifacts, confidence)
            self.features.append(feature)

        logger.info(f"Extracted {len(self.features)} features")

        # Update scan result
        scan_result.features = self.features
        return self.features

    def _group_by_routes(self, artifacts: List[CodeArtifact]) -> Dict[str, tuple]:
        """Group artifacts by API route patterns"""
        groups = defaultdict(list)

        for artifact in artifacts:
            if artifact.type == ArtifactType.ROUTE:
                # Extract route prefix from decorators
                route_prefix = self._extract_route_prefix(artifact)
                if route_prefix:
                    groups[route_prefix].append(artifact)

        # Create feature groups
        feature_groups = {}
        for prefix, route_artifacts in groups.items():
            feature_name = self._route_prefix_to_feature_name(prefix)
            feature_id = f"feature-{prefix.replace('/', '-')}"
            feature_groups[feature_id] = (feature_name, route_artifacts, 0.9)

        logger.debug(f"Found {len(feature_groups)} route-based feature groups")
        return feature_groups

    def _group_by_directory(self, artifacts: List[CodeArtifact]) -> Dict[str, tuple]:
        """Group artifacts by directory structure"""
        groups = defaultdict(list)

        for artifact in artifacts:
            # Get meaningful directory (skip root-level and common dirs)
            parts = artifact.file_path.parts
            meaningful_dir = self._find_meaningful_directory(parts)

            if meaningful_dir:
                groups[meaningful_dir].append(artifact)

        # Create feature groups from directories with significant content
        feature_groups = {}
        for dir_name, dir_artifacts in groups.items():
            # Skip if too few artifacts
            if len(dir_artifacts) < 2:
                continue

            feature_name = self._dir_to_feature_name(dir_name)
            feature_id = f"feature-{dir_name.lower().replace(' ', '-')}"
            confidence = 0.7  # Medium confidence for directory-based grouping
            feature_groups[feature_id] = (feature_name, dir_artifacts, confidence)

        logger.debug(f"Found {len(feature_groups)} directory-based feature groups")
        return feature_groups

    def _group_by_tests(self, artifacts: List[CodeArtifact]) -> Dict[str, tuple]:
        """Group artifacts by test file patterns"""
        groups = defaultdict(list)
        test_files = {}

        # First, identify test files and what they test
        for artifact in artifacts:
            if artifact.type == ArtifactType.TEST:
                # Extract what feature this test is testing
                feature_name = self._extract_feature_from_test(artifact)
                if feature_name:
                    groups[feature_name].append(artifact)
                    test_files[feature_name] = artifact.file_path

        # Map non-test artifacts to test groups
        for artifact in artifacts:
            if artifact.type != ArtifactType.TEST:
                for feature_name, test_path in test_files.items():
                    # Match by file name similarity
                    if self._files_related(artifact.file_path, test_path):
                        groups[feature_name].append(artifact)

        # Create feature groups
        feature_groups = {}
        for feature_name, test_artifacts in groups.items():
            if len(test_artifacts) >= 2:  # At least test + implementation
                feature_id = f"feature-{feature_name.lower().replace(' ', '-')}"
                confidence = 0.8  # Good confidence for test-based grouping
                feature_groups[feature_id] = (feature_name, test_artifacts, confidence)

        logger.debug(f"Found {len(feature_groups)} test-based feature groups")
        return feature_groups

    def _merge_groups(self, *group_dicts) -> Dict[str, tuple]:
        """
        Intelligently merge feature groups from different heuristics

        Priority: routes > tests > directory
        """
        merged = {}
        artifact_assignments = {}  # Track which feature each artifact belongs to

        # Process in priority order
        for groups in group_dicts:
            for feature_id, (name, artifacts, confidence) in groups.items():
                # Check if artifacts already assigned
                unassigned = [a for a in artifacts if id(a) not in artifact_assignments]

                if not unassigned:
                    continue

                # Check if we should merge with existing feature
                merge_target = None
                for existing_id in merged:
                    existing_artifacts = merged[existing_id][1]
                    overlap = sum(1 for a in artifacts if id(a) in [id(ea) for ea in existing_artifacts])
                    overlap_ratio = overlap / len(artifacts) if artifacts else 0

                    if overlap_ratio > 0.5:  # 50% overlap
                        merge_target = existing_id
                        break

                if merge_target:
                    # Merge into existing feature
                    existing_name, existing_artifacts, existing_conf = merged[merge_target]
                    merged[merge_target] = (
                        existing_name,  # Keep existing name
                        existing_artifacts + unassigned,
                        max(existing_conf, confidence)  # Take higher confidence
                    )
                    for a in unassigned:
                        artifact_assignments[id(a)] = merge_target
                else:
                    # Create new feature
                    merged[feature_id] = (name, unassigned, confidence)
                    for a in unassigned:
                        artifact_assignments[id(a)] = feature_id

        # Handle orphaned artifacts (not in any feature)
        all_artifacts_in_features = set()
        for _, artifacts, _ in merged.values():
            all_artifacts_in_features.update(id(a) for a in artifacts)

        logger.debug(f"Merged into {len(merged)} total feature groups")
        return merged

    def _create_feature(self, feature_id: str, name: str,
                       artifacts: List[CodeArtifact], confidence: float) -> ExtractedFeature:
        """Create an ExtractedFeature from artifacts"""

        # Generate description from artifacts
        description = self._generate_description(artifacts)

        # Infer requirements from artifacts
        requirements = self._infer_requirements(artifacts)

        # Extract acceptance criteria from tests
        acceptance_criteria = self._extract_acceptance_criteria(artifacts)

        # Determine priority based on artifact complexity
        priority = self._determine_priority(artifacts)

        # Build technical details
        technical_details = {
            'files': list(set(str(a.file_path) for a in artifacts)),
            'artifact_types': list(set(a.type.value for a in artifacts)),
            'has_tests': any(a.type == ArtifactType.TEST for a in artifacts),
            'has_routes': any(a.type == ArtifactType.ROUTE for a in artifacts),
        }

        return ExtractedFeature(
            id=feature_id,
            name=name,
            description=description,
            artifacts=artifacts,
            confidence=confidence,
            priority=priority,
            requirements=requirements,
            acceptance_criteria=acceptance_criteria,
            technical_details=technical_details
        )

    def _generate_description(self, artifacts: List[CodeArtifact]) -> str:
        """Generate feature description from artifacts"""
        # Try to use docstrings
        docstrings = [a.docstring for a in artifacts if a.docstring]
        if docstrings:
            # Use first non-trivial docstring
            for doc in docstrings:
                if len(doc) > 20:
                    return doc.split('\n')[0].strip()

        # Fallback: describe artifact types
        types = set(a.type.value for a in artifacts)
        return f"Feature with {', '.join(types)}"

    def _infer_requirements(self, artifacts: List[CodeArtifact]) -> List[str]:
        """Infer requirements from artifacts"""
        requirements = []

        # Requirements from routes
        routes = [a for a in artifacts if a.type == ArtifactType.ROUTE]
        if routes:
            requirements.append(f"{len(routes)} API endpoint(s)")

        # Requirements from models
        models = [a for a in artifacts if a.type == ArtifactType.MODEL]
        if models:
            requirements.append(f"Database model(s): {', '.join(m.name for m in models)}")

        # Requirements from tests
        tests = [a for a in artifacts if a.type == ArtifactType.TEST]
        if tests:
            requirements.append(f"Tested with {len(tests)} test case(s)")

        return requirements

    def _extract_acceptance_criteria(self, artifacts: List[CodeArtifact]) -> List[str]:
        """Extract acceptance criteria from test artifacts"""
        criteria = []

        tests = [a for a in artifacts if a.type == ArtifactType.TEST]
        for test in tests:
            # Convert test name to acceptance criterion
            # test_user_can_login → User can login
            criterion = test.name.replace('test_', '').replace('_', ' ').capitalize()
            criteria.append(criterion)

        return criteria

    def _determine_priority(self, artifacts: List[CodeArtifact]) -> str:
        """Determine priority based on artifact complexity"""
        # Simple heuristic: more artifacts = higher priority
        if len(artifacts) > 10:
            return "high"
        elif len(artifacts) > 5:
            return "medium"
        else:
            return "low"

    def _extract_route_prefix(self, artifact: CodeArtifact) -> Optional[str]:
        """Extract route prefix from route artifact"""
        for decorator in artifact.decorators:
            # Look for route patterns like @app.get('/api/users/...')
            match = re.search(r'["\']/(api/)?([^/"\']+)', decorator)
            if match:
                return match.group(2)
        return None

    def _route_prefix_to_feature_name(self, prefix: str) -> str:
        """Convert route prefix to feature name"""
        # /api/users → User Management
        # /api/auth → Authentication
        name = prefix.replace('-', ' ').replace('_', ' ').title()
        if not name.endswith('Management') and not name.endswith('tion'):
            name += ' Management'
        return name

    def _find_meaningful_directory(self, parts: tuple) -> Optional[str]:
        """Find meaningful directory name from path parts"""
        # Skip common root dirs
        skip = {'src', 'lib', 'app', 'core', 'api', 'cli', 'tests', 'test'}

        for part in reversed(parts):
            if part not in skip and not part.startswith('.') and not part.startswith('__'):
                return part

        return None

    def _dir_to_feature_name(self, dir_name: str) -> str:
        """Convert directory name to feature name"""
        return dir_name.replace('-', ' ').replace('_', ' ').title()

    def _extract_feature_from_test(self, artifact: CodeArtifact) -> Optional[str]:
        """Extract feature name from test artifact"""
        # test_auth.py → Authentication
        # test_user_management.py → User Management
        filename = artifact.file_path.stem
        if filename.startswith('test_'):
            feature = filename[5:]  # Remove 'test_'
            return feature.replace('_', ' ').title()
        return None

    def _files_related(self, file1: Path, file2: Path) -> bool:
        """Check if two files are related (e.g., test and implementation)"""
        # Strip 'test_' prefix and compare stems
        stem1 = file1.stem.replace('test_', '')
        stem2 = file2.stem.replace('test_', '')
        return stem1 == stem2
