---
description: Later - Move features from current build to roadmap (next/later horizons)
allowed-tools: Read, Write, Edit, Bash, Grep
model: opus
---

# Move to Later

You are moving features out of the current build into future releases on the roadmap.

---

## Step 1: Understand Context

### 1.1 Check for Active /bp Session
If `/bp` was just run and features are numbered, use that numbering.

### 1.2 Discover Project Structure
```bash
# Check for .buildrunner structure
ls -la .buildrunner/ 2>/dev/null | head -5

# Find build plans
ls -t .buildrunner/builds/BUILD_*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null | head -50

# Check for alternative locations
ls -la ROADMAP.md BUILD*.md 2>/dev/null | head -5
```

### 1.3 Load Roadmap State (if exists)
@.buildrunner/ROADMAP.md
@ROADMAP.md

### 1.4 Load Features (if exists)
@.buildrunner/features.json

---

## Step 2: Parse User Intent

The `/later` command supports multiple formats:

### Format A: Numbers from /bp triage
```
/later 3,4 to next
/later 2,5,7 to 4.0
/later 3
```

### Format B: Quoted feature names
```
/later "dark mode" to next
/later "PDF export, analytics" to 4.0
/later "auth improvements"
```

### Format C: Interactive (no arguments)
```
/later
```
→ Show numbered list and ask what to move

### Format D: Inline conversation tags
If user tagged items during conversation with `[later]`, `[next]`, `[4.0]`:
```
/extract
```
→ Find all tagged items and move them

---

## Step 3: Identify Features to Move

### 3.1 From Numbers
Map numbers to features from:
1. Active /bp feature table (if recent)
2. Current build plan features
3. All features numbered sequentially

### 3.2 From Quoted Text
Search for matching features by:
1. Exact name match
2. Partial name match
3. Description contains text

### 3.3 From Tags
Scan conversation for patterns:
- `[later]` → move to later horizon
- `[next]` → move to next horizon
- `[X.X]` → move to specific release

---

## Step 4: Determine Target

### 4.1 Explicit Target Given
- `to next` → horizon: next
- `to later` → horizon: later
- `to now` → horizon: now (promote)
- `to X.X` → release: X.X, infer horizon from ROADMAP.md mapping

### 4.2 No Target Given - Claude Suggests
Analyze each feature and suggest based on:

**Suggest NEXT if:**
- Feature is a natural extension of current work
- Low complexity, could fit in next release
- Dependencies are in current release

**Suggest LATER if:**
- Feature is a major new capability
- High complexity or architectural change
- Would require significant design work
- Nice-to-have, not blocking anything

Present suggestion:
```markdown
## Suggested Placement

| Feature | Suggested | Reason |
|---------|-----------|--------|
| Dark mode | next (3.3) | UI enhancement, low complexity |
| PDF export | later (4.0) | Requires new document system |

**Accept suggestions? Or specify: "dark mode to 4.0, pdf to next"**
```

---

## Step 5: Confirm Before Moving

Always show what will be moved:

```markdown
## Moving to Later

| Feature | From | To |
|---------|------|------|
| Dark mode | now (3.2) | next (3.3) |
| PDF export | now (3.2) | later (4.0) |

**Confirm? (yes/no or adjust)**
```

Wait for confirmation unless user said "just do it" or similar.

---

## Step 6: Execute Moves

### 6.1 Update features.json (if available)
For each feature:
```bash
# Check for br CLI
which br 2>/dev/null && br feature update [FEATURE_ID] --horizon [horizon] --release [X.X]
```

If no br CLI, edit `.buildrunner/features.json` directly or skip if it doesn't exist.

### 6.2 Update Build Plan
Remove moved features from current BUILD_*.md or mark as "Moved to [release]"

### 6.3 Update ROADMAP.md
Add features to appropriate horizon section.

### 6.4 Log Decision
```bash
# If br CLI available
which br 2>/dev/null && br decision log "Moved [features] to [horizon] ([release]) - [reason]" --type DECISION

# Fallback
echo "[$(date +%Y-%m-%d\ %H:%M)] [DECISION] Moved [features] to [horizon] ([release])" >> .buildrunner/context/decisions.log 2>/dev/null || true
```

---

## Step 7: Confirm Completion

```markdown
## ✅ Moved to Roadmap

**Removed from current build (3.2):**
- Dark mode → next (3.3)
- PDF export → later (4.0)

**Current build now has:** [N] features remaining

**Next steps:**
- Continue with /bp for remaining features
- Use /roadmap to view full roadmap
```

---

## Interactive Mode Flow

When `/later` is called with no arguments:

### Step A: Show Current Features
```markdown
## Current Build Features

| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | Auth system | High | in_progress |
| 2 | Dark mode | Medium | planned |
| 3 | PDF export | Low | planned |
| 4 | Analytics | Medium | planned |

**Which features to move to later?**
Examples:
- "2,3 to next"
- "3,4 to 4.0"
- "2" (I'll suggest where)
```

### Step B: Process Response
Parse user's selection and proceed with Steps 4-7.

---

## Extract Mode Flow

When user says `/extract` or conversation contains `[later]` tags:

### Step A: Scan Conversation
Find all instances of:
- Feature discussions with `[later]`
- Feature discussions with `[next]`
- Feature discussions with `[X.X]`

### Step B: List Found Items
```markdown
## Tagged for Later

| Feature | Tag | Source |
|---------|-----|--------|
| "dark mode toggle" | [next] | Line ~45 |
| "export to PDF" | [4.0] | Line ~67 |

**Move these? (yes/no)**
```

### Step C: Execute
On confirmation, move each to tagged destination.

---

## Rules

1. **Always confirm** - Don't move without user acknowledgment
2. **Show reasoning** - When suggesting, explain why
3. **Keep build focused** - Moving to later helps scope management
4. **Update all files** - features.json, BUILD_*.md, ROADMAP.md
5. **Log decisions** - Record what was moved and why
6. **Preserve context** - Note original priority/status when moving
