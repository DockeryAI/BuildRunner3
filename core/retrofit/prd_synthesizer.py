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

        # Features
        for i, feature in enumerate(prd.features, 1):
            lines.append(f"## Feature {i}: {feature.name}")
            lines.append("")
            lines.append(f"**Priority:** {feature.priority.title()}")
            lines.append("")

            if feature.description:
                lines.append("### Description")
                lines.append("")
                lines.append(feature.description)
                lines.append("")

            if feature.requirements:
                lines.append("### Requirements")
                lines.append("")
                for req in feature.requirements:
                    lines.append(f"- {req}")
                lines.append("")

            if feature.acceptance_criteria:
                lines.append("### Acceptance Criteria")
                lines.append("")
                for criterion in feature.acceptance_criteria:
                    lines.append(f"- [ ] {criterion}")
                lines.append("")

            if feature.technical_details:
                lines.append("### Technical Details")
                lines.append("")

                # Show key technical details
                if "files" in feature.technical_details:
                    lines.append(f"**Files:** {len(feature.technical_details['files'])}")
                if "artifact_types" in feature.technical_details:
                    types = feature.technical_details["artifact_types"]
                    lines.append(f"**Components:** {', '.join(types)}")
                if (
                    "has_routes" in feature.technical_details
                    and feature.technical_details["has_routes"]
                ):
                    lines.append("**Type:** API Endpoint")
                if (
                    "has_tests" in feature.technical_details
                    and feature.technical_details["has_tests"]
                ):
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
