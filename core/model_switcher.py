"""
Model switching protocol for Opus → Sonnet handoff

Creates compact handoff packages that transfer planning context
from Opus (planning mode) to Sonnet (execution mode) efficiently.
"""
import json
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime


class ModelSwitcher:
    """Handle model switching from Opus (planning) to Sonnet (execution)"""

    def __init__(self, project_root: Path):
        """
        Initialize model switcher

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.handoff_dir = self.project_root / ".buildrunner" / "handoffs"
        self.handoff_dir.mkdir(parents=True, exist_ok=True)

    def create_handoff_package(
        self,
        spec_path: Path,
        features_path: Path,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create compact handoff package for Sonnet

        Args:
            spec_path: Path to PROJECT_SPEC.md
            features_path: Path to features.json
            context: Additional context (industry, use_case, constraints)

        Returns:
            Handoff package dict with compressed context

        Raises:
            FileNotFoundError: If spec or features file doesn't exist
            ValueError: If package validation fails
        """
        # Read spec and features
        if not spec_path.exists():
            raise FileNotFoundError(f"PROJECT_SPEC not found: {spec_path}")
        if not features_path.exists():
            raise FileNotFoundError(f"features.json not found: {features_path}")

        spec_content = spec_path.read_text()
        features_data = json.loads(features_path.read_text())

        # Compress context
        compressed = self.compress_context(spec_content, features_data, context)

        # Generate Sonnet prompt
        sonnet_prompt = self.generate_sonnet_prompt(compressed)

        # Create package
        timestamp = self._timestamp()
        package = {
            "version": "1.0",
            "timestamp": timestamp,
            "source_model": "claude-opus-4",
            "target_model": "claude-sonnet-4.5",
            "project_root": str(self.project_root),
            "spec_summary": compressed["spec_summary"],
            "features": compressed["features"],
            "architecture": compressed["architecture"],
            "constraints": compressed["constraints"],
            "next_steps": compressed["next_steps"],
            "sonnet_prompt": sonnet_prompt
        }

        # Validate package
        self.validate_handoff(package)

        # Save package
        package_path = self.handoff_dir / f"handoff_{timestamp}.json"
        package_path.write_text(json.dumps(package, indent=2))

        return package

    def compress_context(
        self,
        spec_content: str,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compress context by removing verbosity, keeping essentials

        Args:
            spec_content: Full PROJECT_SPEC.md content
            features: features.json data
            context: Additional context (industry, use_case, constraints)

        Returns:
            Compressed context dict with:
                - spec_summary: Key points from spec (max 1000 chars)
                - features: Essential feature list (truncated descriptions)
                - architecture: High-level architecture
                - constraints: Technical/business constraints
                - next_steps: Immediate action items (max 3)
        """
        # Extract key sections from spec
        spec_summary = self._extract_spec_summary(spec_content)

        # Simplify features to essential info
        essential_features = [
            {
                "id": f.get("id", f"feature_{i}"),
                "name": f.get("name", "Unnamed feature"),
                "description": f.get("description", "")[:200],  # Truncate to 200 chars
                "status": f.get("status", "pending"),
                "dependencies": f.get("dependencies", [])
            }
            for i, f in enumerate(features.get("features", []))
        ]

        # Extract architecture
        architecture = self._extract_architecture(spec_content)

        # Extract constraints
        constraints = context.get("constraints", [])

        # Determine next steps
        next_steps = self._determine_next_steps(essential_features)

        return {
            "spec_summary": spec_summary,
            "features": essential_features,
            "architecture": architecture,
            "constraints": constraints,
            "next_steps": next_steps
        }

    def generate_sonnet_prompt(self, compressed: Dict[str, Any]) -> str:
        """
        Generate optimized prompt for Sonnet execution

        Args:
            compressed: Compressed context from compress_context()

        Returns:
            Formatted prompt string optimized for Sonnet
        """
        prompt = f"""# BuildRunner Project Handoff

## Project Overview
{compressed["spec_summary"]}

## Architecture
{self._format_architecture(compressed["architecture"])}

## Features to Implement
{self._format_features(compressed["features"])}

## Constraints
{self._format_constraints(compressed["constraints"])}

## Next Steps
{self._format_next_steps(compressed["next_steps"])}

## Instructions
You are now in execution mode. Implement the features according to the spec and architecture above.

Start with: {compressed["next_steps"][0] if compressed["next_steps"] else "Initialize project structure"}

Follow the BuildRunner workflow:
1. Implement each feature completely with tests
2. Update features.json status as you progress
3. Ensure quality gates pass (85%+ coverage, 80%+ quality score)
4. Document as you build
"""
        return prompt

    def validate_handoff(self, package: Dict[str, Any]) -> bool:
        """
        Validate handoff package completeness

        Args:
            package: Handoff package to validate

        Returns:
            True if valid

        Raises:
            ValueError: If package missing required fields or has invalid data
        """
        required = [
            "version", "timestamp", "source_model", "target_model",
            "spec_summary", "features", "architecture", "next_steps"
        ]

        for field in required:
            if field not in package:
                raise ValueError(f"Handoff package missing required field: {field}")

        if not package["features"]:
            raise ValueError("Handoff package has no features")

        if not package["next_steps"]:
            raise ValueError("Handoff package has no next steps")

        # Validate timestamp format
        try:
            datetime.strptime(package["timestamp"], "%Y%m%d_%H%M%S")
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {package['timestamp']}")

        return True

    def load_handoff(self, handoff_id: str) -> Dict[str, Any]:
        """
        Load handoff package by ID

        Args:
            handoff_id: Timestamp ID of the handoff package

        Returns:
            Handoff package dict

        Raises:
            FileNotFoundError: If handoff package doesn't exist
        """
        package_path = self.handoff_dir / f"handoff_{handoff_id}.json"
        if not package_path.exists():
            raise FileNotFoundError(f"Handoff package not found: {handoff_id}")

        return json.loads(package_path.read_text())

    def _extract_spec_summary(self, spec_content: str) -> str:
        """
        Extract key points from PROJECT_SPEC.md

        Args:
            spec_content: Full spec content

        Returns:
            Summary string (max 1000 chars)
        """
        lines = spec_content.split("\n")
        summary = []

        # Extract first 50 lines, focusing on headers and non-empty lines
        for line in lines[:50]:
            if line.startswith("#") or (line.strip() and not line.startswith("```")):
                summary.append(line)

        summary_text = "\n".join(summary)
        # Truncate to 1000 chars
        return summary_text[:1000] if len(summary_text) > 1000 else summary_text

    def _extract_architecture(self, spec_content: str) -> Dict[str, str]:
        """
        Extract architecture from spec

        Args:
            spec_content: Full spec content

        Returns:
            Dict with frontend, backend, database, infrastructure keys
        """
        lines = spec_content.split("\n")
        arch = {
            "frontend": "",
            "backend": "",
            "database": "",
            "infrastructure": ""
        }

        in_arch_section = False
        for line in lines:
            if "## Architecture" in line or "## Technical Architecture" in line:
                in_arch_section = True
                continue
            elif in_arch_section and line.startswith("##"):
                # Exited architecture section
                break
            elif in_arch_section and line.strip():
                # Parse architecture details
                line_lower = line.lower()
                if "frontend" in line_lower or "ui" in line_lower:
                    arch["frontend"] = line.strip()
                elif "backend" in line_lower or "api" in line_lower:
                    arch["backend"] = line.strip()
                elif "database" in line_lower or "db" in line_lower:
                    arch["database"] = line.strip()
                elif "infrastructure" in line_lower or "deployment" in line_lower:
                    arch["infrastructure"] = line.strip()

        return arch

    def _determine_next_steps(self, features: List[Dict]) -> List[str]:
        """
        Determine next steps based on feature status

        Args:
            features: List of feature dicts

        Returns:
            List of next step strings (max 3)
        """
        # Filter to pending features
        pending = [f for f in features if f.get("status") == "pending"]

        if not pending:
            return ["Review and test completed features"]

        # Prioritize features without dependencies
        no_deps = [f for f in pending if not f.get("dependencies")]

        if no_deps:
            # Return up to 3 features without dependencies
            return [f"Implement feature: {f['name']}" for f in no_deps[:3]]
        else:
            # Return up to 3 pending features
            return [f"Implement feature: {f['name']}" for f in pending[:3]]

    def _format_architecture(self, arch: Dict[str, str]) -> str:
        """Format architecture for prompt"""
        lines = []
        for key, value in arch.items():
            if value:
                lines.append(f"- {key.capitalize()}: {value}")
        return "\n".join(lines) if lines else "Architecture not specified"

    def _format_features(self, features: List[Dict]) -> str:
        """Format features for prompt (max 10 features)"""
        if not features:
            return "No features defined"

        lines = []
        for i, f in enumerate(features[:10], 1):  # Max 10 features
            status = f.get("status", "pending")
            desc = f.get("description", "No description")
            lines.append(f"{i}. {f['name']} ({status})")
            lines.append(f"   {desc}")

        if len(features) > 10:
            lines.append(f"\n... and {len(features) - 10} more features")

        return "\n".join(lines)

    def _format_constraints(self, constraints: List[str]) -> str:
        """Format constraints for prompt"""
        if not constraints:
            return "No specific constraints"
        return "\n".join([f"- {c}" for c in constraints])

    def _format_next_steps(self, steps: List[str]) -> str:
        """Format next steps for prompt"""
        if not steps:
            return "No next steps defined"
        return "\n".join([f"{i+1}. {s}" for i, s in enumerate(steps)])

    def _timestamp(self) -> str:
        """Generate timestamp string in format YYYYMMDD_HHMMSS"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
