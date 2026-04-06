# PRD Feature: FEAT-PRD-001
"""PRD Synthesizer - generates PROJECT_SPEC.md from extracted features"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from .models import ExtractedFeature, ScanResult
from core.prd.prd_controller import PRD, PRDFeature
from .doc_scanner import DocumentationScanner
from .doc_analyzer import DocumentationAnalyzer

logger = logging.getLogger(__name__)


class PRDSynthesizer:
    """Generates PRD (PROJECT_SPEC.md) from extracted features"""

    def __init__(self):
        self.doc_analyzer = DocumentationAnalyzer()

    def synthesize(
        self, scan_result: ScanResult, output_path: Path = None, project_root: Optional[Path] = None
    ) -> PRD:
        """
        Generate PRD from scan results

        Args:
            scan_result: Results from codebase scan
            output_path: Optional path to write PROJECT_SPEC.md
            project_root: Optional project root path for documentation scanning

        Returns:
            PRD object
        """
        logger.info(f"Synthesizing PRD from {len(scan_result.features)} features")

        # Scan and analyze documentation if project_root provided
        doc_sections = {}
        if project_root:
            try:
                logger.info("Scanning project documentation...")
                scanner = DocumentationScanner(project_root)
                docs = scanner.scan()

                if docs:
                    logger.info(f"Found {len(docs)} documentation files, analyzing...")
                    doc_sections = self.doc_analyzer.sync_analyze_for_prd(
                        docs, scan_result.project_name
                    )
                else:
                    logger.info("No documentation found")
            except Exception as e:
                logger.warning(f"Failed to analyze documentation: {e}")

        # Generate PRD
        prd = self._create_prd(scan_result, doc_sections)

        # Write to file if path provided
        if output_path:
            self._write_prd_markdown(prd, output_path)
            logger.info(f"Wrote PROJECT_SPEC.md to {output_path}")

        return prd

    def _create_prd(self, scan_result: ScanResult, doc_sections: Dict = None) -> PRD:
        """Create PRD object from scan results and documentation analysis"""

        if doc_sections is None:
            doc_sections = {}

        # Convert ExtractedFeatures to PRDFeatures
        # Mark all discovered features as "implemented" since they exist in the codebase
        prd_features = []
        for i, feature in enumerate(scan_result.features, 1):
            prd_feature = PRDFeature(
                id=feature.id,
                name=feature.name,
                description=feature.description,
                priority=feature.priority,
                status="implemented",  # Features discovered from code are already implemented
                requirements=feature.requirements,
                acceptance_criteria=feature.acceptance_criteria,
                technical_details=feature.technical_details,
                dependencies=feature.dependencies,
            )
            prd_features.append(prd_feature)

        # Generate overview from scan results and documentation
        overview = self._generate_overview(scan_result, doc_sections)

        # Generate architecture details
        architecture = self._generate_architecture(scan_result, doc_sections)

        # Create PRD
        prd = PRD(
            project_name=scan_result.project_name,
            version="1.0.0",
            overview=overview,
            features=prd_features,
            architecture=architecture,
            metadata={
                "generated_from": "br attach",
                "scan_date": datetime.now().isoformat(),
                "total_files": scan_result.total_files,
                "total_lines": scan_result.total_lines,
                "languages": scan_result.languages,
                "frameworks": scan_result.frameworks,
                "doc_sections": doc_sections,  # Store documentation sections
            },
        )

        return prd

    def _generate_overview(self, scan_result: ScanResult, doc_sections: Dict = None) -> str:
        """Generate project overview from scan results and documentation"""
        if doc_sections is None:
            doc_sections = {}

        lines = []

        # Executive Summary from documentation
        if doc_sections.get("executive_summary"):
            lines.append("### Executive Summary")
            lines.append("")
            lines.append(doc_sections["executive_summary"])
            lines.append("")

        # Project Goals from documentation
        if doc_sections.get("goals"):
            lines.append("### Project Goals")
            lines.append("")
            for goal in doc_sections["goals"]:
                lines.append(f"- {goal}")
            lines.append("")

        # Target Users from documentation
        if doc_sections.get("target_users"):
            lines.append("### Target Users")
            lines.append("")
            lines.append(doc_sections["target_users"])
            lines.append("")

        # Basic stats
        lines.append("### Codebase Analysis Summary")
        lines.append("")
        lines.append(f"- **Files:** {scan_result.total_files}")
        lines.append(f"- **Lines of Code:** {scan_result.total_lines:,}")
        lines.append(f"- **Languages:** {', '.join(scan_result.languages)}")
        if scan_result.frameworks:
            lines.append(f"- **Frameworks:** {', '.join(scan_result.frameworks)}")
        lines.append("")

        # Feature summary
        lines.append("### Detected Features")
        lines.append("")
        lines.append(
            f"This project contains {len(scan_result.features)} main features, "
            f"identified through code analysis:"
        )
        lines.append("")

        for i, feature in enumerate(scan_result.features[:5], 1):  # Top 5
            confidence_emoji = (
                "🟢" if feature.confidence >= 0.8 else "🟡" if feature.confidence >= 0.6 else "🔴"
            )
            lines.append(f"{i}. **{feature.name}** {confidence_emoji}")
            lines.append(
                f"   - {feature.artifact_count} code artifacts across {feature.file_count} files"
            )

        if len(scan_result.features) > 5:
            lines.append(f"\n...and {len(scan_result.features) - 5} more features.")

        lines.append("")
        lines.append("*Generated by BuildRunner 3 `br attach` command.*")
        lines.append("*Review and edit feature details as needed.*")

        return "\n".join(lines)

    def _generate_architecture(self, scan_result: ScanResult, doc_sections: Dict = None) -> dict:
        """Generate architecture information from scan results and documentation"""
        if doc_sections is None:
            doc_sections = {}

        architecture = {
            "languages": scan_result.languages,
            "frameworks": scan_result.frameworks,
            "structure": {},
        }

        # Add technical requirements from documentation
        if doc_sections.get("technical_requirements"):
            architecture["technical_requirements"] = doc_sections["technical_requirements"]

        # Identify architecture patterns
        has_api = any("api" in f.id.lower() for f in scan_result.features)
        has_models = any(a.type.value == "model" for f in scan_result.features for a in f.artifacts)
        has_ui = any("component" in str(f.technical_details) for f in scan_result.features)
        has_tests = any(f.technical_details.get("has_tests") for f in scan_result.features)

        if has_api and has_models:
            architecture["pattern"] = "REST API + Database"
        elif has_ui and has_api:
            architecture["pattern"] = "Full-stack (Frontend + Backend API)"
        elif has_api:
            architecture["pattern"] = "API Service"
        elif has_ui:
            architecture["pattern"] = "Frontend Application"
        else:
            architecture["pattern"] = "Application"

        architecture["has_tests"] = has_tests
        architecture["test_coverage"] = self._estimate_test_coverage(scan_result)

        return architecture

    def _estimate_test_coverage(self, scan_result: ScanResult) -> str:
        """Estimate test coverage based on features with tests"""
        features_with_tests = sum(
            1 for f in scan_result.features if f.technical_details.get("has_tests")
        )
        total_features = len(scan_result.features)

        if total_features == 0:
            return "unknown"

        coverage_ratio = features_with_tests / total_features

        if coverage_ratio >= 0.8:
            return "high"
        elif coverage_ratio >= 0.5:
            return "medium"
        elif coverage_ratio > 0:
            return "low"
        else:
            return "none"

    def _write_prd_markdown(self, prd: PRD, output_path: Path):
        """Write PRD to PROJECT_SPEC.md format"""
        # Check if file exists and preserve existing content
        existing_features = {}
        if output_path.exists():
            logger.info(f"Existing PROJECT_SPEC.md found, preserving user-defined features...")
            try:
                existing_content = output_path.read_text()
                # Parse existing features to preserve user-added ones
                existing_features = self._parse_existing_features(existing_content)
                # Create backup
                backup_path = output_path.parent / f"PROJECT_SPEC.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                backup_path.write_text(existing_content)
                logger.info(f"Created backup at {backup_path}")
            except Exception as e:
                logger.warning(f"Could not parse existing PROJECT_SPEC.md: {e}")

        lines = []
        doc_sections = prd.metadata.get("doc_sections", {})

        # Header
        lines.append(f"# {prd.project_name}")
        lines.append("")
        lines.append(f"**Version:** {prd.version}")
        lines.append(f"**Last Updated:** {prd.last_updated}")
        lines.append(f"**Generated:** {prd.metadata.get('scan_date', 'N/A')}")
        lines.append("")

        # Overview
        lines.append("## Project Overview")
        lines.append("")
        lines.append(prd.overview)
        lines.append("")

        # User Stories from documentation
        if doc_sections.get("user_stories"):
            lines.append("## User Stories")
            lines.append("")
            for story in doc_sections["user_stories"]:
                lines.append(f"- {story}")
            lines.append("")

        # Architecture
        if prd.architecture:
            lines.append("## Architecture")
            lines.append("")
            if "pattern" in prd.architecture:
                lines.append(f"**Pattern:** {prd.architecture['pattern']}")
            if "languages" in prd.architecture:
                lines.append(f"**Languages:** {', '.join(prd.architecture['languages'])}")
            if "frameworks" in prd.architecture:
                lines.append(f"**Frameworks:** {', '.join(prd.architecture['frameworks'])}")
            if "test_coverage" in prd.architecture:
                lines.append(f"**Test Coverage:** {prd.architecture['test_coverage']}")
            lines.append("")

            # Technical Requirements from documentation
            if "technical_requirements" in prd.architecture:
                tech_req = prd.architecture["technical_requirements"]
                lines.append("### Technical Requirements")
                lines.append("")
                if tech_req.get("frontend"):
                    lines.append(f"**Frontend:** {tech_req['frontend']}")
                if tech_req.get("backend"):
                    lines.append(f"**Backend:** {tech_req['backend']}")
                if tech_req.get("database"):
                    lines.append(f"**Database:** {tech_req['database']}")
                if tech_req.get("infrastructure"):
                    lines.append(f"**Infrastructure:** {tech_req['infrastructure']}")
                lines.append("")

        # Success Criteria from documentation
        if doc_sections.get("success_criteria"):
            lines.append("## Success Criteria")
            lines.append("")
            for criterion in doc_sections["success_criteria"]:
                lines.append(f"- [ ] {criterion}")
            lines.append("")

        # Features (merge existing with scanned)
        all_features = {}

        # Add existing features first (they take priority)
        for feat_id, feat_data in existing_features.items():
            all_features[feat_id] = feat_data

        # Add scanned features that aren't already in existing
        for feature in prd.features:
            if feature.id not in all_features:
                all_features[feature.id] = {
                    'name': feature.name,
                    'priority': feature.priority,
                    'description': feature.description,
                    'requirements': feature.requirements,
                    'acceptance_criteria': feature.acceptance_criteria,
                    'technical_details': feature.technical_details,
                    'status': feature.status
                }

        # Write all features
        for i, (feat_id, feat_data) in enumerate(all_features.items(), 1):
            lines.append(f"## Feature {i}: {feat_data['name']}")
            lines.append("")
            lines.append(f"**ID:** {feat_id}")
            if 'priority' in feat_data:
                lines.append(f"**Priority:** {feat_data['priority'].title() if isinstance(feat_data['priority'], str) else feat_data['priority']}")
            if 'status' in feat_data:
                lines.append(f"**Status:** {feat_data['status']}")
            lines.append("")

            if 'description' in feat_data and feat_data['description']:
                lines.append("### Description")
                lines.append("")
                lines.append(feat_data['description'])
                lines.append("")

            if 'requirements' in feat_data and feat_data['requirements']:
                lines.append("### Requirements")
                lines.append("")
                for req in feat_data['requirements']:
                    lines.append(f"- {req}")
                lines.append("")

            if 'acceptance_criteria' in feat_data and feat_data['acceptance_criteria']:
                lines.append("### Acceptance Criteria")
                lines.append("")
                for criterion in feat_data['acceptance_criteria']:
                    lines.append(f"- [ ] {criterion}")
                lines.append("")

            if 'technical_details' in feat_data and feat_data['technical_details']:
                lines.append("### Technical Details")
                lines.append("")

                tech_details = feat_data['technical_details']
                # Show key technical details
                if "files" in tech_details:
                    if isinstance(tech_details['files'], list):
                        lines.append(f"**Files:** {', '.join(tech_details['files'])}")
                    else:
                        lines.append(f"**Files:** {len(tech_details['files'])}")
                if "artifact_types" in tech_details:
                    types = tech_details["artifact_types"]
                    lines.append(f"**Components:** {', '.join(types)}")
                if "completed" in tech_details:
                    lines.append(f"**Completed:** {tech_details['completed']}")
                if "has_routes" in tech_details and tech_details["has_routes"]:
                    lines.append("**Type:** API Endpoint")
                if "has_tests" in tech_details and tech_details["has_tests"]:
                    lines.append("**Tested:** ✓")

                lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*This PROJECT_SPEC.md was auto-generated by BuildRunner 3.*")
        lines.append("*Generated from existing codebase using `br attach` command.*")
        lines.append(
            f"*Scanned {prd.metadata.get('total_files', 0)} files "
            f"({prd.metadata.get('total_lines', 0):,} lines) on {prd.metadata.get('scan_date', 'N/A')[:10]}.*"
        )
        lines.append("")

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines))

    def _parse_existing_features(self, content: str) -> Dict:
        """Parse existing PROJECT_SPEC.md to extract features"""
        features = {}
        current_feature = None
        current_section = None
        lines = content.split('\n')

        import re

        for line in lines:
            # Check for feature header (## Feature N: Name or ### FEAT-XXX-NNN: Name)
            feature_match = re.match(r'^###?\s+(?:Feature\s+\d+:\s+)?(\w+-\w+-\d+):\s+(.+)', line)
            if not feature_match:
                # Also check for ## Feature N: Name format with ID on next line
                feature_match = re.match(r'^##\s+Feature\s+\d+:\s+(.+)', line)
                if feature_match:
                    # Look for ID in next few lines
                    current_feature = {'name': feature_match.group(1).strip()}
                    current_section = None
                    continue

            if feature_match:
                feat_id = feature_match.group(1) if len(feature_match.groups()) == 2 else None
                feat_name = feature_match.group(2) if len(feature_match.groups()) == 2 else feature_match.group(1)

                if feat_id and feat_id.startswith('FEAT-'):
                    # Save previous feature if exists
                    if current_feature and 'id' in current_feature:
                        features[current_feature['id']] = current_feature

                    current_feature = {
                        'id': feat_id,
                        'name': feat_name.strip()
                    }
                    current_section = None
                continue

            if current_feature:
                # Parse ID line
                if line.startswith('**ID:**'):
                    feat_id = line.replace('**ID:**', '').strip()
                    current_feature['id'] = feat_id

                # Parse Status
                elif line.startswith('**Status:**'):
                    current_feature['status'] = line.replace('**Status:**', '').strip()

                # Parse Priority
                elif line.startswith('**Priority:**'):
                    current_feature['priority'] = line.replace('**Priority:**', '').strip()

                # Parse Files
                elif line.startswith('**Files:**'):
                    files_str = line.replace('**Files:**', '').strip()
                    # Handle both [file1, file2] format and plain list
                    if files_str.startswith('[') and files_str.endswith(']'):
                        files_str = files_str[1:-1]
                    current_feature.setdefault('technical_details', {})['files'] = [
                        f.strip() for f in files_str.split(',')
                    ]

                # Parse Completed percentage
                elif line.startswith('**Completed:**'):
                    completed = line.replace('**Completed:**', '').strip()
                    current_feature.setdefault('technical_details', {})['completed'] = completed

                # Parse sections
                elif line.startswith('### '):
                    section_name = line.replace('###', '').strip().lower()
                    if 'description' in section_name:
                        current_section = 'description'
                        current_feature['description'] = ''
                    elif 'requirement' in section_name:
                        current_section = 'requirements'
                        current_feature['requirements'] = []
                    elif 'acceptance' in section_name:
                        current_section = 'acceptance_criteria'
                        current_feature['acceptance_criteria'] = []
                    elif 'technical' in section_name or 'component' in section_name:
                        current_section = 'technical_details'
                        if 'technical_details' not in current_feature:
                            current_feature['technical_details'] = {}

                # Parse section content
                elif current_section and line.strip():
                    if current_section == 'description':
                        if current_feature['description']:
                            current_feature['description'] += '\n'
                        current_feature['description'] += line.strip()
                    elif current_section == 'requirements' and line.strip().startswith('-'):
                        current_feature['requirements'].append(line.strip()[1:].strip())
                    elif current_section == 'acceptance_criteria' and line.strip().startswith('-'):
                        current_feature['acceptance_criteria'].append(
                            line.strip().replace('- [ ]', '').replace('- [x]', '').strip()
                        )

        # Save last feature
        if current_feature and 'id' in current_feature:
            features[current_feature['id']] = current_feature

        logger.info(f"Parsed {len(features)} existing features from PROJECT_SPEC.md")
        return features
