"""
Comprehensive tests for Synapse integration.

Tests SynapseConnector, ProfileLoader, and CLI commands with 90%+ coverage goal.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.design_system.synapse_connector import SynapseConnector, NAICSEntry
from core.design_system.profile_loader import ProfileLoader, IndustryProfile


class TestSynapseConnector:
    """Test SynapseConnector class."""

    @pytest.fixture
    def connector(self):
        """Create connector with Synapse path."""
        synapse_path = "/Users/byronhudson/Projects/Synapse/src/data/"
        return SynapseConnector(synapse_path)

    def test_init_valid_path(self, connector):
        """Test initialization with valid path."""
        assert connector.synapse_path.exists()
        assert connector.naics_file.exists()

    def test_init_invalid_path(self):
        """Test initialization with invalid path."""
        with pytest.raises(FileNotFoundError):
            SynapseConnector("/invalid/path")

    def test_load_naics_codes(self, connector):
        """Test loading NAICS codes from TypeScript."""
        entries = connector.load_naics_codes()

        # Should have 140+ entries with full profiles
        assert len(entries) >= 140
        assert all(isinstance(e, NAICSEntry) for e in entries)
        assert all(e.has_full_profile for e in entries)

    def test_naics_entry_structure(self, connector):
        """Test NAICS entry has all required fields."""
        entries = connector.load_naics_codes()

        for entry in entries[:10]:  # Test first 10
            assert entry.naics_code
            assert entry.display_name
            assert entry.category
            assert isinstance(entry.keywords, list)
            assert entry.has_full_profile is True
            # popularity can be None or int
            assert entry.popularity is None or isinstance(entry.popularity, int)

    def test_load_profile_restaurant(self, connector):
        """Test loading restaurant profile from TypeScript."""
        profile = connector.load_profile('restaurant')

        assert profile is not None
        assert profile['id'] == 'restaurant'
        assert 'name' in profile
        assert 'power_words' in profile
        assert 'psychology_profile' in profile

    def test_load_profile_nonexistent(self, connector):
        """Test loading nonexistent profile."""
        profile = connector.load_profile('nonexistent-industry')
        assert profile is None

    def test_export_to_yaml(self, connector):
        """Test exporting profiles to YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            count = connector.export_to_yaml(output_dir)

            # Should export 140+ profiles
            assert count >= 140

            # Check files were created
            yaml_files = list(output_dir.glob("*.yaml"))
            assert len(yaml_files) == count

            # Check one file has valid structure
            test_file = yaml_files[0]
            with open(test_file) as f:
                data = yaml.safe_load(f)

            assert 'id' in data
            assert 'name' in data
            assert 'naics_code' in data

    def test_export_creates_directory(self, connector):
        """Test export creates output directory if not exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "new_dir" / "profiles"

            count = connector.export_to_yaml(output_dir)

            assert output_dir.exists()
            assert count >= 140

    def test_get_profile_summary(self, connector):
        """Test getting profile summary statistics."""
        summary = connector.get_profile_summary()

        assert 'total' in summary
        assert 'by_category' in summary
        assert summary['total'] >= 140
        assert isinstance(summary['by_category'], dict)
        assert len(summary['by_category']) > 0


class TestProfileLoader:
    """Test ProfileLoader class."""

    @pytest.fixture
    def loader(self):
        """Create loader with templates directory."""
        templates_dir = Path(__file__).parent.parent / "templates" / "industries"
        return ProfileLoader(templates_dir)

    def test_init_default_path(self):
        """Test initialization with default path."""
        # This may fail if templates not in expected location, so we skip if not found
        try:
            loader = ProfileLoader()
            assert loader.templates_dir.exists()
        except FileNotFoundError:
            pytest.skip("Default templates directory not found")

    def test_init_custom_path(self, loader):
        """Test initialization with custom path."""
        assert loader.templates_dir.exists()

    def test_init_invalid_path(self):
        """Test initialization with invalid path."""
        with pytest.raises(FileNotFoundError):
            ProfileLoader("/invalid/path")

    def test_list_available(self, loader):
        """Test listing available profiles."""
        profiles = loader.list_available()

        assert isinstance(profiles, list)
        assert len(profiles) >= 140
        assert all(isinstance(p, str) for p in profiles)

        # Should be sorted
        assert profiles == sorted(profiles)

    def test_load_profile_exists(self, loader):
        """Test loading existing profile."""
        # Get first available profile
        profiles = loader.list_available()
        if profiles:
            profile = loader.load_profile(profiles[0])

            assert profile is not None
            assert isinstance(profile, IndustryProfile)
            assert profile.id
            assert profile.name
            assert profile.naics_code
            assert profile.category
            assert isinstance(profile.keywords, list)

    def test_load_profile_nonexistent(self, loader):
        """Test loading nonexistent profile."""
        profile = loader.load_profile("nonexistent-profile-xyz")
        assert profile is None

    def test_search_by_name(self, loader):
        """Test searching profiles by name."""
        results = loader.search("restaurant")

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(p, IndustryProfile) for p in results)

    def test_search_by_category(self, loader):
        """Test searching profiles by category."""
        results = loader.search("healthcare")

        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_by_keyword(self, loader):
        """Test searching profiles by keyword."""
        results = loader.search("dental")

        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_case_insensitive(self, loader):
        """Test search is case insensitive."""
        results_lower = loader.search("healthcare")
        results_upper = loader.search("HEALTHCARE")

        assert len(results_lower) == len(results_upper)

    def test_search_no_results(self, loader):
        """Test search with no results."""
        results = loader.search("xyznonexistentquery123")
        assert results == []

    def test_get_by_category(self, loader):
        """Test getting profiles by category."""
        # Get summary to find a valid category
        summary = loader.get_summary()
        categories = list(summary['by_category'].keys())

        if categories:
            category = categories[0]
            results = loader.get_by_category(category)

            assert isinstance(results, list)
            assert len(results) > 0
            assert all(p.category.lower() == category.lower() for p in results)

    def test_get_by_category_nonexistent(self, loader):
        """Test getting profiles by nonexistent category."""
        results = loader.get_by_category("NonexistentCategory123")
        assert results == []

    def test_get_summary(self, loader):
        """Test getting summary statistics."""
        summary = loader.get_summary()

        assert 'total' in summary
        assert 'full_profiles' in summary
        assert 'basic_profiles' in summary
        assert 'by_category' in summary

        assert summary['total'] >= 140
        assert summary['full_profiles'] + summary['basic_profiles'] == summary['total']
        assert isinstance(summary['by_category'], dict)

    def test_profile_to_dict(self, loader):
        """Test converting profile to dictionary."""
        profiles = loader.list_available()
        if profiles:
            profile = loader.load_profile(profiles[0])

            data = profile.to_dict()

            assert isinstance(data, dict)
            assert 'id' in data
            assert 'name' in data
            assert 'naics_code' in data
            assert 'category' in data
            assert 'keywords' in data


class TestIndustryProfile:
    """Test IndustryProfile dataclass."""

    def test_create_basic_profile(self):
        """Test creating basic profile."""
        profile = IndustryProfile(
            id="test",
            name="Test Industry",
            naics_code="123456",
            category="Test",
            keywords=["test", "industry"]
        )

        assert profile.id == "test"
        assert profile.name == "Test Industry"
        assert profile.naics_code == "123456"
        assert profile.category == "Test"
        assert profile.keywords == ["test", "industry"]
        assert profile.has_full_profile is False

    def test_create_full_profile(self):
        """Test creating full profile with all fields."""
        profile = IndustryProfile(
            id="test",
            name="Test Industry",
            naics_code="123456",
            category="Test",
            keywords=["test"],
            power_words=["amazing", "best"],
            avoid_words=["bad", "worst"],
            content_themes=["theme1", "theme2"],
            psychology_profile={"triggers": ["trust"]},
            has_full_profile=True
        )

        assert profile.power_words == ["amazing", "best"]
        assert profile.avoid_words == ["bad", "worst"]
        assert profile.content_themes == ["theme1", "theme2"]
        assert profile.psychology_profile == {"triggers": ["trust"]}
        assert profile.has_full_profile is True

    def test_to_dict_basic(self):
        """Test converting basic profile to dict."""
        profile = IndustryProfile(
            id="test",
            name="Test",
            naics_code="123",
            category="Test",
            keywords=["test"]
        )

        data = profile.to_dict()

        assert data['id'] == "test"
        assert data['name'] == "Test"
        assert 'power_words' not in data  # Optional field should not be in dict

    def test_to_dict_full(self):
        """Test converting full profile to dict."""
        profile = IndustryProfile(
            id="test",
            name="Test",
            naics_code="123",
            category="Test",
            keywords=["test"],
            power_words=["great"],
            psychology_profile={"trust": "high"}
        )

        data = profile.to_dict()

        assert 'power_words' in data
        assert data['power_words'] == ["great"]
        assert 'psychology_profile' in data


class TestNAICSEntry:
    """Test NAICSEntry dataclass."""

    def test_create_entry(self):
        """Test creating NAICS entry."""
        entry = NAICSEntry(
            naics_code="123456",
            display_name="Test Industry",
            category="Test",
            keywords=["test", "industry"],
            has_full_profile=True,
            popularity=100
        )

        assert entry.naics_code == "123456"
        assert entry.display_name == "Test Industry"
        assert entry.category == "Test"
        assert entry.keywords == ["test", "industry"]
        assert entry.has_full_profile is True
        assert entry.popularity == 100

    def test_entry_to_dict(self):
        """Test converting entry to dict."""
        entry = NAICSEntry(
            naics_code="123456",
            display_name="Test Industry",
            category="Test",
            keywords=["test"],
            has_full_profile=True
        )

        data = entry.to_dict()

        assert data['naics_code'] == "123456"
        assert data['display_name'] == "Test Industry"
        assert data['has_full_profile'] is True


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_end_to_end_export_and_load(self):
        """Test full workflow: export from Synapse, then load profiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Export from Synapse
            synapse_path = "/Users/byronhudson/Projects/Synapse/src/data/"
            connector = SynapseConnector(synapse_path)
            count = connector.export_to_yaml(output_dir)

            assert count >= 140

            # Load with ProfileLoader
            loader = ProfileLoader(output_dir)
            profiles = loader.list_available()

            assert len(profiles) == count

            # Load a specific profile
            if profiles:
                profile = loader.load_profile(profiles[0])
                assert profile is not None

    def test_search_across_all_profiles(self):
        """Test searching across all exported profiles."""
        loader = ProfileLoader()

        # Search for common term
        results = loader.search("service")

        assert len(results) > 0

        # Verify all results contain the search term
        for profile in results:
            found = False
            if "service" in profile.name.lower():
                found = True
            elif "service" in profile.category.lower():
                found = True
            else:
                for keyword in profile.keywords:
                    if "service" in keyword.lower():
                        found = True
                        break

            assert found, f"Profile {profile.name} doesn't contain 'service'"

    def test_category_coverage(self):
        """Test that all major categories are represented."""
        loader = ProfileLoader()
        summary = loader.get_summary()

        # Should have multiple categories
        assert len(summary['by_category']) >= 5

        # Check for major categories
        categories = [c.lower() for c in summary['by_category'].keys()]
        assert any('healthcare' in c for c in categories)
        assert any('technology' in c or 'tech' in c for c in categories)


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=core.design_system", "--cov-report=term-missing"])
