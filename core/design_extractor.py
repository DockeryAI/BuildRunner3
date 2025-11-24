"""Design Style Extractor - Extract and adopt project design patterns

Automatically extracts:
- CSS variables, colors, fonts, spacing
- UI framework (React, Vue, Tailwind, etc.)
- Component patterns and naming conventions
- Design system tokens
- Typography, shadows, borders, transitions

Stores design guide in .buildrunner/design-system.json for AI to reference
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import re
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class DesignTokens:
    """Extracted design tokens from codebase"""

    # Colors
    colors: Dict[str, str] = field(default_factory=dict)
    color_palette: List[str] = field(default_factory=list)

    # Typography
    fonts: Dict[str, str] = field(default_factory=dict)
    font_sizes: Dict[str, str] = field(default_factory=dict)
    font_weights: Dict[str, str] = field(default_factory=dict)
    line_heights: Dict[str, str] = field(default_factory=dict)

    # Spacing
    spacing: Dict[str, str] = field(default_factory=dict)
    padding: Dict[str, str] = field(default_factory=dict)
    margin: Dict[str, str] = field(default_factory=dict)

    # Layout
    borders: Dict[str, str] = field(default_factory=dict)
    border_radius: Dict[str, str] = field(default_factory=dict)
    shadows: Dict[str, str] = field(default_factory=dict)

    # Animation
    transitions: Dict[str, str] = field(default_factory=dict)
    animations: Dict[str, str] = field(default_factory=dict)

    # Breakpoints
    breakpoints: Dict[str, str] = field(default_factory=dict)

    # Z-index
    z_index: Dict[str, str] = field(default_factory=dict)


@dataclass
class ComponentPattern:
    """Detected component pattern"""
    name: str
    type: str  # 'button', 'card', 'modal', etc.
    file_path: str
    naming_convention: str  # 'PascalCase', 'kebab-case', etc.
    props_pattern: Optional[str] = None
    styling_method: Optional[str] = None  # 'css-modules', 'styled-components', 'tailwind', etc.


@dataclass
class UIFramework:
    """Detected UI framework"""
    name: str  # 'React', 'Vue', 'Angular', 'Svelte'
    version: Optional[str] = None
    ui_library: Optional[str] = None  # 'Material-UI', 'Chakra', 'Ant Design', etc.
    styling_system: Optional[str] = None  # 'Tailwind', 'CSS Modules', 'Styled Components', etc.


@dataclass
class DesignSystem:
    """Complete design system extracted from project"""
    framework: Optional[UIFramework] = None
    tokens: DesignTokens = field(default_factory=DesignTokens)
    components: List[ComponentPattern] = field(default_factory=list)
    naming_conventions: Dict[str, str] = field(default_factory=dict)
    file_structure: Dict[str, str] = field(default_factory=dict)
    design_system_file: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            'framework': asdict(self.framework) if self.framework else None,
            'tokens': asdict(self.tokens),
            'components': [asdict(c) for c in self.components],
            'naming_conventions': self.naming_conventions,
            'file_structure': self.file_structure,
            'design_system_file': self.design_system_file,
            'confidence': self.confidence
        }


class DesignExtractor:
    """Extract design patterns from existing codebase"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.design_system = DesignSystem()

    def extract(self) -> DesignSystem:
        """Run full design extraction"""
        logger.info(f"Extracting design system from {self.project_root}")

        # 1. Detect UI framework
        self.design_system.framework = self._detect_framework()

        # 2. Extract design tokens from CSS files
        self._extract_css_tokens()

        # 3. Extract Tailwind config if present
        self._extract_tailwind_config()

        # 4. Extract component patterns
        self._extract_component_patterns()

        # 5. Detect naming conventions
        self._detect_naming_conventions()

        # 6. Find design system files
        self._find_design_system_files()

        # 7. Calculate confidence score
        self.design_system.confidence = self._calculate_confidence()

        logger.info(f"Design extraction complete. Confidence: {self.design_system.confidence:.0%}")
        return self.design_system

    def _detect_framework(self) -> Optional[UIFramework]:
        """Detect UI framework from package.json"""
        package_json_paths = [
            self.project_root / "package.json",
            self.project_root / "ui" / "package.json",
            self.project_root / "frontend" / "package.json",
            self.project_root / "client" / "package.json",
        ]

        for pkg_path in package_json_paths:
            if pkg_path.exists():
                try:
                    with open(pkg_path) as f:
                        pkg = json.load(f)

                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

                    # Detect framework
                    framework_name = None
                    version = None

                    if 'react' in deps:
                        framework_name = 'React'
                        version = deps['react']
                    elif 'vue' in deps:
                        framework_name = 'Vue'
                        version = deps['vue']
                    elif '@angular/core' in deps:
                        framework_name = 'Angular'
                        version = deps['@angular/core']
                    elif 'svelte' in deps:
                        framework_name = 'Svelte'
                        version = deps['svelte']

                    # Detect UI library
                    ui_library = None
                    if '@mui/material' in deps or '@material-ui/core' in deps:
                        ui_library = 'Material-UI'
                    elif '@chakra-ui/react' in deps:
                        ui_library = 'Chakra UI'
                    elif 'antd' in deps:
                        ui_library = 'Ant Design'
                    elif '@headlessui/react' in deps:
                        ui_library = 'Headless UI'
                    elif '@radix-ui/react-dialog' in deps:
                        ui_library = 'Radix UI'

                    # Detect styling system
                    styling_system = None
                    if 'tailwindcss' in deps:
                        styling_system = 'Tailwind CSS'
                    elif 'styled-components' in deps:
                        styling_system = 'Styled Components'
                    elif '@emotion/react' in deps or '@emotion/styled' in deps:
                        styling_system = 'Emotion'
                    elif 'sass' in deps or 'node-sass' in deps:
                        styling_system = 'SASS/SCSS'

                    if framework_name:
                        logger.info(f"Detected {framework_name} {version}")
                        if ui_library:
                            logger.info(f"  UI Library: {ui_library}")
                        if styling_system:
                            logger.info(f"  Styling: {styling_system}")

                        return UIFramework(
                            name=framework_name,
                            version=version,
                            ui_library=ui_library,
                            styling_system=styling_system
                        )

                except Exception as e:
                    logger.warning(f"Error parsing {pkg_path}: {e}")

        return None

    def _extract_css_tokens(self):
        """Extract CSS variables and design tokens from CSS files"""
        css_files = list(self.project_root.glob("**/*.css"))
        css_files.extend(self.project_root.glob("**/*.scss"))

        # Limit to reasonable number of files
        css_files = css_files[:50]

        for css_file in css_files:
            # Skip node_modules and build directories
            if 'node_modules' in str(css_file) or 'dist' in str(css_file) or 'build' in str(css_file):
                continue

            try:
                content = css_file.read_text()

                # Extract CSS variables (--var-name: value)
                var_pattern = r'--([a-zA-Z0-9-]+):\s*([^;]+);'
                for match in re.finditer(var_pattern, content):
                    var_name, var_value = match.groups()
                    var_value = var_value.strip()

                    # Categorize by type
                    if 'color' in var_name or var_value.startswith('#') or var_value.startswith('rgb'):
                        self.design_system.tokens.colors[var_name] = var_value
                    elif 'font-size' in var_name or var_name.startswith('text-'):
                        self.design_system.tokens.font_sizes[var_name] = var_value
                    elif 'font-family' in var_name or 'font' in var_name:
                        self.design_system.tokens.fonts[var_name] = var_value
                    elif 'spacing' in var_name or 'space' in var_name:
                        self.design_system.tokens.spacing[var_name] = var_value
                    elif 'padding' in var_name:
                        self.design_system.tokens.padding[var_name] = var_value
                    elif 'margin' in var_name:
                        self.design_system.tokens.margin[var_name] = var_value
                    elif 'border-radius' in var_name or 'radius' in var_name:
                        self.design_system.tokens.border_radius[var_name] = var_value
                    elif 'shadow' in var_name:
                        self.design_system.tokens.shadows[var_name] = var_value
                    elif 'transition' in var_name:
                        self.design_system.tokens.transitions[var_name] = var_value
                    elif 'z-index' in var_name or 'z' == var_name[0]:
                        self.design_system.tokens.z_index[var_name] = var_value

                # Extract color hex values from file
                hex_colors = re.findall(r'#[0-9A-Fa-f]{3,8}', content)
                for color in hex_colors:
                    if color not in self.design_system.tokens.color_palette:
                        self.design_system.tokens.color_palette.append(color)

            except Exception as e:
                logger.debug(f"Error extracting from {css_file}: {e}")

        # Deduplicate color palette
        self.design_system.tokens.color_palette = list(set(self.design_system.tokens.color_palette))[:20]

        logger.info(f"Extracted {len(self.design_system.tokens.colors)} color tokens, "
                   f"{len(self.design_system.tokens.font_sizes)} font sizes")

    def _extract_tailwind_config(self):
        """Extract design tokens from Tailwind config"""
        config_files = [
            self.project_root / "tailwind.config.js",
            self.project_root / "tailwind.config.ts",
            self.project_root / "ui" / "tailwind.config.js",
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    content = config_file.read_text()

                    # Extract colors from extend or theme
                    color_pattern = r"colors:\s*{([^}]+)}"
                    color_matches = re.findall(color_pattern, content)
                    if color_matches:
                        for match in color_matches:
                            # Parse key-value pairs
                            pairs = re.findall(r"(\w+):\s*['\"]([^'\"]+)['\"]", match)
                            for key, value in pairs:
                                self.design_system.tokens.colors[f'tailwind-{key}'] = value

                    # Extract font families
                    font_pattern = r"fontFamily:\s*{([^}]+)}"
                    font_matches = re.findall(font_pattern, content)
                    if font_matches:
                        for match in font_matches:
                            pairs = re.findall(r"(\w+):\s*\[([^\]]+)\]", match)
                            for key, value in pairs:
                                self.design_system.tokens.fonts[f'font-{key}'] = value

                    logger.info(f"Extracted Tailwind config from {config_file}")
                    self.design_system.naming_conventions['styling'] = 'Tailwind utility classes'

                except Exception as e:
                    logger.debug(f"Error parsing Tailwind config: {e}")

    def _extract_component_patterns(self):
        """Extract component patterns from source files"""
        # Look for React/Vue components
        component_patterns = [
            "**/*.tsx",
            "**/*.jsx",
            "**/*.vue",
            "**/components/**/*.ts",
            "**/components/**/*.js"
        ]

        for pattern in component_patterns:
            for file_path in self.project_root.glob(pattern):
                # Skip node_modules
                if 'node_modules' in str(file_path):
                    continue

                try:
                    content = file_path.read_text()

                    # Detect component type from filename
                    component_name = file_path.stem
                    component_type = self._infer_component_type(component_name, content)

                    # Detect naming convention
                    naming_convention = self._detect_naming_convention(component_name)

                    # Detect styling method
                    styling_method = self._detect_styling_method(content, file_path)

                    self.design_system.components.append(ComponentPattern(
                        name=component_name,
                        type=component_type,
                        file_path=str(file_path.relative_to(self.project_root)),
                        naming_convention=naming_convention,
                        styling_method=styling_method
                    ))

                    # Stop after 50 components to avoid over-processing
                    if len(self.design_system.components) >= 50:
                        break

                except Exception as e:
                    logger.debug(f"Error extracting component from {file_path}: {e}")

            if len(self.design_system.components) >= 50:
                break

        logger.info(f"Extracted {len(self.design_system.components)} component patterns")

    def _infer_component_type(self, name: str, content: str) -> str:
        """Infer component type from name and content"""
        name_lower = name.lower()

        # Common component types
        if 'button' in name_lower:
            return 'button'
        elif 'card' in name_lower:
            return 'card'
        elif 'modal' in name_lower or 'dialog' in name_lower:
            return 'modal'
        elif 'input' in name_lower or 'field' in name_lower:
            return 'input'
        elif 'form' in name_lower:
            return 'form'
        elif 'nav' in name_lower or 'menu' in name_lower:
            return 'navigation'
        elif 'header' in name_lower:
            return 'header'
        elif 'footer' in name_lower:
            return 'footer'
        elif 'layout' in name_lower:
            return 'layout'
        elif 'sidebar' in name_lower:
            return 'sidebar'
        else:
            return 'component'

    def _detect_naming_convention(self, name: str) -> str:
        """Detect naming convention"""
        if name[0].isupper() and '_' not in name and '-' not in name:
            return 'PascalCase'
        elif name[0].islower() and '_' not in name and '-' not in name:
            return 'camelCase'
        elif '-' in name:
            return 'kebab-case'
        elif '_' in name:
            return 'snake_case'
        else:
            return 'unknown'

    def _detect_styling_method(self, content: str, file_path: Path) -> str:
        """Detect how component is styled"""
        # Check for companion CSS file
        css_path = file_path.with_suffix('.css')
        scss_path = file_path.with_suffix('.scss')
        module_path = file_path.parent / f"{file_path.stem}.module.css"

        if module_path.exists():
            return 'CSS Modules'
        elif css_path.exists() or scss_path.exists():
            return 'CSS/SCSS'
        elif 'styled-components' in content or 'styled.' in content:
            return 'Styled Components'
        elif '@emotion' in content or 'css`' in content:
            return 'Emotion'
        elif 'className=' in content and ('tw-' in content or 'bg-' in content or 'text-' in content):
            return 'Tailwind CSS'
        elif 'sx={{' in content or 'sx={' in content:
            return 'MUI sx prop'
        else:
            return 'unknown'

    def _detect_naming_conventions(self):
        """Analyze naming conventions across components"""
        if not self.design_system.components:
            return

        # Count conventions
        conventions = {}
        styling_methods = {}

        for comp in self.design_system.components:
            conventions[comp.naming_convention] = conventions.get(comp.naming_convention, 0) + 1
            if comp.styling_method:
                styling_methods[comp.styling_method] = styling_methods.get(comp.styling_method, 0) + 1

        # Most common convention
        if conventions:
            most_common = max(conventions.items(), key=lambda x: x[1])
            self.design_system.naming_conventions['component'] = most_common[0]

        if styling_methods:
            most_common_styling = max(styling_methods.items(), key=lambda x: x[1])
            self.design_system.naming_conventions['styling'] = most_common_styling[0]

    def _find_design_system_files(self):
        """Find design system or theme files"""
        design_files = [
            "design-system.ts",
            "design-system.js",
            "theme.ts",
            "theme.js",
            "tokens.ts",
            "tokens.js",
            "design-tokens.ts",
            "design-tokens.json",
            "theme.json"
        ]

        for design_file in design_files:
            matches = list(self.project_root.glob(f"**/{design_file}"))
            matches = [m for m in matches if 'node_modules' not in str(m)]

            if matches:
                self.design_system.design_system_file = str(matches[0].relative_to(self.project_root))
                logger.info(f"Found design system file: {self.design_system.design_system_file}")
                break

    def _calculate_confidence(self) -> float:
        """Calculate confidence score for design extraction"""
        score = 0.0
        max_score = 0.0

        # Framework detected (30 points)
        max_score += 30
        if self.design_system.framework:
            score += 30
            if self.design_system.framework.ui_library:
                score += 10
                max_score += 10
            if self.design_system.framework.styling_system:
                score += 10
                max_score += 10

        # Design tokens (30 points)
        max_score += 30
        if self.design_system.tokens.colors:
            score += 10
        if self.design_system.tokens.fonts:
            score += 5
        if self.design_system.tokens.font_sizes:
            score += 5
        if self.design_system.tokens.spacing or self.design_system.tokens.padding:
            score += 5
        if self.design_system.tokens.border_radius:
            score += 5

        # Components (20 points)
        max_score += 20
        if len(self.design_system.components) >= 5:
            score += 20
        elif len(self.design_system.components) > 0:
            score += 10

        # Naming conventions (10 points)
        max_score += 10
        if self.design_system.naming_conventions:
            score += 10

        # Design system file (10 points)
        max_score += 10
        if self.design_system.design_system_file:
            score += 10

        return score / max_score if max_score > 0 else 0.0

    def save(self, output_path: Optional[Path] = None):
        """Save design system to JSON file"""
        if output_path is None:
            output_path = self.project_root / ".buildrunner" / "design-system.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.design_system.to_dict(), f, indent=2)

        logger.info(f"Saved design system to {output_path}")
        return output_path

    @staticmethod
    def load(project_root: Path) -> Optional[DesignSystem]:
        """Load design system from JSON file"""
        design_file = project_root / ".buildrunner" / "design-system.json"

        if not design_file.exists():
            return None

        try:
            with open(design_file) as f:
                data = json.load(f)

            # Reconstruct design system
            design_system = DesignSystem()

            if data.get('framework'):
                design_system.framework = UIFramework(**data['framework'])

            if data.get('tokens'):
                design_system.tokens = DesignTokens(**data['tokens'])

            if data.get('components'):
                design_system.components = [ComponentPattern(**c) for c in data['components']]

            design_system.naming_conventions = data.get('naming_conventions', {})
            design_system.file_structure = data.get('file_structure', {})
            design_system.design_system_file = data.get('design_system_file')
            design_system.confidence = data.get('confidence', 0.0)

            return design_system

        except Exception as e:
            logger.error(f"Error loading design system: {e}")
            return None

    def generate_claude_instructions(self) -> str:
        """Generate Claude instructions for using this design system"""
        instructions = []

        instructions.append("# Design System & Style Guide")
        instructions.append("")
        instructions.append("**CRITICAL:** All UI components MUST match the existing design system.")
        instructions.append("")

        if self.design_system.framework:
            fw = self.design_system.framework
            instructions.append(f"## Framework: {fw.name}")
            if fw.ui_library:
                instructions.append(f"- **UI Library:** {fw.ui_library}")
            if fw.styling_system:
                instructions.append(f"- **Styling:** {fw.styling_system}")
            instructions.append("")

        if self.design_system.tokens.colors:
            instructions.append("## Color Palette")
            for name, value in list(self.design_system.tokens.colors.items())[:10]:
                instructions.append(f"- `{name}`: {value}")
            instructions.append("")

        if self.design_system.tokens.fonts or self.design_system.tokens.font_sizes:
            instructions.append("## Typography")
            if self.design_system.tokens.fonts:
                for name, value in list(self.design_system.tokens.fonts.items())[:5]:
                    instructions.append(f"- Font: `{name}`: {value}")
            if self.design_system.tokens.font_sizes:
                for name, value in list(self.design_system.tokens.font_sizes.items())[:5]:
                    instructions.append(f"- Size: `{name}`: {value}")
            instructions.append("")

        if self.design_system.naming_conventions:
            instructions.append("## Naming Conventions")
            for category, convention in self.design_system.naming_conventions.items():
                instructions.append(f"- {category.title()}: **{convention}**")
            instructions.append("")

        if self.design_system.components:
            instructions.append("## Component Patterns")
            instructions.append(f"- Total components analyzed: {len(self.design_system.components)}")

            # Show common styling method
            styling_counts = {}
            for comp in self.design_system.components:
                if comp.styling_method:
                    styling_counts[comp.styling_method] = styling_counts.get(comp.styling_method, 0) + 1

            if styling_counts:
                most_common = max(styling_counts.items(), key=lambda x: x[1])
                instructions.append(f"- Preferred styling: **{most_common[0]}**")

            instructions.append("")

        if self.design_system.design_system_file:
            instructions.append(f"## Design System File")
            instructions.append(f"- Reference: `{self.design_system.design_system_file}`")
            instructions.append("")

        instructions.append("## Rules for New Components")
        instructions.append("1. **Always** use existing color variables/tokens")
        instructions.append("2. **Always** match typography scale and fonts")
        instructions.append("3. **Always** follow naming conventions")
        instructions.append("4. **Always** use the same styling method as existing components")
        instructions.append("5. **Always** match spacing, borders, and shadows")
        instructions.append("6. Read design system file before creating new components")
        instructions.append("")
        instructions.append(f"_Design system confidence: {self.design_system.confidence:.0%}_")

        return "\n".join(instructions)
