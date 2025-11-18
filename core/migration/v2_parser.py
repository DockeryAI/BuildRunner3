"""
BuildRunner 2.0 Project Parser

Parses legacy .runner/ directory structure and extracts:
- HRPO data
- Governance configuration
- Feature metadata
- Supabase integrations
- Git history
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
import subprocess


@dataclass
class V2Project:
    """
    Represents a parsed BuildRunner 2.0 project
    """
    root_path: Path
    hrpo_data: Dict[str, Any] = field(default_factory=dict)
    governance_config: Dict[str, Any] = field(default_factory=dict)
    features: List[Dict[str, Any]] = field(default_factory=list)
    supabase_config: Optional[Dict[str, Any]] = None
    git_history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Validation flags
    has_runner_dir: bool = False
    has_hrpo: bool = False
    has_governance: bool = False
    has_git: bool = False
    is_valid: bool = False

    # Issues found during parsing
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class V2ProjectParser:
    """
    Parser for BuildRunner 2.0 projects

    Extracts all data from .runner/ directory structure:
    - HRPO (Hypothesis-Reality-Plan-Outcome) data
    - Governance rules and policies
    - Features and build plan
    - Supabase integration config
    - Git commit history
    """

    def __init__(self, project_path: Path):
        """
        Initialize parser

        Args:
            project_path: Path to v2.0 project root
        """
        self.project_path = Path(project_path)
        self.runner_dir = self.project_path / ".runner"

    def parse(self) -> V2Project:
        """
        Parse v2.0 project and extract all data

        Returns:
            V2Project with all extracted data
        """
        project = V2Project(root_path=self.project_path)

        # Validate basic structure
        if not self._validate_structure(project):
            return project

        # Parse each component
        self._parse_hrpo(project)
        self._parse_governance(project)
        self._extract_features(project)
        self._parse_supabase_config(project)
        self._extract_git_history(project)
        self._extract_metadata(project)

        # Final validation
        project.is_valid = self._validate_project(project)

        return project

    def _validate_structure(self, project: V2Project) -> bool:
        """
        Validate basic v2.0 project structure

        Args:
            project: Project to validate

        Returns:
            True if valid structure
        """
        # Check root path exists
        if not self.project_path.exists():
            project.errors.append(f"Project path does not exist: {self.project_path}")
            return False

        # Check .runner directory
        if not self.runner_dir.exists():
            project.errors.append("No .runner/ directory found - not a BuildRunner 2.0 project")
            return False

        project.has_runner_dir = True

        # Check for git
        git_dir = self.project_path / ".git"
        if git_dir.exists():
            project.has_git = True
        else:
            project.warnings.append("No .git directory - git history will not be preserved")

        return True

    def _parse_hrpo(self, project: V2Project):
        """
        Parse HRPO (Hypothesis-Reality-Plan-Outcome) data

        Args:
            project: Project to update
        """
        hrpo_file = self.runner_dir / "hrpo.json"

        if not hrpo_file.exists():
            project.warnings.append("No hrpo.json found")
            return

        try:
            with open(hrpo_file, 'r') as f:
                project.hrpo_data = json.load(f)
            project.has_hrpo = True
        except json.JSONDecodeError as e:
            project.errors.append(f"Invalid hrpo.json: {e}")
        except Exception as e:
            project.errors.append(f"Error reading hrpo.json: {e}")

    def _parse_governance(self, project: V2Project):
        """
        Parse governance configuration

        Args:
            project: Project to update
        """
        governance_file = self.runner_dir / "governance.json"

        if not governance_file.exists():
            project.warnings.append("No governance.json found")
            return

        try:
            with open(governance_file, 'r') as f:
                project.governance_config = json.load(f)
            project.has_governance = True
        except json.JSONDecodeError as e:
            project.errors.append(f"Invalid governance.json: {e}")
        except Exception as e:
            project.errors.append(f"Error reading governance.json: {e}")

    def _extract_features(self, project: V2Project):
        """
        Extract features from HRPO and governance data

        Args:
            project: Project to update
        """
        if not project.hrpo_data:
            return

        # Extract from HRPO features list
        features_list = project.hrpo_data.get("features", [])
        if isinstance(features_list, list):
            for feature in features_list:
                if isinstance(feature, str):
                    # Simple string feature
                    project.features.append({
                        "name": feature,
                        "description": feature,
                        "status": "unknown"
                    })
                elif isinstance(feature, dict):
                    # Structured feature
                    project.features.append(feature)

        # Extract from build plan
        build_plan = project.hrpo_data.get("build_plan", {})
        if build_plan and "phases" in build_plan:
            for phase in build_plan["phases"]:
                phase_name = phase.get("name", "Unknown Phase")
                steps = phase.get("steps", [])

                for step in steps:
                    step_name = step.get("name", "Unknown Step")
                    done = step.get("done", False)

                    project.features.append({
                        "name": f"{phase_name}: {step_name}",
                        "description": f"Step {step.get('id', '?')}: {step_name}",
                        "status": "completed" if done else "pending",
                        "phase": phase_name,
                        "step_id": step.get("id")
                    })

    def _parse_supabase_config(self, project: V2Project):
        """
        Parse Supabase configuration if present

        Args:
            project: Project to update
        """
        # Check for Supabase config in various locations
        possible_locations = [
            self.runner_dir / "supabase.json",
            self.project_path / "supabase" / "config.json",
            self.project_path / ".env"
        ]

        for config_file in possible_locations:
            if config_file.exists():
                if config_file.suffix == ".json":
                    try:
                        with open(config_file, 'r') as f:
                            project.supabase_config = json.load(f)
                        project.metadata["supabase_config_source"] = str(config_file)
                        break
                    except Exception as e:
                        project.warnings.append(f"Error reading Supabase config from {config_file}: {e}")
                elif config_file.name == ".env":
                    # Extract Supabase vars from .env
                    try:
                        with open(config_file, 'r') as f:
                            env_content = f.read()

                        supabase_vars = {}
                        for line in env_content.splitlines():
                            if line.startswith("SUPABASE_"):
                                key, value = line.split("=", 1)
                                supabase_vars[key] = value

                        if supabase_vars:
                            project.supabase_config = supabase_vars
                            project.metadata["supabase_config_source"] = str(config_file)
                            break
                    except Exception as e:
                        project.warnings.append(f"Error reading .env for Supabase config: {e}")

    def _extract_git_history(self, project: V2Project):
        """
        Extract git commit history

        Args:
            project: Project to update
        """
        if not project.has_git:
            return

        try:
            # Get last 100 commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-100"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                project.git_history = result.stdout.strip().split("\n")
                project.metadata["commit_count"] = len(project.git_history)
            else:
                project.warnings.append(f"Error reading git history: {result.stderr}")
        except subprocess.TimeoutExpired:
            project.warnings.append("Git log command timed out")
        except Exception as e:
            project.warnings.append(f"Error extracting git history: {e}")

    def _extract_metadata(self, project: V2Project):
        """
        Extract additional metadata

        Args:
            project: Project to update
        """
        # Project name from governance or hrpo
        if project.governance_config:
            project_info = project.governance_config.get("project", {})
            project.metadata["name"] = project_info.get("name", "Unknown Project")
            project.metadata["slug"] = project_info.get("slug", "unknown-project")
        elif project.hrpo_data:
            project.metadata["name"] = project.hrpo_data.get("executive_summary", "Unknown Project")[:50]

        # Progress info from HRPO
        if project.hrpo_data and "progress" in project.hrpo_data:
            progress = project.hrpo_data["progress"]
            project.metadata["steps_completed"] = progress.get("steps_completed", 0)
            project.metadata["total_steps"] = progress.get("total_steps", 0)
            project.metadata["percent_complete"] = progress.get("percent_complete", 0.0)

        # File counts
        project.metadata["feature_count"] = len(project.features)
        project.metadata["has_supabase"] = project.supabase_config is not None

        # Version detection
        project.metadata["detected_version"] = "2.0"

    def _validate_project(self, project: V2Project) -> bool:
        """
        Final validation of parsed project

        Args:
            project: Project to validate

        Returns:
            True if project is valid for migration
        """
        # Must have .runner directory
        if not project.has_runner_dir:
            return False

        # Must have at least HRPO or governance
        if not project.has_hrpo and not project.has_governance:
            project.errors.append("No HRPO or governance data found")
            return False

        # No critical errors
        if project.errors:
            return False

        return True

    def get_summary(self, project: V2Project) -> str:
        """
        Generate human-readable summary of parsed project

        Args:
            project: Parsed project

        Returns:
            Summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("BuildRunner 2.0 Project Summary")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Project: {project.metadata.get('name', 'Unknown')}")
        lines.append(f"Path: {project.root_path}")
        lines.append(f"Valid: {'✅ Yes' if project.is_valid else '❌ No'}")
        lines.append("")

        lines.append("Components Found:")
        lines.append(f"  HRPO data: {'✅' if project.has_hrpo else '❌'}")
        lines.append(f"  Governance config: {'✅' if project.has_governance else '❌'}")
        lines.append(f"  Git history: {'✅' if project.has_git else '❌'}")
        lines.append(f"  Supabase config: {'✅' if project.supabase_config else '❌'}")
        lines.append("")

        lines.append(f"Features: {len(project.features)}")
        if project.metadata.get("percent_complete"):
            lines.append(f"Progress: {project.metadata['percent_complete']:.1f}%")
        lines.append("")

        if project.warnings:
            lines.append("Warnings:")
            for warning in project.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")

        if project.errors:
            lines.append("Errors:")
            for error in project.errors:
                lines.append(f"  ❌ {error}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
