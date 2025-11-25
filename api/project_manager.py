"""
Project Manager API
Handles project creation, initialization, and BuildRunner setup
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging

from core.retrofit import BRVersionDetector, BRVersion

logger = logging.getLogger(__name__)

PROJECTS_ROOT = Path.home() / "Projects"


class ProjectManager:
    """Manages project lifecycle operations"""

    @staticmethod
    async def create_project(
        project_name: str,
        project_root: Optional[str] = None
    ) -> Dict:
        """
        Create a new project directory and install BuildRunner

        Args:
            project_name: Name of the project
            project_root: Optional custom root (defaults to ~/Projects)

        Returns:
            Dict with success status, project path, and messages
        """
        try:
            # Determine project root
            root = Path(project_root) if project_root else PROJECTS_ROOT
            root.mkdir(parents=True, exist_ok=True)

            project_path = root / project_name

            # Check if project already exists
            if project_path.exists():
                return {
                    'success': False,
                    'error': f'Project "{project_name}" already exists at {project_path}',
                    'project_path': str(project_path)
                }

            # Create project directory
            project_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created project directory: {project_path}")

            # Create virtual environment
            venv_path = project_path / '.venv'
            logger.info("Creating virtual environment...")
            subprocess.run(
                ['python3', '-m', 'venv', str(venv_path)],
                check=True,
                capture_output=True,
                text=True
            )

            # Install buildrunner in the venv
            pip_path = venv_path / 'bin' / 'pip'
            logger.info("Installing BuildRunner...")

            install_result = subprocess.run(
                [str(pip_path), 'install', 'buildrunner'],
                capture_output=True,
                text=True,
                cwd=str(project_path)
            )

            if install_result.returncode != 0:
                logger.warning(f"BuildRunner install failed: {install_result.stderr}")
                # Try installing from local source
                br3_path = Path(__file__).parent.parent
                install_result = subprocess.run(
                    [str(pip_path), 'install', '-e', str(br3_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(project_path)
                )

            # Create initial project structure
            (project_path / 'src').mkdir(exist_ok=True)
            (project_path / 'tests').mkdir(exist_ok=True)
            (project_path / 'docs').mkdir(exist_ok=True)

            # Create .gitignore
            gitignore_content = """
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/
.DS_Store
.idea/
.vscode/
*.swp
*.swo
*~
.env
.buildrunner/
"""
            (project_path / '.gitignore').write_text(gitignore_content.strip())

            # Create README
            readme_content = f"""# {project_name}

Created with BuildRunner 3

## Setup

```bash
source .venv/bin/activate
```

## Usage

```bash
br init
br prd
br run
```
"""
            (project_path / 'README.md').write_text(readme_content)

            return {
                'success': True,
                'project_path': str(project_path),
                'project_name': project_name,
                'message': f'Project "{project_name}" created successfully',
                'venv_path': str(venv_path),
                'install_output': install_result.stdout
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            return {
                'success': False,
                'error': f'Failed to create project: {e.stderr}',
                'project_path': str(project_path) if 'project_path' in locals() else None
            }
        except Exception as e:
            logger.error(f"Project creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'project_path': str(project_path) if 'project_path' in locals() else None
            }

    @staticmethod
    async def initialize_buildrunner(project_path: str) -> Dict:
        """
        Run br init in the project directory

        Args:
            project_path: Path to the project

        Returns:
            Dict with success status and output
        """
        try:
            project_dir = Path(project_path)
            if not project_dir.exists():
                return {
                    'success': False,
                    'error': f'Project directory does not exist: {project_path}'
                }

            # Find br executable in venv
            venv_br = project_dir / '.venv' / 'bin' / 'br'

            if not venv_br.exists():
                return {
                    'success': False,
                    'error': 'BuildRunner not installed in project venv'
                }

            # Run br init
            result = subprocess.run(
                [str(venv_br), 'init'],
                capture_output=True,
                text=True,
                cwd=str(project_dir)
            )

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }

        except Exception as e:
            logger.error(f"BR init failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def list_projects(project_root: Optional[str] = None) -> Dict:
        """
        List all projects in the projects root directory

        Args:
            project_root: Optional custom root (defaults to ~/Projects)

        Returns:
            Dict with list of projects
        """
        try:
            root = Path(project_root) if project_root else PROJECTS_ROOT

            if not root.exists():
                return {
                    'success': True,
                    'projects': [],
                    'root': str(root)
                }

            projects = []
            for item in root.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if it has a venv (likely a project)
                    has_venv = (item / '.venv').exists()

                    # Use version detector to properly detect BR version
                    detector = BRVersionDetector(item)
                    version_result = detector.detect()

                    # Consider BR3 as "attached" for UI compatibility
                    has_buildrunner = version_result.version == BRVersion.BR3
                    br_version = version_result.version.value

                    projects.append({
                        'name': item.name,
                        'path': str(item),
                        'has_venv': has_venv,
                        'has_buildrunner': has_buildrunner,
                        'br_version': br_version,
                        'created': item.stat().st_ctime
                    })

            # Sort by creation time (newest first)
            projects.sort(key=lambda x: x['created'], reverse=True)

            return {
                'success': True,
                'projects': projects,
                'root': str(root),
                'count': len(projects)
            }

        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return {
                'success': False,
                'error': str(e),
                'projects': []
            }


# Singleton instance
project_manager = ProjectManager()
