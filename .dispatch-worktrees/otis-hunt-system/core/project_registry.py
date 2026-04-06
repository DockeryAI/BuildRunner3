"""
Project Registry - Manage BuildRunner project aliases and metadata

Stores project information in ~/.buildrunner/projects.json for quick access
and shell alias generation.

Features:
- Register projects with aliases
- Store project metadata (path, created date, editor preference)
- Query registered projects
- Remove projects
- Validate project structure
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProjectInfo:
    """Information about a registered project"""

    alias: str
    path: str
    created: str
    editor: str = "claude"
    spec_path: Optional[str] = None
    last_accessed: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProjectInfo":
        """Create from dictionary"""
        return ProjectInfo(**data)


class ProjectRegistry:
    """
    Manages BuildRunner project registry

    Registry stored at: ~/.buildrunner/projects.json

    Structure:
    {
        "alias": {
            "path": "/path/to/project",
            "created": "2025-11-24T20:00:00",
            "editor": "claude",
            "spec_path": ".buildrunner/PROJECT_SPEC.md",
            "last_accessed": "2025-11-24T21:00:00"
        }
    }
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize project registry

        Args:
            registry_path: Optional custom registry path (default: ~/.buildrunner/projects.json)
        """
        if registry_path:
            self.registry_path = Path(registry_path)
        else:
            home = Path.home()
            buildrunner_dir = home / ".buildrunner"
            buildrunner_dir.mkdir(exist_ok=True)
            self.registry_path = buildrunner_dir / "projects.json"

        self._ensure_registry_exists()

    def _ensure_registry_exists(self):
        """Create registry file if it doesn't exist"""
        if not self.registry_path.exists():
            self.registry_path.write_text(json.dumps({}, indent=2))
            logger.info(f"Created project registry at {self.registry_path}")

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load registry from disk"""
        try:
            content = self.registry_path.read_text()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}

    def _save_registry(self, registry: Dict[str, Dict[str, Any]]):
        """Save registry to disk"""
        try:
            self.registry_path.write_text(json.dumps(registry, indent=2))
            logger.debug("Registry saved successfully")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            raise

    def register_project(
        self,
        alias: str,
        project_path: Path,
        editor: str = "claude",
        spec_path: Optional[str] = None,
    ) -> ProjectInfo:
        """
        Register a project with an alias

        Args:
            alias: Short alias for the project (e.g., "sales", "br3")
            project_path: Absolute path to project directory
            editor: Editor to use (claude, cursor, windsurf)
            spec_path: Relative path to PROJECT_SPEC.md (default: .buildrunner/PROJECT_SPEC.md)

        Returns:
            ProjectInfo for the registered project

        Raises:
            ValueError: If alias already exists or path is invalid
        """
        # Validate alias
        if not alias or not alias.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Invalid alias '{alias}'. Use alphanumeric characters, hyphens, or underscores."
            )

        # Validate path
        project_path = Path(project_path).resolve()
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        # Check if alias already exists
        registry = self._load_registry()
        if alias in registry:
            existing_path = registry[alias]["path"]
            if existing_path != str(project_path):
                raise ValueError(
                    f"Alias '{alias}' already registered to {existing_path}. "
                    f"Use 'br alias remove {alias}' first."
                )
            # Same alias, same path - update it
            logger.info(f"Updating existing alias '{alias}'")

        # Default spec path
        if spec_path is None:
            spec_path = ".buildrunner/PROJECT_SPEC.md"

        # Create project info
        project_info = ProjectInfo(
            alias=alias,
            path=str(project_path),
            created=datetime.now().isoformat(),
            editor=editor,
            spec_path=spec_path,
            last_accessed=None,
        )

        # Save to registry
        registry[alias] = project_info.to_dict()
        self._save_registry(registry)

        logger.info(f"Registered project '{alias}' at {project_path}")
        return project_info

    def get_project(self, alias: str) -> Optional[ProjectInfo]:
        """
        Get project info by alias

        Args:
            alias: Project alias

        Returns:
            ProjectInfo if found, None otherwise
        """
        registry = self._load_registry()
        if alias not in registry:
            return None

        return ProjectInfo.from_dict(registry[alias])

    def update_last_accessed(self, alias: str):
        """Update last accessed timestamp for a project"""
        registry = self._load_registry()
        if alias in registry:
            registry[alias]["last_accessed"] = datetime.now().isoformat()
            self._save_registry(registry)

    def list_projects(self) -> List[ProjectInfo]:
        """
        List all registered projects

        Returns:
            List of ProjectInfo objects
        """
        registry = self._load_registry()
        return [ProjectInfo.from_dict(data) for data in registry.values()]

    def remove_project(self, alias: str) -> bool:
        """
        Remove a project from registry

        Args:
            alias: Project alias to remove

        Returns:
            True if removed, False if not found
        """
        registry = self._load_registry()
        if alias not in registry:
            return False

        del registry[alias]
        self._save_registry(registry)
        logger.info(f"Removed project '{alias}' from registry")
        return True

    def alias_exists(self, alias: str) -> bool:
        """Check if an alias is already registered"""
        registry = self._load_registry()
        return alias in registry

    def get_project_by_path(self, project_path: Path) -> Optional[ProjectInfo]:
        """
        Find project by path

        Args:
            project_path: Path to search for

        Returns:
            ProjectInfo if found, None otherwise
        """
        project_path = Path(project_path).resolve()
        registry = self._load_registry()

        for data in registry.values():
            if Path(data["path"]).resolve() == project_path:
                return ProjectInfo.from_dict(data)

        return None

    def validate_project(self, alias: str) -> Dict[str, Any]:
        """
        Validate a registered project's structure

        Args:
            alias: Project alias

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "exists": bool,
                "has_buildrunner": bool,
                "has_spec": bool,
                "issues": [list of issues]
            }
        """
        project = self.get_project(alias)
        if not project:
            return {
                "valid": False,
                "exists": False,
                "has_buildrunner": False,
                "has_spec": False,
                "issues": [f"Project '{alias}' not found in registry"],
            }

        project_path = Path(project.path)
        issues = []

        # Check if path exists
        if not project_path.exists():
            issues.append(f"Project path does not exist: {project_path}")
            return {
                "valid": False,
                "exists": False,
                "has_buildrunner": False,
                "has_spec": False,
                "issues": issues,
            }

        # Check for .buildrunner directory
        buildrunner_dir = project_path / ".buildrunner"
        has_buildrunner = buildrunner_dir.exists()
        if not has_buildrunner:
            issues.append("Missing .buildrunner directory")

        # Check for PROJECT_SPEC.md
        spec_path = project_path / (project.spec_path or ".buildrunner/PROJECT_SPEC.md")
        has_spec = spec_path.exists()
        if not has_spec:
            issues.append(f"Missing PROJECT_SPEC.md at {spec_path}")

        valid = has_buildrunner and has_spec

        return {
            "valid": valid,
            "exists": True,
            "has_buildrunner": has_buildrunner,
            "has_spec": has_spec,
            "issues": issues,
        }


# Global registry instance
_registry: Optional[ProjectRegistry] = None


def get_project_registry() -> ProjectRegistry:
    """Get or create global project registry instance"""
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
    return _registry
