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
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict

# OpusClient kept for backwards compatibility but not required
try:
    from core.opus_client import OpusClient, OpusAPIError

    OPUS_AVAILABLE = True
except ImportError:
    OPUS_AVAILABLE = False

from core.design_system.profile_loader import ProfileLoader, IndustryProfile


def conversational_input(prompt: str) -> str:
    """
    Conversational input that properly handles pastes.

    Shows clear instruction: type answer, hit Enter on empty line to finish.
    This prevents paste fragmentation.

    Args:
        prompt: Question to ask

    Returns:
        User's response (single or multi-line)
    """
    print(f"\n{prompt}")
    print("[dim](Type your answer, press Enter on empty line when done)[/dim]")

    lines = []

    while True:
        try:
            line = input()

            if not line.strip():
                # Empty line - end of input
                break

            lines.append(line)

        except EOFError:
            break

    result = "\n".join(lines).strip()
    return result if result else ""


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
                    content = file_path.read_text(encoding="utf-8")
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
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))

    # Create temp file with helpful header
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tf:
        tf.write(f"# {prompt}\n")
        tf.write("# Write your content below (delete this header if you want)\n")
        tf.write("# Save and close the editor when done\n\n")
        temp_path = tf.name

    try:
        # Open editor
        print(f"\nOpening {editor}... (save and close when done)")
        subprocess.call([editor, temp_path])

        # Read result
        with open(temp_path, "r") as f:
            content = f.read()

        # Remove comment header lines if present
        lines = content.split("\n")
        filtered_lines = [line for line in lines if not line.strip().startswith("#")]
        result = "\n".join(filtered_lines).strip()

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

        # Initialize Synapse profile loader
        try:
            self.profile_loader = ProfileLoader()
            print(
                f"[dim]✓ Loaded {len(self.profile_loader.list_available())} industry profiles[/dim]"
            )
        except Exception as e:
            print(f"[yellow]⚠️  Could not load industry profiles: {e}[/yellow]")
            self.profile_loader = None

        # Check if we should use Claude Code mode (default) or API mode
        api_key = os.getenv("ANTHROPIC_API_KEY")
        use_api_mode = os.getenv("BR_USE_API_MODE", "false").lower() == "true"

        if use_api_mode and api_key and OPUS_AVAILABLE:
            # API mode: Make external Opus calls (costs money)
            try:
                self.opus_client = OpusClient()
                self.use_opus_api = True
                self.use_claude_code = False
                print("\n[cyan]Using Opus API mode[/cyan]")
            except:
                self.use_opus_api = False
                self.use_claude_code = True
        else:
            # Claude Code mode: Generate prompts for user to send to their AI assistant (free)
            self.opus_client = None
            self.use_opus_api = False
            self.use_claude_code = True
            print("\n[cyan]🤖 Using Claude Code mode (interactive)[/cyan]")
            print("[dim]Wizard will generate prompts for you to send to Claude Code[/dim]\n")

    def check_existing_spec(self) -> bool:
        """Check if PROJECT_SPEC.md already exists"""
        return self.spec_path.exists()

    def load_spec_state(self) -> Optional[ProjectSpec]:
        """Load existing spec state from file"""
        if not self.state_path.exists():
            return None

        with open(self.state_path, "r") as f:
            data = yaml.safe_load(f)

        return ProjectSpec(
            state=SpecState(data["state"]),
            industry=data.get("industry"),
            use_case=data.get("use_case"),
            tech_stack=data.get("tech_stack"),
            sections=[SpecSection(**s) for s in data.get("sections", [])],
        )

    def save_spec_state(self, spec: ProjectSpec):
        """Save spec state to file"""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "state": spec.state.value,
            "industry": spec.industry,
            "use_case": spec.use_case,
            "tech_stack": spec.tech_stack,
            "sections": [asdict(s) for s in spec.sections],
        }

        with open(self.state_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def detect_industry_and_use_case(
        self, app_description: str
    ) -> Tuple[str, str, Optional[IndustryProfile]]:
        """
        Detect industry and use case from app description using Synapse database.

        Searches the 148+ industry profiles for matches, returns best match.
        If no match found in database, returns generic categories.

        Returns:
            Tuple of (industry_id, use_case, profile)
        """
        if not self.profile_loader:
            # Fallback to generic if profile loader not available
            return "saas", "dashboard", None

        app_lower = app_description.lower()

        # Search Synapse database
        print("\n🔍 Searching 148 industry profiles...")
        matches = self.profile_loader.search(app_description)

        if matches:
            # Show top 5 matches
            print(f"\n✓ Found {len(matches)} matching industries:\n")
            for i, profile in enumerate(matches[:5], 1):
                print(f"  {i}. {profile.name} ({profile.category})")
                if profile.keywords:
                    print(f"     Keywords: {', '.join(profile.keywords[:5])}")
                print()

            # Use best match
            best_match = matches[0]
            print(f"[cyan]→ Best match: {best_match.name}[/cyan]")

            # Detect use case from keywords
            use_case = self._detect_use_case(app_description)

            return best_match.id, use_case, best_match
        else:
            print("[yellow]⚠️  No exact match found in database[/yellow]")
            print(
                "[dim]You can manually select from available profiles or research new industry[/dim]"
            )

            # Fallback to generic detection
            use_case = self._detect_use_case(app_description)
            return "saas", use_case, None

    def _detect_use_case(self, app_description: str) -> str:
        """
        Detect use case pattern from app description.

        Args:
            app_description: App description text

        Returns:
            Use case identifier (dashboard, marketplace, crm, etc.)
        """
        app_lower = app_description.lower()

        use_case_keywords = {
            "dashboard": ["dashboard", "metrics", "analytics", "reports", "visualize", "insights"],
            "marketplace": ["marketplace", "listing", "buy", "sell", "vendor", "buyer", "seller"],
            "crm": ["crm", "customer", "contact", "lead", "sales", "pipeline"],
            "analytics": ["analytics", "data", "insights", "charts", "graphs", "statistics"],
            "ecommerce": ["shop", "store", "product", "cart", "checkout", "catalog"],
            "social": ["social", "community", "feed", "post", "share", "follow"],
            "saas-platform": ["platform", "tool", "service", "application", "software"],
        }

        for uc, keywords in use_case_keywords.items():
            if any(kw in app_lower for kw in keywords):
                return uc

        return "dashboard"  # default

    def get_section_template(self, section_name: str) -> str:
        """Get template content for a section"""
        templates = {
            "product_requirements": """# Product Requirements

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
            "technical_architecture": """# Technical Architecture

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
            "design_architecture": """# Design Architecture

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
""",
        }

        return templates.get(section_name, "")

    async def claude_code_discuss_section(
        self, section_name: str, app_description: str, industry: str, use_case: str
    ) -> str:
        """
        Claude Code mode: Generate prompt for user to send to their AI assistant.
        User copies prompt, sends to Claude Code, pastes response back.
        """
        print(f"\n{'='*70}")
        print(f"  Section: {section_name.replace('_', ' ').title()}")
        print(f"{'='*70}\n")

        # Generate comprehensive prompt
        prompt = f"""I'm building a PROJECT_SPEC for a {industry} {use_case} application.

My description:
{app_description}

For the "{section_name}" section, please:

1. **Extract** what I already mentioned that relates to {section_name}
   - List each item as a bullet with details
   - Be specific about what I said

2. **Suggest** 5-8 additional items I should consider
   - Format each as: [ID] Title: Description
   - Include concrete details and why it matters for {industry}
   - Make them actionable and valuable

3. **Format the response** as:
   ```
   ## From Your Description
   - Item 1: [what you mentioned]
   - Item 2: [what you mentioned]

   ## Additional Suggestions
   [1] Suggestion title: Brief description
       - Detail 1
       - Detail 2
       - Why this matters

   [2] Next suggestion...
   ```

Please be thorough and specific for this {industry} application."""

        # Save prompt to clipboard-friendly file
        prompt_file = self.project_root / ".buildrunner" / f"prompt_{section_name}.txt"
        prompt_file.write_text(prompt)

        print("[bold cyan]📋 SEND THIS TO CLAUDE CODE:[/bold cyan]\n")
        print(f"{'-'*70}")
        print(prompt)
        print(f"{'-'*70}\n")
        print(f"[dim]Prompt also saved to: {prompt_file}[/dim]\n")

        print("[yellow]Instructions:[/yellow]")
        print("  1. Copy the prompt above")
        print("  2. Send it to Claude Code")
        print("  3. Copy Claude's full response")
        print("  4. Paste it below\n")

        # Wait for user to paste Claude's response
        print("[cyan]Paste Claude Code's response below (press Ctrl+D when done):[/cyan]\n")

        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass

        claude_response = "\n".join(lines).strip()

        if not claude_response:
            print("\n[yellow]No response provided, using template...[/yellow]")
            return self.get_section_template(section_name)

        # Parse the response to extract suggestions
        print("\n[cyan]Which suggestions do you want to include?[/cyan]")
        print("Enter IDs (comma-separated), 'all', or 'none'")
        print("Example: 1,3,5\n")

        selection = input("Your selection: ").strip().lower()

        # Build final content
        final_content = f"# {section_name.replace('_', ' ').title()}\n\n"

        if selection == "all":
            final_content += claude_response
        elif selection == "none":
            # Only include "From Your Description" part
            if "## From Your Description" in claude_response:
                end_idx = claude_response.find("## Additional Suggestions")
                if end_idx > 0:
                    final_content += claude_response[:end_idx].strip()
                else:
                    final_content += claude_response
            else:
                final_content += claude_response
        else:
            # Parse and include only selected items
            selected_ids = [s.strip() for s in selection.split(",")]

            # Include "From Your Description" section
            if "## From Your Description" in claude_response:
                desc_start = claude_response.find("## From Your Description")
                desc_end = claude_response.find("## Additional Suggestions", desc_start)
                if desc_end > 0:
                    final_content += claude_response[desc_start:desc_end].strip() + "\n\n"
                else:
                    final_content += claude_response[desc_start:].strip() + "\n\n"

            # Add selected suggestions
            if "## Additional Suggestions" in claude_response:
                final_content += "## Additional Items\n\n"
                suggestions_start = claude_response.find("## Additional Suggestions")
                suggestions_text = claude_response[suggestions_start:]

                lines = suggestions_text.split("\n")
                current_suggestion = []
                include_current = False

                for line in lines:
                    if line.strip() and line.strip()[0] == "[":
                        # Save previous if selected
                        if include_current and current_suggestion:
                            final_content += "\n".join(current_suggestion) + "\n\n"

                        # Check if this ID is selected
                        suggestion_id = line.strip()[1:].split("]")[0]
                        include_current = suggestion_id in selected_ids
                        current_suggestion = [line] if include_current else []
                    elif include_current:
                        current_suggestion.append(line)

                # Add last suggestion
                if include_current and current_suggestion:
                    final_content += "\n".join(current_suggestion) + "\n\n"

        print(f"\n✓ Built {section_name} content")
        return final_content

    async def opus_discuss_section(
        self, section_name: str, app_description: str, industry: str, use_case: str
    ) -> str:
        """
        Interactive discussion with AI to build section content.

        Workflow:
        1. Extract what's in user's prompt for this section
        2. Generate additional suggestions
        3. Let user select which suggestions to include
        4. Build final content = extracted + selected
        """
        if self.use_claude_code:
            # Claude Code mode: Generate prompt for user to send to their AI
            return await self.claude_code_discuss_section(
                section_name, app_description, industry, use_case
            )
        elif not self.use_opus_api:
            # Fall back to template
            return self.get_section_template(section_name)

        print(f"\n🤖 Analyzing your description for {section_name}...")

        # Step 1: Extract what user already mentioned
        extract_prompt = f"""You're analyzing a project description for a {industry} {use_case} application.

App Description:
{app_description}

Extract ONLY what the user already mentioned that relates to the "{section_name}" section.
List each item as a bullet point with details.

Be specific and concrete. If they didn't mention anything for this section, say "Nothing specified yet."

Format as:
## What You Specified:
- Item 1: [details from their description]
- Item 2: [details from their description]
"""

        try:
            # Extract existing requirements
            message = await self.opus_client.async_client.messages.create(
                model=self.opus_client.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": extract_prompt}],
            )

            extracted = message.content[0].text
            print(f"\n✓ Extracted from your description:\n")
            print(extracted)
            print(f"\n{'-'*60}")

            # Step 2: Generate additional suggestions
            print(f"\n🤖 Generating additional suggestions...")

            suggest_prompt = f"""Based on this {industry} {use_case} application:

{app_description}

What they already specified for {section_name}:
{extracted}

Suggest 5-8 ADDITIONAL items they should consider for the "{section_name}" section.
Make them concrete, actionable, and valuable.

Format each suggestion as:
[ID] Title: Brief description
    - Specific detail 1
    - Specific detail 2
    - Why this matters for {industry}

Example:
[1] API Rate Limiting: Protect backend resources
    - Implement token bucket algorithm
    - 1000 requests/hour for free tier
    - Prevents abuse and ensures fair usage
"""

            message = await self.opus_client.async_client.messages.create(
                model=self.opus_client.model,
                max_tokens=3072,
                messages=[{"role": "user", "content": suggest_prompt}],
            )

            suggestions = message.content[0].text
            print(f"\n✓ Additional suggestions:\n")
            print(suggestions)

            # Step 3: Let user select which to include
            print(f"\n\n{'='*60}")
            print("Select suggestions to include:")
            print(f"{'='*60}")
            print("Enter the IDs of suggestions you want (comma-separated)")
            print("Examples: '1,3,5' or 'all' or 'none'")

            selection = input("\nYour selection: ").strip().lower()

            # Build final content
            final_content = f"# {section_name.replace('_', ' ').title()}\n\n"
            final_content += "## From Your Description\n\n"
            final_content += extracted.replace("## What You Specified:", "").strip()
            final_content += "\n\n"

            if selection != "none":
                final_content += "## Additional Items\n\n"

                if selection == "all":
                    final_content += suggestions
                else:
                    # Parse selected IDs
                    selected_ids = [s.strip() for s in selection.split(",")]

                    # Extract selected suggestions (simple line-based parsing)
                    lines = suggestions.split("\n")
                    current_suggestion = []
                    include_current = False

                    for line in lines:
                        # Check if line starts with [ID]
                        if line.strip() and line.strip()[0] == "[":
                            # Save previous suggestion if it was selected
                            if include_current and current_suggestion:
                                final_content += "\n".join(current_suggestion) + "\n\n"

                            # Check if this ID is selected
                            suggestion_id = line.strip()[1:].split("]")[0]
                            include_current = suggestion_id in selected_ids
                            current_suggestion = [line] if include_current else []
                        elif include_current:
                            current_suggestion.append(line)

                    # Add last suggestion if selected
                    if include_current and current_suggestion:
                        final_content += "\n".join(current_suggestion) + "\n\n"

            print(f"\n✓ Built {section_name} content")
            return final_content

        except OpusAPIError as e:
            print(f"\n⚠️  Opus API error: {e}")
            print("Falling back to template...")
            return self.get_section_template(section_name)
        except Exception as e:
            print(f"\n⚠️  Unexpected error: {e}")
            return self.get_section_template(section_name)

    def opus_prefill_section(
        self, section_name: str, app_description: str, industry: str, use_case: str
    ) -> str:
        """
        Wrapper to run async opus_discuss_section synchronously.
        """
        return asyncio.run(
            self.opus_discuss_section(section_name, app_description, industry, use_case)
        )

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

        # Step 2: Detect industry + use case from Synapse database
        print("\nStep 2: Detecting Industry and Use Case...")
        industry, use_case, industry_profile = self.detect_industry_and_use_case(app_description)
        print(f"  Detected Industry: {industry}")
        print(f"  Detected Use Case: {use_case}")

        confirm = input("\nIs this correct? (y/n): ")
        if confirm.lower() != "y":
            # Show available industries
            if self.profile_loader:
                available = self.profile_loader.list_available()
                print(f"\n[dim]Available industries ({len(available)}):[/dim]")
                for i, ind_id in enumerate(available[:20], 1):
                    print(f"  {ind_id}")
                print(f"  ... and {len(available) - 20} more")

            industry = input("\n  Enter industry ID: ")
            use_case = input("  Enter use case: ")

            # Try to load the profile they selected
            if self.profile_loader:
                industry_profile = self.profile_loader.load_profile(industry)

        # Create spec object
        spec = ProjectSpec(state=SpecState.DRAFT, industry=industry, use_case=use_case)

        # Step 3-4: Interactive section wizard
        print("\nStep 3-4: Building PROJECT_SPEC Sections...")

        sections = ["product_requirements", "technical_architecture", "design_architecture"]

        for section_name in sections:
            print(f"\n{'='*60}")
            print(f"Section: {section_name.replace('_', ' ').title()}")
            print(f"{'='*60}")

            # Interactive Opus discussion (handles option generation, selection, refinement)
            content = self.opus_prefill_section(section_name, app_description, industry, use_case)

            # Check if user wants to make final edits
            print("\n\nFinal review:")
            print("  1. Accept this content")
            print("  2. Make manual edits")
            print("  3. Skip this section for now")

            final_choice = input("\nChoice (1-3): ").strip()

            if final_choice == "2":
                print("\nOpening editor for final edits...")
                content = get_multiline_input("Edit the content:", allow_file=False)
                completed = True
                skipped = False
            elif final_choice == "3":
                completed = False
                skipped = True
            else:  # Accept
                completed = True
                skipped = False

            spec.sections.append(
                SpecSection(
                    name=section_name,
                    title=section_name.replace("_", " ").title(),
                    content=content,
                    completed=completed,
                    skipped=skipped,
                )
            )

            print(f"✓ {section_name} {'completed' if completed else 'skipped'}")

        # Step 5: Design Architecture (done as part of section wizard above)

        # Step 6: Tech stack suggestion
        print("\nStep 6: Tech Stack Suggestion")
        print(f"Based on your {use_case} in {industry}, we suggest:")
        print("  - Frontend: React with TypeScript")
        print("  - Backend: FastAPI (Python)")
        print("  - Database: PostgreSQL")

        tech_stack = input("Accept this stack? (y/n): ")
        if tech_stack.lower() == "y":
            spec.tech_stack = "react-fastapi-postgres"
        else:
            spec.tech_stack = input("  Enter your tech stack: ")

        # Step 7-8: Review and confirm
        print("\nStep 7-8: Review")
        print("PROJECT_SPEC is complete. Ready to confirm and lock?")
        confirm = input("Confirm (y/n): ")

        if confirm.lower() == "y":
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

        with open(self.spec_path, "w") as f:
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

        if choice == "1":
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

        elif choice == "2":
            for section in spec.sections:
                print(f"\n--- {section.title} ---")
                print(section.content[:200] + "...")

        elif choice == "3":
            print("\nStates: new, draft, reviewed, confirmed, locked")
            new_state = input("Enter new state: ")
            spec.state = SpecState(new_state)

        return spec

    def run_brainstorming_mode(self) -> ProjectSpec:
        """
        Brainstorming mode: Fully conversational PRD building with Opus/Claude Code.

        Natural discussion to gather all requirements, make suggestions iteratively,
        build complete spec through conversation. Then simplified wizard confirms sections.
        """
        print("\n" + "=" * 70)
        print("  BRAINSTORMING MODE - Conversational PRD Builder")
        print("=" * 70)
        print()
        print("[cyan]Let's build your PROJECT_SPEC through conversation![/cyan]")
        print("[dim]I'll ask questions, make suggestions, and we'll build it together.[/dim]\n")

        # Conversational gathering using conversational_input to handle paste properly
        app_description = conversational_input(
            "Tell me about your project idea:\n[dim]Just describe it in your own words - I'll ask follow-up questions.[/dim]\n\n[cyan]What do you want to build?[/cyan]"
        )

        # Detect industry
        print("\n🔍 Let me analyze that...")
        industry, use_case, industry_profile = self.detect_industry_and_use_case(app_description)

        print(f"\n[cyan]It looks like you're building a {industry} {use_case} application.[/cyan]")

        if industry_profile:
            print(f"[dim]I found the '{industry_profile.name}' industry profile.[/dim]")
            if industry_profile.common_pain_points:
                print(f"\n[yellow]Common pain points in {industry}:[/yellow]")
                for pain in industry_profile.common_pain_points[:3]:
                    print(f"  • {pain}")
                print()

        # Start conversational requirements gathering
        print("\n" + "-" * 70)
        print("Let's dig deeper. I'll ask some questions to build your PRD.\n")

        conversation_prompts = [
            {
                "section": "product_requirements",
                "questions": [
                    "Who is your target audience? Be specific about user personas.",
                    "What's the main problem you're solving for them?",
                    "What are the 3-5 core features you need for MVP?",
                    "What's out of scope for v1.0?",
                ],
            },
            {
                "section": "technical_architecture",
                "questions": [
                    "Do you have preferences for tech stack? (or should I suggest based on your needs)",
                    "Any specific scalability requirements? (users, data volume, regions)",
                    "What integrations do you need? (payment, auth, APIs, etc.)",
                ],
            },
            {
                "section": "design_architecture",
                "questions": [
                    "What's the desired user experience? (simple/feature-rich, mobile-first/desktop, etc.)",
                    f"Are there {industry} compliance requirements I should know about?",
                    "Any accessibility requirements? (WCAG level, specific needs)",
                ],
            },
        ]

        sections_content = {}

        for prompt_set in conversation_prompts:
            section = prompt_set["section"]
            print(f"\n{'='*70}")
            print(f"  {section.replace('_', ' ').title()}")
            print(f"{'='*70}\n")

            responses = []
            for question in prompt_set["questions"]:
                answer = conversational_input(f"[cyan]{question}[/cyan]")
                responses.append({"question": question, "answer": answer})
                print()

            # Generate section content from conversation
            section_content = self._build_section_from_conversation(
                section, app_description, industry, use_case, responses, industry_profile
            )

            sections_content[section] = section_content

        # Build spec object
        spec = ProjectSpec(state=SpecState.DRAFT, industry=industry, use_case=use_case)

        for section_name, content in sections_content.items():
            spec.sections.append(
                SpecSection(
                    name=section_name,
                    title=section_name.replace("_", " ").title(),
                    content=content,
                    completed=True,
                    skipped=False,
                )
            )

        # Save spec
        self.save_spec_state(spec)
        self.write_spec_to_file(spec)

        print("\n" + "=" * 70)
        print("  ✓ PROJECT_SPEC Built from Conversation!")
        print("=" * 70)
        print(f"\nSaved to: {self.spec_path}")
        print("\n[cyan]Next: Review each section and confirm[/cyan]\n")

        # Run simplified confirmation wizard
        return self.run_confirmation_wizard(spec)

    def _build_section_from_conversation(
        self,
        section: str,
        app_description: str,
        industry: str,
        use_case: str,
        conversation: List[Dict],
        industry_profile: Optional[IndustryProfile],
    ) -> str:
        """
        Build section content from conversational responses.

        Args:
            section: Section name
            app_description: Original app description
            industry: Industry ID
            use_case: Use case pattern
            conversation: List of Q&A dicts
            industry_profile: Industry profile if available

        Returns:
            Formatted section content
        """
        content = f"# {section.replace('_', ' ').title()}\n\n"

        # Add conversation responses
        for qa in conversation:
            # Extract clean question (remove markdown)
            question = qa["question"].strip()
            answer = qa["answer"].strip()

            if answer:
                # Format as section
                content += f"## {question}\n\n"
                content += f"{answer}\n\n"

        # Add industry-specific guidance if available
        if industry_profile and section == "product_requirements":
            if industry_profile.common_pain_points:
                content += "## Additional Considerations\n\n"
                content += f"Common pain points in {industry}:\n"
                for pain in industry_profile.common_pain_points:
                    content += f"- {pain}\n"
                content += "\n"

        return content

    def run_confirmation_wizard(self, spec: ProjectSpec) -> ProjectSpec:
        """
        Simplified confirmation wizard - just review and approve sections.

        Args:
            spec: ProjectSpec built from brainstorming

        Returns:
            Updated ProjectSpec
        """
        print("\n" + "=" * 70)
        print("  CONFIRMATION - Review Your PRD")
        print("=" * 70)
        print()

        for section in spec.sections:
            print(f"\n{'-'*70}")
            print(f"Section: {section.title}")
            print(f"{'-'*70}\n")
            print(section.content[:500] + "..." if len(section.content) > 500 else section.content)
            print()

            choice = input("  1. Accept  2. Edit  3. Skip\nChoice (1-3): ").strip()

            if choice == "2":
                print("\nOpening editor...")
                edited = get_multiline_input(f"Edit {section.title}:", allow_file=False)
                section.content = edited
            elif choice == "3":
                section.skipped = True
                section.completed = False
            else:
                section.completed = True
                section.skipped = False

        # Update state and save
        spec.state = SpecState.REVIEWED
        self.save_spec_state(spec)
        self.write_spec_to_file(spec)

        print("\n✓ PROJECT_SPEC confirmed and saved!")
        return spec

    def run_simple_brainstorm(self) -> ProjectSpec:
        """
        Simple brainstorming mode - no fragmentation, no complexity.

        Opens text editor once, user pastes/writes everything, we build the PRD,
        then simple confirmation.
        """
        print("=" * 70)
        print("  BRAINSTORMING MODE")
        print("=" * 70)
        print()
        print("[cyan]I'll open a text editor for you to describe your project.[/cyan]")
        print("[dim]Write or paste everything about your project idea.[/dim]")
        print()
        print("Include:")
        print("  • What you want to build")
        print("  • Who it's for (target audience)")
        print("  • Core features and functionality")
        print("  • Technical requirements or preferences")
        print("  • Any specific goals or constraints")
        print()

        # Get full project description in text editor (no fragmentation!)
        app_description = get_multiline_input(
            "Opening text editor for your project description...", allow_file=True
        )

        if not app_description or len(app_description.strip()) < 50:
            print("\n[yellow]⚠️  Description too short. Please provide more detail.[/yellow]")
            print("[dim]Try again with 'br spec brainstorm'[/dim]")
            raise ValueError("Insufficient project description")

        print(f"\n✓ Got {len(app_description)} characters")

        # Detect industry using Synapse
        print("\n🔍 Analyzing your project...")
        industry, use_case, industry_profile = self.detect_industry_and_use_case(app_description)

        print(f"\n[cyan]Industry: {industry}[/cyan]")
        print(f"[cyan]Use Case: {use_case}[/cyan]")

        if industry_profile:
            print(f"\n[dim]✓ Found '{industry_profile.name}' profile[/dim]")
            if industry_profile.common_pain_points:
                print(f"\n[yellow]Industry insights ({industry}):[/yellow]")
                for pain in industry_profile.common_pain_points[:3]:
                    print(f"  • {pain}")

        # Parse description into structured sections
        print("\n📝 Building your PROJECT_SPEC...")

        sections_content = self._parse_description_into_sections(
            app_description, industry, use_case, industry_profile
        )

        # Build spec object
        spec = ProjectSpec(state=SpecState.DRAFT, industry=industry, use_case=use_case)

        for section_name, content in sections_content.items():
            spec.sections.append(
                SpecSection(
                    name=section_name,
                    title=section_name.replace("_", " ").title(),
                    content=content,
                    completed=True,
                    skipped=False,
                )
            )

        # Save initial version
        self.save_spec_state(spec)
        self.write_spec_to_file(spec)

        print("\n" + "=" * 70)
        print("  PRD GENERATED - Review")
        print("=" * 70)
        print()
        print(f"[green]✓ Created {len(spec.sections)} sections[/green]")
        print()

        # Simple confirmation - just accept or edit whole thing
        print("Would you like to:")
        print("  1. Accept and save")
        print("  2. Edit in text editor")
        print("  3. Cancel")

        choice = input("\nChoice (1-3): ").strip()

        if choice == "2":
            # Let them edit the generated PRD
            current_content = self._render_spec_for_editing(spec)
            edited_content = get_multiline_input("Edit your PROJECT_SPEC...", allow_file=False)

            # Re-parse edited version
            sections_content = self._parse_description_into_sections(
                edited_content, industry, use_case, industry_profile
            )

            spec.sections = []
            for section_name, content in sections_content.items():
                spec.sections.append(
                    SpecSection(
                        name=section_name,
                        title=section_name.replace("_", " ").title(),
                        content=content,
                        completed=True,
                        skipped=False,
                    )
                )

        elif choice == "3":
            print("\n[yellow]Cancelled. Run 'br spec brainstorm' to try again.[/yellow]")
            raise ValueError("User cancelled")

        # Final save
        spec.state = SpecState.REVIEWED
        self.save_spec_state(spec)
        self.write_spec_to_file(spec)

        print("\n[green]✓ PROJECT_SPEC saved successfully![/green]")

        return spec

    def _parse_description_into_sections(
        self,
        description: str,
        industry: str,
        use_case: str,
        industry_profile: Optional[IndustryProfile],
    ) -> Dict[str, str]:
        """
        Parse raw project description into structured PRD sections.

        Extracts key information and formats it into sections:
        - Product Requirements
        - Technical Architecture
        - Design Architecture
        """
        sections = {}

        # Product Requirements section
        product_section = f"""# Product Requirements

## Project Description
{description}

## Industry Context
- **Industry:** {industry}
- **Use Case:** {use_case}
"""

        if industry_profile and industry_profile.common_pain_points:
            product_section += "\n## Industry Pain Points\n"
            for pain in industry_profile.common_pain_points[:5]:
                product_section += f"- {pain}\n"

        sections["product_requirements"] = product_section

        # Technical Architecture section
        tech_section = """# Technical Architecture

## Technology Stack
- To be determined based on project requirements
- Consider: scalability, team expertise, ecosystem

## Integration Requirements
- Identify third-party services needed
- API integrations
- Authentication/authorization

## Infrastructure
- Hosting requirements
- Database needs
- Caching strategy
"""
        sections["technical_architecture"] = tech_section

        # Design Architecture section
        design_section = f"""# Design Architecture

## User Experience
- Industry: {industry}
- Use Case: {use_case}
"""

        if industry_profile:
            if industry_profile.common_pain_points:
                design_section += "\n## Design Considerations\n"
                for pain in industry_profile.common_pain_points[:3]:
                    design_section += f"- Address: {pain}\n"

        design_section += """
## Accessibility
- WCAG 2.1 Level AA compliance
- Keyboard navigation
- Screen reader support
"""

        sections["design_architecture"] = design_section

        return sections

    def _render_spec_for_editing(self, spec: ProjectSpec) -> str:
        """Render spec as markdown for editing"""
        content = f"# {spec.industry.title()} {spec.use_case.title()} Project\n\n"

        for section in spec.sections:
            content += f"\n---\n\n{section.content}\n"

        return content

    def run(self):
        """Main wizard entry point"""
        if self.check_existing_spec():
            print("Existing PROJECT_SPEC found.")
            spec = self.load_spec_state()
            if spec:
                spec = self.run_existing_spec_mode(spec)
            else:
                print("Could not load spec state. Starting fresh.")
                spec = self._choose_and_run_wizard_mode()
        else:
            spec = self._choose_and_run_wizard_mode()

        # Save state and write file (might already be saved in brainstorming mode)
        self.save_spec_state(spec)
        self.write_spec_to_file(spec)

        print(f"\nPROJECT_SPEC saved to: {self.spec_path}")
        print(f"State: {spec.state.value}")

        return spec

    def _choose_and_run_wizard_mode(self) -> ProjectSpec:
        """
        Let user choose between brainstorming mode and regular wizard.

        Returns:
            Completed ProjectSpec
        """
        print("\n" + "=" * 70)
        print("  BuildRunner PROJECT_SPEC Wizard")
        print("=" * 70)
        print()
        print("Choose your mode:\n")
        print("  1. [cyan]Brainstorming Mode[/cyan] (Recommended)")
        print("     Conversational - I'll ask questions and build your PRD through")
        print("     natural discussion. Great for new projects.\n")
        print("  2. [dim]Structured Wizard[/dim]")
        print("     Step-by-step sections with AI suggestions.")
        print("     Good if you have a clear spec in mind.\n")

        choice = input("Choice (1-2): ").strip()

        if choice == "2":
            return self.run_first_time_wizard()
        else:
            # Default to brainstorming
            return self.run_brainstorming_mode()


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
            choices=[
                "Healthcare",
                "Fintech",
                "E-commerce",
                "SaaS",
                "Education",
                "Social",
                "Marketplace",
                "Analytics",
                "Government",
                "Legal",
                "Nonprofit",
                "Gaming",
                "Manufacturing",
            ],
            default="SaaS",
        )

        use_case = Prompt.ask(
            "Use Case",
            choices=[
                "Dashboard",
                "Marketplace",
                "CRM",
                "Analytics",
                "Onboarding",
                "API Service",
                "Admin Panel",
                "Mobile App",
                "Chat",
                "Video",
                "Calendar",
                "Forms",
                "Search",
            ],
            default="Dashboard",
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
            "key_features": "User auth, Dashboard, API",
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
        console.print(
            "[yellow]Warning: sync_spec_to_features not available, creating basic features.json[/yellow]"
        )
        features_path = project_root / ".buildrunner" / "features.json"
        features_data = {
            "features": [],
            "metadata": {"industry": industry, "use_case": use_case, "generated_by": "prd_wizard"},
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
        context={"industry": industry, "use_case": use_case, "constraints": []},
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
        "handoff_package": handoff_package,
    }


def main():
    """CLI entry point for testing"""
    import sys

    project_root = sys.argv[1] if len(sys.argv) > 1 else "."

    wizard = PRDWizard(project_root)
    wizard.run()


if __name__ == "__main__":
    main()
