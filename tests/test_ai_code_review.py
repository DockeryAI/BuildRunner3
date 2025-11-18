"""
Tests for AI Code Review System
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from core.ai_code_review import CodeReviewer, CodeReviewError


class TestCodeReviewer:
    """Test CodeReviewer class"""

    @pytest.fixture
    def reviewer(self):
        """Create CodeReviewer instance with test API key"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            return CodeReviewer()

    def test_init_with_api_key(self):
        """Test initialization with API key"""
        reviewer = CodeReviewer(api_key="test-key")
        assert reviewer.api_key == "test-key"
        assert reviewer.model == "claude-sonnet-4-20250514"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises error"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CodeReviewError, match="ANTHROPIC_API_KEY"):
                CodeReviewer()

    @pytest.mark.asyncio
    async def test_review_diff_empty(self, reviewer):
        """Test reviewing empty diff"""
        result = await reviewer.review_diff("")

        assert result["summary"] == "No changes to review"
        assert result["issues"] == []
        assert result["suggestions"] == []
        assert result["score"] == 100

    @pytest.mark.asyncio
    async def test_review_diff_success(self, reviewer):
        """Test successful diff review"""
        mock_response = Mock()
        mock_response.content = [Mock(text="""
SUMMARY: Good changes with minor issues

ISSUES:
- Missing error handling
- No type hints

SUGGESTIONS:
- Add try/except blocks
- Add type annotations

SCORE: 75
""")]

        with patch.object(reviewer.client.messages, "create", AsyncMock(return_value=mock_response)):
            diff = "+  def foo():\n+    print('hello')"
            result = await reviewer.review_diff(diff)

            assert "minor issues" in result["summary"]
            assert len(result["issues"]) == 2
            assert "Missing error handling" in result["issues"]
            assert len(result["suggestions"]) == 2
            assert result["score"] == 75

    @pytest.mark.asyncio
    async def test_review_diff_with_context(self, reviewer):
        """Test diff review with context"""
        mock_response = Mock()
        mock_response.content = [Mock(text="SUMMARY: Good\nSCORE: 90")]

        with patch.object(reviewer.client.messages, "create", AsyncMock(return_value=mock_response)) as mock_create:
            diff = "+  def test(): pass"
            context = {"file_path": "test.py", "commit_msg": "Add test"}

            await reviewer.review_diff(diff, context)

            # Verify context was included in prompt
            call_args = mock_create.call_args
            prompt = call_args[1]["messages"][0]["content"]
            assert "test.py" in prompt
            assert "Add test" in prompt

    @pytest.mark.asyncio
    async def test_review_diff_api_error(self, reviewer):
        """Test diff review with API error"""
        with patch.object(reviewer.client.messages, "create", AsyncMock(side_effect=Exception("API Error"))):
            diff = "+  def foo(): pass"

            with pytest.raises(CodeReviewError, match="Failed to review diff"):
                await reviewer.review_diff(diff)

    @pytest.mark.asyncio
    async def test_analyze_architecture_success(self, reviewer):
        """Test successful architecture analysis"""
        mock_response = Mock()
        mock_response.content = [Mock(text="""
COMPLIANCE: YES

VIOLATIONS:

RECOMMENDATIONS:
- Consider adding more documentation

ALIGNMENT_SCORE: 95
""")]

        with patch.object(reviewer.client.messages, "create", AsyncMock(return_value=mock_response)):
            with patch.object(reviewer, "_load_project_spec", return_value="# Spec"):
                code = "def test(): pass"
                result = await reviewer.analyze_architecture(code, "test.py")

                assert result["compliant"] is True
                assert result["violations"] == []
                assert len(result["recommendations"]) == 1
                assert result["spec_alignment"] == 95

    @pytest.mark.asyncio
    async def test_analyze_architecture_violations(self, reviewer):
        """Test architecture analysis with violations"""
        mock_response = Mock()
        mock_response.content = [Mock(text="""
COMPLIANCE: NO

VIOLATIONS:
- Direct database access bypasses repository layer
- Missing service layer

RECOMMENDATIONS:
- Use repository pattern
- Add service layer

ALIGNMENT_SCORE: 45
""")]

        with patch.object(reviewer.client.messages, "create", AsyncMock(return_value=mock_response)):
            with patch.object(reviewer, "_load_project_spec", return_value="# Spec"):
                code = "db.query('SELECT * FROM users')"
                result = await reviewer.analyze_architecture(code, "bad.py")

                assert result["compliant"] is False
                assert len(result["violations"]) == 2
                assert "repository layer" in result["violations"][0]
                assert len(result["recommendations"]) == 2
                assert result["spec_alignment"] == 45

    @pytest.mark.asyncio
    async def test_analyze_architecture_api_error(self, reviewer):
        """Test architecture analysis with API error"""
        with patch.object(reviewer.client.messages, "create", AsyncMock(side_effect=Exception("API Error"))):
            with patch.object(reviewer, "_load_project_spec", return_value="# Spec"):
                with pytest.raises(CodeReviewError, match="Failed to analyze architecture"):
                    await reviewer.analyze_architecture("code", "test.py")

    @pytest.mark.asyncio
    async def test_review_file_success(self, reviewer, tmp_path):
        """Test successful file review"""
        # Create temp file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test():\n    pass")

        mock_review_response = Mock()
        mock_review_response.content = [Mock(text="SUMMARY: Good\nSCORE: 90")]

        mock_arch_response = Mock()
        mock_arch_response.content = [Mock(text="COMPLIANCE: YES\nALIGNMENT_SCORE: 95")]

        with patch.object(reviewer.client.messages, "create", AsyncMock(side_effect=[mock_review_response, mock_arch_response])):
            with patch.object(reviewer, "_get_file_diff", return_value="+  def test(): pass"):
                with patch.object(reviewer, "_load_project_spec", return_value="# Spec"):
                    result = await reviewer.review_file(str(test_file))

                    assert "file" in result
                    assert "review" in result
                    assert "architecture" in result
                    assert result["review"]["score"] == 90
                    assert result["architecture"]["spec_alignment"] == 95

    @pytest.mark.asyncio
    async def test_review_file_not_found(self, reviewer):
        """Test review of non-existent file"""
        with pytest.raises(CodeReviewError, match="File not found"):
            await reviewer.review_file("/nonexistent/file.py")

    @pytest.mark.asyncio
    async def test_review_file_no_architecture_check(self, reviewer, tmp_path):
        """Test file review without architecture check"""
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        mock_response = Mock()
        mock_response.content = [Mock(text="SUMMARY: Good\nSCORE: 90")]

        with patch.object(reviewer.client.messages, "create", AsyncMock(return_value=mock_response)):
            with patch.object(reviewer, "_get_file_diff", return_value="+  def test(): pass"):
                result = await reviewer.review_file(str(test_file), check_architecture=False)

                assert "review" in result
                assert result["architecture"] == {}

    def test_parse_review_response(self, reviewer):
        """Test parsing of review response"""
        response = """
SUMMARY: Code looks good with minor improvements needed

ISSUES:
- Missing docstring
- No type hints

SUGGESTIONS:
- Add comprehensive docstring
- Add type annotations

SCORE: 82
"""
        result = reviewer._parse_review_response(response)

        assert "minor improvements" in result["summary"]
        assert len(result["issues"]) == 2
        assert len(result["suggestions"]) == 2
        assert result["score"] == 82

    def test_parse_review_response_no_score(self, reviewer):
        """Test parsing response without score"""
        response = "SUMMARY: Good code"
        result = reviewer._parse_review_response(response)

        assert result["summary"] == "Good code"
        assert result["score"] == 85  # Default score

    def test_parse_architecture_response(self, reviewer):
        """Test parsing of architecture response"""
        response = """
COMPLIANCE: NO

VIOLATIONS:
- Layer violation detected
- Missing abstraction

RECOMMENDATIONS:
- Use dependency injection
- Add interface layer

ALIGNMENT_SCORE: 60
"""
        result = reviewer._parse_architecture_response(response)

        assert result["compliant"] is False
        assert len(result["violations"]) == 2
        assert len(result["recommendations"]) == 2
        assert result["spec_alignment"] == 60

    def test_parse_architecture_response_compliant(self, reviewer):
        """Test parsing compliant architecture response"""
        response = """
COMPLIANCE: YES

VIOLATIONS:

RECOMMENDATIONS:
- Consider adding more tests

ALIGNMENT_SCORE: 95
"""
        result = reviewer._parse_architecture_response(response)

        assert result["compliant"] is True
        assert result["violations"] == []
        assert len(result["recommendations"]) == 1

    def test_load_project_spec_exists(self, reviewer, tmp_path):
        """Test loading existing PROJECT_SPEC"""
        spec_dir = tmp_path / ".buildrunner"
        spec_dir.mkdir()
        spec_file = spec_dir / "PROJECT_SPEC.md"
        spec_file.write_text("# Test Spec\nContent")

        reviewer.project_root = tmp_path
        spec = reviewer._load_project_spec()

        assert "# Test Spec" in spec
        assert "Content" in spec

    def test_load_project_spec_not_found(self, reviewer, tmp_path):
        """Test loading non-existent PROJECT_SPEC"""
        reviewer.project_root = tmp_path
        spec = reviewer._load_project_spec()

        assert spec == "No PROJECT_SPEC.md found"

    def test_get_file_diff_success(self, reviewer, tmp_path):
        """Test getting file diff"""
        reviewer.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="+  new line")

            diff = reviewer._get_file_diff("test.py")

            assert "+  new line" in diff
            mock_run.assert_called_once()

    def test_get_file_diff_error(self, reviewer, tmp_path):
        """Test getting file diff with error"""
        reviewer.project_root = tmp_path

        with patch("subprocess.run", side_effect=Exception("Git error")):
            diff = reviewer._get_file_diff("test.py")

            assert diff == ""  # Returns empty string on error


# Integration test (requires real API key - skipped in CI)
@pytest.mark.skip(reason="Requires real ANTHROPIC_API_KEY")
@pytest.mark.asyncio
async def test_integration_review_diff():
    """Integration test with real API (manual testing only)"""
    reviewer = CodeReviewer()

    diff = """
+  def calculate_total(items):
+    total = 0
+    for item in items:
+      total += item.price
+    return total
"""

    result = await reviewer.review_diff(diff)

    assert "summary" in result
    assert "score" in result
    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100
