"""
Tests for Spec Parser
"""
import pytest
from pathlib import Path
from core.spec_parser import SpecParser, Feature


class TestSpecParser:
    """Test SpecParser class"""

    @pytest.fixture
    def parser(self):
        """Create SpecParser instance"""
        return SpecParser()

    @pytest.fixture
    def sample_spec(self, tmp_path):
        """Create sample PROJECT_SPEC.md"""
        spec_content = """# Project Specification

## Overview

This is a test project for user authentication and profile management.

## Features

### User Authentication

User authentication system with email/password login.

Requirements:
- Email validation
- Password hashing with bcrypt
- Session management

Acceptance Criteria:
- Users can register with email/password
- Users can login with valid credentials
- Sessions expire after 24 hours

Technical Details:
- Use JWT for tokens
- Store in PostgreSQL

### User Profile Management

Depends on: User Authentication

Allow users to view and edit their profiles.

Requirements:
- Profile CRUD operations
- Avatar upload support

Acceptance Criteria:
- Users can view their profile
- Users can update profile fields
- Avatar images are validated

### Admin Dashboard

Requires: User Authentication, User Profile Management

Admin interface for user management.

Requirements:
- User list view
- User search functionality
- Role management

## Technical Requirements

- Python 3.10+
- FastAPI framework
- PostgreSQL database
- Redis for caching
"""
        spec_file = tmp_path / "PROJECT_SPEC.md"
        spec_file.write_text(spec_content)
        return spec_file

    def test_init(self, parser):
        """Test initialization"""
        assert parser is not None
        assert 'overview' in parser.required_sections
        assert 'features' in parser.required_sections

    def test_parse_spec_success(self, parser, sample_spec):
        """Test successful spec parsing"""
        result = parser.parse_spec(sample_spec)

        assert 'features' in result
        assert 'technical_requirements' in result
        assert 'overview' in result
        assert 'metadata' in result

        # Check metadata
        assert result['metadata']['feature_count'] == 3
        assert result['metadata']['has_dependencies'] is True

    def test_parse_spec_file_not_found(self, parser):
        """Test parsing non-existent file"""
        with pytest.raises(FileNotFoundError):
            parser.parse_spec(Path("/nonexistent/spec.md"))

    def test_parse_spec_invalid_structure(self, parser, tmp_path):
        """Test parsing spec with missing required sections"""
        invalid_spec = tmp_path / "invalid.md"
        invalid_spec.write_text("# Just a heading\n\nSome content")

        with pytest.raises(ValueError, match="missing required sections"):
            parser.parse_spec(invalid_spec)

    def test_extract_features(self, parser, sample_spec):
        """Test feature extraction"""
        content = sample_spec.read_text()
        features = parser.extract_features(content)

        assert len(features) == 3

        # Check first feature
        auth_feature = features[0]
        assert auth_feature.name == "User Authentication"
        assert auth_feature.id == "user_authentication"
        assert "email/password" in auth_feature.description.lower()
        assert len(auth_feature.requirements) == 3
        assert len(auth_feature.acceptance_criteria) == 3

    def test_extract_features_no_features_section(self, parser):
        """Test extraction when Features section is missing"""
        content = "# Spec\n\n## Overview\nSome text"
        features = parser.extract_features(content)

        assert len(features) == 0

    def test_extract_dependencies(self, parser, sample_spec):
        """Test dependency extraction"""
        content = sample_spec.read_text()
        dependencies = parser.extract_dependencies(content)

        # Profile depends on Authentication
        assert 'user_profile_management' in dependencies
        assert 'user_authentication' in dependencies['user_profile_management']

        # Admin depends on both
        assert 'admin_dashboard' in dependencies
        assert 'user_authentication' in dependencies['admin_dashboard']
        assert 'user_profile_management' in dependencies['admin_dashboard']

    def test_extract_dependencies_no_dependencies(self, parser):
        """Test extraction when no dependencies exist"""
        content = """
## Features

### Simple Feature

No dependencies here.
"""
        dependencies = parser.extract_dependencies(content)

        assert len(dependencies) == 0

    def test_validate_spec_valid(self, parser, sample_spec):
        """Test validation of valid spec"""
        content = sample_spec.read_text()
        is_valid = parser.validate_spec(content)

        assert is_valid is True

    def test_validate_spec_missing_section(self, parser):
        """Test validation with missing section"""
        content = """
# Spec

## Overview
Text

## Features
More text
"""
        # Missing "Technical Requirements"
        is_valid = parser.validate_spec(content)

        assert is_valid is False

    def test_generate_feature_id(self, parser):
        """Test feature ID generation"""
        assert parser._generate_feature_id("User Authentication") == "user_authentication"
        assert parser._generate_feature_id("API Gateway") == "api_gateway"
        assert parser._generate_feature_id("Real-Time Chat") == "real_time_chat"
        assert parser._generate_feature_id("OAuth2.0 Integration") == "oauth2_0_integration"

    def test_extract_description(self, parser):
        """Test description extraction"""
        feature_body = """
This is the feature description.

Requirements:
- Requirement 1
"""
        description = parser._extract_description(feature_body)

        assert description == "This is the feature description."

    def test_extract_description_with_headings(self, parser):
        """Test description extraction skips headings"""
        feature_body = """
#### Subheading

This is the actual description.

More content.
"""
        description = parser._extract_description(feature_body)

        assert description == "This is the actual description."

    def test_extract_requirements(self, parser):
        """Test requirements extraction"""
        feature_body = """
Requirements:
- Email validation
- Password hashing
- Session management

Other text.
"""
        requirements = parser._extract_requirements(feature_body)

        assert len(requirements) == 3
        assert "Email validation" in requirements
        assert "Password hashing" in requirements

    def test_extract_requirements_none(self, parser):
        """Test extraction when no requirements"""
        feature_body = "Just some text with no requirements."
        requirements = parser._extract_requirements(feature_body)

        assert len(requirements) == 0

    def test_extract_acceptance_criteria(self, parser):
        """Test acceptance criteria extraction"""
        feature_body = """
Acceptance Criteria:
- Users can register
- Users can login
- Sessions expire
"""
        criteria = parser._extract_acceptance_criteria(feature_body)

        assert len(criteria) == 3
        assert "Users can register" in criteria

    def test_extract_acceptance_criteria_with_checkboxes(self, parser):
        """Test extraction with checkbox format"""
        feature_body = """
Acceptance Criteria:
- [ ] Users can register
- [ ] Users can login
"""
        criteria = parser._extract_acceptance_criteria(feature_body)

        assert len(criteria) == 2

    def test_extract_technical_details(self, parser):
        """Test technical details extraction"""
        feature_body = """
Technical Details:
- Use JWT for tokens
- Store in PostgreSQL
- Redis for caching
"""
        details = parser._extract_technical_details(feature_body)

        assert len(details) == 3
        assert "Use JWT for tokens" in details

    def test_extract_technical_details_implementation_section(self, parser):
        """Test extraction from Implementation section"""
        feature_body = """
Implementation:
- Backend API
- Frontend UI
"""
        details = parser._extract_technical_details(feature_body)

        assert len(details) == 2
        assert "Backend API" in details

    def test_estimate_complexity_simple(self, parser):
        """Test complexity estimation for simple feature"""
        feature_body = """
Simple feature.

Requirements:
- One thing
- Another thing
"""
        complexity = parser._estimate_complexity(feature_body)

        assert complexity == "simple"

    def test_estimate_complexity_complex(self, parser):
        """Test complexity estimation for complex feature"""
        feature_body = """
This is a very complex feature with lots of details and requirements.
""" + " ".join(["word"] * 350) + """

Requirements:
- Req 1
- Req 2
- Req 3
- Req 4
- Req 5
- Req 6
- Req 7
- Req 8
"""
        complexity = parser._estimate_complexity(feature_body)

        assert complexity == "complex"

    def test_estimate_complexity_medium(self, parser):
        """Test complexity estimation for medium feature"""
        feature_body = """
Medium complexity feature with moderate details.
""" + " ".join(["word"] * 150) + """

Requirements:
- Req 1
- Req 2
- Req 3
- Req 4
"""
        complexity = parser._estimate_complexity(feature_body)

        assert complexity == "medium"

    def test_apply_dependencies(self, parser):
        """Test applying dependencies to features"""
        features = [
            Feature(id="feature_a", name="Feature A", description="A"),
            Feature(id="feature_b", name="Feature B", description="B"),
            Feature(id="feature_c", name="Feature C", description="C")
        ]

        dependencies = {
            "feature_b": ["feature_a"],
            "feature_c": ["feature_a", "feature_b"]
        }

        parser._apply_dependencies(features, dependencies)

        assert features[0].dependencies == []
        assert features[1].dependencies == ["feature_a"]
        assert features[2].dependencies == ["feature_a", "feature_b"]

    def test_apply_dependencies_invalid_reference(self, parser):
        """Test applying dependencies with invalid references"""
        features = [
            Feature(id="feature_a", name="Feature A", description="A")
        ]

        dependencies = {
            "feature_a": ["nonexistent_feature"]
        }

        parser._apply_dependencies(features, dependencies)

        # Invalid dependency should be filtered out
        assert features[0].dependencies == []

    def test_feature_to_dict(self, parser):
        """Test converting Feature to dict"""
        feature = Feature(
            id="test_feature",
            name="Test Feature",
            description="Description",
            requirements=["Req 1"],
            dependencies=["other_feature"],
            acceptance_criteria=["AC 1"],
            technical_details=["Detail 1"],
            complexity="medium"
        )

        feature_dict = parser._feature_to_dict(feature)

        assert feature_dict['id'] == "test_feature"
        assert feature_dict['name'] == "Test Feature"
        assert feature_dict['complexity'] == "medium"
        assert len(feature_dict['requirements']) == 1
        assert len(feature_dict['dependencies']) == 1

    def test_extract_overview(self, parser, sample_spec):
        """Test overview extraction"""
        content = sample_spec.read_text()
        overview = parser._extract_overview(content)

        assert "user authentication" in overview.lower()
        assert "profile management" in overview.lower()

    def test_extract_tech_requirements(self, parser, sample_spec):
        """Test technical requirements extraction"""
        content = sample_spec.read_text()
        tech_reqs = parser._extract_tech_requirements(content)

        assert len(tech_reqs) == 4
        assert "Python 3.10+" in tech_reqs
        assert "FastAPI framework" in tech_reqs

    def test_full_integration(self, parser, sample_spec):
        """Test full parsing integration"""
        result = parser.parse_spec(sample_spec)

        # Verify features
        assert len(result['features']) == 3

        # Verify dependencies applied
        profile_feature = [f for f in result['features'] if f['id'] == 'user_profile_management'][0]
        assert 'user_authentication' in profile_feature['dependencies']

        admin_feature = [f for f in result['features'] if f['id'] == 'admin_dashboard'][0]
        assert len(admin_feature['dependencies']) == 2

        # Verify technical requirements
        assert len(result['technical_requirements']) == 4

        # Verify overview
        assert len(result['overview']) > 0
