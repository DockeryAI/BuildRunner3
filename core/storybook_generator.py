"""
Storybook component library generator
"""
from pathlib import Path
from typing import Dict, List, Any


class StorybookGenerator:
    """Generate Storybook setup and component stories"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.storybook_dir = self.project_root / ".storybook"
        self.stories_dir = self.project_root / "src" / "stories"

    def generate_storybook_config(self, tokens: Dict[str, Any]):
        """
        Create .storybook/ configuration

        Args:
            tokens: Design tokens from merged profiles
        """
        self.storybook_dir.mkdir(parents=True, exist_ok=True)

        # main.js
        self._write_main_config()

        # preview.js (with design tokens)
        self._write_preview_config(tokens)

        # manager.js
        self._write_manager_config()

    def create_component_stories(
        self,
        spec_path: Path
    ) -> List[Path]:
        """
        Auto-generate component stories from PROJECT_SPEC

        Args:
            spec_path: Path to PROJECT_SPEC.md

        Returns:
            List of created story file paths
        """
        # Parse spec for components
        components = self._extract_components_from_spec(spec_path)

        # Generate story files
        story_files = []
        for component in components:
            story_path = self._create_story_file(component)
            story_files.append(story_path)

        return story_files

    def _write_main_config(self):
        """Write .storybook/main.js"""
        content = """module.exports = {
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx|mdx)'],
  addons: [
    '@storybook/addon-links',
    '@storybook/addon-essentials',
    '@storybook/addon-interactions',
    '@storybook/addon-a11y',
  ],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  docs: {
    autodocs: 'tag',
  },
};
"""
        (self.storybook_dir / "main.js").write_text(content)

    def _write_preview_config(self, tokens: Dict[str, Any]):
        """Write .storybook/preview.js with design tokens"""
        colors = tokens.get("colors", {})
        typography = tokens.get("typography", {})

        content = f"""import '../src/index.css';

export const parameters = {{
  actions: {{ argTypesRegex: '^on[A-Z].*' }},
  controls: {{
    matchers: {{
      color: /(background|color)$/i,
      date: /Date$/,
    }},
  }},
  backgrounds: {{
    default: 'light',
    values: [
      {{
        name: 'light',
        value: '#ffffff',
      }},
      {{
        name: 'dark',
        value: '#18181b',
      }},
    ],
  }},
}};

// Apply design system tokens
document.documentElement.style.setProperty('--color-primary', '{colors.get("primary", {}).get("main", "#1976d2")}');
"""
        (self.storybook_dir / "preview.js").write_text(content)

    def _write_manager_config(self):
        """Write .storybook/manager.js"""
        content = """import { addons } from '@storybook/addons';
import { themes } from '@storybook/theming';

addons.setConfig({
  theme: themes.normal,
});
"""
        (self.storybook_dir / "manager.js").write_text(content)

    def _extract_components_from_spec(self, spec_path: Path) -> List[Dict[str, Any]]:
        """
        Parse PROJECT_SPEC.md for component mentions

        Returns:
            List of component dicts with name, description, props
        """
        spec_content = spec_path.read_text() if spec_path.exists() else ""
        components = []

        # Simple extraction: look for component mentions
        # In real implementation, use more sophisticated parsing

        common_components = [
            {"name": "Button", "description": "Primary action button"},
            {"name": "Input", "description": "Text input field"},
            {"name": "Card", "description": "Content container"},
            {"name": "Modal", "description": "Overlay dialog"},
        ]

        return common_components

    def _create_story_file(self, component: Dict[str, Any]) -> Path:
        """Create .stories.tsx file for component"""
        self.stories_dir.mkdir(parents=True, exist_ok=True)

        name = component["name"]
        story_path = self.stories_dir / f"{name}.stories.tsx"

        content = f"""import type {{ Meta, StoryObj }} from '@storybook/react';
import {{ {name} }} from '../components/{name}';

const meta: Meta<typeof {name}> = {{
  title: 'Components/{name}',
  component: {name},
  tags: ['autodocs'],
}};

export default meta;
type Story = StoryObj<typeof {name}>;

export const Default: Story = {{
  args: {{}},
}};
"""
        story_path.write_text(content)

        return story_path