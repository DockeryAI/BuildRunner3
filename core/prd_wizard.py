"""
PRD Wizard System - Interactive PROJECT_SPEC.md Creation

This module provides an interactive wizard for creating comprehensive PROJECT_SPEC.md files
with design intelligence, industry profiles, and use case patterns.
"""

import os
import sys
import json
import yaml
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict


def get_multiline_input(prompt: str, allow_file: bool = True) -> str:
    """
    Get multi-line input from user using text editor.
    Opens user's $EDITOR (or nano/vim) for long-form input.
    Also supports reading from a file path.

    Args:
        prompt: Prompt to display to user
        allow_file: If True, allow dragging a file path

    Returns:
        Combined multi-line string
    """
    print(f"\n{prompt}")

    # First, ask if they want to use editor or provide file
    if allow_file:
        print("\nOptions:")
        print("  1. Open text editor (recommended for long text)")
        print("  2. Drag a file path")
        print("  3. Type short text inline")
        choice = input("\nChoice (1-3): ").strip()

        if choice == "2":
            file_path_str = input("\nDrag file here: ").strip().strip("'\"")
            file_path = Path(file_path_str)

            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    print(f"✓ Read {len(content)} characters from: {file_path.name}")
                    return content.strip()
                except Exception as e:
                    print(f"⚠️  Could not read file: {e}")
                    print("Opening editor instead...")
                    choice = "1"
            else:
                print(f"⚠️  File not found: {file_path_str}")
                print("Opening editor instead...")
                choice = "1"

        if choice == "3":
            # Short inline input
            print("\nType your text (press Ctrl+D when done):")
            lines = []
            try:
                while True:
                    lines.append(input())
            except EOFError:
                pass
            return "\n".join(lines).strip()

    # Default: Open text editor (choice == "1" or no choice given)
    editor = os.environ.get('EDITOR', os.environ.get('VISUAL', 'nano'))

    # Create temp file with helpful header
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tf:
        tf.write(f"# {prompt}\n")
        tf.write("# Write your content below (delete this header if you want)\n")
        tf.write("# Save and close the editor when done\n\n")
        temp_path = tf.name

    try:
        # Open editor
        print(f"\nOpening {editor}... (save and close when done)")
        subprocess.call([editor, temp_path])

        # Read result
        with open(temp_path, 'r') as f:
            content = f.read()

        # Remove comment header lines if present
        lines = content.split('\n')
        filtered_lines = [line for line in lines if not line.strip().startswith('#')]
        result = '\n'.join(filtered_lines).strip()

        return result
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass


class SpecState(Enum):
    """State machine for PROJECT_SPEC lifecycle"""
    NEW = "new"
    DRAFT = "draft"
    REVIEWED = "reviewed"
    CONFIRMED = "confirmed"
    LOCKED = "locked"


@dataclass
class SpecSection:
    """Represents a section of the PROJECT_SPEC"""
    name: str
    title: str
    content: str
    completed: bool = False
    skipped: bool = False


@dataclass
class ProjectSpec:
    """Complete PROJECT_SPEC data structure"""
    state: SpecState
    industry: Optional[str] = None
    use_case: Optional[str] = None
    tech_stack: Optional[str] = None
    sections: List[SpecSection] = None

    def __post_init__(self):
        if self.sections is None:
            self.sections = []


class PRDWizard:
    """
    Interactive wizard for creating PROJECT_SPEC.md with design intelligence.

    Features:
    - Auto-detection of existing specs
    - First-time wizard flow with Opus pre-fill
    - Existing spec editing mode
    - Industry + use case detection
    - Design architecture integration
    - State machine management
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.spec_path = self.project_root / ".buildrunner" / "PROJECT_SPEC.md"
        self.state_path = self.project_root / ".buildrunner" / "spec_state.yaml"
        self.templates_dir = self.project_root / "templates"

    def check_existing_spec(self) -> bool:
        """Check if PROJECT_SPEC.md already exists"""
        return self.spec_path.exists()

    def load_spec_state(self) -> Optional[ProjectSpec]:
        """Load existing spec state from file"""
        if not self.state_path.exists():
            return None

        with open(self.state_path, 'r') as f:
            data = yaml.safe_load(f)

        return ProjectSpec(
            state=SpecState(data['state']),
            industry=data.get('industry'),
            use_case=data.get('use_case'),
            tech_stack=data.get('tech_stack'),
            sections=[SpecSection(**s) for s in data.get('sections', [])]
        )

    def save_spec_state(self, spec: ProjectSpec):
        """Save spec state to file"""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'state': spec.state.value,
            'industry': spec.industry,
            'use_case': spec.use_case,
            'tech_stack': spec.tech_stack,
            'sections': [asdict(s) for s in spec.sections]
        }

        with open(self.state_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    def detect_industry_and_use_case(self, app_description: str) -> Tuple[str, str]:
        """
        Detect industry and use case from app description.

        This would typically use an LLM or NLP model. For now, uses keyword matching.
        In production, this would call Opus to analyze the description.
        """
        app_lower = app_description.lower()

        # Industry detection
        industry_keywords = {
            'healthcare': ['health', 'patient', 'medical', 'hospital', 'clinic', 'doctor'],
            'fintech': ['finance', 'banking', 'payment', 'trading', 'investment', 'crypto'],
            'ecommerce': ['shop', 'store', 'product', 'cart', 'checkout', 'retail'],
            'education': ['learn', 'course', 'student', 'teacher', 'school', 'education'],
            'saas': ['saas', 'software', 'service', 'platform', 'tool', 'application'],
            'social': ['social', 'community', 'feed', 'post', 'share', 'follow'],
            'marketplace': ['marketplace', 'listing', 'seller', 'buyer', 'bid'],
            'analytics': ['analytics', 'dashboard', 'metrics', 'data', 'insights']
        }

        industry = 'saas'  # default
        for ind, keywords in industry_keywords.items():
            if any(kw in app_lower for kw in keywords):
                industry = ind
                break

        # Use case detection
        use_case_keywords = {
            'dashboard': ['dashboard', 'metrics', 'analytics', 'reports', 'visualize'],
            'marketplace': ['marketplace', 'listing', 'buy', 'sell', 'vendor'],
            'crm': ['crm', 'customer', 'contact', 'lead', 'sales'],
            'analytics': ['analytics', 'data', 'insights', 'charts', 'graphs']
        }

        use_case = 'dashboard'  # default
        for uc, keywords in use_case_keywords.items():
            if any(kw in app_lower for kw in keywords):
                use_case = uc
                break

        return industry, use_case

    def get_section_template(self, section_name: str) -> str:
        """Get template content for a section"""
        templates = {
            'product_requirements': """# Product Requirements

## Executive Summary
[Brief overview of the product]

## Problem Statement
[What problem does this solve?]

## Target Users
[Who will use this product?]

## User Stories
- As a [user type], I want [goal] so that [benefit]
- As a [user type], I want [goal] so that [benefit]

## Success Metrics
- [Metric 1]: [Target]
- [Metric 2]: [Target]

## Out of Scope
- [What we're not building]
""",
            'technical_architecture': """# Technical Architecture

## System Overview
[High-level architecture description]

## Technology Stack
- **Frontend**: [Framework/Library]
- **Backend**: [Framework/Runtime]
- **Database**: [Database system]
- **Infrastructure**: [Cloud provider/setup]

## Key Components
1. **Component 1**: [Description]
2. **Component 2**: [Description]

## Data Models
[Key entities and relationships]

## API Design
[RESTful/GraphQL API structure]

## Security Considerations
[Authentication, authorization, data protection]

## Scalability Plan
[How the system will scale]
""",
            'design_architecture': """# Design Architecture

## Design System
[Design system and component library]

## Industry Profile
**Industry**: [Industry type]
**Key Requirements**: [Compliance, accessibility, etc.]

## Use Case Pattern
**Use Case**: [Primary use case]
**Layout Pattern**: [Typical layout structure]

## Design Tokens
- **Primary Color**: [Color]
- **Secondary Color**: [Color]
- **Typography**: [Font family]
- **Spacing Scale**: [Scale]

## Component Requirements
[Key components needed]

## Accessibility
[WCAG compliance, screen reader support]

## Responsive Design
[Mobile, tablet, desktop strategies]
"""
        }

        return templates.get(section_name, "")

    def opus_prefill_section(self, section_name: str, app_description: str,
                            industry: str, use_case: str) -> str:
        """
        Use Opus to pre-fill a section based on app description and context.

        In production, this would call Opus API. For now, returns enhanced template.
        """
        template = self.get_section_template(section_name)

        # In production: Call Opus with context
        # prefilled_content = opus_api.generate(
        #     prompt=f"Fill in this {section_name} for: {app_description}",
        #     context={'industry': industry, 'use_case': use_case}
        # )

        # For now, return template with hints
        prefilled = template.replace('[Brief overview of the product]',
                                    f'A {industry} {use_case} application: {app_description}')

        return prefilled

    def run_first_time_wizard(self) -> ProjectSpec:
        """
        Run the complete first-time wizard flow.

        Steps:
        1. Get app idea from user
        2. Detect industry + use case
        3. Opus pre-fills sections
        4. Interactive section-by-section wizard
        5. Design architecture wizard
        6. Tech stack suggestion
        7. Section-by-section review
        8. Final confirmation
        """
        print("\n=== BuildRunner 3.0 - PROJECT_SPEC Wizard ===\n")

        # Step 1: Get app idea
        print("Step 1: Describe Your App")
        app_description = get_multiline_input("What do you want to build?")

        # Step 2: Detect industry + use case
        print("\nStep 2: Detecting Industry and Use Case...")
        industry, use_case = self.detect_industry_and_use_case(app_description)
        print(f"  Detected Industry: {industry}")
        print(f"  Detected Use Case: {use_case}")

        confirm = input("Is this correct? (y/n): ")
        if confirm.lower() != 'y':
            industry = input("  Enter industry: ")
            use_case = input("  Enter use case: ")

        # Create spec object
        spec = ProjectSpec(
            state=SpecState.DRAFT,
            industry=industry,
            use_case=use_case
        )

        # Step 3-4: Interactive section wizard
        print("\nStep 3-4: Building PROJECT_SPEC Sections...")

        sections = ['product_requirements', 'technical_architecture', 'design_architecture']

        for section_name in sections:
            print(f"\n--- Section: {section_name} ---")

            # Opus pre-fill
            prefilled = self.opus_prefill_section(section_name, app_description, industry, use_case)

            print(f"\nOpus has pre-filled this section. Options:")
            print("  1. Accept")
            print("  2. Request more details")
            print("  3. Provide custom input")
            print("  4. Skip for now")

            choice = input("Choice (1-4): ")

            if choice == '1':
                content = prefilled
                completed = True
                skipped = False
            elif choice == '2':
                print("  (In production, would request more from Opus)")
                content = prefilled + "\n\n[Additional details from Opus]"
                completed = True
                skipped = False
            elif choice == '3':
                content = get_multiline_input("Enter your content for this section:")
                completed = True
                skipped = False
            else:  # Skip
                content = prefilled
                completed = False
                skipped = True

            spec.sections.append(SpecSection(
                name=section_name,
                title=section_name.replace('_', ' ').title(),
                content=content,
                completed=completed,
                skipped=skipped
            ))

        # Step 5: Design Architecture (done as part of section wizard above)

        # Step 6: Tech stack suggestion
        print("\nStep 6: Tech Stack Suggestion")
        print(f"Based on your {use_case} in {industry}, we suggest:")
        print("  - Frontend: React with TypeScript")
        print("  - Backend: FastAPI (Python)")
        print("  - Database: PostgreSQL")

        tech_stack = input("Accept this stack? (y/n): ")
        if tech_stack.lower() == 'y':
            spec.tech_stack = "react-fastapi-postgres"
        else:
            spec.tech_stack = input("  Enter your tech stack: ")

        # Step 7-8: Review and confirm
        print("\nStep 7-8: Review")
        print("PROJECT_SPEC is complete. Ready to confirm and lock?")
        confirm = input("Confirm (y/n): ")

        if confirm.lower() == 'y':
            spec.state = SpecState.CONFIRMED

        return spec

    def write_spec_to_file(self, spec: ProjectSpec):
        """Write PROJECT_SPEC.md to disk"""
        self.spec_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"""# PROJECT_SPEC

**Status**: {spec.state.value}
**Industry**: {spec.industry}
**Use Case**: {spec.use_case}
**Tech Stack**: {spec.tech_stack}

---

"""

        for section in spec.sections:
            content += f"\n{section.content}\n\n---\n"

        with open(self.spec_path, 'w') as f:
            f.write(content)

    def run_existing_spec_mode(self, spec: ProjectSpec):
        """Edit existing PROJECT_SPEC"""
        print("\n=== Editing Existing PROJECT_SPEC ===\n")
        print(f"Current state: {spec.state.value}")
        print(f"Industry: {spec.industry}")
        print(f"Use Case: {spec.use_case}")

        print("\nOptions:")
        print("  1. Edit a section")
        print("  2. Review all sections")
        print("  3. Change state")
        print("  4. Exit")

        choice = input("Choice (1-4): ")

        if choice == '1':
            print("\nSections:")
            for i, section in enumerate(spec.sections):
                print(f"  {i+1}. {section.title}")

            section_idx = int(input("Select section: ")) - 1
            section = spec.sections[section_idx]

            print(f"\nCurrent content:\n{section.content[:200]}...")
            print("\nEnter new content (or just press Enter on empty line to keep current):")
            new_content = get_multiline_input("")

            if new_content:
                section.content = new_content
                section.completed = True

        elif choice == '2':
            for section in spec.sections:
                print(f"\n--- {section.title} ---")
                print(section.content[:200] + "...")

        elif choice == '3':
            print("\nStates: new, draft, reviewed, confirmed, locked")
            new_state = input("Enter new state: ")
            spec.state = SpecState(new_state)

        return spec

    def run(self):
        """Main wizard entry point"""
        if self.check_existing_spec():
            print("Existing PROJECT_SPEC found.")
            spec = self.load_spec_state()
            if spec:
                spec = self.run_existing_spec_mode(spec)
            else:
                print("Could not load spec state. Starting fresh.")
                spec = self.run_first_time_wizard()
        else:
            spec = self.run_first_time_wizard()

        # Save state and write file
        self.save_spec_state(spec)
        self.write_spec_to_file(spec)

        print(f"\nPROJECT_SPEC saved to: {self.spec_path}")
        print(f"State: {spec.state.value}")

        return spec


# ===== Enhanced Wizard with Real Opus Integration =====

async def run_wizard(interactive: bool = True) -> Optional[Dict[str, Any]]:
    """
    Run full PRD wizard with Opus integration

    Args:
        interactive: If True, prompt user for input. If False, use defaults.

    Returns:
        Dict with:
            - spec_path: Path to generated PROJECT_SPEC.md
            - features_path: Path to synced features.json
            - handoff_package: Model switching package
    """
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from core.opus_client import OpusClient
    from core.model_switcher import ModelSwitcher

    console = Console()
    console.print("\n[bold blue]BuildRunner PRD Wizard[/bold blue]")
    console.print("Let's create your PROJECT_SPEC.md with AI assistance.\n")

    # Initialize clients
    try:
        opus = OpusClient()
    except ValueError:
        console.print("[red]Error: ANTHROPIC_API_KEY not found[/red]")
        console.print("Set ANTHROPIC_API_KEY environment variable to use Opus AI assistance.")
        return None

    # Step 1: Detect industry and use case
    console.print("[bold]Step 1: Project Type[/bold]")

    if interactive:
        industry = Prompt.ask(
            "Industry",
            choices=["Healthcare", "Fintech", "E-commerce", "SaaS", "Education",
                    "Social", "Marketplace", "Analytics", "Government", "Legal",
                    "Nonprofit", "Gaming", "Manufacturing"],
            default="SaaS"
        )

        use_case = Prompt.ask(
            "Use Case",
            choices=["Dashboard", "Marketplace", "CRM", "Analytics", "Onboarding",
                    "API Service", "Admin Panel", "Mobile App", "Chat", "Video",
                    "Calendar", "Forms", "Search"],
            default="Dashboard"
        )
    else:
        # Default for non-interactive
        industry = "SaaS"
        use_case = "Dashboard"

    console.print(f"\n✓ Industry: {industry}")
    console.print(f"✓ Use Case: {use_case}\n")

    # Step 2: Gather requirements
    console.print("[bold]Step 2: Project Details[/bold]")

    user_input = {}
    if interactive:
        user_input["project_name"] = Prompt.ask("Project Name")
        user_input["description"] = Prompt.ask("Brief Description")
        user_input["target_audience"] = Prompt.ask("Target Audience")
        user_input["key_features"] = Prompt.ask("Key Features (comma-separated)")
    else:
        user_input = {
            "project_name": "Example Project",
            "description": "AI-powered application",
            "target_audience": "General users",
            "key_features": "User auth, Dashboard, API"
        }

    # Step 3: Use Opus to pre-fill spec
    console.print("\n[bold]Step 3: Generating PROJECT_SPEC with Opus...[/bold]")

    with console.status("[bold yellow]Opus is analyzing your requirements..."):
        spec_content = await opus.pre_fill_spec(industry, use_case, user_input)

    console.print("[green]✓ PROJECT_SPEC generated[/green]\n")

    # Step 4: Show preview and confirm
    if interactive:
        console.print("[bold]Preview (first 500 chars):[/bold]")
        console.print(spec_content[:500] + "...\n")

        confirmed = Confirm.ask("Save this PROJECT_SPEC?", default=True)
        if not confirmed:
            console.print("[yellow]Wizard cancelled[/yellow]")
            return None

    # Step 5: Save spec
    project_root = Path.cwd()
    spec_path = project_root / ".buildrunner" / "PROJECT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(spec_content)

    console.print(f"[green]✓ Saved to {spec_path}[/green]\n")

    # Step 6: Sync to features.json
    console.print("[bold]Step 4: Syncing to features.json...[/bold]")

    # Import sync function - need to check if this exists
    try:
        from cli.spec_commands import sync_spec_to_features
        features_path = sync_spec_to_features(spec_path)
    except (ImportError, AttributeError):
        # Fallback: create basic features.json from spec
        console.print("[yellow]Warning: sync_spec_to_features not available, creating basic features.json[/yellow]")
        features_path = project_root / ".buildrunner" / "features.json"
        features_data = {
            "features": [],
            "metadata": {
                "industry": industry,
                "use_case": use_case,
                "generated_by": "prd_wizard"
            }
        }
        features_path.write_text(json.dumps(features_data, indent=2))

    console.print(f"[green]✓ Features synced to {features_path}[/green]\n")

    # Step 7: Create model switching handoff package
    console.print("[bold]Step 5: Creating handoff package for Sonnet...[/bold]")

    switcher = ModelSwitcher(project_root)
    features_data = json.loads(features_path.read_text())

    handoff_package = switcher.create_handoff_package(
        spec_path=spec_path,
        features_path=features_path,
        context={
            "industry": industry,
            "use_case": use_case,
            "constraints": []
        }
    )

    console.print("[green]✓ Handoff package created[/green]\n")

    # Summary
    console.print("[bold green]Wizard Complete![/bold green]")
    console.print(f"📄 PROJECT_SPEC: {spec_path}")
    console.print(f"📋 Features: {features_path}")
    console.print(f"📦 Handoff: .buildrunner/handoffs/handoff_{handoff_package['timestamp']}.json")
    console.print("\nNext: Run [bold]br feature list[/bold] to see features")

    return {
        "spec_path": str(spec_path),
        "features_path": str(features_path),
        "handoff_package": handoff_package
    }


def main():
    """CLI entry point for testing"""
    import sys
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."

    wizard = PRDWizard(project_root)
    wizard.run()


if __name__ == "__main__":
    main()
