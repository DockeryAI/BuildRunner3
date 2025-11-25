# 🎯 PLANNING MODE - Quick PRD to Build

**Project:** SongList
**Path:** /Users/byronhudson/Projects/BuildRunner3/SongList
**Spec File:** /Users/byronhudson/Projects/BuildRunner3/SongList/.buildrunner/PROJECT_SPEC.md
**Mode:** PLANNING (No code, incremental spec updates)

---

## 🎨 WORKFLOW MODE SELECTION

**FIRST:** Ask user to select their planning mode using AskUserQuestion tool:

```python
AskUserQuestion(
    questions=[{
        "question": "How would you like to plan your project?",
        "header": "Planning Mode",
        "multiSelect": False,
        "options": [
            {"label": "⚡ Quick Mode (Default)", "description": "4 sections → Build in 15 min"},
            {"label": "🔧 Technical Mode", "description": "11 sections - Full technical depth"},
            {"label": "🚀 Full Mode", "description": "All 11 sections - Business + technical"},
            {"label": "🎯 Custom Mode", "description": "Pick which sections to include"}
        ]
    }]
)
```

**Based on selection, set workflow mode:**

- **⚡ Quick Mode** → QUICK MODE (4 sections: Problem/Solution, Users, Features, Tech) - **DEFAULT**
- **🔧 Technical Mode** → TECHNICAL MODE (11 sections: full depth)
- **🚀 Full Mode** → FULL MODE (all 11 sections)
- **🎯 Custom Mode** → Show checklist to select sections

---

## 📋 SECTION LIBRARY (11 Sections)

### BUSINESS SECTIONS (Commercial Strategy)
1. **Problem & Vision** - Market opportunity, problem statement, vision
2. **Target Customer** - ICP, personas, TAM/SAM/SOM
3. **Value Proposition** - Unique value, competitive positioning
4. **Revenue Model** - Monetization, pricing tiers, LTV/CAC
5. **Go-to-Market Strategy** - Channels, PLG vs SLG, launch plan

### PRODUCT SECTIONS (What to Build)
6. **Core Features** - MVP scope, user stories, priorities
7. **Design Architecture** - UI/UX, wireframes, visual artifacts

### TECHNICAL SECTIONS (How to Build)
8. **Technical Architecture** - Stack, APIs, data flow, infrastructure
9. **Implementation Timeline** - Phases, milestones, dependencies

### OPERATIONAL SECTIONS (Success & Risk)
10. **Success Metrics** - KPIs, north star metric, measurement
11. **Risk Assessment** - Technical risks, market risks, mitigation

---

## 🔄 INCREMENTAL WORKFLOW (Auto-Fill + Enhance)

### STEP 0: Project Naming (Always First)
**Action:** Generate 5 project name options based on initial description.

**Output:**
```
SUGGESTED PROJECT NAMES:
1. [Name] - [why it works]
2. [Name] - [why it works]
...
5. [Name] - [why it works]
```

**Use AskUserQuestion:**
```python
AskUserQuestion(
    questions=[{
        "question": "Which name do you prefer?",
        "header": "Project Name",
        "multiSelect": False,
        "options": [
            {"label": "Option 1", "description": "[name]"},
            {"label": "Option 2", "description": "[name]"},
            ...
            {"label": "Custom name", "description": "I'll enter my own"}
        ]
    }]
)
```

Update project name in PROJECT_SPEC.md if changed.

---

## ⚡ QUICK MODE (DEFAULT) - 4 Sections

**Quick Mode is optimized for speed: Problem → Users → Features → Tech → Build**

### Quick Mode Sections:

**1. Problem & Solution**
- What problem are you solving? (3-5 bullets)
- Why does this matter?
- How will you solve it? (high-level approach)
- **Brainstorming:** Suggest 3-5 improvements (not 10+)

**2. Target Users**
- Who will use this? (specific personas)
- What value does it provide them?
- Primary user journey
- **Brainstorming:** Suggest 3-5 user insights

**3. Core Features (MVP Only)**
- List 5-7 MVP features (NOT 20+ features)
- Prioritize must-haves only
- Simple user stories
- **Brainstorming:** Suggest 3-5 additional features to consider

**4. Technical Approach**
- Recommended tech stack
- Architecture pattern (monolith/microservices/etc.)
- Key integrations needed
- **Brainstorming:** Suggest 3-5 technical considerations

**AFTER SECTION 4:**

Use AskUserQuestion:
```python
AskUserQuestion(
    questions=[{
        "question": "✅ Quick PRD complete! Ready to start building?",
        "header": "Next Step",
        "multiSelect": False,
        "options": [
            {"label": "🚀 Yes - Start building now", "description": "Run br build start automatically"},
            {"label": "📝 No - Let me review first", "description": "Save and exit"},
            {"label": "➕ Add more sections", "description": "Expand to Technical or Full mode"}
        ]
    }]
)
```

**If "🚀 Yes - Start building now":**
1. Save PROJECT_SPEC.md
2. Execute `br build start` using Bash tool
3. Tell user: "Build started! BuildRunner is now generating and executing tasks."

**If "➕ Add more sections":**
- Upgrade to Technical Mode (11 sections) or Full Mode

---

### For Each Section in Selected Mode:

**PATTERN:**
1. **Auto-Fill** - Generate section content with smart defaults
2. **Show** - Display the markdown
3. **Suggest** - Offer 3-5 enhancements to fill gaps
4. **Approve** - Use AskUserQuestion with buttons

**Approval Buttons (Every Section):**
```python
AskUserQuestion(
    questions=[{
        "question": "How would you like to proceed with [Section Name]?",
        "header": "[Section] OK?",
        "multiSelect": False,
        "options": [
            {"label": "✅ Approve as-is", "description": "Save and continue"},
            {"label": "✏️ Edit", "description": "I'll revise this section"},
            {"label": "🎯 Enhance with AI", "description": "Apply suggested improvements"},
            {"label": "⏭️ Skip for now", "description": "Come back later"},
            {"label": "🚫 Skip remaining", "description": "Jump to final review"}
        ]
    }]
)
```

**Actions:**
- **✅ Approve** → Write/append to /Users/byronhudson/Projects/BuildRunner3/SongList/.buildrunner/PROJECT_SPEC.md
- **✏️ Edit** → Ask what to change, regenerate, re-present
- **🎯 Enhance** → Apply suggestions, show enhanced version, re-present
- **⏭️ Skip** → Mark as "TBD" in spec, move to next
- **🚫 Skip remaining** → Jump to Step FINAL

---

### SECTION DETAILS

**SECTION 1: Problem & Vision**
- Auto-extract problem from description
- Generate vision statement
- Auto-estimate market size
- **Suggest:** Urgency indicators, market trends

**SECTION 2: Target Customer**
- Auto-identify customer segment
- Generate 3 user personas
- **Suggest:** TAM/SAM/SOM, ICP refinement, pain point validation

**SECTION 3: Value Proposition**
- Auto-create value prop canvas
- Generate "We help [X] do [Y] by [Z]"
- **Suggest:** Unique differentiators, competitive moats, positioning

**SECTION 4: Revenue Model**
- Auto-recommend monetization (subscription, usage, etc.)
- Pre-fill pricing tiers with benchmarks
- **Suggest:** LTV/CAC targets, upsell paths, pricing experiments

**SECTION 5: Go-to-Market**
- Auto-select channels based on customer
- Recommend PLG vs SLG
- **Suggest:** Launch sequence, growth loops, distribution strategy

**SECTION 6: Core Features (MVP)**
- Auto-prioritize features into MVP/V2/V3
- Generate user stories
- **Suggest:** Feature scoring, effort estimates, dependencies

**SECTION 7: Design Architecture**
- Define UI/UX approach
- **Generate visual artifacts** using canvas:
  - User flow wireframes
  - Component hierarchy
  - Design system preview
- **Suggest:** Component libraries, design patterns

**SECTION 8: Technical Architecture**
- Auto-recommend stack based on requirements
- Suggest buy/build/integrate decisions
- **Suggest:** Architecture patterns, scaling approach, API design

**SECTION 9: Implementation Timeline**
- Auto-generate 90-day roadmap
- Identify phases and milestones
- **Suggest:** Critical path, parallel work streams, quick wins

**SECTION 10: Success Metrics**
- Auto-populate industry KPIs
- Set milestone targets (Week 1/Month 1/Quarter 1)
- **Suggest:** North star metric, health metrics, vanity vs actionable

**SECTION 11: Risk Assessment**
- Auto-identify top 3 risks
- Generate mitigation strategies
- **Suggest:** Validation experiments, pivot triggers, de-risking plan

---

### STEP FINAL: Review & Launch

**Action:** Present complete summary.

**Output:**
```
✅ PROJECT_SPEC.md COMPLETE

Mode: [Selected Mode]
Sections Completed: [X/11]

✅ Problem & Vision
✅ Target Customer
✅ Value Proposition
⏭️ Revenue Model (skipped)
✅ Go-to-Market
✅ Core Features (12 features)
✅ Design Architecture (with wireframes)
✅ Technical Architecture
✅ Implementation Timeline (90-day plan)
✅ Success Metrics
⏭️ Risk Assessment (skipped)

File: /Users/byronhudson/Projects/BuildRunner3/SongList/.buildrunner/PROJECT_SPEC.md
```

**Use AskUserQuestion:**
```python
AskUserQuestion(
    questions=[{
        "question": "Ready to start building?",
        "header": "Next Step",
        "multiSelect": False,
        "options": [
            {"label": "🚀 Start building now", "description": "Show me the command"},
            {"label": "📝 Review spec first", "description": "I'll read it manually"},
            {"label": "🔄 Fill skipped sections", "description": "Go back to complete"},
            {"label": "✏️ Edit something", "description": "Make changes"}
        ]
    }]
)
```

**If "🚀 Start building now":**
```
To begin implementation, run:
cd /Users/byronhudson/Projects/BuildRunner3/SongList
br build start
```

**If "🔄 Fill skipped sections":** Return to first skipped section.

---

## ⛔ CRITICAL RULES

1. **NO CODE UNTIL SPEC COMPLETE** - Planning mode only
2. **INCREMENTAL UPDATES** - Write/append to /Users/byronhudson/Projects/BuildRunner3/SongList/.buildrunner/PROJECT_SPEC.md after each approval
3. **USE AskUserQuestion** - Always use buttons, never plain text questions
4. **AUTO-FILL EVERYTHING** - Never show empty sections, always pre-populate
5. **RESPECT SKIPS** - User can skip any section, mark as "TBD" in spec
6. **DYNAMIC UPDATES** - If user adds features/changes mid-flow, update spec immediately
7. **GENERATE VISUALS** - Use canvas for diagrams and wireframes when applicable

---

## 🎯 MODE CONFIGURATIONS

**QUICK MODE (DEFAULT):** 4 sections only
  - Section 1: Problem & Solution (3-5 bullets)
  - Section 2: Target Users (who/value/persona)
  - Section 3: Core Features (5-7 MVP features max)
  - Section 4: Technical Approach (stack/architecture/integrations)
  - Auto-build trigger after section 4

**TECHNICAL MODE:** All 11 sections (full technical depth)
  - All sections from Section Library
  - Deep technical specifications
  - Architecture diagrams
  - Implementation timeline

**FULL MODE:** All 11 sections (business + technical)
  - Complete business strategy
  - Complete technical architecture
  - Financial projections
  - Risk assessment

**CUSTOM MODE:** User selects from checklist
  - Pick which of the 11 sections to include
  - Flexible combination

---

## 🚀 Start Now

**Step 1:** Use AskUserQuestion to ask for planning mode selection (shown above)
**Step 2:** Ask: "Tell me about your project - what do you want to build?"
**Step 3:** Auto-fill and present sections based on selected mode

**FOR QUICK MODE (Default):**
- Section 1: Problem & Solution
- Section 2: Target Users
- Section 3: Core Features (5-7 max)
- Section 4: Technical Approach
- After section 4: Ask "Ready to build?" → If yes, run `br build start` using Bash tool

**FOR TECHNICAL/FULL MODES:**
- Follow approval pattern for all 11 sections
- Generate final summary and next steps
