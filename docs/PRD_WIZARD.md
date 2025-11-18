# PRD Wizard - Interactive PROJECT_SPEC Creation

The PRD Wizard provides an interactive, AI-assisted workflow for creating comprehensive PROJECT_SPEC.md files with design intelligence.

## Overview

The wizard guides you through:
1. **App Idea** - Describe what you want to build
2. **Auto-Detection** - AI detects industry + use case
3. **Opus Pre-fill** - Strategic AI pre-fills all sections
4. **Interactive Review** - Accept, modify, or skip each section
5. **Design Architecture** - Industry + use case design profiles merged
6. **Tech Stack** - AI suggests optimal stack
7. **Review & Confirm** - Final review and lock

## Quick Start

```bash
# Start the wizard
br spec wizard

# Follow the prompts:
# 1. Describe your app idea
# 2. Confirm industry and use case (or override)
# 3. Review each pre-filled section
# 4. Accept, customize, or skip sections
# 5. Review design profile
# 6. Accept tech stack suggestion
# 7. Confirm and lock
```

## Commands

### `br spec wizard`
Start interactive PROJECT_SPEC creation wizard

**First-time flow:**
- No existing spec detected
- Full wizard with all steps
- Opus pre-fills based on app description

**Existing spec mode:**
- Spec already exists
- Edit specific sections
- Changes tracked automatically

### `br spec sync`
Sync PROJECT_SPEC to features.json and build plans

**What it does:**
- Parses PROJECT_SPEC.md
- Extracts features, phases, dependencies
- Generates features.json
- Identifies parallel build opportunities

```bash
br spec sync
# Output:
#  Features: 15
#  Phases: 4
#  File: .buildrunner/features.json
#  💡 8 features can be built in parallel
```

### `br spec validate`
Check PROJECT_SPEC completeness

**Validates:**
- Required metadata (industry, use case, tech stack)
- Required sections (PRD, Technical, Design)
- Feature definitions
- Implementation phases

```bash
br spec validate
# Output: ✓ PROJECT_SPEC is complete!
```

### `br spec confirm`
Lock PROJECT_SPEC and generate build plans

**State change:** `draft` → `confirmed` → `locked`

Once confirmed, the spec becomes the immutable contract for development.

### `br spec unlock`
Unlock PROJECT_SPEC for editing (triggers rebuild)

**Warning:** Changes will trigger rebuild when re-confirmed.

## Wizard Flow Details

### Step 1: App Idea
Describe your application in natural language:

```
What do you want to build?
> A healthcare patient dashboard for doctors to view and update patient vitals,
> medication lists, and appointment schedules.
```

### Step 2: Auto-Detection
AI analyzes your description:

```
Detected Industry: healthcare
Detected Use Case: dashboard
Is this correct? (y/n): y
```

**Industries supported:**
- healthcare
- fintech
- ecommerce
- education
- saas
- social
- marketplace
- analytics

**Use cases supported:**
- dashboard
- marketplace
- crm
- analytics

### Step 3: Opus Pre-fill
Opus (strategic AI) pre-fills all sections based on:
- Your app description
- Detected industry
- Detected use case
- Industry best practices
- Design patterns

### Step 4: Interactive Section Review
For each section, you can:

**Options:**
1. **Accept** - Use Opus pre-fill as-is
2. **Request more** - Ask Opus for additional details
3. **Provide custom** - Write your own content
4. **Skip** - Defer for later (marked incomplete)

**Sections:**
- Product Requirements (user stories, success metrics)
- Technical Architecture (tech stack, components, API design)
- Design Architecture (design system, industry patterns, accessibility)

### Step 5: Design Architecture
The wizard:
1. Loads industry profile (e.g., healthcare.yaml)
2. Loads use case profile (e.g., dashboard.yaml)
3. Merges profiles with conflict resolution
4. Researches current best practices
5. Generates design requirements
6. Presents for approval

**Result:** Complete design profile with:
- Colors, typography, spacing
- Required components
- Compliance requirements
- Trust signals
- Accessibility checklist

### Step 6: Tech Stack Suggestion
Based on your use case and design needs:

```
Suggested Tech Stack:
  Frontend: React with TypeScript
  Backend: FastAPI (Python)
  Database: PostgreSQL
Accept? (y/n):
```

### Step 7: Review & Confirm
Review complete PROJECT_SPEC:
- All sections present
- Design profile integrated
- Tech stack selected

**Final confirmation locks the spec.**

## PROJECT_SPEC Structure

```markdown
# PROJECT_SPEC

**Status**: confirmed
**Industry**: healthcare
**Use Case**: dashboard
**Tech Stack**: react-fastapi-postgres

---

# Product Requirements

## Executive Summary
[Product overview]

## User Stories
- As a [user], I want [goal] so that [benefit]

## Success Metrics
- [Metric]: [Target]

---

# Technical Architecture

## Tech Stack
[Stack details]

## Components
[System components]

## API Design
[API structure]

---

# Design Architecture

## Design System
[Design system details]

## Industry Profile
[Healthcare-specific requirements]

## Design Tokens
[Colors, typography, spacing]

## Components
[UI components list]

## Accessibility
[WCAG, ADA compliance]
```

## State Machine

PROJECT_SPEC lifecycle:

```
new → draft → reviewed → confirmed → locked
         ↑                              ↓
         └─────── unlock ───────────────┘
```

**States:**
- `new` - Just created, empty
- `draft` - Being edited, incomplete OK
- `reviewed` - All sections reviewed
- `confirmed` - Approved, locked for builds
- `locked` - Immutable (unlock to edit)

## Best Practices

### 1. Be Descriptive in App Idea
Good: "A fintech dashboard for tracking cryptocurrency portfolio with real-time price updates, transaction history, and tax reporting"

Poor: "Make a crypto app"

### 2. Review All Sections
Don't skip sections - complete specs lead to better builds.

### 3. Lock After Confirmation
Locking prevents accidental architecture drift.

### 4. Use Sync Regularly
Run `br spec sync` after any changes to keep features.json up-to-date.

### 5. Validate Before Building
Always run `br spec validate` before starting implementation.

## Troubleshooting

**Issue:** "No spec found"
**Solution:** Run `br spec wizard` first

**Issue:** "Industry profile not found"
**Solution:** Check that templates/ directory has industry YAML files

**Issue:** "Validation failed"
**Solution:** Run `br spec validate` to see specific issues

**Issue:** "Spec is locked"
**Solution:** Run `br spec unlock` to edit (triggers rebuild)

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

1. **pre_fill_spec()** - Generates complete PROJECT_SPEC from user input
2. **analyze_requirements()** - Extracts features, architecture, tech stack
3. **generate_design_tokens()** - Creates Tailwind-compatible design system
4. **validate_spec()** - Validates completeness and provides suggestions

All API calls include:
- Retry logic with exponential backoff
- Error handling
- Token optimization (<4096 tokens per call)

## Integration with Other Systems

### Features.json
`br spec sync` generates features.json from PROJECT_SPEC

### Build Plans
Confirmed specs generate atomic build plans

### Git Hooks
Specs are validated in pre-commit hooks

### Quality Gates
Architecture guard validates code against spec
