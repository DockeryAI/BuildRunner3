"""
Tests for Feature 8: Quick PRD Mode (Build 7D)

Verifies:
- Quick mode is default with 4 sections
- Auto-build trigger after section 4
- Can upgrade Quick → Technical → Full
- Technical mode (11 sections) still available
- Brainstorming limited to 3-5 suggestions in Quick mode
"""

import pytest
from pathlib import Path


class TestQuickPRDModeCLAUDETemplate:
    """Test Quick PRD Mode implementation in CLAUDE.md template."""

    def get_claude_template_content(self):
        """Get the CLAUDE.md template content from main.py."""
        # Read the main.py file and extract the template
        main_py = Path("cli/main.py")
        content = main_py.read_text()

        # Find the template content between the triple quotes
        start_marker = 'planning_content = f"""'
        end_marker = '"""'

        start = content.find(start_marker) + len(start_marker)
        end = content.find(end_marker, start)

        template = content[start:end]
        return template

    def test_claude_template_contains_quick_mode(self):
        """Test that CLAUDE.md template mentions Quick Mode."""
        template = self.get_claude_template_content()

        assert "QUICK MODE" in template, "Should mention Quick Mode"
        assert "⚡ Quick Mode" in template, "Should have Quick Mode option"

    def test_quick_mode_has_4_sections(self):
        """Test that Quick Mode defines exactly 4 sections."""
        template = self.get_claude_template_content()

        # Verify 4 section names
        assert "Problem & Solution" in template, "Should have Problem & Solution section"
        assert "Target Users" in template, "Should have Target Users section"
        assert "Core Features" in template, "Should have Core Features section"
        assert "Technical Approach" in template, "Should have Technical Approach section"

    def test_quick_mode_limits_brainstorming(self):
        """Test that Quick Mode limits brainstorming to 3-5 suggestions."""
        template = self.get_claude_template_content()

        # Verify brainstorming limits
        assert "3-5" in template, "Should mention 3-5 suggestion limit"
        assert (
            "not 10+" in template or "NOT 20+" in template
        ), "Should emphasize limited suggestions"

    def test_quick_mode_has_auto_build_trigger(self):
        """Test that Quick Mode includes auto-build trigger after section 4."""
        template = self.get_claude_template_content()

        # Verify auto-build trigger
        assert "br build start" in template, "Should mention br build start command"
        assert (
            "Ready to start building?" in template or "Ready to build?" in template
        ), "Should ask if ready to build"
        assert "🚀 Yes - Start building now" in template, "Should have build now option"

    def test_technical_mode_still_available(self):
        """Test that Technical Mode (11 sections) is still available."""
        template = self.get_claude_template_content()

        # Verify Technical Mode exists
        assert (
            "Technical Mode" in template or "TECHNICAL MODE" in template
        ), "Should have Technical Mode"
        assert "11 sections" in template, "Should mention 11 sections"

    def test_mode_selection_has_all_options(self):
        """Test that mode selection includes Quick, Technical, Full, and Custom."""
        template = self.get_claude_template_content()

        # Verify all modes
        assert "Quick Mode" in template, "Should have Quick Mode"
        assert "Technical Mode" in template, "Should have Technical Mode"
        assert "Full Mode" in template, "Should have Full Mode"
        assert "Custom Mode" in template, "Should have Custom Mode"

    def test_quick_mode_is_default(self):
        """Test that Quick Mode is marked as default."""
        template = self.get_claude_template_content()

        # Verify Quick Mode is default
        assert "(Default)" in template or "DEFAULT" in template, "Should mark Quick Mode as default"

        # Verify it's associated with Quick Mode
        quick_section_start = template.find("Quick Mode")
        if quick_section_start != -1:
            quick_section = template[quick_section_start : quick_section_start + 200]
            assert (
                "(Default)" in quick_section or "DEFAULT" in quick_section
            ), "Default should be near Quick Mode"

    def test_quick_mode_feature_limit(self):
        """Test that Quick Mode limits features to 5-7 MVP features."""
        template = self.get_claude_template_content()

        # Verify feature limits
        assert "5-7" in template, "Should mention 5-7 features"
        assert "MVP" in template, "Should emphasize MVP features"

    def test_upgrade_path_exists(self):
        """Test that Quick Mode can upgrade to Technical or Full mode."""
        template = self.get_claude_template_content()

        # Verify upgrade options
        assert (
            "Add more sections" in template or "Expand to Technical" in template
        ), "Should allow adding sections"

    def test_mode_configurations_section_updated(self):
        """Test that MODE CONFIGURATIONS section includes Quick Mode."""
        template = self.get_claude_template_content()

        # Find MODE CONFIGURATIONS section
        assert "MODE CONFIGURATIONS" in template, "Should have MODE CONFIGURATIONS section"

        config_section_start = template.find("MODE CONFIGURATIONS")
        if config_section_start != -1:
            config_section = template[config_section_start:]

            # Verify Quick Mode in configurations
            assert "QUICK MODE" in config_section, "Should define QUICK MODE configuration"
            assert "4 sections" in config_section, "Should specify 4 sections"


class TestQuickPRDModeAcceptanceCriteria:
    """Test acceptance criteria from PROJECT_SPEC.md."""

    def get_claude_template_content(self):
        """Get the CLAUDE.md template content from main.py."""
        main_py = Path("cli/main.py")
        content = main_py.read_text()

        start_marker = 'planning_content = f"""'
        end_marker = '"""'

        start = content.find(start_marker) + len(start_marker)
        end = content.find(end_marker, start)

        template = content[start:end]
        return template

    def test_acceptance_quick_mode_default(self):
        """Acceptance: Quick mode default (4 sections)."""
        template = self.get_claude_template_content()

        # Quick mode should be default
        assert "DEFAULT" in template.upper(), "Quick mode should be marked as default"

        # Should have 4 sections
        quick_section_start = template.find("QUICK MODE")
        if quick_section_start != -1:
            quick_section = template[quick_section_start : quick_section_start + 1000]
            assert "4 sections" in quick_section, "Should specify 4 sections"

    def test_acceptance_auto_build_confirmation(self):
        """Acceptance: Auto-build on 'Yes' confirmation."""
        template = self.get_claude_template_content()

        # Should have auto-build trigger
        assert "br build start" in template, "Should include build start command"
        assert "Bash tool" in template, "Should use Bash tool to execute"

    def test_acceptance_upgrade_path(self):
        """Acceptance: Can upgrade Quick → Technical → Full."""
        template = self.get_claude_template_content()

        # Should allow upgrading
        assert "Technical" in template, "Should mention Technical mode"
        assert "Full" in template, "Should mention Full mode"

    def test_acceptance_technical_mode_available(self):
        """Acceptance: Technical mode (11 sections) still available."""
        template = self.get_claude_template_content()

        # Technical mode should exist
        assert "TECHNICAL MODE" in template.upper(), "Should have Technical mode"
        assert "11 sections" in template, "Should specify 11 sections"

    def test_acceptance_brainstorming_limited(self):
        """Acceptance: Brainstorming limited to 3-5 suggestions in Quick mode."""
        template = self.get_claude_template_content()

        # Should limit brainstorming
        assert "3-5" in template, "Should mention 3-5 suggestions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
