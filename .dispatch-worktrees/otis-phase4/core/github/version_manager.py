"""Version Manager - Semantic versioning automation"""

from pathlib import Path
from typing import Optional, Tuple
import re
import tomllib  # Python 3.11+ built-in


class VersionManager:
    """Manage semantic versioning"""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()

    def get_current_version(self) -> str:
        """Get current version from pyproject.toml"""
        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version", "0.1.0")
        return "0.1.0"

    def bump_version(self, bump_type: str) -> str:
        """Bump version (major/minor/patch)"""
        current = self.get_current_version()
        parts = [int(p) for p in current.split(".")]

        if bump_type == "major":
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif bump_type == "minor":
            parts[1] += 1
            parts[2] = 0
        else:  # patch
            parts[2] += 1

        return ".".join(map(str, parts))

    def update_version_files(self, new_version: str) -> None:
        """Update version in all files"""
        # Update pyproject.toml using regex replacement
        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            # Replace version line in [project] section
            content = re.sub(
                r'(version\s*=\s*["\'])([^"\']+)(["\'])', rf"\g<1>{new_version}\g<3>", content
            )
            pyproject.write_text(content)

        # Update package.json if exists
        package_json = self.repo_path / "ui" / "package.json"
        if package_json.exists():
            import json

            with open(package_json) as f:
                data = json.load(f)
            data["version"] = new_version
            with open(package_json, "w") as f:
                json.dump(data, f, indent=2)
