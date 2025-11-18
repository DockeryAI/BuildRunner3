"""
Profile Loader - Load industry profiles from YAML templates

Provides access to 140+ industry profiles exported from Synapse.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class IndustryProfile:
    """Industry profile with psychology and content guidance."""

    id: str
    name: str
    naics_code: str
    category: str
    keywords: List[str]

    # Optional rich profile data
    power_words: Optional[List[str]] = None
    avoid_words: Optional[List[str]] = None
    content_themes: Optional[List[str]] = None
    common_pain_points: Optional[List[str]] = None
    common_buying_triggers: Optional[List[str]] = None
    trust_builders: Optional[List[str]] = None
    audience_characteristics: Optional[List[str]] = None
    psychology_profile: Optional[Dict] = None

    # Metadata
    has_full_profile: bool = False
    source: str = 'yaml'

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = {
            'id': self.id,
            'name': self.name,
            'naics_code': self.naics_code,
            'category': self.category,
            'keywords': self.keywords,
            'has_full_profile': self.has_full_profile,
            'source': self.source
        }

        # Add optional fields if present
        if self.power_words:
            data['power_words'] = self.power_words
        if self.avoid_words:
            data['avoid_words'] = self.avoid_words
        if self.content_themes:
            data['content_themes'] = self.content_themes
        if self.common_pain_points:
            data['common_pain_points'] = self.common_pain_points
        if self.common_buying_triggers:
            data['common_buying_triggers'] = self.common_buying_triggers
        if self.trust_builders:
            data['trust_builders'] = self.trust_builders
        if self.audience_characteristics:
            data['audience_characteristics'] = self.audience_characteristics
        if self.psychology_profile:
            data['psychology_profile'] = self.psychology_profile

        return data


class ProfileLoader:
    """
    Load and manage industry profiles from YAML templates.

    Provides access to 140+ industry profiles with psychology profiles,
    power words, content themes, and buying triggers.
    """

    def __init__(self, templates_dir: str | Path = None):
        """
        Initialize profile loader.

        Args:
            templates_dir: Path to templates directory. If None, uses default.
        """
        if templates_dir is None:
            # Default to templates/industries/ relative to this file
            templates_dir = Path(__file__).parent.parent.parent / "templates" / "industries"

        self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")

    def load_profile(self, industry_id: str) -> Optional[IndustryProfile]:
        """
        Load industry profile by ID.

        Args:
            industry_id: Industry ID (e.g., 'restaurant', 'msp')

        Returns:
            IndustryProfile object, or None if not found
        """
        profile_file = self.templates_dir / f"{industry_id}.yaml"

        if not profile_file.exists():
            return None

        with open(profile_file, 'r') as f:
            data = yaml.safe_load(f)

        return IndustryProfile(
            id=data.get('id', industry_id),
            name=data.get('name', industry_id.replace('-', ' ').title()),
            naics_code=data.get('naics_code', ''),
            category=data.get('category', 'Unknown'),
            keywords=data.get('keywords', []),
            power_words=data.get('power_words'),
            avoid_words=data.get('avoid_words'),
            content_themes=data.get('content_themes'),
            common_pain_points=data.get('common_pain_points'),
            common_buying_triggers=data.get('common_buying_triggers'),
            trust_builders=data.get('trust_builders'),
            audience_characteristics=data.get('audience_characteristics'),
            psychology_profile=data.get('psychology_profile'),
            has_full_profile=data.get('has_full_profile', True),
            source=data.get('source', 'yaml')
        )

    def list_available(self) -> List[str]:
        """
        List all available industry profile IDs.

        Returns:
            Sorted list of industry IDs
        """
        profile_files = list(self.templates_dir.glob("*.yaml"))
        industry_ids = [f.stem for f in profile_files]
        return sorted(industry_ids)

    def search(self, query: str) -> List[IndustryProfile]:
        """
        Search for profiles matching query.

        Searches in industry name, category, and keywords.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching IndustryProfile objects
        """
        query_lower = query.lower()
        results = []

        for industry_id in self.list_available():
            profile = self.load_profile(industry_id)

            if not profile:
                continue

            # Search in name
            if query_lower in profile.name.lower():
                results.append(profile)
                continue

            # Search in category
            if query_lower in profile.category.lower():
                results.append(profile)
                continue

            # Search in keywords
            for keyword in profile.keywords:
                if query_lower in keyword.lower():
                    results.append(profile)
                    break

        return results

    def get_by_category(self, category: str) -> List[IndustryProfile]:
        """
        Get all profiles in a category.

        Args:
            category: Category name (e.g., 'Healthcare', 'Technology')

        Returns:
            List of IndustryProfile objects in category
        """
        results = []

        for industry_id in self.list_available():
            profile = self.load_profile(industry_id)

            if profile and profile.category.lower() == category.lower():
                results.append(profile)

        return results

    def get_summary(self) -> Dict[str, int]:
        """
        Get summary statistics of available profiles.

        Returns:
            Dictionary with counts by category
        """
        category_counts = {}
        full_profile_count = 0

        for industry_id in self.list_available():
            profile = self.load_profile(industry_id)

            if not profile:
                continue

            # Count by category
            category_counts[profile.category] = category_counts.get(profile.category, 0) + 1

            # Count full profiles
            if profile.has_full_profile:
                full_profile_count += 1

        return {
            'total': len(self.list_available()),
            'full_profiles': full_profile_count,
            'basic_profiles': len(self.list_available()) - full_profile_count,
            'by_category': category_counts
        }


def main():
    """Demo: Load and display profiles."""
    print("=" * 70)
    print("Industry Profile Loader")
    print("=" * 70)
    print()

    loader = ProfileLoader()

    # Show summary
    summary = loader.get_summary()
    print(f"📊 Total profiles: {summary['total']}")
    print(f"   Full profiles: {summary['full_profiles']}")
    print(f"   Basic profiles: {summary['basic_profiles']}")
    print()

    print("By category:")
    for category, count in sorted(summary['by_category'].items(), key=lambda x: -x[1]):
        print(f"  {category:30s} {count:3d} profiles")
    print()

    # Load and show restaurant profile
    print("=" * 70)
    print("Example: Restaurant Profile")
    print("=" * 70)
    print()

    restaurant = loader.load_profile('restaurant')
    if restaurant:
        print(f"ID: {restaurant.id}")
        print(f"Name: {restaurant.name}")
        print(f"Category: {restaurant.category}")
        print(f"NAICS: {restaurant.naics_code}")
        print()

        if restaurant.power_words:
            print(f"Power Words ({len(restaurant.power_words)}): {', '.join(restaurant.power_words[:10])}...")

        if restaurant.content_themes:
            print(f"\nContent Themes:")
            for theme in restaurant.content_themes[:5]:
                print(f"  • {theme}")

        if restaurant.psychology_profile:
            print(f"\nPsychology Profile:")
            print(f"  Primary Triggers: {', '.join(restaurant.psychology_profile.get('primary_triggers', []))}")
            print(f"  Urgency Level: {restaurant.psychology_profile.get('urgency_level', 'N/A')}")

    # Search example
    print()
    print("=" * 70)
    print("Search: 'dental'")
    print("=" * 70)
    print()

    results = loader.search('dental')
    print(f"Found {len(results)} matches:")
    for profile in results[:5]:
        print(f"  • {profile.name} ({profile.category})")


if __name__ == "__main__":
    main()
