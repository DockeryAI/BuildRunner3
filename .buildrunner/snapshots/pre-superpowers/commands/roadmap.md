---
description: Roadmap - View and manage feature horizons (now/next/later) and releases
allowed-tools: Read, Write, Edit, Bash, Grep
model: opus
---

# Roadmap Manager

You are managing the project roadmap - viewing and organizing features across horizons and releases.

---

## Step 1: Discover & Load Current State

### 1.1 Check for Roadmap Structure
```bash
# Check for .buildrunner structure
ls -la .buildrunner/ROADMAP.md .buildrunner/features.json 2>/dev/null | head -5

# Check for alternative locations
ls -la ROADMAP.md features.json 2>/dev/null | head -5

# Check if br CLI is available
which br 2>/dev/null && br roadmap show 2>/dev/null | head -30
```

### 1.2 Read Roadmap (whichever exists)
@.buildrunner/ROADMAP.md
@ROADMAP.md

### 1.3 Read Features (if exists)
@.buildrunner/features.json

---

## Step 2: Display Roadmap View

Present the roadmap in this format:

```markdown
## Project Roadmap

### NOW - Release [X.X] (Active)
| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | [Name] | [High/Med/Low] | [planned/in_progress/complete] |

### NEXT - Release [X.X] (Planned)
| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | [Name] | [High/Med/Low] | [planned] |

### LATER - Release [X.X] (Future)
| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | [Name] | [High/Med/Low] | [planned] |

### Unassigned (No Horizon)
| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | [Name] | [High/Med/Low] | [status] |
```

**Number features sequentially across all horizons for easy reference.**

---

## Step 3: Handle Commands

Listen for these patterns in the conversation:

### View Commands
- "show roadmap" / "view roadmap" → Display full roadmap (Step 2)
- "show now" / "what's current" → Show only NOW horizon
- "show next" / "what's planned" → Show only NEXT horizon
- "show later" / "what's future" → Show only LATER horizon
- "show release 3.3" → Show features for specific release

### Move Commands
- "move X to next" → Move feature #X to NEXT horizon
- "move X to later" → Move feature #X to LATER horizon
- "move X to now" → Promote feature #X to NOW horizon
- "move X to 4.0" → Move feature #X to release 4.0
- "move 'feature name' to next" → Move by name match

### Add Commands
- "add 'feature' to later" → Quick-add feature to LATER
- "add 'feature' to 4.0" → Quick-add to specific release

---

## Step 4: Execute Moves

When moving features:

### 4.1 Identify Feature
- If number given: Map to feature from numbered list
- If quoted text: Search for matching feature name

### 4.2 Determine Target
- If horizon (now/next/later): Set horizon field
- If release (X.X format): Set release field AND infer horizon
  - Current release version → now
  - Next release version → next
  - Future release version → later

### 4.3 Update Feature
```bash
# If br CLI available
which br 2>/dev/null && br feature update [FEATURE_ID] --horizon [now/next/later] --release [X.X]
```

If no br CLI, edit features.json directly or skip if it doesn't exist.

### 4.4 Update ROADMAP.md
After any move, regenerate the relevant section of ROADMAP.md.

### 4.5 Confirm Change
> "✅ Moved '[Feature Name]' to [HORIZON] (Release [X.X])"

---

## Step 5: Quick-Add Features

When adding new features to roadmap:

### 5.1 Generate Feature ID
Format: `feat-[NNN]` where NNN is next sequential number

### 5.2 Add to features.json (if br CLI available)
```bash
which br 2>/dev/null && br feature add "[Name]" --priority [low/medium/high] --horizon [horizon] --release [X.X]
```

If no br CLI, add directly to ROADMAP.md.

### 5.3 Confirm Addition
> "✅ Added '[Feature Name]' to [HORIZON] (Release [X.X])"

---

## Step 6: Release Management

### Promote Releases
When user says "release 3.2 is done" or "promote releases":
1. Move all "next" features to "now"
2. Move all "later" features to "next"
3. Update ROADMAP.md release definitions
4. Create new "later" release placeholder

### Define New Release
When user says "add release 4.1":
1. Add to ROADMAP.md release definitions
2. Set as new "later" horizon target

---

## Horizon-to-Release Mapping

Maintain this mapping in ROADMAP.md:

| Horizon | Release | Theme |
|---------|---------|-------|
| now | 3.2 | Context Preservation |
| next | 3.3 | Parallel Orchestration |
| later | 4.0 | Major Rewrite |

When moving features, use this mapping to set both fields consistently.

---

## Output Format

Always show updated roadmap section after changes:

```markdown
## Updated Roadmap

[Show affected horizon(s) with numbered features]

**Changes made:**
- Moved "Feature X" from NOW to LATER (4.0)
- Added "Feature Y" to NEXT (3.3)
```

---

## Rules

1. **Always number features** - Makes referencing easy
2. **Show changes clearly** - Confirm what was moved/added
3. **Keep horizons balanced** - Warn if NOW has too many items
4. **Maintain release mapping** - Horizon and release should align
5. **Update both files** - features.json AND ROADMAP.md stay in sync
