# Interactive PRD Builder - Implementation Complete

**Status:** Backend Complete (3 files, ~600 lines) | Frontend Ready for Build
**Date:** 2025-11-18

## What Was Built

### Backend (✅ Complete)

**1. `api/project_manager.py` (197 lines)**
- Creates projects in `~/Projects/{name}`
- Installs BuildRunner in project venv
- Initializes project structure (src/, tests/, docs/)
- Creates .gitignore and README
- Lists all projects

**2. `api/openrouter_client.py` (220 lines)**
- OpenRouter API integration for Claude Opus
- `parse_project_description()` - Converts natural language → structured PRD
- `generate_feature_suggestions()` - On-demand AI suggestions per section
- JSON parsing with markdown code block handling

**3. `api/routes/prd_builder.py` (160 lines)**
- `POST /api/project/init` - Create project + install BR3
- `GET /api/project/list` - List all projects
- `POST /api/prd/parse` - Parse description with AI
- `POST /api/prd/suggestions` - Get AI suggestions (on-demand, not auto-refresh)
- `POST /api/prd/save` - Save PRD to PROJECT_SPEC.md
- Markdown conversion utility

**4. `api/server.py` (modified)**
- Integrated PRD router
- Installed httpx dependency

## Frontend Components Needed

### 1. **ProjectInitWizard.tsx**
```typescript
// Multi-step wizard:
// Step 1: Project name input
// Step 2: Create project (API call)
// Step 3: Choose PRD mode (quick/default/detailed)
// Step 4: Description input
// Step 5: AI parses → Go to PRD builder
```

### 2. **FeatureCard.tsx**
```typescript
// Expandable card component:
// - One-line title (collapsed state)
// - Click to expand → show full description
// - Edit inline
// - Priority badge (high/medium/low)
// - Drag handle for reordering
// - Delete button
```

### 3. **InteractivePRDBuilder.tsx**
```typescript
// Split panel editor:
// LEFT PANEL:
//   - Overview section
//   - Features list (FeatureCard components)
//   - User stories
//   - Technical requirements
//   - Success criteria
//
// RIGHT PANEL (SuggestionsPanel):
//   - "Generate Suggestions" button
//   - Text input for custom requests
//   - List of AI suggestions
//   - Drag suggestions to left panel
//   - Dismiss button per suggestion
//
// BOTTOM:
//   - Save button
//   - Generate Claude Context button
```

### 4. **SuggestionsPanel.tsx**
```typescript
// AI suggestions sidebar:
// - Loads on-demand (when entering section)
// - User can refresh manually
// - Text box: "Ask for specific suggestions..."
// - Suggestion cards with:
//   * Title
//   * Description
//   * Priority badge
//   * Rationale
//   * Drag to add
//   * Dismiss button
```

### 5. Integration Points
```typescript
// Update WorkspaceUI.tsx:
// - Add "New Project" button/flow
// - Show ProjectInitWizard modal/page
// - On init success → Open InteractivePRDBuilder
// - On PRD save → Generate context → Show terminal command
```

## API Flow

### Project Initialization
```
User enters "MyApp" → Click Init
  ↓
POST /api/project/init { project_name: "MyApp" }
  ↓
Backend:
  - Creates ~/Projects/MyApp/
  - python3 -m venv .venv
  - .venv/bin/pip install buildrunner
  - Creates src/, tests/, docs/
  - Creates .gitignore, README
  ↓
Returns: { success: true, project_path: "/Users/.../MyApp" }
```

### PRD Creation
```
User describes: "Build a task management app with real-time collaboration"
  ↓
POST /api/prd/parse { description: "..." }
  ↓
OpenRouter (Opus):
  - Parses description
  - Generates structured PRD
  - Returns JSON with features, stories, tech req
  ↓
UI displays in InteractivePRDBuilder
```

### AI Suggestions
```
User opens "Features" section → Click "Generate Suggestions"
  ↓
POST /api/prd/suggestions {
  project_context: { overview, features },
  section: "features",
  custom_request: null  // or user's specific request
}
  ↓
OpenRouter (Opus):
  - Analyzes current PRD
  - Generates 3-5 relevant suggestions
  - Returns with priorities and rationales
  ↓
UI shows draggable suggestion cards
User drags to add or clicks dismiss
```

### Save PRD
```
User clicks "Save PRD"
  ↓
POST /api/prd/save {
  project_path: "~/Projects/MyApp",
  prd_data: { overview, features, ... }
}
  ↓
Backend converts to markdown → Saves to PROJECT_SPEC.md
  ↓
Returns: { success: true, file_path: ".../PROJECT_SPEC.md" }
```

## Key Design Decisions

### BuildRunnerSaaS Patterns Used
1. **Expandable Cards**: Features as collapsible boxes (not plain markdown)
2. **Split Panel**: Left (your PRD) + Right (AI suggestions)
3. **Drag-and-Drop**: Drag suggestions to add them
4. **On-Demand AI**: Generate when needed, not auto-refresh every 30s
5. **Custom Requests**: Text box to ask for specific suggestions

### Differences from BuildRunnerSaaS
1. **No Preview Mode**: This is pure PRD building (no preview iframe)
2. **No Feedback System**: Direct AI suggestions instead
3. **File-Based**: Saves to project's PROJECT_SPEC.md
4. **Desktop Integration**: Creates real ~/Projects directories

### Dark Theme (Maintained)
- All components use existing dark theme from WorkspaceUI
- VS Code-style colors (#1e1e1e background, #d4d4d4 text)
- Priority badges: 🔴 high, 🟡 medium, 🟢 low

## Environment Setup

### Required Environment Variable
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Add to `.env`:
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

## Testing Checklist

### Backend Tests
- [ ] Create project: `curl -X POST http://localhost:8080/api/project/init -d '{"project_name":"TestApp"}'`
- [ ] List projects: `curl http://localhost:8080/api/project/list`
- [ ] Parse description: Test with sample project description
- [ ] Generate suggestions: Test with sample PRD context
- [ ] Save PRD: Test markdown generation

### Frontend Integration
- [ ] Init wizard flow works end-to-end
- [ ] PRD sections display correctly
- [ ] Feature cards expand/collapse
- [ ] AI suggestions generate on-demand
- [ ] Drag-and-drop works
- [ ] Save creates PROJECT_SPEC.md in correct location
- [ ] Generate Claude context button works

## File Structure

```
api/
├── project_manager.py       # NEW - Project lifecycle
├── openrouter_client.py     # NEW - AI integration
├── routes/
│   └── prd_builder.py      # NEW - PRD API endpoints
└── server.py               # MODIFIED - Added PRD router

ui/src/components/
├── ProjectInitWizard.tsx   # TODO - Init flow
├── FeatureCard.tsx         # TODO - Expandable feature
├── InteractivePRDBuilder.tsx  # TODO - Main editor
├── SuggestionsPanel.tsx    # TODO - AI suggestions
└── WorkspaceUI.tsx         # TODO - Integration

~/Projects/
└── {ProjectName}/
    ├── .venv/              # Python venv with BR3
    ├── src/
    ├── tests/
    ├── docs/
    ├── PROJECT_SPEC.md     # Generated PRD
    ├── .gitignore
    └── README.md
```

## Next Steps

1. **Set OpenRouter API Key** (required)
2. **Build React Components** (4-5 components needed)
3. **Test Init Flow** (create project, verify structure)
4. **Test AI Integration** (parse description, generate suggestions)
5. **End-to-End Test** (full workflow from init → PRD → Claude context)

## Usage Flow (After Implementation)

1. Open BuildRunner UI
2. Click "New Project" → Enter name → Init
3. Choose PRD mode → Enter description
4. AI parses → Populates PRD editor
5. Refine features:
   - Expand cards to edit
   - Click "Suggestions" → AI generates ideas
   - Drag suggestions to add
6. Save PRD → Generate Context
7. UI shows: `claude /Users/.../MyApp/PROJECT_SPEC.md`
8. Run command in terminal → Claude builds

---

**Backend Status:** ✅ Complete and Ready
**Frontend Status:** 🔨 Specs Ready, Components Need Implementation
**Total Backend LOC:** ~600 lines (3 new files)
**Estimated Frontend LOC:** ~800 lines (4-5 components)
