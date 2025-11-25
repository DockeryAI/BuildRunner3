"""
Tests for completed PRD wizard with Opus integration
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from core.opus_client import OpusClient, OpusAPIError
from core.model_switcher import ModelSwitcher
from core.planning_mode import detect_planning_mode, get_project_state
from core.prd_wizard import run_wizard


class TestOpusClient:
    """Test real Opus API client"""

    @pytest.fixture
    def opus_client(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            return OpusClient()

    def test_init_with_api_key(self):
        """Test initialization with API key"""
        client = OpusClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model == "claude-opus-4-20250514"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises ValueError"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                OpusClient()

    @pytest.mark.asyncio
    async def test_pre_fill_spec(self, opus_client):
        """Test spec pre-filling"""
        mock_response = Mock()
        mock_response.content = [Mock(text="# PROJECT_SPEC\n\nTest content")]

        with patch.object(
            opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)
        ):
            result = await opus_client.pre_fill_spec(
                industry="Healthcare", use_case="Dashboard", user_input={"project_name": "Test"}
            )

            assert "PROJECT_SPEC" in result
            assert "Test content" in result

    @pytest.mark.asyncio
    async def test_analyze_requirements(self, opus_client):
        """Test requirements analysis"""
        mock_response = Mock()
        mock_response.content = [
            Mock(text='{"features": [], "architecture": {}, "tech_stack": []}')
        ]

        with patch.object(
            opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)
        ):
            result = await opus_client.analyze_requirements("Build a dashboard")

            assert "features" in result
            assert "architecture" in result

    @pytest.mark.asyncio
    async def test_analyze_requirements_invalid_json(self, opus_client):
        """Test requirements analysis with invalid JSON response"""
        mock_response = Mock()
        mock_response.content = [Mock(text="invalid json")]

        with patch.object(
            opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(OpusAPIError, match="Failed to parse JSON"):
                await opus_client.analyze_requirements("Build a dashboard")

    @pytest.mark.asyncio
    async def test_generate_design_tokens(self, opus_client):
        """Test design token generation"""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"colors": {}, "typography": {}}')]

        with patch.object(
            opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)
        ):
            result = await opus_client.generate_design_tokens("Healthcare", "Dashboard")

            assert "colors" in result
            assert "typography" in result

    @pytest.mark.asyncio
    async def test_generate_design_tokens_invalid_json(self, opus_client):
        """Test design token generation with invalid JSON"""
        mock_response = Mock()
        mock_response.content = [Mock(text="not json")]

        with patch.object(
            opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(OpusAPIError, match="Failed to parse design tokens JSON"):
                await opus_client.generate_design_tokens("Healthcare", "Dashboard")

    @pytest.mark.asyncio
    async def test_validate_spec(self, opus_client):
        """Test spec validation"""
        mock_response = Mock()
        mock_response.content = [
            Mock(text='{"valid": true, "missing_sections": [], "suggestions": [], "score": 95}')
        ]

        with patch.object(
            opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)
        ):
            result = await opus_client.validate_spec("# Test Spec")

            assert result["valid"] is True
            assert isinstance(result["missing_sections"], list)
            assert result["score"] == 95

    @pytest.mark.asyncio
    async def test_validate_spec_invalid_json(self, opus_client):
        """Test spec validation with invalid JSON"""
        mock_response = Mock()
        mock_response.content = [Mock(text="bad json")]

        with patch.object(
            opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(OpusAPIError, match="Failed to parse validation JSON"):
                await opus_client.validate_spec("# Test Spec")


class TestModelSwitcher:
    """Test model switching protocol"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project structure"""
        project = tmp_path / "test_project"
        project.mkdir()
        (project / ".buildrunner").mkdir()

        # Create spec
        spec = project / ".buildrunner" / "PROJECT_SPEC.md"
        spec.write_text("# Test Spec\n\n## Architecture\nFrontend: React")

        # Create features
        features = project / ".buildrunner" / "features.json"
        features.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "id": "1",
                            "name": "Feature 1",
                            "description": "Test feature description",
                            "status": "pending",
                            "dependencies": [],
                        }
                    ]
                }
            )
        )

        return project

    def test_create_handoff_package(self, temp_project):
        """Test handoff package creation"""
        switcher = ModelSwitcher(temp_project)

        package = switcher.create_handoff_package(
            spec_path=temp_project / ".buildrunner" / "PROJECT_SPEC.md",
            features_path=temp_project / ".buildrunner" / "features.json",
            context={"constraints": ["Use TypeScript"]},
        )

        assert package["version"] == "1.0"
        assert package["source_model"] == "claude-opus-4"
        assert package["target_model"] == "claude-sonnet-4.5"
        assert "spec_summary" in package
        assert "features" in package
        assert len(package["features"]) == 1

    def test_create_handoff_package_missing_spec(self, temp_project):
        """Test handoff package creation with missing spec"""
        switcher = ModelSwitcher(temp_project)

        with pytest.raises(FileNotFoundError, match="PROJECT_SPEC not found"):
            switcher.create_handoff_package(
                spec_path=temp_project / ".buildrunner" / "NONEXISTENT.md",
                features_path=temp_project / ".buildrunner" / "features.json",
                context={},
            )

    def test_compress_context(self, temp_project):
        """Test context compression"""
        switcher = ModelSwitcher(temp_project)

        spec = "# Test\n\n" + ("x" * 5000)  # Long spec
        features = {
            "features": [
                {
                    "id": "1",
                    "name": "F1",
                    "description": "x" * 500,
                    "status": "pending",
                    "dependencies": [],
                }
            ]
        }
        context = {"constraints": ["Constraint 1"]}

        compressed = switcher.compress_context(spec, features, context)

        assert len(compressed["spec_summary"]) <= 1000
        assert len(compressed["features"][0]["description"]) == 200  # Truncated
        assert "next_steps" in compressed

    def test_generate_sonnet_prompt(self, temp_project):
        """Test Sonnet prompt generation"""
        switcher = ModelSwitcher(temp_project)

        compressed = {
            "spec_summary": "Test project",
            "features": [
                {
                    "id": "1",
                    "name": "F1",
                    "description": "Test",
                    "status": "pending",
                    "dependencies": [],
                }
            ],
            "architecture": {"frontend": "React"},
            "constraints": ["TypeScript"],
            "next_steps": ["Implement F1"],
        }

        prompt = switcher.generate_sonnet_prompt(compressed)

        assert "BuildRunner Project Handoff" in prompt
        assert "Test project" in prompt
        assert "React" in prompt
        assert "Implement F1" in prompt

    def test_validate_handoff_success(self, temp_project):
        """Test handoff validation success"""
        switcher = ModelSwitcher(temp_project)

        package = {
            "version": "1.0",
            "timestamp": "20250101_120000",
            "source_model": "opus",
            "target_model": "sonnet",
            "spec_summary": "Test",
            "features": [{"id": "1"}],
            "architecture": {},
            "next_steps": ["Step 1"],
        }

        assert switcher.validate_handoff(package) is True

    def test_validate_handoff_missing_field(self, temp_project):
        """Test handoff validation fails on missing field"""
        switcher = ModelSwitcher(temp_project)

        package = {"version": "1.0"}  # Missing required fields

        with pytest.raises(ValueError, match="missing required field"):
            switcher.validate_handoff(package)

    def test_validate_handoff_no_features(self, temp_project):
        """Test handoff validation fails with no features"""
        switcher = ModelSwitcher(temp_project)

        package = {
            "version": "1.0",
            "timestamp": "20250101_120000",
            "source_model": "opus",
            "target_model": "sonnet",
            "spec_summary": "Test",
            "features": [],  # Empty
            "architecture": {},
            "next_steps": ["Step 1"],
        }

        with pytest.raises(ValueError, match="has no features"):
            switcher.validate_handoff(package)

    def test_load_handoff(self, temp_project):
        """Test loading handoff package"""
        switcher = ModelSwitcher(temp_project)

        # Create a handoff
        package = switcher.create_handoff_package(
            spec_path=temp_project / ".buildrunner" / "PROJECT_SPEC.md",
            features_path=temp_project / ".buildrunner" / "features.json",
            context={},
        )

        # Load it
        loaded = switcher.load_handoff(package["timestamp"])

        assert loaded["timestamp"] == package["timestamp"]
        assert loaded["version"] == "1.0"

    def test_load_handoff_not_found(self, temp_project):
        """Test loading non-existent handoff"""
        switcher = ModelSwitcher(temp_project)

        with pytest.raises(FileNotFoundError, match="Handoff package not found"):
            switcher.load_handoff("20990101_000000")


class TestPlanningMode:
    """Test planning mode auto-detection"""

    def test_detect_new_project(self):
        """Test detection for new project"""
        result = detect_planning_mode(
            user_prompt="Create a new healthcare dashboard",
            project_state={"has_spec": False, "has_features": False, "features": []},
            conversation_history=[],
        )

        assert result["use_opus"] is True
        assert result["confidence"] >= 0.9
        assert "New project" in result["reason"]

    def test_detect_planning_keywords(self):
        """Test detection with planning keywords"""
        result = detect_planning_mode(
            user_prompt="Help me design the architecture for this feature",
            project_state={"has_spec": True, "has_features": True, "features": []},
            conversation_history=[],
        )

        assert result["use_opus"] is True
        assert "Planning-related" in result["reason"] or "planning" in result["reason"].lower()

    def test_detect_execution_keywords(self):
        """Test detection with execution keywords"""
        result = detect_planning_mode(
            user_prompt="Implement the user authentication feature",
            project_state={"has_spec": True, "has_features": True, "features": []},
            conversation_history=[],
        )

        assert result["use_opus"] is False
        assert "Execution-related" in result["reason"] or "execution" in result["reason"].lower()

    def test_detect_ambiguous_defaults_to_sonnet(self):
        """Test ambiguous request defaults to Sonnet for existing project"""
        result = detect_planning_mode(
            user_prompt="Tell me about this project",
            project_state={
                "has_spec": True,
                "has_features": True,
                "features": [{"id": "1", "name": "Feature"}],
            },
            conversation_history=[],
        )

        assert result["use_opus"] is False
        assert result["confidence"] == 0.6

    def test_get_project_state(self, tmp_path):
        """Test project state extraction"""
        # Create project with spec and features
        (tmp_path / ".buildrunner").mkdir()
        (tmp_path / ".buildrunner" / "PROJECT_SPEC.md").write_text("# Spec")
        (tmp_path / ".buildrunner" / "features.json").write_text(
            json.dumps({"features": [{"status": "completed"}, {"status": "pending"}]})
        )

        state = get_project_state(tmp_path)

        assert state["has_spec"] is True
        assert state["has_features"] is True
        assert state["feature_count"] == 2
        assert state["completed_count"] == 1

    def test_get_project_state_no_files(self, tmp_path):
        """Test project state with no files"""
        state = get_project_state(tmp_path)

        assert state["has_spec"] is False
        assert state["has_features"] is False
        assert state["feature_count"] == 0
        assert state["completed_count"] == 0


class TestPRDWizard:
    """Test complete PRD wizard"""

    @pytest.mark.asyncio
    async def test_run_wizard_non_interactive(self, tmp_path):
        """Test wizard in non-interactive mode"""
        with patch("core.opus_client.OpusClient") as MockOpus:
            mock_opus = MockOpus.return_value
            mock_opus.pre_fill_spec = AsyncMock(return_value="# Generated Spec\n\nTest content")

            with patch("core.model_switcher.ModelSwitcher") as MockSwitcher:
                mock_switcher = MockSwitcher.return_value
                mock_switcher.create_handoff_package.return_value = {
                    "timestamp": "20250101_120000",
                    "version": "1.0",
                }

                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    # Create features.json for fallback path
                    (tmp_path / ".buildrunner").mkdir(parents=True, exist_ok=True)

                    result = await run_wizard(interactive=False)

                    assert result is not None
                    assert "spec_path" in result
                    assert "features_path" in result
                    assert "handoff_package" in result

    @pytest.mark.asyncio
    async def test_run_wizard_no_api_key(self, tmp_path):
        """Test wizard without API key"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("pathlib.Path.cwd", return_value=tmp_path):
                result = await run_wizard(interactive=False)

                assert result is None  # Should return None when no API key


# Coverage target: 85%+
# All async tests use pytest-asyncio
# Mock external API calls (Anthropic)
