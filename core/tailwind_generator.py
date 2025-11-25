"""
Tailwind 4 configuration generator for BuildRunner design system
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any


class TailwindGenerator:
    """Generate Tailwind 4 config from industry + use case profiles"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.templates_dir = self.project_root / "templates"

    def generate_tailwind_config(
        self, industry: str, use_case: str, output_path: Path = None
    ) -> Dict[str, Any]:
        """
        Generate complete Tailwind config from profiles

        Args:
            industry: Industry profile name
            use_case: Use case pattern name
            output_path: Where to write tailwind.config.js

        Returns:
            Tailwind config dict
        """
        # Load profiles
        industry_profile = self._load_profile("industries", industry)
        use_case_profile = self._load_profile("use_cases", use_case)

        # Merge profiles
        merged = self.merge_design_tokens(industry_profile, use_case_profile)

        # Generate Tailwind config
        config = self._build_tailwind_config(merged)

        # Write to file if path provided
        if output_path:
            self._write_config(config, output_path)

        return config

    def merge_design_tokens(
        self, industry: Dict[str, Any], use_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge industry and use case design tokens

        Industry takes precedence for colors, typography
        Use case takes precedence for layout, components

        Args:
            industry: Industry profile dict
            use_case: Use case profile dict

        Returns:
            Merged design tokens
        """
        merged = {
            "colors": industry.get("colors", {}),
            "typography": industry.get("typography", {}),
            "spacing": industry.get("spacing", use_case.get("spacing", {})),
            "borders": industry.get("borders", {}),
            "shadows": industry.get("shadows", {}),
            "breakpoints": industry.get("breakpoints", use_case.get("breakpoints", {})),
            "components": {**industry.get("components", {}), **use_case.get("components", {})},
            "layout": use_case.get("layout", {}),
            "patterns": use_case.get("patterns", []),
        }

        return merged

    def apply_css_variables(self, tokens: Dict[str, Any]) -> str:
        """
        Generate CSS custom properties from design tokens

        Args:
            tokens: Design tokens dict

        Returns:
            CSS string with :root variables
        """
        css_vars = [":root {"]

        # Colors
        if "colors" in tokens:
            css_vars.extend(self._colors_to_css_vars(tokens["colors"]))

        # Typography
        if "typography" in tokens:
            css_vars.extend(self._typography_to_css_vars(tokens["typography"]))

        # Spacing
        if "spacing" in tokens and "scale" in tokens["spacing"]:
            for i, value in enumerate(tokens["spacing"]["scale"]):
                css_vars.append(f"  --spacing-{i}: {value}px;")

        css_vars.append("}")

        return "\n".join(css_vars)

    def generate_theme_json(self, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate theme.json for Tailwind 4

        Args:
            tokens: Merged design tokens

        Returns:
            Theme JSON object
        """
        theme = {
            "colors": self._flatten_colors(tokens.get("colors", {})),
            "fontFamily": {
                "sans": [
                    tokens.get("typography", {}).get("fonts", {}).get("primary", "sans-serif")
                ],
                "serif": [tokens.get("typography", {}).get("fonts", {}).get("secondary", "serif")],
                "mono": [
                    tokens.get("typography", {}).get("fonts", {}).get("monospace", "monospace")
                ],
            },
            "fontSize": tokens.get("typography", {}).get("sizes", {}),
            "fontWeight": tokens.get("typography", {}).get("weights", {}),
            "lineHeight": tokens.get("typography", {}).get("lineHeights", {}),
            "spacing": self._spacing_to_scale(tokens.get("spacing", {})),
            "borderRadius": tokens.get("borders", {}).get("radius", {}),
            "boxShadow": tokens.get("shadows", {}),
            "screens": tokens.get("breakpoints", {}),
        }

        return theme

    def _load_profile(self, category: str, name: str) -> Dict[str, Any]:
        """Load YAML profile"""
        profile_path = self.templates_dir / category / f"{name}.yaml"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path, "r") as f:
            return yaml.safe_load(f)

    def _build_tailwind_config(self, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """Build complete Tailwind config object"""
        return {
            "content": ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
            "theme": self.generate_theme_json(tokens),
            "plugins": [],
        }

    def _write_config(self, config: Dict[str, Any], output_path: Path):
        """Write Tailwind config to JavaScript file"""
        js_content = f"""/** @type {{import('tailwindcss').Config}} */
module.exports = {json.dumps(config, indent=2)}
"""
        output_path.write_text(js_content)

    def _colors_to_css_vars(self, colors: Dict[str, Any], prefix: str = "color") -> List[str]:
        """Convert color dict to CSS variables"""
        vars = []
        for key, value in colors.items():
            if isinstance(value, dict):
                # Nested (e.g., primary.main)
                for sub_key, sub_value in value.items():
                    vars.append(f"  --{prefix}-{key}-{sub_key}: {sub_value};")
            else:
                # Flat
                vars.append(f"  --{prefix}-{key}: {value};")
        return vars

    def _typography_to_css_vars(self, typography: Dict[str, Any]) -> List[str]:
        """Convert typography to CSS variables"""
        vars = []
        if "fonts" in typography:
            for key, value in typography["fonts"].items():
                vars.append(f"  --font-{key}: {value};")
        if "sizes" in typography:
            for key, value in typography["sizes"].items():
                vars.append(f"  --text-{key}: {value};")
        return vars

    def _flatten_colors(self, colors: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested color structure for Tailwind"""
        flat = {}
        for key, value in colors.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[f"{key}-{sub_key}"] = sub_value
            else:
                flat[key] = value
        return flat

    def _spacing_to_scale(self, spacing: Dict[str, Any]) -> Dict[str, str]:
        """Convert spacing scale to Tailwind format"""
        if "scale" not in spacing:
            return {}

        scale = {}
        for i, value in enumerate(spacing["scale"]):
            scale[str(i)] = f"{value}px"

        return scale
