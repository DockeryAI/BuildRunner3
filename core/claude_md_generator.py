"""
CLAUDE.md Generator
Centralized generation of CLAUDE.md files with personality profiles
"""

from pathlib import Path
from typing import Optional
from core.profile_manager import ProfileManager
from cli.config_manager import get_config_manager


class ClaudeMdGenerator:
    """
    Generates CLAUDE.md files with optional personality profiles.

    Used by:
    - br init: Auto-activate global default profile
    - br profile activate: Activate specific profile
    - br attach: Activate profile + codebase warnings
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize generator.

        Args:
            project_root: Project root directory. Defaults to current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.claude_md = self.project_root / "CLAUDE.md"
        self.profile_manager = ProfileManager(self.project_root)

    def generate(
        self,
        profile_name: Optional[str] = None,
        planning_content: Optional[str] = None,
        existing_codebase: bool = False,
        force: bool = False,
    ) -> Path:
        """
        Generate CLAUDE.md with optional profile and planning content.

        Args:
            profile_name: Profile to activate (None = use global default)
            planning_content: Planning mode content (for br init)
            existing_codebase: Add codebase warning (for br attach)
            force: Overwrite existing CLAUDE.md

        Returns:
            Path to created CLAUDE.md

        Raises:
            ValueError: If CLAUDE.md exists and not force
        """
        # Check if CLAUDE.md exists
        if self.claude_md.exists() and not force:
            content = self.claude_md.read_text()
            if "<!-- BUILDRUNNER_PROFILE:" not in content and not planning_content:
                raise ValueError(
                    f"CLAUDE.md already exists and was not created by BuildRunner.\n"
                    f"Please remove or rename it first: {self.claude_md}"
                )

        # Build CLAUDE.md content
        sections = []

        # 1. Profile section (if specified)
        if profile_name:
            profile_content, source = self._get_profile_content(profile_name)
            sections.append(self._format_profile_section(profile_name, profile_content, source))

        # 2. Existing codebase warning (if attach)
        if existing_codebase:
            sections.append(self._format_codebase_warning())

        # 3. Planning content (if br init)
        if planning_content:
            sections.append(planning_content)

        # Write to CLAUDE.md
        final_content = "\n\n".join(sections)
        self.claude_md.write_text(final_content)

        return self.claude_md

    def activate_profile(self, profile_name: str, force: bool = False) -> Path:
        """
        Activate a profile by generating CLAUDE.md.

        Args:
            profile_name: Profile name to activate
            force: Overwrite existing CLAUDE.md

        Returns:
            Path to created CLAUDE.md
        """
        return self.generate(profile_name=profile_name, force=force)

    def activate_default_profile(self, force: bool = False) -> Optional[Path]:
        """
        Activate global default profile if configured.

        Args:
            force: Overwrite existing CLAUDE.md

        Returns:
            Path to created CLAUDE.md, or None if no default configured
        """
        config = get_config_manager(self.project_root)
        default_profile = config.get("profiles.default_profile")
        auto_activate = config.get("profiles.auto_activate", True)

        if default_profile and auto_activate:
            return self.generate(profile_name=default_profile, force=force)

        return None

    def generate_planning_mode(
        self, project_name: str, profile_name: Optional[str] = None, force: bool = False
    ) -> Path:
        """
        Generate CLAUDE.md for planning mode (br init).

        Args:
            project_name: Project name
            profile_name: Profile to activate (None = use global default)
            force: Overwrite existing CLAUDE.md

        Returns:
            Path to created CLAUDE.md
        """
        # Use default profile if none specified
        if not profile_name:
            config = get_config_manager(self.project_root)
            profile_name = config.get("profiles.default_profile")

        # Get planning content
        spec_path = self.project_root / ".buildrunner" / "PROJECT_SPEC.md"

        planning_content = f"""# 🎯 PLANNING MODE - Quick PRD to Build

**Project:** {project_name}
**Path:** {self.project_root}
**Spec File:** {spec_path}
**Mode:** PLANNING (No code, incremental spec updates)

---

## ⚡ AUTO-CONTINUE MODE: ENABLED

**CRITICAL:** This project has auto-continue enabled. You MUST:

1. **Never pause** or ask "should I continue?" between tasks
2. **Never ask for permission** to proceed to next steps
3. **Build to 100% completion** unless you encounter a critical blocker
4. **Only stop if:**
   - You need information only the human can provide
   - There's a critical error you cannot resolve
   - User intervention is absolutely required

**Your job is to build completely and autonomously. Keep going until done.**

---

## 🎨 WORKFLOW MODE SELECTION

**FIRST:** Ask user to select their planning mode using AskUserQuestion tool:

```python
AskUserQuestion(
    questions=[{{
        "question": "How would you like to plan your project?",
        "header": "Planning Mode",
        "multiSelect": False,
        "options": [
            {{"label": "⚡ Quick Mode (Default)", "description": "4 sections → Build in 15 min"}},
            {{"label": "🔧 Technical Mode", "description": "11 sections - Full technical depth"}},
            {{"label": "🚀 Full Mode", "description": "All 11 sections - Business + technical"}},
            {{"label": "🎯 Custom Mode", "description": "Pick which sections to include"}}
        ]
    }}]
)
```

**Based on selection, set workflow mode and proceed with planning.**
"""

        return self.generate(
            profile_name=profile_name, planning_content=planning_content, force=force
        )

    def generate_attach_mode(self, profile_name: Optional[str] = None, force: bool = False) -> Path:
        """
        Generate CLAUDE.md for attach mode (br attach).

        Args:
            profile_name: Profile to activate (None = use global default)
            force: Overwrite existing CLAUDE.md

        Returns:
            Path to created CLAUDE.md
        """
        # Use default profile if none specified
        if not profile_name:
            config = get_config_manager(self.project_root)
            profile_name = config.get("profiles.default_profile")

        return self.generate(profile_name=profile_name, existing_codebase=True, force=force)

    def _get_profile_content(self, profile_name: str) -> tuple[str, str]:
        """
        Get profile content and source.

        Args:
            profile_name: Profile name

        Returns:
            Tuple of (content, source)
        """
        content = self.profile_manager.read_profile(profile_name)
        profile_path = self.profile_manager.get_profile_path(profile_name)

        if profile_path.parent == self.profile_manager.project_personalities_dir:
            source = "project-specific"
        else:
            source = "global"

        return content, source

    def _format_profile_section(self, name: str, content: str, source: str) -> str:
        """Format profile section for CLAUDE.md."""
        return f"""<!-- BUILDRUNNER_PROFILE: {name} (source: {source}) -->
# BuildRunner Profile: {name}

{content}

---

**Profile Management:**
- Deactivate: `br profile deactivate`
- Switch: `br profile activate <name>`
- List: `br profile list`
"""

    def _format_codebase_warning(self) -> str:
        """Format existing codebase warning section."""
        return """<!-- BUILDRUNNER_EXISTING_CODEBASE -->
# ⚠️ EXISTING CODEBASE DETECTED

**CRITICAL:** This project already has code. Before building new features:

1. **Check PROJECT_SPEC.md** - Features marked `status: DISCOVERED` are already built
2. **Verify confidence scores** - HIGH = definitely exists, LOW = uncertain
3. **Don't rebuild existing features** - Only build features marked `status: PLANNED`
4. **When unsure** - Ask user if feature already exists

This project was attached with BuildRunner. The PROJECT_SPEC.md contains a complete
inventory of discovered features. Always check before implementing.

---

## ⚡ AUTO-CONTINUE MODE: ENABLED

**CRITICAL:** This project has auto-continue enabled. You MUST:

1. **Never pause** or ask "should I continue?" between tasks
2. **Never ask for permission** to proceed to next steps
3. **Build to 100% completion** unless you encounter a critical blocker
4. **Only stop if:**
   - You need information only the human can provide
   - There's a critical error you cannot resolve
   - User intervention is absolutely required

**Your job is to build completely and autonomously. Keep going until done.**

---
"""
