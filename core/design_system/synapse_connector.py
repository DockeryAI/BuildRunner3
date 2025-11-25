"""
Synapse Connector - Connect to Synapse industry database

Parses TypeScript files from Synapse project to extract industry profiles
and export them to YAML format for BuildRunner.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import json


@dataclass
class NAICSEntry:
    """NAICS code entry from Synapse database."""

    naics_code: str
    display_name: str
    category: str
    keywords: List[str]
    has_full_profile: bool
    popularity: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "naics_code": self.naics_code,
            "display_name": self.display_name,
            "category": self.category,
            "keywords": self.keywords,
            "has_full_profile": self.has_full_profile,
            "popularity": self.popularity,
        }


class SynapseConnector:
    """
    Connect to Synapse industry database.

    Parses TypeScript files containing industry profiles and NAICS codes,
    extracting structured data for use in BuildRunner's design system.
    """

    def __init__(self, synapse_path: str | Path):
        """
        Initialize connector with path to Synapse data directory.

        Args:
            synapse_path: Path to Synapse/src/data/ directory
        """
        self.synapse_path = Path(synapse_path)
        self.naics_file = self.synapse_path / "complete-naics-codes.ts"
        self.industries_dir = self.synapse_path / "industries"

        # Validate paths exist
        if not self.synapse_path.exists():
            raise FileNotFoundError(f"Synapse path not found: {self.synapse_path}")
        if not self.naics_file.exists():
            raise FileNotFoundError(f"NAICS file not found: {self.naics_file}")

    def load_naics_codes(self) -> List[NAICSEntry]:
        """
        Parse complete-naics-codes.ts and extract all entries with has_full_profile: true.

        Returns:
            List of NAICSEntry objects with full profiles
        """
        print(f"📖 Reading NAICS codes from: {self.naics_file}")

        content = self.naics_file.read_text()

        # Extract the array content between COMPLETE_NAICS_CODES: NAICSOption[] = [ ... ];
        array_pattern = r"export const COMPLETE_NAICS_CODES:\s*NAICSOption\[\]\s*=\s*\[(.*?)\];"
        array_match = re.search(array_pattern, content, re.DOTALL)

        if not array_match:
            raise ValueError("Could not find COMPLETE_NAICS_CODES array in file")

        array_content = array_match.group(1)

        # Parse each object entry
        # Pattern handles has_full_profile before or after keywords, and negative popularity
        entry_pattern = r'\{\s*naics_code:\s*[\'"]([^\'"]+)[\'"]\s*,\s*display_name:\s*[\'"]([^\'"]+)[\'"]\s*,\s*category:\s*[\'"]([^\'"]+)[\'"]\s*,\s*(?:has_full_profile:\s*(true|false)\s*,\s*)?keywords:\s*\[(.*?)\](?:\s*,\s*has_full_profile:\s*(true|false))?(?:\s*,\s*popularity:\s*(-?\d+))?\s*\}'

        entries = []
        for match in re.finditer(entry_pattern, array_content, re.DOTALL):
            naics_code = match.group(1)
            display_name = match.group(2)
            category = match.group(3)
            has_full_profile_1 = match.group(4)  # has_full_profile before keywords
            keywords_str = match.group(5)
            has_full_profile_2 = match.group(6)  # has_full_profile after keywords
            popularity_str = match.group(7)

            # has_full_profile can be before or after keywords
            has_full_profile = (has_full_profile_1 == "true") or (has_full_profile_2 == "true")

            # Parse keywords array
            keywords = []
            for keyword in re.findall(r'[\'"]([^\'"]+)[\'"]', keywords_str):
                keywords.append(keyword)

            # Parse popularity
            popularity = int(popularity_str) if popularity_str else None

            entry = NAICSEntry(
                naics_code=naics_code,
                display_name=display_name,
                category=category,
                keywords=keywords,
                has_full_profile=has_full_profile,
                popularity=popularity,
            )

            entries.append(entry)

        # Filter only entries with full profiles
        full_profile_entries = [e for e in entries if e.has_full_profile]

        print(f"✅ Parsed {len(entries)} total entries")
        print(f"✅ Found {len(full_profile_entries)} entries with full profiles")

        return full_profile_entries

    def load_profile(self, industry_id: str) -> Optional[Dict]:
        """
        Load full profile from industries/*.profile.ts.

        Args:
            industry_id: Industry ID (e.g., 'restaurant', 'msp')

        Returns:
            Dictionary with profile data, or None if not found
        """
        profile_file = self.industries_dir / f"{industry_id}.profile.ts"

        if not profile_file.exists():
            return None

        content = profile_file.read_text()

        # Parse TypeScript profile object
        # Pattern: export const XxxProfile: IndustryProfile = { ... };
        profile_pattern = r"export const \w+Profile:\s*IndustryProfile\s*=\s*\{(.*?)\};"
        match = re.search(profile_pattern, content, re.DOTALL)

        if not match:
            return None

        profile_content = match.group(1)

        profile = {}

        # Extract id
        id_match = re.search(r'id:\s*[\'"]([^\'"]+)[\'"]', profile_content)
        if id_match:
            profile["id"] = id_match.group(1)

        # Extract name
        name_match = re.search(r'name:\s*[\'"]([^\'"]+)[\'"]', profile_content)
        if name_match:
            profile["name"] = name_match.group(1)

        # Extract naicsCode
        naics_match = re.search(r'naicsCode:\s*[\'"]([^\'"]+)[\'"]', profile_content)
        if naics_match:
            profile["naics_code"] = naics_match.group(1)

        # Extract arrays
        for array_name in [
            "powerWords",
            "avoidWords",
            "contentThemes",
            "commonPainPoints",
            "commonBuyingTriggers",
            "trustBuilders",
            "audienceCharacteristics",
        ]:
            array_pattern = f"{array_name}:\\s*\\[(.*?)\\]"
            array_match = re.search(array_pattern, profile_content, re.DOTALL)
            if array_match:
                items = re.findall(r'[\'"]([^\'"]+)[\'"]', array_match.group(1))
                snake_case_name = "".join(
                    ["_" + c.lower() if c.isupper() else c for c in array_name]
                ).lstrip("_")
                profile[snake_case_name] = items

        # Extract psychology profile
        psych_pattern = r"psychologyProfile:\s*\{(.*?)\}"
        psych_match = re.search(psych_pattern, profile_content, re.DOTALL)
        if psych_match:
            psych_content = psych_match.group(1)
            profile["psychology_profile"] = {}

            # Extract primary triggers
            triggers_match = re.search(r"primaryTriggers:\s*\[(.*?)\]", psych_content)
            if triggers_match:
                triggers = re.findall(r'[\'"]([^\'"]+)[\'"]', triggers_match.group(1))
                profile["psychology_profile"]["primary_triggers"] = triggers

            # Extract urgency level
            urgency_match = re.search(r'urgencyLevel:\s*[\'"]([^\'"]+)[\'"]', psych_content)
            if urgency_match:
                profile["psychology_profile"]["urgency_level"] = urgency_match.group(1)

            # Extract trust importance
            trust_match = re.search(r'trustImportance:\s*[\'"]([^\'"]+)[\'"]', psych_content)
            if trust_match:
                profile["psychology_profile"]["trust_importance"] = trust_match.group(1)

        return profile

    def export_to_yaml(self, output_dir: Path) -> int:
        """
        Export all profiles with has_full_profile: true to YAML files.

        Args:
            output_dir: Directory to export YAML files to (typically templates/industries/)

        Returns:
            Number of profiles exported
        """
        import yaml

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        entries = self.load_naics_codes()

        print(f"\n📦 Exporting {len(entries)} profiles to YAML...")

        exported = 0
        for entry in entries:
            # Create industry ID from display name (lowercase, replace spaces with -)
            industry_id = (
                entry.display_name.lower()
                .replace(" ", "-")
                .replace("/", "-")
                .replace("(", "")
                .replace(")", "")
                .replace("&", "and")
            )

            # Try to load full profile from TypeScript
            full_profile = self.load_profile(industry_id)

            if full_profile:
                # Use full profile
                yaml_data = full_profile
            else:
                # Create basic profile from NAICS data
                yaml_data = {
                    "id": industry_id,
                    "name": entry.display_name,
                    "naics_code": entry.naics_code,
                    "category": entry.category,
                    "keywords": entry.keywords,
                    "has_full_profile": False,  # Mark as basic profile
                    "source": "naics_only",
                }

            # Write to YAML file
            output_file = output_dir / f"{industry_id}.yaml"
            with open(output_file, "w") as f:
                yaml.dump(
                    yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
                )

            exported += 1

            if exported % 20 == 0:
                print(f"  Exported {exported}/{len(entries)}...")

        print(f"✅ Exported {exported} profiles to {output_dir}")
        return exported

    def get_profile_summary(self) -> Dict[str, int]:
        """
        Get summary statistics of the NAICS database.

        Returns:
            Dictionary with counts by category
        """
        entries = self.load_naics_codes()

        # Count by category
        category_counts = {}
        for entry in entries:
            category_counts[entry.category] = category_counts.get(entry.category, 0) + 1

        return {"total": len(entries), "by_category": category_counts}


def main():
    """Demo: Parse NAICS codes and show results."""
    import sys

    synapse_path = "/Users/byronhudson/Projects/Synapse/src/data/"

    print("=" * 70)
    print("Synapse NAICS Code Parser")
    print("=" * 70)
    print()

    try:
        connector = SynapseConnector(synapse_path)
        entries = connector.load_naics_codes()

        print()
        print("=" * 70)
        print(f"Summary: {len(entries)} industry profiles with full data")
        print("=" * 70)
        print()

        # Show first 10 entries
        print("First 10 entries:")
        print()
        for i, entry in enumerate(entries[:10], 1):
            print(f"{i:2d}. {entry.display_name:35s} ({entry.naics_code}) - {entry.category}")
            print(f"    Keywords: {', '.join(entry.keywords[:5])}")
            if entry.popularity:
                print(f"    Popularity: {entry.popularity}")
            print()

        # Show summary by category
        summary = connector.get_profile_summary()
        print()
        print("=" * 70)
        print("By Category:")
        print("=" * 70)
        for category, count in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
            print(f"  {category:30s} {count:3d} profiles")

        print()
        print("=" * 70)
        print(f"✅ Successfully parsed {summary['total']} industry profiles!")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
