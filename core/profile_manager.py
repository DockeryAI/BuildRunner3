"""
Profile Manager for BuildRunner 3.0

Manages personality profiles and preferences that persist across Claude Code sessions.
Profiles are loaded into CLAUDE.md which is auto-read by Claude Code.
"""

from pathlib import Path
from typing import Optional, List, Dict
import shutil


class ProfileError(Exception):
    """Raised when profile operations fail."""
    pass


class ProfileManager:
    """
    Manages personality profiles and user preferences.

    Profiles are markdown files that define response styles and personalities.
    When activated, they're injected into CLAUDE.md for Claude Code to read.

    Profile Locations:
        - Project-specific: .buildrunner/personalities/{name}.md
        - Global: ~/.br/personalities/{name}.md

    Active Profile:
        - Written to: CLAUDE.md (in project root)
        - Auto-read by Claude Code on every request
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize ProfileManager.

        Args:
            project_root: Root directory of project. Defaults to current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.global_personalities_dir = Path.home() / ".br" / "personalities"
        self.project_personalities_dir = self.project_root / ".buildrunner" / "personalities"
        self.claude_md = self.project_root / "CLAUDE.md"

    def list_profiles(self) -> Dict[str, str]:
        """
        List all available profiles.

        Returns:
            Dictionary mapping profile names to their source ('project' or 'global')
        """
        profiles = {}

        # Find global profiles
        if self.global_personalities_dir.exists():
            for file in self.global_personalities_dir.glob("*.md"):
                if file.stem not in ['README', 'readme']:
                    profiles[file.stem] = 'global'

        # Find project profiles (override global)
        if self.project_personalities_dir.exists():
            for file in self.project_personalities_dir.glob("*.md"):
                if file.stem not in ['README', 'readme']:
                    profiles[file.stem] = 'project'

        return profiles

    def get_profile_path(self, name: str) -> Optional[Path]:
        """
        Get path to a profile file, checking project then global.

        Args:
            name: Profile name (without .md extension)

        Returns:
            Path to profile file, or None if not found
        """
        # Check project-specific first
        project_profile = self.project_personalities_dir / f"{name}.md"
        if project_profile.exists():
            return project_profile

        # Check global
        global_profile = self.global_personalities_dir / f"{name}.md"
        if global_profile.exists():
            return global_profile

        return None

    def read_profile(self, name: str) -> str:
        """
        Read profile content.

        Args:
            name: Profile name

        Returns:
            Profile content as string

        Raises:
            ProfileError: If profile not found
        """
        profile_path = self.get_profile_path(name)
        if not profile_path:
            available = list(self.list_profiles().keys())
            raise ProfileError(
                f"Profile '{name}' not found.\n"
                f"Available profiles: {', '.join(available) if available else 'none'}\n"
                f"Searched in:\n"
                f"  - Project: {self.project_personalities_dir}\n"
                f"  - Global: {self.global_personalities_dir}"
            )

        return profile_path.read_text()

    def activate_profile(self, name: str) -> Path:
        """
        Activate a profile by writing it to CLAUDE.md.

        Args:
            name: Profile name to activate

        Returns:
            Path to created CLAUDE.md

        Raises:
            ProfileError: If profile not found or CLAUDE.md already exists
        """
        # Check if CLAUDE.md already exists
        if self.claude_md.exists():
            # Check if it was created by us (contains activation marker)
            content = self.claude_md.read_text()
            if "<!-- BUILDRUNNER_PROFILE:" not in content:
                raise ProfileError(
                    f"CLAUDE.md already exists and was not created by BuildRunner.\n"
                    f"Please remove or rename it first: {self.claude_md}"
                )

        # Read profile content
        profile_content = self.read_profile(name)
        profile_path = self.get_profile_path(name)
        source = "project-specific" if profile_path.parent == self.project_personalities_dir else "global"

        # Generate CLAUDE.md with profile
        claude_content = f"""<!-- BUILDRUNNER_PROFILE: {name} (source: {source}) -->
# BuildRunner Profile: {name}

This profile is active for this session. It will persist across Claude Code context
compaction and clearing.

To deactivate: `br profile deactivate`
To switch: `br profile activate <other_name>`

---

{profile_content}
"""

        # Write to CLAUDE.md
        self.claude_md.write_text(claude_content)

        return self.claude_md

    def deactivate_profile(self) -> bool:
        """
        Deactivate current profile by removing CLAUDE.md.

        Returns:
            True if profile was deactivated, False if no profile was active

        Raises:
            ProfileError: If CLAUDE.md exists but wasn't created by BuildRunner
        """
        if not self.claude_md.exists():
            return False

        # Check if it was created by us
        content = self.claude_md.read_text()
        if "<!-- BUILDRUNNER_PROFILE:" not in content:
            raise ProfileError(
                f"CLAUDE.md exists but was not created by BuildRunner.\n"
                f"Please remove it manually if you want to deactivate: {self.claude_md}"
            )

        # Remove CLAUDE.md
        self.claude_md.unlink()
        return True

    def get_active_profile(self) -> Optional[str]:
        """
        Get currently active profile name.

        Returns:
            Profile name if active, None otherwise
        """
        if not self.claude_md.exists():
            return None

        # Parse profile name from marker
        content = self.claude_md.read_text()
        for line in content.split('\n'):
            if line.startswith("<!-- BUILDRUNNER_PROFILE:"):
                # Extract name from: <!-- BUILDRUNNER_PROFILE: roy (source: global) -->
                parts = line.split(":", 1)[1].strip()
                name = parts.split("(")[0].strip()
                return name

        return None

    def copy_profile(self, name: str, source: str = 'global', overwrite: bool = False) -> Path:
        """
        Copy a profile from global to project or vice versa.

        Args:
            name: Profile name
            source: 'global' or 'project' - where to copy FROM
            overwrite: Whether to overwrite if destination exists

        Returns:
            Path to copied profile

        Raises:
            ProfileError: If source not found or destination exists
        """
        if source not in ['global', 'project']:
            raise ProfileError(f"Invalid source: {source}. Must be 'global' or 'project'.")

        # Determine source and destination
        if source == 'global':
            src_file = self.global_personalities_dir / f"{name}.md"
            dst_file = self.project_personalities_dir / f"{name}.md"
        else:
            src_file = self.project_personalities_dir / f"{name}.md"
            dst_file = self.global_personalities_dir / f"{name}.md"

        # Check source exists
        if not src_file.exists():
            raise ProfileError(f"Source profile not found: {src_file}")

        # Check destination
        if dst_file.exists() and not overwrite:
            raise ProfileError(
                f"Destination profile already exists: {dst_file}\n"
                f"Use --overwrite to replace it."
            )

        # Copy file
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)

        return dst_file

    def create_profile(self, name: str, content: str, scope: str = 'project') -> Path:
        """
        Create a new profile.

        Args:
            name: Profile name
            content: Profile content (markdown)
            scope: 'project' or 'global'

        Returns:
            Path to created profile

        Raises:
            ProfileError: If profile already exists
        """
        if scope not in ['project', 'global']:
            raise ProfileError(f"Invalid scope: {scope}. Must be 'project' or 'global'.")

        # Determine file path
        if scope == 'project':
            profile_file = self.project_personalities_dir / f"{name}.md"
        else:
            profile_file = self.global_personalities_dir / f"{name}.md"

        # Check if exists
        if profile_file.exists():
            raise ProfileError(f"Profile already exists: {profile_file}")

        # Create profile
        profile_file.parent.mkdir(parents=True, exist_ok=True)
        profile_file.write_text(content)

        return profile_file

    def init_personalities_dir(self, scope: str = 'both') -> List[Path]:
        """
        Initialize personalities directories with example profiles.

        Args:
            scope: 'project', 'global', or 'both'

        Returns:
            List of created directory paths
        """
        created = []

        if scope in ['project', 'both']:
            self.project_personalities_dir.mkdir(parents=True, exist_ok=True)

            # Create README
            readme = self.project_personalities_dir / "README.md"
            if not readme.exists():
                readme.write_text("""# BuildRunner Personalities

Project-specific personality profiles for Claude Code sessions.

## Usage

Activate a personality:
```bash
br profile activate roy
```

Deactivate:
```bash
br profile deactivate
```

List available:
```bash
br profile list
```

## Creating Profiles

Create a new markdown file in this directory with your personality definition.
See global profiles in `~/.br/personalities/` for examples.

## How It Works

When activated, the profile is written to `CLAUDE.md` in the project root.
Claude Code automatically reads CLAUDE.md on every request, so the personality
persists across context clearing and compaction.
""")
            created.append(self.project_personalities_dir)

        if scope in ['global', 'both']:
            self.global_personalities_dir.mkdir(parents=True, exist_ok=True)
            created.append(self.global_personalities_dir)

        return created


def get_profile_manager(project_root: Optional[Path] = None) -> ProfileManager:
    """
    Factory function to create a ProfileManager.

    Args:
        project_root: Root directory of project

    Returns:
        ProfileManager instance
    """
    return ProfileManager(project_root)
