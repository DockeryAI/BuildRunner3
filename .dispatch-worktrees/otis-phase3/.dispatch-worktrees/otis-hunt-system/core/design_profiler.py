"""
Design Profiler - Industry + Use Case Profile Merger

Loads industry and use case design profiles and merges them with intelligent
conflict resolution to create a comprehensive project design profile.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class DesignProfile:
    """Complete design profile for a project"""

    industry: str
    use_case: str
    colors: Dict[str, str] = field(default_factory=dict)
    typography: Dict[str, Any] = field(default_factory=dict)
    spacing: Dict[str, str] = field(default_factory=dict)
    components: List[str] = field(default_factory=list)
    compliance_requirements: List[str] = field(default_factory=list)
    trust_signals: List[str] = field(default_factory=list)
    layout_patterns: List[str] = field(default_factory=list)
    navigation: Dict[str, Any] = field(default_factory=dict)
    data_viz_preferences: List[str] = field(default_factory=list)


class DesignProfiler:
    """
    Merge industry and use case design profiles with intelligent conflict resolution.

    Features:
    - Load industry profiles from templates/industries/
    - Load use case profiles from templates/use_cases/
    - Merge with conflict resolution (industry overrides use case)
    - Generate design tokens
    - Generate component requirements
    """

    def __init__(self, templates_dir: str):
        self.templates_dir = Path(templates_dir)
        self.industries_dir = self.templates_dir / "industries"
        self.use_cases_dir = self.templates_dir / "use_cases"

    def load_industry_profile(self, industry: str) -> Optional[Dict]:
        """Load industry design profile from YAML"""
        profile_path = self.industries_dir / f"{industry}.yaml"

        if not profile_path.exists():
            return None

        with open(profile_path, "r") as f:
            return yaml.safe_load(f)

    def load_use_case_profile(self, use_case: str) -> Optional[Dict]:
        """Load use case design profile from YAML"""
        profile_path = self.use_cases_dir / f"{use_case}.yaml"

        if not profile_path.exists():
            return None

        with open(profile_path, "r") as f:
            return yaml.safe_load(f)

    def _deep_merge_dict(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries, with override taking precedence"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    def merge_profiles(self, industry_profile: Dict, use_case_profile: Dict) -> DesignProfile:
        """
        Merge industry and use case profiles with conflict resolution.

        Conflict resolution strategy:
        - Industry profile takes precedence for compliance, trust, colors
        - Use case profile takes precedence for layout, navigation, data viz
        - Components and requirements are merged (union)
        """
        # Start with industry profile as base
        merged = DesignProfile(
            industry=industry_profile.get("name", "unknown"),
            use_case=use_case_profile.get("name", "unknown"),
        )

        # Colors: Industry first, use case fills in gaps (deep merge for nested structures)
        industry_colors = industry_profile.get("colors", {})
        use_case_colors = use_case_profile.get("colors", {})
        merged.colors = self._deep_merge_dict(
            use_case_colors, industry_colors
        )  # Industry overrides

        # Typography: Industry first (deep merge for nested structures)
        merged.typography = self._deep_merge_dict(
            use_case_profile.get("typography", {}), industry_profile.get("typography", {})
        )

        # Spacing: Use case provides defaults, industry can override
        merged.spacing = self._deep_merge_dict(
            use_case_profile.get("spacing", {}), industry_profile.get("spacing", {})
        )

        # Components: Handle both list and dict formats
        industry_components = industry_profile.get("components", [])
        use_case_components = use_case_profile.get("components", [])

        # Convert dict to list if needed (extract keys for component names)
        if isinstance(industry_components, dict):
            industry_components = list(industry_components.keys())
        if isinstance(use_case_components, dict):
            use_case_components = list(use_case_components.keys())

        merged.components = list(set(industry_components + use_case_components))

        # Compliance: Industry only (handle both list and dict formats)
        compliance = industry_profile.get("compliance", [])
        if isinstance(compliance, dict):
            compliance = compliance.get("standards", [])
        merged.compliance_requirements = compliance

        # Trust signals: Industry only
        merged.trust_signals = industry_profile.get("trust_signals", [])

        # Layout patterns: Use case provides
        merged.layout_patterns = use_case_profile.get("layout_patterns", [])

        # Navigation: Use case provides
        merged.navigation = use_case_profile.get("navigation", {})

        # Data viz: Use case provides
        merged.data_viz_preferences = use_case_profile.get("data_viz", [])

        return merged

    def generate_design_tokens(self, profile: DesignProfile) -> Dict[str, Any]:
        """
        Generate design tokens from merged profile.

        Outputs Tailwind-compatible token structure.
        """
        tokens = {"colors": {}, "typography": {}, "spacing": {}, "components": profile.components}

        # Color tokens
        for key, value in profile.colors.items():
            tokens["colors"][key] = value

        # Typography tokens
        tokens["typography"] = {
            "fontFamily": profile.typography.get("font_family", "Inter, sans-serif"),
            "fontSize": profile.typography.get(
                "scale",
                {
                    "xs": "0.75rem",
                    "sm": "0.875rem",
                    "base": "1rem",
                    "lg": "1.125rem",
                    "xl": "1.25rem",
                    "2xl": "1.5rem",
                    "3xl": "1.875rem",
                    "4xl": "2.25rem",
                },
            ),
            "fontWeight": profile.typography.get(
                "weights", {"normal": "400", "medium": "500", "semibold": "600", "bold": "700"}
            ),
        }

        # Spacing tokens
        tokens["spacing"] = profile.spacing

        return tokens

    def generate_tailwind_config(self, tokens: Dict[str, Any]) -> str:
        """Generate Tailwind config from design tokens"""
        config = f"""// tailwind.config.js - Generated by BuildRunner
module.exports = {{
  theme: {{
    extend: {{
      colors: {{
"""

        # Add colors
        for key, value in tokens["colors"].items():
            config += f"        '{key}': '{value}',\n"

        config += """      },
      fontFamily: {
"""

        # Add fonts
        font_family = tokens["typography"]["fontFamily"]
        config += f"        'sans': ['{font_family}'],\n"

        config += """      },
      fontSize: {
"""

        # Add font sizes
        for key, value in tokens["typography"]["fontSize"].items():
            config += f"        '{key}': '{value}',\n"

        config += """      },
      spacing: {
"""

        # Add spacing
        for key, value in tokens["spacing"].items():
            config += f"        '{key}': '{value}',\n"

        config += """      }
    }
  },
  plugins: []
}
"""

        return config

    def get_component_requirements(self, profile: DesignProfile) -> List[Dict[str, str]]:
        """Generate component requirements from profile"""
        requirements = []

        for component in profile.components:
            requirements.append(
                {
                    "component": component,
                    "description": f"{component} component required for {profile.use_case}",
                    "priority": "high" if component in ["Button", "Input", "Card"] else "medium",
                }
            )

        return requirements

    def generate_accessibility_checklist(self, profile: DesignProfile) -> List[str]:
        """Generate accessibility checklist based on compliance requirements"""
        checklist = [
            "Color contrast ratio ≥ 4.5:1 for normal text",
            "Color contrast ratio ≥ 3:1 for large text",
            "All interactive elements keyboard accessible",
            "Focus indicators visible",
            "Alt text for all images",
            "ARIA labels for complex components",
            "Semantic HTML structure",
            "Screen reader testing",
        ]

        # Add industry-specific requirements
        if "WCAG 2.1 AA" in profile.compliance_requirements:
            checklist.append("WCAG 2.1 AA compliance verified")
        if "ADA" in profile.compliance_requirements:
            checklist.append("ADA compliance verified")
        if "HIPAA" in profile.compliance_requirements:
            checklist.append("Secure data display (no PHI exposure)")

        return checklist

    def create_profile(self, industry: str, use_case: str) -> Optional[DesignProfile]:
        """
        Create complete design profile by merging industry and use case profiles.

        Returns:
            DesignProfile with all merged data, or None if profiles not found
        """
        industry_profile = self.load_industry_profile(industry)
        use_case_profile = self.load_use_case_profile(use_case)

        if not industry_profile or not use_case_profile:
            return None

        merged_profile = self.merge_profiles(industry_profile, use_case_profile)

        return merged_profile

    def export_profile(self, profile: DesignProfile, output_path: str):
        """Export merged profile to YAML"""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "industry": profile.industry,
            "use_case": profile.use_case,
            "colors": profile.colors,
            "typography": profile.typography,
            "spacing": profile.spacing,
            "components": profile.components,
            "compliance": profile.compliance_requirements,
            "trust_signals": profile.trust_signals,
            "layout_patterns": profile.layout_patterns,
            "navigation": profile.navigation,
            "data_viz": profile.data_viz_preferences,
        }

        with open(output, "w") as f:
            yaml.dump(data, f, default_flow_style=False)


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 4:
        print("Usage: python design_profiler.py <templates_dir> <industry> <use_case>")
        sys.exit(1)

    templates_dir = sys.argv[1]
    industry = sys.argv[2]
    use_case = sys.argv[3]

    profiler = DesignProfiler(templates_dir)
    profile = profiler.create_profile(industry, use_case)

    if profile:
        print(f"\nDesign Profile Created:")
        print(f"  Industry: {profile.industry}")
        print(f"  Use Case: {profile.use_case}")
        print(f"  Components: {len(profile.components)}")
        print(f"  Compliance: {', '.join(profile.compliance_requirements)}")

        # Generate tokens
        tokens = profiler.generate_design_tokens(profile)
        print(f"\nDesign Tokens Generated: {len(tokens['colors'])} colors")

        # Generate Tailwind config
        tailwind_config = profiler.generate_tailwind_config(tokens)
        print(f"\nTailwind Config: {len(tailwind_config)} characters")
    else:
        print(f"Could not load profiles for {industry} + {use_case}")


if __name__ == "__main__":
    main()
