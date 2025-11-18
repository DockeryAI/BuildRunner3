# Week 2 Concise Prompts - References BUILD_PLAN.md

---

## PROMPT 1: Build 2A - CLI

```
BUILDRUNNER 3.0 - BUILD 2A: CLI WITH AUTOMATED DEBUGGING

═══════════════════════════════════════════════════════════════════

SETUP:

```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree remove ../br3-cli --force 2>/dev/null || true
git branch -D build/week2-cli 2>/dev/null || true
git worktree add ../br3-cli -b build/week2-cli
cd ../br3-cli
python3 -m venv .venv
source .venv/bin/activate
pip install typer rich watchdog pytest pyyaml pytest-cov
```

═══════════════════════════════════════════════════════════════════

TASK LIST:

Execute all tasks from BUILD_PLAN.md Build 2A (lines 177-254):
- Read: /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN.md
- Section: "Build 2A - Python CLI Commands [PARALLEL]"
- Complete all 15 tasks listed
- Achieve 85%+ test coverage
- All tests must pass

═══════════════════════════════════════════════════════════════════

COMMIT:

```bash
git add .
git commit -m "feat: Implement CLI with automated debugging and behavior config (Build 2A)"
```

DO NOT MERGE - Wait for Build 2C.
```

---

## PROMPT 2: Build 2B - API

```
BUILDRUNNER 3.0 - BUILD 2B: FASTAPI BACKEND

═══════════════════════════════════════════════════════════════════

SETUP:

```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree remove ../br3-api --force 2>/dev/null || true
git branch -D build/week2-api 2>/dev/null || true
git worktree add ../br3-api -b build/week2-api
cd ../br3-api
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pytest httpx python-dotenv pytest-asyncio aiofiles pyyaml websockets pytest-cov
```

═══════════════════════════════════════════════════════════════════

TASK LIST:

Execute all tasks from BUILD_PLAN.md Build 2B (lines 258-344):
- Read: /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN.md
- Section: "Build 2B - FastAPI Backend [PARALLEL]"
- Complete all 14 tasks listed
- Achieve 85%+ test coverage
- All tests must pass

═══════════════════════════════════════════════════════════════════

COMMIT:

```bash
git add .
git commit -m "feat: Implement FastAPI backend with test runner and error detection (Build 2B)"
```

DO NOT MERGE - Wait for Build 2C.
```

---

## PROMPT 3: Build 2C - Integration

```
BUILDRUNNER 3.0 - BUILD 2C: INTEGRATION + PRD SYSTEM

═══════════════════════════════════════════════════════════════════

CONTEXT:

Working in: /Users/byronhudson/Projects/BuildRunner3 (main branch)
Builds 2A and 2B must be COMMITTED first.

═══════════════════════════════════════════════════════════════════

TASK LIST:

Execute all tasks from BUILD_PLAN.md Build 2C (lines 348-407):
- Read: /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN.md
- Section: "Build 2C - Week 2 Integration + PRD System [MAIN BRANCH]"
- Complete all 10 tasks listed
- Merge both builds
- Implement PRD system
- All integration tests must pass

═══════════════════════════════════════════════════════════════════

COMMIT AND TAG:

```bash
git add .
git commit -m "feat: Complete Week 2 Integration with PRD System (Build 2C)"
git tag -a v3.0.0-alpha.2 -m "Week 2 Complete: CLI + API + PRD System"
```

CLEANUP:

```bash
git worktree remove ../br3-cli
git worktree remove ../br3-api
git branch -d build/week2-cli
git branch -d build/week2-api
```
```

---

**Usage:** Copy/paste each prompt. The atomic task lists in BUILD_PLAN.md contain all implementation details.
