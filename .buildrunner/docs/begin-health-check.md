# Code Health Check Reference

This document covers the mandatory code health checklist that MUST be completed before entering plan mode.

---

## Purpose

This step prevents:
- Parallel/competing code paths
- Dead code accumulation
- Reinventing existing utilities
- API key exposure

---

## Code Health Checklist Template

**You MUST output this checklist explicitly before planning. Copy this template and fill it in:**

```
═══════════════════════════════════════════════════════════════════
📋 CODE HEALTH CHECKLIST - Phase [N]: [Phase Name]
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ 2.5.1 REUSE ANALYSIS                                            │
├─────────────────────────────────────────────────────────────────┤
│ Planned feature keywords: [keyword1, keyword2, keyword3]        │
│                                                                 │
│ Search results:                                                 │
│ □ grep "[keyword1]" src/ → [N files found / none]              │
│ □ grep "[keyword2]" src/ → [N files found / none]              │
│                                                                 │
│ Existing code to REUSE:                                         │
│ - [file path]: [what it does] → WILL EXTEND                    │
│ - [none found - creating new]                                   │
│                                                                 │
│ VERDICT: [REUSE X / CREATE NEW Y]                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2.5.2 COMPETING CODE DETECTION                                  │
├─────────────────────────────────────────────────────────────────┤
│ Searched for parallel implementations:                          │
│ □ Services doing similar thing: [list or "none"]               │
│ □ Multiple fetch/API patterns: [list or "none"]                │
│ □ Duplicate utilities: [list or "none"]                        │
│                                                                 │
│ Competing code found:                                           │
│ - [file1] and [file2] both do [X] → CONSOLIDATE                │
│ - [none found]                                                  │
│                                                                 │
│ VERDICT: [CLEAN / CONSOLIDATE REQUIRED - add to plan]          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2.5.3 DEAD CODE DETECTION                                       │
├─────────────────────────────────────────────────────────────────┤
│ Scanned files this phase will touch:                            │
│ □ [file1]: unused imports? [yes/no] unused exports? [yes/no]   │
│ □ [file2]: unused imports? [yes/no] unused exports? [yes/no]   │
│                                                                 │
│ Dead code found:                                                │
│ - [file]: [unused function/import] → REMOVE                    │
│ - [none found]                                                  │
│                                                                 │
│ VERDICT: [CLEAN / CLEANUP REQUIRED - add to plan]              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2.5.4 API KEY SECURITY                                          │
├─────────────────────────────────────────────────────────────────┤
│ Scanned for exposed keys:                                       │
│ □ API_KEY/SECRET in src/: [N found / none]                     │
│ □ Private keys in frontend: [list or "none"]                   │
│                                                                 │
│ Security issues:                                                │
│ - [file]: [key type] exposed → MOVE TO EDGE FUNCTION           │
│ - [none found]                                                  │
│                                                                 │
│ VERDICT: [SECURE / FIX REQUIRED - add to plan]                 │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
OVERALL HEALTH: [✅ PASS - proceed to planning / ⚠️ ISSUES - add fixes to plan]

PRE-WORK TASKS (add to plan if any):
- [ ] [Consolidate X and Y into single service]
- [ ] [Remove dead code from Z]
- [ ] [Move API key to edge function]
═══════════════════════════════════════════════════════════════════
```

---

## Filled Example

```
═══════════════════════════════════════════════════════════════════
📋 CODE HEALTH CHECKLIST - Phase 4: Content Pool Migration
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ 2.5.1 REUSE ANALYSIS                                            │
├─────────────────────────────────────────────────────────────────┤
│ Planned feature keywords: [content, pool, migration]            │
│                                                                 │
│ Search results:                                                 │
│ □ grep "content.*pool" src/ → 3 files found                    │
│ □ grep "migration" src/ → none                                 │
│                                                                 │
│ Existing code to REUSE:                                         │
│ - src/hooks/useContentPool.ts: fetches content → WILL EXTEND   │
│ - src/types/content.ts: content types → WILL REUSE             │
│                                                                 │
│ VERDICT: REUSE 2 / CREATE NEW 1                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2.5.2 COMPETING CODE DETECTION                                  │
├─────────────────────────────────────────────────────────────────┤
│ Searched for parallel implementations:                          │
│ □ Services doing similar thing: none                           │
│ □ Multiple fetch/API patterns: none                            │
│ □ Duplicate utilities: none                                    │
│                                                                 │
│ Competing code found:                                           │
│ - [none found]                                                  │
│                                                                 │
│ VERDICT: CLEAN                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2.5.3 DEAD CODE DETECTION                                       │
├─────────────────────────────────────────────────────────────────┤
│ Scanned files this phase will touch:                            │
│ □ useContentPool.ts: unused imports? no, unused exports? yes   │
│                                                                 │
│ Dead code found:                                                │
│ - useContentPool.ts: getOldContent() unused → REMOVE           │
│                                                                 │
│ VERDICT: CLEANUP REQUIRED - add to plan                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2.5.4 API KEY SECURITY                                          │
├─────────────────────────────────────────────────────────────────┤
│ Scanned for exposed keys:                                       │
│ □ API_KEY/SECRET in src/: none                                 │
│ □ Private keys in frontend: none                               │
│                                                                 │
│ Security issues:                                                │
│ - [none found]                                                  │
│                                                                 │
│ VERDICT: SECURE                                                 │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
OVERALL HEALTH: ⚠️ ISSUES - add fixes to plan

PRE-WORK TASKS (add to plan if any):
- [ ] Remove getOldContent() from useContentPool.ts
═══════════════════════════════════════════════════════════════════
```

---

## Search Commands

### Code Reuse Analysis

```bash
# Example: If phase involves "content generation"
grep -r "generate.*content\|content.*generat" src/ --include="*.ts" --include="*.tsx" -l 2>/dev/null

# Example: If phase involves "image upload"
grep -r "upload.*image\|image.*upload" src/ --include="*.ts" --include="*.tsx" -l 2>/dev/null

# Generic: Find services/hooks matching feature area
grep -r "export.*function\|export.*const.*=" src/services/ src/hooks/ --include="*.ts" -l 2>/dev/null | head -20
```

**Decision matrix:**
| Search Result | Action |
|---------------|--------|
| Exact match exists | REUSE - do not recreate |
| Similar code exists | EXTEND - add to existing |
| Nothing found | CREATE NEW - proceed |

---

### Competing Code Detection

```bash
# Find multiple services doing similar things
grep -r "export class.*Service" src/services/ --include="*.ts" -l 2>/dev/null
grep -r "export async function" src/services/ --include="*.ts" | cut -d: -f1 | sort | uniq -c | sort -rn | head -10

# Find duplicate fetch/API patterns
grep -r "fetch\|axios\|supabase\.from" src/ --include="*.ts" --include="*.tsx" -l 2>/dev/null | wc -l

# Find multiple implementations of same concept
grep -rn "function.*[Gg]enerate\|function.*[Cc]reate\|function.*[Ff]etch" src/services/ src/utils/ --include="*.ts" 2>/dev/null
```

**If competing code found:**
1. Add "Consolidate X into Y" as FIRST task in plan
2. Remove the duplicate after consolidation
3. Update all imports to use single source

---

### Dead Code Detection

```bash
# Check for unused exports in a file
FILE="src/services/example.ts"
grep -o "export.*function [a-zA-Z]*\|export.*const [a-zA-Z]*" "$FILE" 2>/dev/null | while read export; do
  name=$(echo "$export" | grep -oE "[a-zA-Z]+$")
  count=$(grep -r "import.*$name\|from.*$name" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l)
  echo "$name: $count imports"
done

# Find commented-out code blocks
grep -rn "^[[:space:]]*//.*function\|^[[:space:]]*//.*const\|^[[:space:]]*//.*export" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | head -10

# Find TODO/FIXME that indicate dead code
grep -rn "TODO.*remove\|FIXME.*delete\|deprecated" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | head -10
```

**If dead code found in files being modified:**
1. Add cleanup task to plan
2. Remove during implementation (same commit as feature)

---

### API Key Security

```bash
# Find potential API key exposure
grep -rn "API_KEY\|apiKey\|api_key\|SECRET\|PRIVATE_KEY" src/ --include="*.ts" --include="*.tsx" 2>/dev/null

# Find Authorization headers in frontend
grep -rn "Authorization.*Bearer\|x-api-key\|X-API-Key" src/ --include="*.ts" --include="*.tsx" 2>/dev/null

# Find direct API calls that might need edge function proxy
grep -rn "fetch.*api\.\|axios.*api\." src/ --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v "supabase\|localhost" | head -10
```

**Rules (NO EXCEPTIONS):**
| Key Type | Frontend OK? | Action |
|----------|--------------|--------|
| Supabase anon key | ✅ Yes | None |
| Stripe publishable | ✅ Yes | None |
| OpenRouter/OpenAI | ❌ No | Edge function |
| Any *_SECRET_* | ❌ No | Edge function |
| Any private key | ❌ No | Edge function |

**If private key in frontend:**
1. Add "Create edge function for X" as BLOCKING task
2. Cannot proceed with feature until key is secured

---

## Enforcement Gate

**YOU CANNOT PROCEED TO PLANNING UNTIL:**

1. ✅ Code Health Checklist is output (copy template above)
2. ✅ All searches executed and results documented
3. ✅ Any consolidation/cleanup tasks added to plan
4. ✅ Any security fixes added as blocking tasks

**If you skip this step and proceed to planning, you are violating the /begin protocol.**
