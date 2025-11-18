# PRD System Architecture

Complete guide to BuildRunner's PRD/PROJECT_SPEC system including design intelligence, parsing, mapping, and Opus handoff protocols.

## System Overview

The PRD System transforms high-level product ideas into executable build plans through multiple integrated subsystems:

```
App Idea
   ↓
PRD Wizard (Opus) → PROJECT_SPEC.md
   ↓                        ↓
Industry + Use Case    ← Design Profiler →  Design Researcher
   Profiles                   ↓                    ↓
   ↓                   Design Profile      Best Practices
   ↓                          ↓                    ↓
PRD Parser  ←────────────────┴────────────────────┘
   ↓
PRD Mapper → features.json → Build Plans
   ↓
Opus Handoff → Sonnet Execution
```

## Core Components

### 1. PRD Wizard (`core/prd_wizard.py`)

**Purpose:** Interactive creation of PROJECT_SPEC.md with real Opus API integration

**Key Features:**
- Real Anthropic Opus API integration
- Auto-detection of industry + use case
- Intelligent spec pre-filling using Claude Opus 4
- Automatic model switching (Opus → Sonnet handoff)
- Rich terminal UI with progress indicators
- Async/await pattern for API calls

**New Async Function:**
```python
import asyncio
from core.prd_wizard import run_wizard

# Run wizard (interactive)
result = asyncio.run(run_wizard(interactive=True))

# Run wizard (non-interactive, for testing)
result = asyncio.run(run_wizard(interactive=False))

# Returns:
# {
#   "spec_path": "path/to/PROJECT_SPEC.md",
#   "features_path": "path/to/features.json",
#   "handoff_package": { ... }
# }
```

**Legacy Class-Based API:**
```python
from core.prd_wizard import PRDWizard

wizard = PRDWizard("/path/to/project")
spec = wizard.run()  # Interactive wizard
wizard.write_spec_to_file(spec)
```

### 2. Design Profiler (`core/design_profiler.py`)

**Purpose:** Merge industry + use case design profiles

**Key Features:**
- Load YAML templates
- Intelligent conflict resolution
- Generate design tokens
- Create Tailwind config

**Conflict Resolution Strategy:**
- Industry profile → Compliance, trust, colors
- Use case profile → Layout, navigation, data viz
- Components → Union of both

**Usage:**
```python
from core.design_profiler import DesignProfiler

profiler = DesignProfiler("/path/to/templates")
profile = profiler.create_profile("healthcare", "dashboard")
tokens = profiler.generate_design_tokens(profile)
tailwind_config = profiler.generate_tailwind_config(tokens)
```

### 3. Design Researcher (`core/design_researcher.py`)

**Purpose:** Research current design best practices

**Key Features:**
- Web research integration (simulated for now)
- Pattern extraction
- Best practices compilation
- Save/load research results

**Research Output:**
```python
@dataclass
class DesignResearch:
    patterns: List[str]
    best_practices: List[str]
    components: List[str]
    color_trends: List[str]
    layout_examples: List[str]
    sources: List[str]
```

**Usage:**
```python
from core.design_researcher import DesignResearcher

researcher = DesignResearcher("/path/to/project")
research = researcher.research_design_patterns("fintech", "dashboard")
researcher.save_research(research, "project_name")
```

### 4. PRD Parser (`core/prd_parser.py`)

**Purpose:** Parse PROJECT_SPEC.md into structured data

**Key Features:**
- Extract metadata (status, industry, use case)
- Parse features from user stories
- Extract implementation phases
- Identify dependencies and credentials
- Validate completeness
- Track deltas (incremental updates)

**Parsed Output:**
```python
@dataclass
class ParsedSpec:
    status: str
    industry: str
    use_case: str
    tech_stack: str
    features: List[Feature]
    phases: List[Phase]
    credentials: List[Credential]
    dependencies: Set[str]
    raw_sections: Dict[str, str]
```

**Usage:**
```python
from core.prd_parser import PRDParser

parser = PRDParser("/path/to/PROJECT_SPEC.md")
spec = parser.parse()

# Validate
issues = parser.validate_completeness(spec)

# Track changes
delta = parser.calculate_delta(new_spec)
```

### 5. PRD Mapper (`core/prd_mapper.py`)

**Purpose:** Map PROJECT_SPEC to features.json

**Key Features:**
- Convert spec to features.json format
- Auto-generate feature entries
- Bidirectional sync
- Generate atomic task lists
- Identify parallel vs sequential builds

**Features JSON Structure:**
```json
{
  "version": "3.0.0",
  "project": {
    "name": "healthcare_dashboard_app",
    "industry": "healthcare",
    "use_case": "dashboard",
    "status": "confirmed"
  },
  "features": [
    {
      "id": "feature_1",
      "name": "Patient Vitals View",
      "priority": "high",
      "status": "planned",
      "dependencies": [],
      "tasks": [...]
    }
  ],
  "phases": [...]
}
```

**Usage:**
```python
from core.prd_mapper import PRDMapper

mapper = PRDMapper("/path/to/project")
features_data = mapper.sync_spec_to_features()
mapper.save_features_json(features_data)

# Identify parallel builds
parallel_groups = mapper.identify_parallel_builds(features_data)
```

### 6. Opus Handoff (`core/opus_handoff.py`)

**Purpose:** Optimize Opus → Sonnet model handoff

**Key Features:**
- Create compact context packages
- Generate atomic task lists
- Identify key decision points
- Build execution-ready instructions
- Minimize context while preserving critical info

**Handoff Package:**
```python
@dataclass
class HandoffPackage:
    project_summary: str
    technical_decisions: List[str]
    build_instructions: List[Dict]
    atomic_tasks: List[Dict]
    context_files: List[str]
    success_criteria: List[str]
```

**Usage:**
```python
from core.opus_handoff import OpusHandoff

handoff = OpusHandoff("/path/to/project")
package = handoff.create_handoff_package()
prompt = handoff.generate_sonnet_prompt(package)
```

### 7. Opus Client (`core/opus_client.py`) **NEW**

**Purpose:** Real Anthropic Opus API integration for PRD generation

**Key Features:**
- Async/await pattern with AsyncAnthropic client
- Retry logic with exponential backoff
- Comprehensive error handling
- Token-optimized prompts (<4096 tokens)
- Model: claude-opus-4-20250514

**API Methods:**
```python
from core.opus_client import OpusClient

opus = OpusClient(api_key="sk-ant-...")

# Generate complete PROJECT_SPEC
spec = await opus.pre_fill_spec(
    industry="Healthcare",
    use_case="Dashboard",
    user_input={
        "project_name": "Patient Portal",
        "description": "Healthcare dashboard for patient vitals"
    }
)

# Analyze requirements
analysis = await opus.analyze_requirements("Build a patient dashboard")
# Returns: {features: [...], architecture: {...}, tech_stack: [...]}

# Generate design tokens
tokens = await opus.generate_design_tokens("Healthcare", "Dashboard")
# Returns: Tailwind-compatible design system

# Validate spec
validation = await opus.validate_spec(spec_content)
# Returns: {valid: bool, missing_sections: [], suggestions: [], score: 0-100}
```

**Error Handling:**
- OpusAPIError for all API failures
- Automatic retry with 2^attempt backoff
- Max 3 retries per call

### 8. Model Switcher (`core/model_switcher.py`) **NEW**

**Purpose:** Efficient Opus → Sonnet handoff protocol

**Key Features:**
- Context compression (<2000 tokens)
- Handoff package creation
- Sonnet prompt generation
- Package validation
- Persistent storage

**Compression Rules:**
- Spec summary: max 1000 chars
- Feature descriptions: max 200 chars each
- Next steps: max 3 prioritized items

**Usage:**
```python
from core.model_switcher import ModelSwitcher
from pathlib import Path

switcher = ModelSwitcher(Path("/path/to/project"))

# Create handoff package
package = switcher.create_handoff_package(
    spec_path=Path(".buildrunner/PROJECT_SPEC.md"),
    features_path=Path(".buildrunner/features.json"),
    context={
        "industry": "Healthcare",
        "use_case": "Dashboard",
        "constraints": ["HIPAA compliant", "Use TypeScript"]
    }
)

# Package structure:
# {
#   "version": "1.0",
#   "timestamp": "20250124_143022",
#   "source_model": "claude-opus-4",
#   "target_model": "claude-sonnet-4.5",
#   "spec_summary": "...",
#   "features": [...],
#   "architecture": {...},
#   "constraints": [...],
#   "next_steps": [...],
#   "sonnet_prompt": "..."
# }

# Load handoff later
loaded = switcher.load_handoff("20250124_143022")
```

**Handoff Storage:**
- Location: `.buildrunner/handoffs/`
- Format: `handoff_YYYYMMDD_HHMMSS.json`
- Validated before saving

### 9. Planning Mode Detector (`core/planning_mode.py`)

**Purpose:** Auto-detect strategic vs tactical conversations

**Key Features:**
- Enhanced keyword-based detection
- Project state awareness
- Confidence scoring (0.0-1.0)
- Automatic mode recommendation

**New Enhanced Functions:**
```python
from core.planning_mode import (
    detect_planning_mode,
    should_use_opus,
    should_use_sonnet,
    get_project_state
)

# Get project state
state = get_project_state(Path("/path/to/project"))
# Returns: {has_spec: bool, has_features: bool, features: [...], ...}

# Detect mode
detection = detect_planning_mode(
    user_prompt="Design the user authentication architecture",
    project_state=state,
    conversation_history=[]
)
# Returns: {use_opus: bool, confidence: float, reason: str}

# Decision helpers
if should_use_opus(detection, confidence_threshold=0.7):
    # Use Opus for planning
    pass

if should_use_sonnet(detection, confidence_threshold=0.7):
    # Use Sonnet for execution
    pass
```

**Detection Logic:**
- **New project** (no spec): Auto-recommend Opus (confidence: 0.95)
- **Planning keywords** ("design", "architecture", "plan"): Recommend Opus
- **Execution keywords** ("implement", "build", "fix"): Recommend Sonnet
- **Ambiguous**: Default to Sonnet for existing projects, Opus for new

**Legacy Class-Based API:**
```python
from core.planning_mode import PlanningModeDetector

detector = PlanningModeDetector("/path/to/project")
mode, confidence = detector.detect_mode(user_input)
suggested_model = detector.suggest_model(mode, confidence)
```

## Template System

### Industry Profiles (`templates/industries/`)

**Structure:**
```yaml
name: healthcare
description: Healthcare and medical applications
colors:
  primary: "#0066CC"
  secondary: "#00A86B"
  success: "#00A86B"
  warning: "#FFB020"
  error: "#DC3545"
typography:
  font_family: "Inter, system-ui, sans-serif"
  scale: {...}
components:
  - Button
  - PatientCard
  - VitalsWidget
compliance:
  - HIPAA
  - WCAG 2.1 AA
  - ADA
trust_signals:
  - HIPAA compliance badge
  - Secure data encryption
```

**Available Industries:**
- healthcare
- fintech
- ecommerce
- education
- saas
- social
- marketplace
- analytics

### Use Case Profiles (`templates/use_cases/`)

**Structure:**
```yaml
name: dashboard
description: Dashboard and analytics interface
layout_patterns:
  - Sidebar navigation
  - Widget-based main area
  - Responsive grid
navigation:
  type: sidebar
  position: left
  collapsible: true
components:
  - StatCard
  - LineChart
  - DataTable
data_viz:
  - Time series charts
  - KPI cards
```

**Available Use Cases:**
- dashboard
- marketplace
- crm
- analytics

### Tech Stack Templates (`templates/tech_stacks/`)

**Example:**
```yaml
name: react-fastapi-postgres
frontend:
  framework: React
  language: TypeScript
  styling: Tailwind CSS
backend:
  framework: FastAPI
  language: Python 3.11+
  orm: SQLAlchemy
database:
  primary: PostgreSQL 15+
  cache: Redis
```

## Data Flow

### 1. Creation Flow

```
User Input (App Idea)
  ↓
Industry + Use Case Detection
  ↓
Opus Pre-fill (Strategic Planning)
  ↓
Interactive Section Editing
  ↓
Design Profile Merger
  ↓
Design Research
  ↓
Tech Stack Suggestion
  ↓
PROJECT_SPEC.md (Confirmed)
```

### 2. Sync Flow

```
PROJECT_SPEC.md
  ↓
PRD Parser (Extract Features, Phases, Dependencies)
  ↓
PRD Mapper (Generate Atomic Tasks)
  ↓
features.json
  ↓
Build Plan Generator
  ↓
Parallel Build Groups
```

### 3. Execution Flow

```
Confirmed PROJECT_SPEC
  ↓
Opus Handoff Package Creation
  ↓
Compact Context Generation
  ↓
Sonnet Execution Prompt
  ↓
Atomic Task Execution
  ↓
Build Complete
```

## CLI Integration

All PRD system components accessible via CLI:

```bash
# Wizard
br spec wizard

# Sync
br spec sync

# Validate
br spec validate

# Design
br design profile healthcare dashboard
br design research

# Confirm/Lock
br spec confirm
br spec unlock
```

## API Integration

All PRD operations available via FastAPI endpoints (Build 2B):

```
GET  /spec/status
POST /spec/wizard/start
POST /spec/sync
GET  /spec/validate
POST /spec/confirm
```

## Best Practices

### 1. Always Use Wizard for First-Time
Don't manually create PROJECT_SPEC.md - use the wizard for proper structure.

### 2. Sync After Every Change
Run `br spec sync` after any spec changes to keep features.json current.

### 3. Validate Before Confirm
Always run `br spec validate` before confirming to catch issues early.

### 4. Lock After Confirmation
Lock specs to prevent accidental architecture drift.

### 5. Use Design Profiles
Leverage industry + use case profiles for consistent, compliant designs.

## Troubleshooting

### Common Issues

**Wizard doesn't detect industry correctly:**
- Be more specific in app description
- Mention industry explicitly
- Override auto-detection when prompted

**Design profiles not loading:**
- Check templates/ directory exists
- Verify YAML files are valid
- Ensure file names match (lowercase, no spaces)

**Sync fails:**
- Validate spec first: `br spec validate`
- Check PROJECT_SPEC.md structure
- Ensure all required sections present

**Features.json not updating:**
- Run `br spec sync` after spec changes
- Check spec state (must be `confirmed` or later)

## Architecture Decisions

### Why PROJECT_SPEC over Traditional PRD?

**Traditional PRD:**
- Human-readable docs
- Disconnected from implementation
- Becomes stale quickly

**PROJECT_SPEC:**
- AI-optimized format
- Direct mapping to features.json
- Single source of truth
- Automatically synced
- Enforced via git hooks

### Why Industry + Use Case Profiles?

**Benefits:**
- Consistent designs across similar apps
- Built-in compliance requirements
- Proven patterns from research
- Faster time-to-market
- Reduced decision fatigue

### Why Opus for Planning, Sonnet for Execution?

**Opus Strengths:**
- Strategic thinking
- Complex trade-off analysis
- Long-term planning
- Architectural decisions

**Sonnet Strengths:**
- Fast execution
- Code implementation
- Tactical decisions
- Cost-effective for repetitive tasks

**Handoff Protocol:**
- Opus creates strategic plan
- Compact handoff package
- Sonnet executes tactically
- Best of both models

## Future Enhancements

### Planned Features
- Visual spec editor (web UI)
- Template marketplace
- Multi-project specs
- Spec versioning with branches
- Collaborative editing
- AI-powered gap analysis
- Auto-update from production metrics

### Integration Roadmap
- Figma design import
- Jira/Linear sync
- Notion documentation export
- Slack notifications
- GitHub Issues integration
