"""
Synapse Database Connector - Connect to Synapse Supabase DB for industry profiles

Uses Supabase client to fetch industry profiles directly from the database.
Credentials should be loaded from Synapse .env file.
"""

from typing import Optional, List, Dict
import os
from pathlib import Path


class SynapseDBConnector:
    """
    Connect to Synapse Supabase database for industry profiles

    Fetches industry data from the live Supabase database used by Synapse.
    Credentials are loaded from environment variables or Synapse .env file.
    """

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize connector with Supabase credentials

        Args:
            supabase_url: Supabase project URL (or set SUPABASE_URL env var)
            supabase_key: Supabase service role key (or set SUPABASE_SERVICE_ROLE_KEY env var)
        """
        # Try to load from environment first
        self.url = supabase_url or os.getenv('SUPABASE_URL')
        self.key = supabase_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        # If not in environment, try to load from Synapse .env file
        if not self.url or not self.key:
            synapse_env = Path.home() / 'Projects' / 'Synapse' / '.env'
            if synapse_env.exists():
                self._load_from_env_file(synapse_env)

        if not self.url or not self.key:
            raise ValueError(
                "Synapse credentials not found. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment "
                "or ensure /Users/byronhudson/Projects/Synapse/.env exists"
            )

        # Lazy import supabase to avoid dependency issues
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(self.url, self.key)
        except ImportError:
            raise ImportError(
                "supabase-py not installed. Install with: pip install supabase"
            )

    def _load_from_env_file(self, env_path: Path):
        """Load credentials from .env file"""
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('SUPABASE_URL='):
                        self.url = line.split('=', 1)[1].strip()
                    elif line.startswith('SUPABASE_SERVICE_ROLE_KEY='):
                        self.key = line.split('=', 1)[1].strip()
        except Exception as e:
            print(f"Warning: Could not load from {env_path}: {e}")

    def get_industry_profile(self, industry_name: str) -> Optional[Dict]:
        """
        Fetch industry profile from Synapse database

        Args:
            industry_name: Industry name (e.g., "Healthcare", "E-commerce")

        Returns:
            Industry profile with design data, or None if not found
        """
        try:
            # Try exact match first
            result = self.client.table('industry_profiles')\
                .select('*')\
                .eq('industry_name', industry_name)\
                .limit(1)\
                .execute()

            if result.data:
                return self._transform_to_br3_format(result.data[0])

            # Try case-insensitive search
            result = self.client.table('industry_profiles')\
                .select('*')\
                .ilike('industry_name', industry_name)\
                .limit(1)\
                .execute()

            if result.data:
                return self._transform_to_br3_format(result.data[0])

            return None

        except Exception as e:
            print(f"Error fetching {industry_name} from Synapse: {e}")
            return None

    def list_all_industries(self) -> List[str]:
        """
        Get list of all available industries

        Returns:
            Sorted list of industry names
        """
        try:
            result = self.client.table('industry_profiles')\
                .select('industry_name')\
                .execute()

            industries = [row['industry_name'] for row in result.data]
            return sorted(industries)

        except Exception as e:
            print(f"Error listing industries: {e}")
            return []

    def search_industries(self, query: str) -> List[str]:
        """
        Search industries by keyword

        Args:
            query: Search term

        Returns:
            List of matching industry names
        """
        try:
            result = self.client.table('industry_profiles')\
                .select('industry_name')\
                .ilike('industry_name', f'%{query}%')\
                .execute()

            return [row['industry_name'] for row in result.data]

        except Exception as e:
            print(f"Error searching industries: {e}")
            return []

    def get_profile_count(self) -> int:
        """Get total number of industry profiles"""
        try:
            result = self.client.table('industry_profiles')\
                .select('id', count='exact')\
                .execute()

            return result.count or 0

        except Exception as e:
            print(f"Error counting profiles: {e}")
            return 0

    def _transform_to_br3_format(self, synapse_data: Dict) -> Dict:
        """
        Transform Synapse industry profile to BR3 design system format

        Maps Synapse database fields to BR3-compatible structure:
        - psychology_data → design_psychology
        - design_patterns → ui_patterns
        - color_psychology → color_scheme
        - typography_rules → typography
        """
        return {
            'industry': synapse_data.get('industry_name'),
            'naics_code': synapse_data.get('naics_code'),
            'category': synapse_data.get('category'),

            # Design & psychology
            'design_psychology': synapse_data.get('psychology_data', {}),
            'ui_patterns': synapse_data.get('design_patterns', {}),
            'color_scheme': synapse_data.get('color_psychology', {}),
            'typography': synapse_data.get('typography_rules', {}),

            # Content
            'power_words': synapse_data.get('power_words', []),
            'avoid_words': synapse_data.get('avoid_words', []),
            'content_themes': synapse_data.get('content_themes', []),

            # Target audience
            'target_audience': synapse_data.get('target_demographics', {}),
            'audience_characteristics': synapse_data.get('audience_characteristics', []),

            # Trust & conversion
            'trust_signals': synapse_data.get('trust_factors', []),
            'trust_builders': synapse_data.get('trust_builders', []),
            'conversion_patterns': synapse_data.get('conversion_psychology', {}),
            'buying_triggers': synapse_data.get('common_buying_triggers', []),

            # Pain points & benefits
            'pain_points': synapse_data.get('common_pain_points', []),

            # Metadata
            'source': 'synapse_db',
            'synapse_id': synapse_data.get('id'),
            'has_full_profile': True
        }


def main():
    """Test Synapse DB connector"""
    import sys
    import json

    print("=" * 70)
    print("Synapse Database Connector Test")
    print("=" * 70)
    print()

    try:
        connector = SynapseDBConnector()
        print(f"✅ Connected to Synapse database")
        print(f"📊 Total profiles: {connector.get_profile_count()}")
        print()

        # List all industries
        print("Fetching all industries...")
        industries = connector.list_all_industries()
        print(f"✅ Found {len(industries)} industries")
        print()

        # Show first 10
        print("First 10 industries:")
        for i, industry in enumerate(industries[:10], 1):
            print(f"  {i:2d}. {industry}")
        print()

        # Test search
        print("Testing search for 'health'...")
        results = connector.search_industries('health')
        print(f"✅ Found {len(results)} matches:")
        for industry in results:
            print(f"  • {industry}")
        print()

        # Test fetching a profile
        if industries:
            test_industry = industries[0]
            print(f"Fetching profile for '{test_industry}'...")
            profile = connector.get_industry_profile(test_industry)

            if profile:
                print(f"✅ Successfully fetched profile")
                print(f"\nProfile data:")
                print(json.dumps(profile, indent=2))
            else:
                print(f"⚠️  Profile data not available")

        print()
        print("=" * 70)
        print("✅ Test completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
