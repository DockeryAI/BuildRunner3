"""
Project Manager - Handles project creation and initialization
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
import json


class ProjectManager:
    """Manages project creation and initialization"""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.home() / "Projects"
        self.project_root.mkdir(parents=True, exist_ok=True)

    async def create_project(self, project_name: str) -> Dict:
        """
        Create a new project directory with basic structure

        Args:
            project_name: Name of the project

        Returns:
            Dict with success status and project paths
        """
        try:
            # Create project directory
            project_path = self.project_root / project_name

            if project_path.exists():
                return {
                    "success": False,
                    "error": f"Project '{project_name}' already exists at {project_path}"
                }

            # Create project directory
            project_path.mkdir(parents=True, exist_ok=True)

            # Create basic project structure
            (project_path / "src").mkdir(exist_ok=True)
            (project_path / "tests").mkdir(exist_ok=True)
            (project_path / "docs").mkdir(exist_ok=True)

            # Create .gitignore
            gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# BuildRunner
.buildrunner/
"""
            (project_path / ".gitignore").write_text(gitignore_content)

            # Create README.md
            readme_content = f"""# {project_name}

Created with BuildRunner 3.2

## Project Structure

- `src/` - Source code
- `tests/` - Test files
- `docs/` - Documentation
- `PROJECT_SPEC.md` - Product Requirements Document

## Getting Started

1. Review the `PROJECT_SPEC.md` for project requirements
2. Run `buildrunner plan` to generate implementation tasks
3. Run `buildrunner run` to start building

"""
            (project_path / "README.md").write_text(readme_content)

            # Create virtual environment
            venv_path = project_path / ".venv"
            try:
                subprocess.run(
                    ["python3", "-m", "venv", str(venv_path)],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to create venv: {e}")

            # Try to install buildrunner in the venv
            if venv_path.exists():
                pip_path = venv_path / "bin" / "pip"
                try:
                    # Try installing from PyPI
                    subprocess.run(
                        [str(pip_path), "install", "buildrunner"],
                        check=True,
                        capture_output=True,
                        timeout=30
                    )
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    # If PyPI install fails, try installing from local source
                    buildrunner_src = Path(__file__).parent.parent
                    try:
                        subprocess.run(
                            [str(pip_path), "install", "-e", str(buildrunner_src)],
                            check=True,
                            capture_output=True,
                            timeout=30
                        )
                    except Exception as e:
                        print(f"Warning: Failed to install buildrunner: {e}")

            return {
                "success": True,
                "project_name": project_name,
                "project_path": str(project_path),
                "message": f"Project '{project_name}' created successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def list_projects(self) -> Dict:
        """List all projects in the project root"""
        try:
            projects = []

            if not self.project_root.exists():
                return {
                    "success": True,
                    "projects": [],
                    "root": str(self.project_root),
                    "count": 0
                }

            for item in self.project_root.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    project_info = {
                        "name": item.name,
                        "path": str(item),
                        "has_venv": (item / ".venv").exists(),
                        "has_buildrunner": (item / "PROJECT_SPEC.md").exists() or
                                         (item / ".buildrunner").exists(),
                        "created": item.stat().st_ctime
                    }
                    projects.append(project_info)

            # Sort by creation time (most recent first)
            projects.sort(key=lambda x: x["created"], reverse=True)

            return {
                "success": True,
                "projects": projects,
                "root": str(self.project_root),
                "count": len(projects)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "projects": [],
                "count": 0
            }
