# Build 1A - Complete PRD Wizard

**Branch:** `build/v3.1-prd-wizard`
**Worktree:** `../br3-prd-wizard`
**Duration:** 1 week
**Execute in parallel with Build 1B**

**⚠️ IMPORTANT:** Read `.buildrunner/WORKFLOW_PRINCIPLES.md` before starting

---

## Execution Strategy

**Pattern:** Domain Batch Mode (3-5 tasks per batch)
**Batches:** 2 batches with verification gates
**State Tracking:** CLAUDE.md + TodoWrite

---

## Context

Currently, the PRD wizard has stubs and simulated Opus integration (17-32% test coverage). This build completes the implementation with:
- Real Anthropic Opus API integration
- Model switching protocol (Opus → Sonnet handoff)
- Planning mode auto-detection
- Full test coverage (85%+)

---

## State Management Setup

### Step 0: Initialize State Tracking

Before starting any tasks, create `CLAUDE.md` in worktree root:

```bash
cd ../br3-prd-wizard
cat > CLAUDE.md << 'EOF'
# Claude State Tracker - Build 1A: PRD Wizard

## Project Info
**Branch:** build/v3.1-prd-wizard
**Start Date:** [CURRENT_DATE]
**Target:** Real Opus integration, model switching, planning mode

## Progress
**Overall:** 0% → Target: 100%
**Current Batch:** None
**Last Updated:** [TIMESTAMP]

## Batches
- [ ] Batch 1: Core Infrastructure (Tasks 1-3)
- [ ] Batch 2: Integration & Testing (Tasks 4-6)

## Completed Components
(None yet)

## In Progress
(None yet)

## Blockers
(None yet)

## Next Steps
1. Start Batch 1
2. Create OpusClient
3. Create ModelSwitcher
4. Update planning mode detection

## Metrics
- Files Created: 0
- Tests Written: 0
- Coverage: 0%
- Time Spent: 0h
EOF
```

### Step 0.1: Initialize TodoWrite

```bash
# In Claude Code, run:
br todo init

# Or manually create .buildrunner/todos.json:
{
  "todos": [
    {"content": "Complete Batch 1: Core Infrastructure", "status": "pending", "activeForm": "Completing core infrastructure"},
    {"content": "Complete Batch 2: Integration & Testing", "status": "pending", "activeForm": "Completing integration and testing"}
  ]
}
```

---

## Setup

### 1. Create Git Worktree
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree add ../br3-prd-wizard -b build/v3.1-prd-wizard
cd ../br3-prd-wizard
```

### 2. Install Dependencies
```bash
pip install anthropic>=0.18.0 -q
pip install pytest pytest-asyncio pytest-cov -q
pip install pyyaml python-dotenv -q
```

### 3. Verify Current State
```bash
# Check existing files
ls -la core/prd_wizard.py core/opus_handoff.py core/planning_mode.py

# Run existing tests
pytest tests/test_integration_prd_system.py -v
```

---

## Batch Overview

### Batch 1: Core Infrastructure (3 tasks, ~4 hours)
**Domain:** Backend API Integration
**Dependencies:** None
**Goal:** Create foundation for Opus integration and model switching

**Tasks:**
1. Task 1.1: Create Real Opus API Client (90 min)
2. Task 1.2: Implement Model Switching Protocol (90 min)
3. Task 1.3: Implement Planning Mode Auto-Detection (60 min)

**✅ Verification Gate 1:**
After completing Batch 1, verify:
- [ ] All 3 files created (opus_client.py, model_switcher.py, planning_mode.py updates)
- [ ] Files have proper docstrings and type hints
- [ ] Basic unit tests pass
- [ ] No import errors
- [ ] Update CLAUDE.md with completed components
- [ ] Mark Batch 1 complete in TodoWrite

**⏸️ STOP HERE. Do not proceed to Batch 2 until Batch 1 is verified.**

---

### Batch 2: Integration & Testing (3 tasks, ~4 hours)
**Domain:** Integration and Quality Assurance
**Dependencies:** Batch 1 complete
**Goal:** Complete wizard, comprehensive tests, documentation

**Tasks:**
2. Task 2.1: Complete PRD Wizard Implementation (90 min)
3. Task 2.2: Write Comprehensive Tests (90 min)
4. Task 2.3: Update Documentation (60 min)

**✅ Verification Gate 2:**
After completing Batch 2, verify:
- [ ] Wizard runs end-to-end successfully
- [ ] All tests pass (45+ tests)
- [ ] Test coverage ≥ 85%
- [ ] Documentation complete and accurate
- [ ] Manual testing successful
- [ ] Update CLAUDE.md with final status
- [ ] Mark Batch 2 complete in TodoWrite
- [ ] Ready for branch push

---

## Batch 1: Core Infrastructure

### Task 1.1: Create Real Opus API Client

**Domain:** Backend API Integration
**Duration:** 90 minutes
**Dependencies:** None

**File:** `core/opus_client.py` (NEW FILE)

**Purpose:** Replace simulated Opus calls with real Anthropic API

**Implementation Details:**

```python
"""
Real Anthropic Opus API client for PRD generation
"""
import os
from typing import Dict, List, Optional
from anthropic import Anthropic, AsyncAnthropic
import asyncio
import json

class OpusClient:
    """Real Opus API client for PRD wizard"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Opus client

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")

        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-opus-4-20250514"  # Latest Opus
        self.max_tokens = 4096

    async def pre_fill_spec(
        self,
        industry: str,
        use_case: str,
        user_input: Dict[str, str]
    ) -> str:
        """
        Pre-fill PROJECT_SPEC.md using Opus

        Args:
            industry: Industry type (e.g., "Healthcare")
            use_case: Use case pattern (e.g., "Dashboard")
            user_input: User responses from wizard

        Returns:
            Generated PROJECT_SPEC.md content
        """
        prompt = self._build_spec_prompt(industry, use_case, user_input)

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Opus API error: {e}")

    async def analyze_requirements(self, requirements: str) -> Dict[str, any]:
        """
        Analyze user requirements and suggest features

        Args:
            requirements: Raw user requirements text

        Returns:
            Dict with:
                - features: List of suggested features
                - architecture: Suggested architecture
                - tech_stack: Recommended technologies
        """
        prompt = f"""Analyze these project requirements and provide:
1. List of features (as feature objects with id, name, description)
2. Suggested architecture (frontend, backend, database)
3. Recommended tech stack

Requirements:
{requirements}

Respond in JSON format."""

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            return json.loads(message.content[0].text)
        except Exception as e:
            raise RuntimeError(f"Requirements analysis failed: {e}")

    async def generate_design_tokens(
        self,
        industry: str,
        use_case: str
    ) -> Dict[str, any]:
        """
        Generate design system tokens for industry + use case

        Args:
            industry: Industry type
            use_case: Use case pattern

        Returns:
            Dict with design tokens (colors, typography, spacing, etc.)
        """
        prompt = f"""Generate design system tokens for:
Industry: {industry}
Use Case: {use_case}

Include:
- Color palette (primary, secondary, accent, neutral)
- Typography (fonts, sizes, weights)
- Spacing scale
- Border radius
- Shadows
- Breakpoints

Respond in JSON format compatible with Tailwind config."""

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            return json.loads(message.content[0].text)
        except Exception as e:
            raise RuntimeError(f"Design token generation failed: {e}")

    def _build_spec_prompt(
        self,
        industry: str,
        use_case: str,
        user_input: Dict[str, str]
    ) -> str:
        """Build prompt for PROJECT_SPEC generation"""
        return f"""Generate a complete PROJECT_SPEC.md for:

Industry: {industry}
Use Case: {use_case}

User Input:
{json.dumps(user_input, indent=2)}

The spec should include:
1. Project Overview
2. Core Features
3. Technical Architecture
4. Design System
5. Compliance Requirements
6. Security Considerations
7. Testing Strategy
8. Deployment Plan

Use the BuildRunner PROJECT_SPEC.md format."""

    async def validate_spec(self, spec_content: str) -> Dict[str, any]:
        """
        Validate PROJECT_SPEC completeness

        Args:
            spec_content: PROJECT_SPEC.md content

        Returns:
            Dict with validation results:
                - valid: bool
                - missing_sections: List[str]
                - suggestions: List[str]
        """
        prompt = f"""Validate this PROJECT_SPEC.md for completeness:

{spec_content}

Check for:
- All required sections present
- Technical details specified
- Architecture clearly defined
- Security/compliance addressed

Respond in JSON format with: valid (bool), missing_sections (list), suggestions (list)"""

        try:
            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            return json.loads(message.content[0].text)
        except Exception as e:
            raise RuntimeError(f"Spec validation failed: {e}")


# Error handling and retries
class OpusAPIError(Exception):
    """Opus API error"""
    pass


def with_retry(max_retries: int = 3):
    """Decorator for retry logic"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        return wrapper
    return decorator
```

**Acceptance Criteria:**
- ✅ Real Opus API integration (not mocked)
- ✅ Async/await pattern
- ✅ Error handling with retries
- ✅ Exponential backoff for rate limits
- ✅ Environment variable for API key

---

## Task 2: Implement Model Switching Protocol

**File:** `core/model_switcher.py` (NEW FILE)

**Purpose:** Create compact handoff packages for Opus → Sonnet switching

**Implementation Details:**

```python
"""
Model switching protocol for Opus → Sonnet handoff
"""
import json
from typing import Dict, List
from pathlib import Path


class ModelSwitcher:
    """Handle model switching from Opus (planning) to Sonnet (execution)"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.handoff_dir = self.project_root / ".buildrunner" / "handoffs"
        self.handoff_dir.mkdir(parents=True, exist_ok=True)

    def create_handoff_package(
        self,
        spec_path: Path,
        features_path: Path,
        context: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Create compact handoff package for Sonnet

        Args:
            spec_path: Path to PROJECT_SPEC.md
            features_path: Path to features.json
            context: Additional context (decisions, constraints)

        Returns:
            Handoff package dict
        """
        # Read spec and features
        spec_content = spec_path.read_text()
        features = json.loads(features_path.read_text())

        # Compress context
        compressed = self.compress_context(spec_content, features, context)

        # Generate Sonnet prompt
        sonnet_prompt = self.generate_sonnet_prompt(compressed)

        # Create package
        package = {
            "version": "1.0",
            "timestamp": self._timestamp(),
            "source_model": "claude-opus-4",
            "target_model": "claude-sonnet-4.5",
            "project_root": str(self.project_root),
            "spec_summary": compressed["spec_summary"],
            "features": compressed["features"],
            "architecture": compressed["architecture"],
            "constraints": compressed["constraints"],
            "next_steps": compressed["next_steps"],
            "sonnet_prompt": sonnet_prompt
        }

        # Validate package
        self.validate_handoff(package)

        # Save package
        package_path = self.handoff_dir / f"handoff_{self._timestamp()}.json"
        package_path.write_text(json.dumps(package, indent=2))

        return package

    def compress_context(
        self,
        spec_content: str,
        features: Dict[str, any],
        context: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Compress context by removing verbosity, keeping essentials

        Returns:
            Compressed context dict with:
                - spec_summary: Key points from spec
                - features: Essential feature list
                - architecture: High-level architecture
                - constraints: Technical/business constraints
                - next_steps: Immediate action items
        """
        # Extract key sections from spec
        spec_summary = self._extract_spec_summary(spec_content)

        # Simplify features to essential info
        essential_features = [
            {
                "id": f["id"],
                "name": f["name"],
                "description": f.get("description", "")[:200],  # Truncate
                "status": f.get("status", "pending"),
                "dependencies": f.get("dependencies", [])
            }
            for f in features.get("features", [])
        ]

        # Extract architecture
        architecture = self._extract_architecture(spec_content)

        # Extract constraints
        constraints = context.get("constraints", [])

        # Determine next steps
        next_steps = self._determine_next_steps(essential_features)

        return {
            "spec_summary": spec_summary,
            "features": essential_features,
            "architecture": architecture,
            "constraints": constraints,
            "next_steps": next_steps
        }

    def generate_sonnet_prompt(self, compressed: Dict[str, any]) -> str:
        """
        Generate optimized prompt for Sonnet execution

        Args:
            compressed: Compressed context from compress_context()

        Returns:
            Formatted prompt for Sonnet
        """
        prompt = f"""# BuildRunner Project Handoff

## Project Overview
{compressed["spec_summary"]}

## Architecture
{self._format_architecture(compressed["architecture"])}

## Features to Implement
{self._format_features(compressed["features"])}

## Constraints
{self._format_constraints(compressed["constraints"])}

## Next Steps
{self._format_next_steps(compressed["next_steps"])}

## Instructions
You are now in execution mode. Implement the features according to the spec and architecture above.

Start with: {compressed["next_steps"][0] if compressed["next_steps"] else "Initialize project structure"}
"""
        return prompt

    def validate_handoff(self, package: Dict[str, any]) -> bool:
        """
        Validate handoff package completeness

        Raises:
            ValueError: If package missing required fields
        """
        required = [
            "version", "timestamp", "source_model", "target_model",
            "spec_summary", "features", "architecture", "next_steps"
        ]

        for field in required:
            if field not in package:
                raise ValueError(f"Handoff package missing required field: {field}")

        if not package["features"]:
            raise ValueError("Handoff package has no features")

        if not package["next_steps"]:
            raise ValueError("Handoff package has no next steps")

        return True

    def load_handoff(self, handoff_id: str) -> Dict[str, any]:
        """Load handoff package by ID"""
        package_path = self.handoff_dir / f"handoff_{handoff_id}.json"
        if not package_path.exists():
            raise FileNotFoundError(f"Handoff package not found: {handoff_id}")

        return json.loads(package_path.read_text())

    def _extract_spec_summary(self, spec_content: str) -> str:
        """Extract key points from PROJECT_SPEC.md"""
        # Simple extraction: first 500 chars + key sections
        lines = spec_content.split("\n")
        summary = []

        for line in lines[:50]:  # First 50 lines
            if line.startswith("#") or line.strip():
                summary.append(line)

        return "\n".join(summary)[:1000]  # Max 1000 chars

    def _extract_architecture(self, spec_content: str) -> Dict[str, any]:
        """Extract architecture from spec"""
        # Look for ## Architecture section
        lines = spec_content.split("\n")
        arch = {"frontend": "", "backend": "", "database": "", "infrastructure": ""}

        in_arch_section = False
        for line in lines:
            if "## Architecture" in line or "## Technical Architecture" in line:
                in_arch_section = True
            elif in_arch_section and line.startswith("##"):
                break
            elif in_arch_section and line.strip():
                # Parse architecture details
                if "frontend" in line.lower():
                    arch["frontend"] = line
                elif "backend" in line.lower():
                    arch["backend"] = line
                elif "database" in line.lower():
                    arch["database"] = line

        return arch

    def _determine_next_steps(self, features: List[Dict]) -> List[str]:
        """Determine next steps based on feature status"""
        pending = [f for f in features if f.get("status") == "pending"]

        # Prioritize by dependencies
        no_deps = [f for f in pending if not f.get("dependencies")]

        if no_deps:
            return [f"Implement feature: {no_deps[0]['name']}" for f in no_deps[:3]]
        else:
            return [f"Implement feature: {pending[0]['name']}" for f in pending[:3]]

    def _format_architecture(self, arch: Dict[str, any]) -> str:
        """Format architecture for prompt"""
        return "\n".join([f"- {k}: {v}" for k, v in arch.items() if v])

    def _format_features(self, features: List[Dict]) -> str:
        """Format features for prompt"""
        return "\n".join([
            f"{i+1}. {f['name']} ({f['status']})\n   {f['description']}"
            for i, f in enumerate(features[:10])  # Max 10 features
        ])

    def _format_constraints(self, constraints: List[str]) -> str:
        """Format constraints for prompt"""
        return "\n".join([f"- {c}" for c in constraints])

    def _format_next_steps(self, steps: List[str]) -> str:
        """Format next steps for prompt"""
        return "\n".join([f"{i+1}. {s}" for i, s in enumerate(steps)])

    def _timestamp(self) -> str:
        """Generate timestamp string"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
```

**Acceptance Criteria:**
- ✅ Creates compact handoff packages (<2000 tokens)
- ✅ Includes all essential context
- ✅ Validates package completeness
- ✅ Generates optimized Sonnet prompts
- ✅ Saves packages to `.buildrunner/handoffs/`

---

## Task 3: Implement Planning Mode Auto-Detection

**File:** `core/planning_mode.py` (UPDATE EXISTING)

**Purpose:** Auto-detect when to use Opus (planning) vs Sonnet (execution)

**Current State:** File exists at 42% coverage with basic detection

**Updates Needed:**

```python
# ADD TO EXISTING FILE

def detect_planning_mode(
    user_prompt: str,
    project_state: Dict[str, any],
    conversation_history: List[Dict[str, str]]
) -> Dict[str, any]:
    """
    Detect if user request requires planning mode (Opus)

    Args:
        user_prompt: User's request
        project_state: Current project state (features, spec exists, etc.)
        conversation_history: Recent conversation

    Returns:
        Dict with:
            - use_opus: bool
            - confidence: float (0-1)
            - reason: str
    """
    # Indicators for Opus (planning mode)
    opus_indicators = [
        "new project",
        "design",
        "architecture",
        "plan",
        "spec",
        "requirements",
        "what should",
        "how to structure",
        "best approach"
    ]

    # Indicators for Sonnet (execution mode)
    sonnet_indicators = [
        "implement",
        "add feature",
        "fix bug",
        "write test",
        "update",
        "refactor",
        "debug"
    ]

    # Check if PROJECT_SPEC.md exists
    has_spec = project_state.get("has_spec", False)

    # Check if features defined
    has_features = len(project_state.get("features", [])) > 0

    # Score prompt
    opus_score = sum(1 for indicator in opus_indicators if indicator in user_prompt.lower())
    sonnet_score = sum(1 for indicator in sonnet_indicators if indicator in user_prompt.lower())

    # Decision logic
    if not has_spec and not has_features:
        # New project - always use Opus for planning
        return {
            "use_opus": True,
            "confidence": 0.95,
            "reason": "New project detected - planning mode recommended"
        }

    if opus_score > sonnet_score:
        # Planning-related request
        confidence = min(0.9, 0.6 + (opus_score * 0.1))
        return {
            "use_opus": True,
            "confidence": confidence,
            "reason": f"Planning-related keywords detected ({opus_score})"
        }

    if sonnet_score > opus_score:
        # Execution-related request
        confidence = min(0.9, 0.6 + (sonnet_score * 0.1))
        return {
            "use_opus": False,
            "confidence": confidence,
            "reason": f"Execution-related keywords detected ({sonnet_score})"
        }

    # Ambiguous - default to Sonnet for existing projects
    if has_spec and has_features:
        return {
            "use_opus": False,
            "confidence": 0.6,
            "reason": "Ambiguous request, defaulting to execution mode"
        }

    # Ambiguous - default to Opus for new projects
    return {
        "use_opus": True,
        "confidence": 0.6,
        "reason": "Ambiguous request, defaulting to planning mode"
    }


def should_use_opus(detection: Dict[str, any], confidence_threshold: float = 0.7) -> bool:
    """
    Decide if Opus should be used based on detection

    Args:
        detection: Result from detect_planning_mode()
        confidence_threshold: Minimum confidence for auto-selection

    Returns:
        True if Opus should be used
    """
    if detection["confidence"] >= confidence_threshold:
        return detection["use_opus"]

    # Low confidence - ask user
    return None  # Signals need for user confirmation


def should_use_sonnet(detection: Dict[str, any], confidence_threshold: float = 0.7) -> bool:
    """
    Decide if Sonnet should be used based on detection

    Args:
        detection: Result from detect_planning_mode()
        confidence_threshold: Minimum confidence for auto-selection

    Returns:
        True if Sonnet should be used
    """
    if detection["confidence"] >= confidence_threshold:
        return not detection["use_opus"]

    # Low confidence - ask user
    return None


def get_project_state(project_root: Path) -> Dict[str, any]:
    """
    Get current project state for mode detection

    Returns:
        Dict with:
            - has_spec: bool
            - has_features: bool
            - features: List[Dict]
            - feature_count: int
            - completed_count: int
    """
    spec_path = project_root / ".buildrunner" / "PROJECT_SPEC.md"
    features_path = project_root / ".buildrunner" / "features.json"

    has_spec = spec_path.exists()
    has_features = features_path.exists()

    features = []
    if has_features:
        features = json.loads(features_path.read_text()).get("features", [])

    completed = [f for f in features if f.get("status") == "completed"]

    return {
        "has_spec": has_spec,
        "has_features": has_features,
        "features": features,
        "feature_count": len(features),
        "completed_count": len(completed)
    }
```

**Acceptance Criteria:**
- ✅ Detects planning vs execution mode with 90%+ accuracy
- ✅ Returns confidence scores
- ✅ Considers project state (spec exists, features defined)
- ✅ Provides reasoning for decisions
- ✅ Allows manual override for low confidence

---

## Task 4: Complete PRD Wizard Implementation

**File:** `core/prd_wizard.py` (UPDATE EXISTING)

**Current State:** 32% coverage, mostly stubs

**Updates Needed:**

```python
# REPLACE EXISTING run_wizard() with:

async def run_wizard(interactive: bool = True) -> Dict[str, any]:
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

    from cli.spec_commands import sync_spec_to_features
    features_path = sync_spec_to_features(spec_path)

    console.print(f"[green]✓ Features synced to {features_path}[/green]\n")

    # Step 7: Create model switching handoff package
    console.print("[bold]Step 5: Creating handoff package for Sonnet...[/bold]")

    switcher = ModelSwitcher(project_root)
    features = json.loads(features_path.read_text())

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
```

**Acceptance Criteria:**
- ✅ Full interactive wizard flow
- ✅ Uses real Opus API (not simulation)
- ✅ Generates valid PROJECT_SPEC.md
- ✅ Syncs to features.json automatically
- ✅ Creates handoff package
- ✅ Rich terminal UI with colors

---

## Task 5: Write Comprehensive Tests

**File:** `tests/test_prd_wizard_complete.py` (NEW FILE)

**Purpose:** Test all new functionality with 85%+ coverage

```python
"""
Tests for completed PRD wizard with Opus integration
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from core.opus_client import OpusClient, OpusAPIError
from core.model_switcher import ModelSwitcher
from core.planning_mode import detect_planning_mode, get_project_state
from core.prd_wizard import run_wizard


class TestOpusClient:
    """Test real Opus API client"""

    @pytest.fixture
    def opus_client(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            return OpusClient()

    def test_init_with_api_key(self):
        """Test initialization with API key"""
        client = OpusClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model == "claude-opus-4-20250514"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises ValueError"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                OpusClient()

    @pytest.mark.asyncio
    async def test_pre_fill_spec(self, opus_client):
        """Test spec pre-filling"""
        mock_response = Mock()
        mock_response.content = [Mock(text="# PROJECT_SPEC\n\nTest content")]

        with patch.object(opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)):
            result = await opus_client.pre_fill_spec(
                industry="Healthcare",
                use_case="Dashboard",
                user_input={"project_name": "Test"}
            )

            assert "PROJECT_SPEC" in result
            assert "Test content" in result

    @pytest.mark.asyncio
    async def test_analyze_requirements(self, opus_client):
        """Test requirements analysis"""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"features": [], "architecture": {}}')]

        with patch.object(opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)):
            result = await opus_client.analyze_requirements("Build a dashboard")

            assert "features" in result
            assert "architecture" in result

    @pytest.mark.asyncio
    async def test_generate_design_tokens(self, opus_client):
        """Test design token generation"""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"colors": {}, "typography": {}}')]

        with patch.object(opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)):
            result = await opus_client.generate_design_tokens("Healthcare", "Dashboard")

            assert "colors" in result
            assert "typography" in result

    @pytest.mark.asyncio
    async def test_validate_spec(self, opus_client):
        """Test spec validation"""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"valid": true, "missing_sections": [], "suggestions": []}')]

        with patch.object(opus_client.async_client.messages, "create", AsyncMock(return_value=mock_response)):
            result = await opus_client.validate_spec("# Test Spec")

            assert result["valid"] is True
            assert isinstance(result["missing_sections"], list)


class TestModelSwitcher:
    """Test model switching protocol"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project structure"""
        project = tmp_path / "test_project"
        project.mkdir()
        (project / ".buildrunner").mkdir()

        # Create spec
        spec = project / ".buildrunner" / "PROJECT_SPEC.md"
        spec.write_text("# Test Spec\n\n## Architecture\nFrontend: React")

        # Create features
        features = project / ".buildrunner" / "features.json"
        features.write_text(json.dumps({
            "features": [
                {"id": "1", "name": "Feature 1", "description": "Test", "status": "pending", "dependencies": []}
            ]
        }))

        return project

    def test_create_handoff_package(self, temp_project):
        """Test handoff package creation"""
        switcher = ModelSwitcher(temp_project)

        package = switcher.create_handoff_package(
            spec_path=temp_project / ".buildrunner" / "PROJECT_SPEC.md",
            features_path=temp_project / ".buildrunner" / "features.json",
            context={"constraints": ["Use TypeScript"]}
        )

        assert package["version"] == "1.0"
        assert package["source_model"] == "claude-opus-4"
        assert package["target_model"] == "claude-sonnet-4.5"
        assert "spec_summary" in package
        assert "features" in package
        assert len(package["features"]) == 1

    def test_compress_context(self, temp_project):
        """Test context compression"""
        switcher = ModelSwitcher(temp_project)

        spec = "# Test\n\n" + ("x" * 5000)  # Long spec
        features = {"features": [{"id": "1", "name": "F1", "description": "x" * 500, "status": "pending"}]}
        context = {"constraints": ["Constraint 1"]}

        compressed = switcher.compress_context(spec, features, context)

        assert len(compressed["spec_summary"]) <= 1000
        assert compressed["features"][0]["description"] == "x" * 200  # Truncated
        assert "next_steps" in compressed

    def test_generate_sonnet_prompt(self, temp_project):
        """Test Sonnet prompt generation"""
        switcher = ModelSwitcher(temp_project)

        compressed = {
            "spec_summary": "Test project",
            "features": [{"id": "1", "name": "F1", "description": "Test", "status": "pending"}],
            "architecture": {"frontend": "React"},
            "constraints": ["TypeScript"],
            "next_steps": ["Implement F1"]
        }

        prompt = switcher.generate_sonnet_prompt(compressed)

        assert "BuildRunner Project Handoff" in prompt
        assert "Test project" in prompt
        assert "React" in prompt
        assert "Implement F1" in prompt

    def test_validate_handoff_success(self, temp_project):
        """Test handoff validation success"""
        switcher = ModelSwitcher(temp_project)

        package = {
            "version": "1.0",
            "timestamp": "20250101_120000",
            "source_model": "opus",
            "target_model": "sonnet",
            "spec_summary": "Test",
            "features": [{"id": "1"}],
            "architecture": {},
            "next_steps": ["Step 1"]
        }

        assert switcher.validate_handoff(package) is True

    def test_validate_handoff_missing_field(self, temp_project):
        """Test handoff validation fails on missing field"""
        switcher = ModelSwitcher(temp_project)

        package = {"version": "1.0"}  # Missing required fields

        with pytest.raises(ValueError, match="missing required field"):
            switcher.validate_handoff(package)


class TestPlanningMode:
    """Test planning mode auto-detection"""

    def test_detect_new_project(self):
        """Test detection for new project"""
        result = detect_planning_mode(
            user_prompt="Create a new healthcare dashboard",
            project_state={"has_spec": False, "has_features": False, "features": []},
            conversation_history=[]
        )

        assert result["use_opus"] is True
        assert result["confidence"] >= 0.9
        assert "New project" in result["reason"]

    def test_detect_planning_keywords(self):
        """Test detection with planning keywords"""
        result = detect_planning_mode(
            user_prompt="Help me design the architecture for this feature",
            project_state={"has_spec": True, "has_features": True, "features": []},
            conversation_history=[]
        )

        assert result["use_opus"] is True
        assert "Planning-related" in result["reason"]

    def test_detect_execution_keywords(self):
        """Test detection with execution keywords"""
        result = detect_planning_mode(
            user_prompt="Implement the user authentication feature",
            project_state={"has_spec": True, "has_features": True, "features": []},
            conversation_history=[]
        )

        assert result["use_opus"] is False
        assert "Execution-related" in result["reason"]

    def test_detect_ambiguous_defaults_to_sonnet(self):
        """Test ambiguous request defaults to Sonnet for existing project"""
        result = detect_planning_mode(
            user_prompt="What should I do next?",
            project_state={"has_spec": True, "has_features": True, "features": []},
            conversation_history=[]
        )

        assert result["use_opus"] is False
        assert result["confidence"] == 0.6

    def test_get_project_state(self, tmp_path):
        """Test project state extraction"""
        # Create project with spec and features
        (tmp_path / ".buildrunner").mkdir()
        (tmp_path / ".buildrunner" / "PROJECT_SPEC.md").write_text("# Spec")
        (tmp_path / ".buildrunner" / "features.json").write_text(json.dumps({
            "features": [
                {"status": "completed"},
                {"status": "pending"}
            ]
        }))

        state = get_project_state(tmp_path)

        assert state["has_spec"] is True
        assert state["has_features"] is True
        assert state["feature_count"] == 2
        assert state["completed_count"] == 1


class TestPRDWizard:
    """Test complete PRD wizard"""

    @pytest.mark.asyncio
    async def test_run_wizard_non_interactive(self, tmp_path):
        """Test wizard in non-interactive mode"""
        with patch("core.prd_wizard.OpusClient") as MockOpus:
            mock_opus = MockOpus.return_value
            mock_opus.pre_fill_spec = AsyncMock(return_value="# Generated Spec")

            with patch("core.prd_wizard.sync_spec_to_features") as mock_sync:
                mock_sync.return_value = tmp_path / "features.json"
                (tmp_path / "features.json").write_text(json.dumps({"features": []}))

                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    result = await run_wizard(interactive=False)

                assert result is not None
                assert "spec_path" in result
                assert "features_path" in result
                assert "handoff_package" in result


# Coverage target: 85%+
# All async tests use pytest-asyncio
# Mock external API calls (Anthropic)
```

**Acceptance Criteria:**
- ✅ Test coverage 85%+
- ✅ All core functions tested
- ✅ API calls mocked (no real API usage in tests)
- ✅ Async tests use pytest-asyncio
- ✅ Edge cases covered (missing API key, validation failures)

---

## Task 6: Update Documentation

**Files to Update:**
1. `docs/PRD_WIZARD.md`
2. `docs/PRD_SYSTEM.md`

### `docs/PRD_WIZARD.md` Updates

Add these sections:

```markdown
## Real Opus Integration

The PRD wizard now uses **real Anthropic Opus API** for intelligent spec generation.

### Setup

1. Get Anthropic API key from https://console.anthropic.com/
2. Set environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
3. Run wizard:
   ```bash
   br spec wizard
   ```

### Features

- **AI-Powered Pre-Fill**: Opus analyzes your requirements and generates a complete PROJECT_SPEC.md
- **Industry Intelligence**: Combines industry profiles with your specific needs
- **Design Token Generation**: Auto-generates Tailwind-compatible design tokens
- **Validation**: Opus validates spec completeness before saving

### Model Switching

The wizard automatically creates a **handoff package** for switching from Opus (planning) to Sonnet (execution):

```bash
# After wizard completes:
ls .buildrunner/handoffs/
# handoff_20250124_143022.json

# Handoff package contains:
# - Compressed spec summary
# - Essential features list
# - Architecture overview
# - Next steps for Sonnet
```

### Planning Mode Auto-Detection

BuildRunner automatically detects when to use planning mode:

| Prompt | Mode | Reason |
|--------|------|--------|
| "Create new dashboard" | Opus | New project |
| "Design the architecture" | Opus | Planning keywords |
| "Implement user auth" | Sonnet | Execution keywords |
| "Fix the bug in login" | Sonnet | Execution keywords |

Override with `--mode` flag:
```bash
br spec wizard --mode opus   # Force Opus
br spec wizard --mode sonnet # Force Sonnet
```

### API Usage

The wizard makes these Opus API calls:

1. `pre_fill_spec()` - Generate PROJECT_SPEC.md (~2000 tokens)
2. `analyze_requirements()` - Extract features (~1000 tokens)
3. `generate_design_tokens()` - Create design system (~1000 tokens)
4. `validate_spec()` - Check completeness (~500 tokens)

**Total cost per wizard run:** ~$0.15 USD (using Opus pricing as of Jan 2025)

### Troubleshooting

**Error: ANTHROPIC_API_KEY not found**
- Set the environment variable
- Check spelling: `ANTHROPIC_API_KEY` (not ANTHROPIC_KEY)

**Error: Rate limit exceeded**
- Wait 60 seconds and retry
- Opus has rate limits for API calls

**Error: Invalid response from Opus**
- Check API key is valid
- Verify internet connection
- Check Anthropic status page
```

### `docs/PRD_SYSTEM.md` Updates

Add architecture diagram:

```markdown
## Model Switching Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   PRD Wizard Flow                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. User Input                                               │
│     ├─ Industry (Healthcare)                                 │
│     ├─ Use Case (Dashboard)                                  │
│     └─ Requirements                                          │
│                                                               │
│  2. Planning Mode (Opus)                                     │
│     ├─ Analyze requirements                                  │
│     ├─ Generate PROJECT_SPEC.md                              │
│     ├─ Generate design tokens                                │
│     └─ Validate completeness                                 │
│                                                               │
│  3. Handoff Package Creation                                 │
│     ├─ Compress context (<2000 tokens)                       │
│     ├─ Extract essentials                                    │
│     ├─ Determine next steps                                  │
│     └─ Generate Sonnet prompt                                │
│                                                               │
│  4. Execution Mode (Sonnet)                                  │
│     ├─ Load handoff package                                  │
│     ├─ Implement features                                    │
│     ├─ Follow spec & architecture                            │
│     └─ Complete project                                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Handoff Package Specification

A handoff package is a JSON file containing:

```json
{
  "version": "1.0",
  "timestamp": "20250124_143022",
  "source_model": "claude-opus-4",
  "target_model": "claude-sonnet-4.5",
  "project_root": "/path/to/project",
  "spec_summary": "Key points from spec (max 1000 chars)",
  "features": [
    {
      "id": "feature_1",
      "name": "User Authentication",
      "description": "Truncated to 200 chars...",
      "status": "pending",
      "dependencies": []
    }
  ],
  "architecture": {
    "frontend": "React + TypeScript",
    "backend": "FastAPI",
    "database": "PostgreSQL"
  },
  "constraints": [
    "Must use TypeScript",
    "HIPAA compliance required"
  ],
  "next_steps": [
    "Implement feature: User Authentication",
    "Implement feature: Dashboard Layout",
    "Implement feature: Patient Records"
  ],
  "sonnet_prompt": "Complete formatted prompt..."
}
```

### Compression Rules

1. **Spec Summary**: First 1000 chars of PROJECT_SPEC.md
2. **Features**: Max 200 chars per description
3. **Features**: Only include pending/in-progress (skip completed)
4. **Next Steps**: Max 3 prioritized steps
5. **Total Size**: Target <2000 tokens for efficient context

### Planning Mode Decision Tree

```
User Prompt
    │
    ├─ Has PROJECT_SPEC? ────No──→ Use Opus (95% confidence)
    │       │
    │      Yes
    │       │
    ├─ Planning keywords? ───Yes──→ Use Opus (80% confidence)
    │       │
    │       No
    │       │
    ├─ Execution keywords? ──Yes──→ Use Sonnet (80% confidence)
    │       │
    │       No
    │       │
    └─ Ambiguous ────────────────→ Use Sonnet if spec exists (60%)
                                  → Use Opus if no spec (60%)
```

### Planning Keywords
- "new project", "create", "design", "architecture", "plan", "spec",
  "requirements", "what should", "how to structure", "best approach"

### Execution Keywords
- "implement", "add feature", "fix bug", "write test", "update",
  "refactor", "debug", "complete", "finish"
```

**Acceptance Criteria:**
- ✅ Opus integration documented
- ✅ Model switching explained
- ✅ Architecture diagrams added
- ✅ Troubleshooting section complete
- ✅ API usage and costs documented

---

## Testing

### Run Tests
```bash
cd ../br3-prd-wizard

# Run all tests
pytest tests/test_prd_wizard_complete.py -v

# Run with coverage
pytest tests/test_prd_wizard_complete.py --cov=core/opus_client.py --cov=core/model_switcher.py --cov=core/planning_mode.py --cov-report=term-missing

# Target: 85%+ coverage
```

### Manual Testing

**Test 1: Wizard with Real API**
```bash
# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Run wizard
python -m cli.main spec wizard

# Follow prompts:
# - Industry: Healthcare
# - Use Case: Dashboard
# - Project Name: Test Dashboard
# - Description: Patient monitoring dashboard
# - Target Audience: Healthcare providers
# - Key Features: Patient vitals, Alerts, Reports

# Verify:
# ✓ PROJECT_SPEC.md created
# ✓ features.json created
# ✓ Handoff package created
# ✓ Spec contains relevant healthcare content
```

**Test 2: Planning Mode Detection**
```bash
# Create test project with spec
mkdir test-project && cd test-project
br init
# (Creates spec and features)

# Test planning detection
python -c "
from core.planning_mode import detect_planning_mode, get_project_state
from pathlib import Path

state = get_project_state(Path('.'))
result = detect_planning_mode('design the architecture', state, [])
print(f'Use Opus: {result[\"use_opus\"]}')
print(f'Confidence: {result[\"confidence\"]}')
print(f'Reason: {result[\"reason\"]}')
"

# Should show: Use Opus: True, Confidence: 0.7+
```

**Test 3: Model Switching**
```bash
# After wizard completes
ls .buildrunner/handoffs/
cat .buildrunner/handoffs/handoff_*.json | jq .

# Verify handoff package contains:
# ✓ spec_summary
# ✓ features (array)
# ✓ architecture
# ✓ next_steps
# ✓ sonnet_prompt
```

---

## Commit and Push

### Commit Message
```bash
git add .
git commit -m "feat: Complete PRD wizard with real Opus integration

- Real Anthropic Opus API client (core/opus_client.py)
- Model switching protocol (core/model_switcher.py)
- Planning mode auto-detection (core/planning_mode.py)
- Complete wizard implementation (core/prd_wizard.py)
- Comprehensive tests (85%+ coverage)
- Updated documentation (PRD_WIZARD.md, PRD_SYSTEM.md)

Features:
- AI-powered PROJECT_SPEC generation
- Handoff packages for Opus → Sonnet switching
- Auto-detect planning vs execution mode
- Design token generation
- Spec validation

Test Coverage: 85%+
Tests Passing: 45+

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Push Branch
```bash
git push -u origin build/v3.1-prd-wizard
```

---

## Completion Checklist

Before reporting completion, verify:

- [ ] All 6 tasks complete
- [ ] `core/opus_client.py` created with real API integration
- [ ] `core/model_switcher.py` created with handoff packages
- [ ] `core/planning_mode.py` updated with auto-detection
- [ ] `core/prd_wizard.py` updated with full wizard flow
- [ ] `tests/test_prd_wizard_complete.py` created
- [ ] Test coverage 85%+ confirmed
- [ ] All tests passing
- [ ] Documentation updated (PRD_WIZARD.md, PRD_SYSTEM.md)
- [ ] Manual tests successful
- [ ] Branch pushed to GitHub

---

## Report Format

When complete, report:

```
✅ Build 1A Complete: PRD Wizard

Branch: build/v3.1-prd-wizard
Status: Pushed to GitHub

Files Created/Updated:
- core/opus_client.py (NEW - 387 lines)
- core/model_switcher.py (NEW - 284 lines)
- core/planning_mode.py (UPDATED - added 156 lines)
- core/prd_wizard.py (UPDATED - rewrote run_wizard())
- tests/test_prd_wizard_complete.py (NEW - 312 lines)
- docs/PRD_WIZARD.md (UPDATED - added 98 lines)
- docs/PRD_SYSTEM.md (UPDATED - added 67 lines)

Tests:
- 45 tests passing
- Coverage: 87%
- Test time: 2.3s

Manual Testing:
- ✓ Wizard with real Opus API
- ✓ Planning mode detection
- ✓ Model switching handoff packages

Ready for Review: ⏸️ Awaiting merge approval
```

---

**DO NOT MERGE THIS BRANCH.** Wait for review before integration.
