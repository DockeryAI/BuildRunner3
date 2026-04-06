"""
Tests for completed design system
"""

import pytest
import yaml
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tailwind_generator import TailwindGenerator
from core.storybook_generator import StorybookGenerator
from core.visual_regression import VisualRegressionTester


class TestIndustryProfiles:
    """Test all 8 industry profiles load correctly"""

    def test_healthcare_profile_loads(self):
        """Test healthcare profile"""
        profile_path = Path("templates/industries/healthcare.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "healthcare"
        assert "colors" in profile
        assert "compliance" in profile

    def test_fintech_profile_loads(self):
        """Test fintech profile"""
        profile_path = Path("templates/industries/fintech.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "fintech"
        assert "colors" in profile

    def test_saas_profile_loads(self):
        """Test SaaS profile"""
        profile_path = Path("templates/industries/saas.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "saas"
        assert "colors" in profile

    def test_government_profile_loads(self):
        """Test government profile (NEW)"""
        profile_path = Path("templates/industries/government.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Government"
        assert "colors" in profile
        assert "Section 508" in profile["compliance"]["standards"]

    def test_legal_profile_loads(self):
        """Test legal profile (NEW)"""
        profile_path = Path("templates/industries/legal.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Legal"
        assert "ABA Technology Standards" in profile["compliance"]["standards"]

    def test_nonprofit_profile_loads(self):
        """Test nonprofit profile (NEW)"""
        profile_path = Path("templates/industries/nonprofit.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Nonprofit"
        assert "501(c)(3)" in profile["compliance"]["standards"][0]

    def test_gaming_profile_loads(self):
        """Test gaming profile (NEW)"""
        profile_path = Path("templates/industries/gaming.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Gaming"
        assert "COPPA" in profile["compliance"]["standards"][0]

    def test_manufacturing_profile_loads(self):
        """Test manufacturing profile (NEW)"""
        profile_path = Path("templates/industries/manufacturing.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Manufacturing"
        assert "ISO 9001" in profile["compliance"]["standards"][0]


class TestUseCasePatterns:
    """Test all 8 use case patterns load correctly"""

    def test_dashboard_pattern_loads(self):
        """Test dashboard pattern"""
        pattern_path = Path("templates/use_cases/dashboard.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "dashboard"

    def test_marketplace_pattern_loads(self):
        """Test marketplace pattern"""
        pattern_path = Path("templates/use_cases/marketplace.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "marketplace"

    def test_crm_pattern_loads(self):
        """Test CRM pattern"""
        pattern_path = Path("templates/use_cases/crm.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "crm"

    def test_chat_pattern_loads(self):
        """Test chat pattern (NEW)"""
        pattern_path = Path("templates/use_cases/chat.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Chat / Messaging"
        assert pattern["layout"]["structure"] == "sidebar-main-detail"

    def test_video_pattern_loads(self):
        """Test video pattern (NEW)"""
        pattern_path = Path("templates/use_cases/video.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Video Streaming"

    def test_calendar_pattern_loads(self):
        """Test calendar pattern (NEW)"""
        pattern_path = Path("templates/use_cases/calendar.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Calendar / Scheduling"

    def test_forms_pattern_loads(self):
        """Test forms pattern (NEW)"""
        pattern_path = Path("templates/use_cases/forms.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Complex Forms"

    def test_search_pattern_loads(self):
        """Test search pattern (NEW)"""
        pattern_path = Path("templates/use_cases/search.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Search / Discovery"


class TestTailwindGenerator:
    """Test Tailwind 4 config generation"""

    def test_generate_config(self, tmp_path):
        """Test config generation"""
        generator = TailwindGenerator(tmp_path)

        # Mock profiles
        (tmp_path / "templates" / "industries").mkdir(parents=True)
        (tmp_path / "templates" / "use_cases").mkdir(parents=True)

        industry_yaml = tmp_path / "templates" / "industries" / "test.yaml"
        industry_yaml.write_text(
            """
name: Test
colors:
  primary:
    main: "#1976d2"
typography:
  fonts:
    primary: "Roboto, sans-serif"
"""
        )

        use_case_yaml = tmp_path / "templates" / "use_cases" / "test.yaml"
        use_case_yaml.write_text(
            """
name: Test
layout:
  structure: "sidebar-main"
"""
        )

        config = generator.generate_tailwind_config("test", "test")

        assert "theme" in config
        assert "content" in config

    def test_merge_tokens(self):
        """Test token merging"""
        generator = TailwindGenerator(Path("."))

        industry = {"colors": {"primary": {"main": "#1976d2"}}}
        use_case = {"layout": {"structure": "grid"}}

        merged = generator.merge_design_tokens(industry, use_case)

        assert merged["colors"]["primary"]["main"] == "#1976d2"
        assert merged["layout"]["structure"] == "grid"

    def test_css_variables_generation(self):
        """Test CSS variable generation"""
        generator = TailwindGenerator(Path("."))

        tokens = {"colors": {"primary": {"main": "#1976d2", "light": "#42a5f5"}}}

        css = generator.apply_css_variables(tokens)

        assert "--color-primary-main: #1976d2;" in css
        assert "--color-primary-light: #42a5f5;" in css

    def test_theme_json_generation(self):
        """Test theme.json generation"""
        generator = TailwindGenerator(Path("."))

        tokens = {
            "colors": {"primary": {"main": "#1976d2"}},
            "typography": {"fonts": {"primary": "Roboto"}, "sizes": {"base": "1rem"}},
        }

        theme = generator.generate_theme_json(tokens)

        assert "colors" in theme
        assert "primary-main" in theme["colors"]
        assert theme["colors"]["primary-main"] == "#1976d2"


class TestStorybookGenerator:
    """Test Storybook generation"""

    def test_generate_config(self, tmp_path):
        """Test Storybook config generation"""
        generator = StorybookGenerator(tmp_path)
        generator.generate_storybook_config({})

        assert (tmp_path / ".storybook" / "main.js").exists()
        assert (tmp_path / ".storybook" / "preview.js").exists()
        assert (tmp_path / ".storybook" / "manager.js").exists()

    def test_create_stories(self, tmp_path):
        """Test story file creation"""
        generator = StorybookGenerator(tmp_path)

        # Create mock spec
        spec_path = tmp_path / "PROJECT_SPEC.md"
        spec_path.write_text("# Spec\n\nButton component")

        stories = generator.create_component_stories(spec_path)

        assert len(stories) > 0
        assert all(path.exists() for path in stories)

    def test_story_file_content(self, tmp_path):
        """Test generated story file content"""
        generator = StorybookGenerator(tmp_path)

        component = {"name": "TestButton", "description": "Test button"}
        story_path = generator._create_story_file(component)

        assert story_path.exists()
        content = story_path.read_text()
        assert "TestButton" in content
        assert "Meta<typeof TestButton>" in content


class TestVisualRegression:
    """Test visual regression testing"""

    def test_directory_creation(self, tmp_path):
        """Test directory structure creation"""
        tester = VisualRegressionTester(tmp_path)

        assert (tmp_path / "tests" / "visual" / "baseline").exists()
        assert (tmp_path / "tests" / "visual" / "current").exists()
        assert (tmp_path / "tests" / "visual" / "diff").exists()

    @pytest.mark.asyncio
    async def test_capture_baseline_mock(self, tmp_path):
        """Test baseline capture (mocked)"""
        tester = VisualRegressionTester(tmp_path)

        # Mock test without playwright
        screenshots = await tester.capture_baseline("http://localhost:3000", ["Button", "Card"])

        assert "Button" in screenshots
        assert "Card" in screenshots

    @pytest.mark.asyncio
    async def test_run_visual_tests_mock(self, tmp_path):
        """Test visual regression run (mocked)"""
        tester = VisualRegressionTester(tmp_path)

        # Mock test without playwright
        results = await tester.run_visual_tests("http://localhost:3000", ["Button", "Card"])

        assert "passed" in results
        assert "failed" in results
        assert "diffs" in results

    def test_generate_report(self, tmp_path):
        """Test HTML report generation"""
        tester = VisualRegressionTester(tmp_path)

        results = {
            "passed": ["Button", "Card"],
            "failed": ["Modal"],
            "diffs": {"Modal": tmp_path / "diff.png"},
        }

        report_path = tester.generate_report(results)

        assert report_path.exists()
        content = report_path.read_text()
        assert "Visual Regression Report" in content
        assert "Passed (2)" in content
        assert "Failed (1)" in content


class TestIntegration:
    """Integration tests for the complete design system"""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow from profiles to Tailwind config"""
        # Create test profiles
        (tmp_path / "templates" / "industries").mkdir(parents=True)
        (tmp_path / "templates" / "use_cases").mkdir(parents=True)

        industry_yaml = tmp_path / "templates" / "industries" / "test.yaml"
        industry_yaml.write_text(
            """
name: Test Industry
colors:
  primary:
    main: "#1976d2"
typography:
  fonts:
    primary: "Roboto"
"""
        )

        use_case_yaml = tmp_path / "templates" / "use_cases" / "test.yaml"
        use_case_yaml.write_text(
            """
name: Test Use Case
layout:
  structure: "grid"
components:
  grid:
    columns: 3
"""
        )

        # Generate Tailwind config
        generator = TailwindGenerator(tmp_path)
        config_path = tmp_path / "tailwind.config.js"
        config = generator.generate_tailwind_config("test", "test", config_path)

        assert config_path.exists()
        assert "theme" in config

        # Generate Storybook config
        sb_generator = StorybookGenerator(tmp_path)
        sb_generator.generate_storybook_config(config["theme"])

        assert (tmp_path / ".storybook" / "main.js").exists()

    def test_all_profiles_valid(self):
        """Test all profile files are valid YAML"""
        profiles_dir = Path("templates")

        if not profiles_dir.exists():
            pytest.skip("Templates directory not found")

        errors = []
        for category in ["industries", "use_cases"]:
            category_dir = profiles_dir / category
            if category_dir.exists():
                for yaml_file in category_dir.glob("*.yaml"):
                    try:
                        with open(yaml_file) as f:
                            data = yaml.safe_load(f)
                            assert "name" in data
                            assert "description" in data
                    except Exception as e:
                        errors.append(f"{yaml_file}: {e}")

        assert len(errors) == 0, f"YAML errors: {errors}"
