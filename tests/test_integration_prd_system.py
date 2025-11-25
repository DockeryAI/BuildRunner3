"""
Integration tests for PRD System (Build 2C)

Tests the complete PRD wizard, design system, and integration flow.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

from core.prd_wizard import PRDWizard, SpecState, ProjectSpec
from core.prd_parser import PRDParser
from core.prd_mapper import PRDMapper
from core.design_profiler import DesignProfiler
from core.design_researcher import DesignResearcher
from core.opus_handoff import OpusHandoff
from core.planning_mode import PlanningModeDetector


@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def templates_dir(temp_project):
    """Create templates directory structure"""
    templates = temp_project / "templates"
    industries = templates / "industries"
    use_cases = templates / "use_cases"

    industries.mkdir(parents=True)
    use_cases.mkdir(parents=True)

    # Copy templates from main project
    src_templates = Path(__file__).parent.parent / "templates"
    if src_templates.exists():
        for industry_file in (src_templates / "industries").glob("*.yaml"):
            shutil.copy(industry_file, industries)
        for use_case_file in (src_templates / "use_cases").glob("*.yaml"):
            shutil.copy(use_case_file, use_cases)

    return templates


class TestPRDWizard:
    """Test PRD Wizard functionality"""

    def test_wizard_initialization(self, temp_project):
        """Test wizard can be initialized"""
        wizard = PRDWizard(str(temp_project))
        assert wizard.project_root == temp_project
        assert not wizard.check_existing_spec()

    def test_industry_detection(self, temp_project):
        """Test industry and use case detection"""
        wizard = PRDWizard(str(temp_project))

        industry, use_case = wizard.detect_industry_and_use_case(
            "Build a healthcare patient dashboard"
        )

        assert industry == "healthcare"
        assert use_case == "dashboard"

    def test_spec_state_machine(self, temp_project):
        """Test spec state transitions"""
        spec = ProjectSpec(state=SpecState.NEW, industry="healthcare", use_case="dashboard")

        assert spec.state == SpecState.NEW

        spec.state = SpecState.DRAFT
        assert spec.state == SpecState.DRAFT

        spec.state = SpecState.CONFIRMED
        assert spec.state == SpecState.CONFIRMED


class TestDesignProfiler:
    """Test design profile merging"""

    def test_profiler_initialization(self, temp_project, templates_dir):
        """Test profiler can be initialized"""
        profiler = DesignProfiler(str(templates_dir))
        assert profiler.templates_dir == templates_dir

    def test_load_industry_profile(self, temp_project, templates_dir):
        """Test loading industry profile"""
        profiler = DesignProfiler(str(templates_dir))
        profile = profiler.load_industry_profile("healthcare")

        if profile:  # Only test if template exists
            assert profile["name"] == "healthcare"
            assert "colors" in profile
            assert "components" in profile

    def test_load_use_case_profile(self, temp_project, templates_dir):
        """Test loading use case profile"""
        profiler = DesignProfiler(str(templates_dir))
        profile = profiler.load_use_case_profile("dashboard")

        if profile:  # Only test if template exists
            assert profile["name"] == "dashboard"
            assert "layout_patterns" in profile

    def test_merge_profiles(self, temp_project, templates_dir):
        """Test profile merging"""
        profiler = DesignProfiler(str(templates_dir))

        industry_profile = profiler.load_industry_profile("healthcare")
        use_case_profile = profiler.load_use_case_profile("dashboard")

        if industry_profile and use_case_profile:
            merged = profiler.merge_profiles(industry_profile, use_case_profile)

            assert merged.industry == "healthcare"
            assert merged.use_case == "dashboard"
            assert len(merged.colors) > 0
            assert len(merged.components) > 0


class TestDesignResearcher:
    """Test design research functionality"""

    def test_researcher_initialization(self, temp_project):
        """Test researcher can be initialized"""
        researcher = DesignResearcher(str(temp_project))
        assert researcher.project_root == temp_project

    def test_research_patterns(self, temp_project):
        """Test research pattern generation"""
        researcher = DesignResearcher(str(temp_project))
        research = researcher.research_design_patterns("healthcare", "dashboard")

        assert research.industry == "healthcare"
        assert research.use_case == "dashboard"
        assert len(research.patterns) > 0
        assert len(research.best_practices) > 0

    def test_save_and_load_research(self, temp_project):
        """Test saving and loading research"""
        researcher = DesignResearcher(str(temp_project))
        research = researcher.research_design_patterns("fintech", "dashboard")

        # Save
        output_path = researcher.save_research(research, "test_project")
        assert output_path.exists()

        # Load
        loaded = researcher.load_research("test_project")
        assert loaded is not None
        assert loaded.industry == "fintech"
        assert loaded.use_case == "dashboard"


class TestPRDParser:
    """Test PRD parsing"""

    def test_parser_initialization(self, temp_project):
        """Test parser can be initialized"""
        spec_path = temp_project / ".buildrunner" / "PROJECT_SPEC.md"
        spec_path.parent.mkdir(parents=True)

        # Create minimal spec
        spec_path.write_text(
            """# PROJECT_SPEC

**Status**: draft
**Industry**: healthcare
**Use Case**: dashboard
**Tech Stack**: react-fastapi-postgres

---

# Product Requirements

## User Stories
- As a doctor, I want to view patient vitals so that I can make informed decisions
- As a nurse, I want to update patient records so that information stays current

---
"""
        )

        parser = PRDParser(str(spec_path))
        spec = parser.parse()

        assert spec.status == "draft"
        assert spec.industry == "healthcare"
        assert spec.use_case == "dashboard"
        assert len(spec.features) == 2


class TestPRDMapper:
    """Test PRD to features.json mapping"""

    def test_mapper_initialization(self, temp_project):
        """Test mapper can be initialized"""
        mapper = PRDMapper(str(temp_project))
        assert mapper.project_root == temp_project

    def test_parallel_build_identification(self, temp_project):
        """Test parallel build identification"""
        mapper = PRDMapper(str(temp_project))

        features_data = {
            "features": [
                {"id": "feature_1", "dependencies": []},
                {"id": "feature_2", "dependencies": []},
                {"id": "feature_3", "dependencies": ["feature_1"]},
            ]
        }

        parallel_groups = mapper.identify_parallel_builds(features_data)

        assert len(parallel_groups["parallel"]) == 2  # feature_1 and feature_2
        assert len(parallel_groups["sequential"]) == 1  # feature_3


class TestOpusHandoff:
    """Test Opus handoff protocol"""

    def test_handoff_initialization(self, temp_project):
        """Test handoff can be initialized"""
        handoff = OpusHandoff(str(temp_project))
        assert handoff.project_root == temp_project


class TestPlanningMode:
    """Test planning mode detection"""

    def test_detector_initialization(self, temp_project):
        """Test detector can be initialized"""
        detector = PlanningModeDetector(str(temp_project))
        assert detector.project_root == temp_project

    def test_strategic_detection(self, temp_project):
        """Test strategic keyword detection"""
        detector = PlanningModeDetector(str(temp_project))

        mode, confidence = detector.detect_mode("What architecture should we use for scalability?")

        assert mode == "planning"
        assert confidence > 0.6

    def test_tactical_detection(self, temp_project):
        """Test tactical keyword detection"""
        detector = PlanningModeDetector(str(temp_project))

        mode, confidence = detector.detect_mode(
            "Implement the user authentication feature and write tests"
        )

        assert mode == "execution"
        assert confidence > 0.6

    def test_model_suggestion(self, temp_project):
        """Test model suggestion logic"""
        detector = PlanningModeDetector(str(temp_project))

        # Strategic → Opus
        suggested = detector.suggest_model("planning", 0.8)
        assert suggested == "opus"

        # Tactical → Sonnet
        suggested = detector.suggest_model("execution", 0.8)
        assert suggested == "sonnet"

        # Low confidence → None
        suggested = detector.suggest_model("planning", 0.5)
        assert suggested is None


class TestEndToEndIntegration:
    """Test complete end-to-end workflow"""

    def test_full_spec_to_features_flow(self, temp_project):
        """Test complete flow from spec creation to features.json"""
        # 1. Create spec manually (simulating wizard)
        spec_path = temp_project / ".buildrunner" / "PROJECT_SPEC.md"
        spec_path.parent.mkdir(parents=True)

        spec_path.write_text(
            """# PROJECT_SPEC

**Status**: confirmed
**Industry**: healthcare
**Use Case**: dashboard
**Tech Stack**: react-fastapi-postgres

---

# Product Requirements

## User Stories
- As a doctor, I want to view patient vitals so that I can make informed decisions

---

# Technical Architecture

Tech stack: React + FastAPI + PostgreSQL

---
"""
        )

        # 2. Parse spec
        parser = PRDParser(str(spec_path))
        spec = parser.parse()

        assert spec.industry == "healthcare"
        assert len(spec.features) == 1

        # 3. Map to features.json
        mapper = PRDMapper(str(temp_project))
        features_data = mapper.spec_to_features(spec)

        assert features_data["project"]["industry"] == "healthcare"
        assert len(features_data["features"]) == 1

        # 4. Save features.json
        mapper.save_features_json(features_data)

        assert mapper.features_path.exists()

        # 5. Load and verify
        loaded = mapper.load_features_json()
        assert loaded["project"]["industry"] == "healthcare"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
