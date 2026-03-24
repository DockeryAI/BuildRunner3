---
description: Create a git worktree with full project setup — BR3, Claude config, .env, alias
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
model: opus
argument-hint: <build-plan-name>
---

# Worktree Setup Wizard

Create a fully independent git worktree from a build plan. Sets up Claude Code project, .env symlink, node_modules, shell alias with `--dangerously-skip-permissions`, and BR3 infrastructure.

**Arguments:** $ARGUMENTS

---

## Step 1: Detect Source Repo

```bash
SOURCE_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
SOURCE_NAME=$(basename "$SOURCE_ROOT")
```

If not in a git repo, exit with error.

---

## Step 2: Resolve Build Plan

### 2a: Find the build plan

List available build plans:
```bash
ls "$SOURCE_ROOT/.buildrunner/builds/BUILD_"*.md 2>/dev/null
```

If $ARGUMENTS is provided, fuzzy-match it against available build plan filenames (case-insensitive, partial match). For example:
- `/worktree content-performance` matches `BUILD_content-performance-intelligence.md`
- `/worktree video` matches `BUILD_video-system.md`

If no match or no argument, ask:
**Question:** "Which build plan should this worktree use?"
- Show each `BUILD_*.md` file found as an option (display just the name portion)
- Allow "None (start fresh with /spec)"

### 2b: Read the build plan header

Read the first 50 lines of the matched build plan to extract:
- **Build name** (from the `# Build: ...` header)
- **Branch name** (look for branch references like `standalone branch`, `feature branch`, or branch names in backticks)
- **Overview** (first paragraph after Overview heading)

Store the branch name for later — it will be used automatically in Step 5, NOT asked in the wizard.

---

## Step 3: Wizard — Name & Configure

The wizard asks about the **project identity** — the user's answers drive ALL naming. Branch is a technical detail resolved automatically from the build plan.

Use AskUserQuestion to collect all info. Present all questions in a **single AskUserQuestion call** (up to 4 questions).

### 3a: Project Name (DRIVES EVERYTHING)

**Question:** "What should this project be called?"
- Suggest PascalCase names derived from the build name:
  - e.g., "Content Performance Intelligence" → `SynapseContentPerformance` or `ContentPerformance`
  - e.g., "Video System" → `VideoSystem`
- This name determines:
  - **Directory:** `~/Projects/$PROJECT_NAME`
  - **Shell alias:** lowercase initials (e.g., `SynapseContentPerformance` → `scp`)
  - **Claude project key:** derived from full path
  - **Terminal tab title:** shown in precmd
- Options: 2-3 suggested names, user can type custom via "Other"

### 3b: Shell Alias

**Question:** "What shell alias to launch this project?"
- Suggest: lowercase initials of project name (e.g., `SynapseContentPerformance` → `scp`)
- If initials conflict with a system command (check `which`), suggest alternatives:
  - Full lowercase: `synapsecontentperformance` (too long, avoid)
  - Abbreviated: `syncps`, `cps`, first-word-lowercase
- Options: 2-3 suggestions based on project name chosen above

### 3c: Dev Server Port

Detect which ports are likely in use:
```bash
git worktree list
grep "port" ~/.zshrc 2>/dev/null
```

**Question:** "Which port for the dev server? (main project uses 3000)"
- Options: 3001, 3002, 3003 (skip any already in use)

---

## Step 4: Derive All Names from Wizard Answers

After the wizard, compute ALL naming from the user's answers:

```
PROJECT_NAME     = wizard answer 3a (e.g., "SynapseContentPerformance")
ALIAS_NAME       = wizard answer 3b (e.g., "cps")
PORT             = wizard answer 3c (e.g., 3001)
WORKTREE_PATH    = ~/Projects/$PROJECT_NAME
BRANCH_NAME      = auto-detected from build plan in Step 2b
BUILD_PLAN_FILE  = resolved in Step 2a
```

The user's chosen PROJECT_NAME is the single source of truth for directory structure. Branch name is NEVER used for directory naming.

---

## Step 5: Create Worktree

```bash
WORKTREE_PATH="$HOME/Projects/$PROJECT_NAME"

# Verify target doesn't exist
if [ -d "$WORKTREE_PATH" ]; then
  echo "ERROR: $WORKTREE_PATH already exists"
  # Ask user: delete and recreate, or abort?
fi

# Create worktree on the branch found in the build plan
git worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
```

If the branch doesn't exist yet, create it from current HEAD:
```bash
git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH"
```

If NO branch was found in the build plan, create a new branch named after the project:
```bash
BRANCH_NAME=$(echo "$PROJECT_NAME" | sed 's/\([A-Z]\)/-\L\1/g' | sed 's/^-//')
# e.g., SynapseContentPerformance → synapse-content-performance
git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH"
```

---

## Step 6: Symlink Shared Files

Symlink ALL dot-env files. NEVER copy — symlinks keep credentials in sync.

```bash
# Symlink .env (shared database)
ln -s "$SOURCE_ROOT/.env" "$WORKTREE_PATH/.env"

# Symlink .env.example if exists
[ -f "$SOURCE_ROOT/.env.example" ] && ln -s "$SOURCE_ROOT/.env.example" "$WORKTREE_PATH/.env.example"

# Symlink .env.local if exists
[ -f "$SOURCE_ROOT/.env.local" ] && ln -s "$SOURCE_ROOT/.env.local" "$WORKTREE_PATH/.env.local"
```

---

## Step 7: Install Dependencies

```bash
cd "$WORKTREE_PATH" && npm install
```

Wait for completion. If it fails, report the error but continue setup.

---

## Step 8: Set Up Claude Code Project

This is what makes the worktree a **separate Claude Code project** so it gets its own conversation history, memory, and instructions.

```bash
# Claude uses the absolute path with slashes replaced by dashes as the project key
CLAUDE_PROJECT_KEY=$(echo "$WORKTREE_PATH" | sed 's|/|-|g' | sed 's|^-||')
CLAUDE_PROJECT_DIR="$HOME/.claude/projects/$CLAUDE_PROJECT_KEY"
mkdir -p "$CLAUDE_PROJECT_DIR/memory"
```

### 8a: Create Project CLAUDE.md

Write `$CLAUDE_PROJECT_DIR/CLAUDE.md` with:

```markdown
# $PROJECT_NAME — Worktree Project

This is a **git worktree** of the $SOURCE_NAME repo, checked out on `$BRANCH_NAME` branch.

## Worktree Info
- **Parent repo:** $SOURCE_ROOT ($SOURCE_NAME main branch)
- **This worktree:** $WORKTREE_PATH
- **Shared:** Same database, same .env (symlinked), same Supabase project
- **Independent:** Separate node_modules, separate dev server (port $PORT), separate branch

## Build Plan
- Primary build spec: `.buildrunner/builds/$BUILD_PLAN_FILE`
- [Paste the Overview section from the build plan here]

## Branch Rules
- NEVER switch branches in this worktree — it's locked to `$BRANCH_NAME`
- If you need to work on the main project, use $SOURCE_ROOT instead
- Commits here stay on the `$BRANCH_NAME` branch

## Dev Server
- Run on port $PORT: `npx vite --port $PORT`
- Main project runs on port 3000 at $SOURCE_ROOT
```

### 8b: Create Memory Seed

Read the build plan to find completed phases and current phase. Write `$CLAUDE_PROJECT_DIR/memory/MEMORY.md`:

```markdown
# $PROJECT_NAME Memory

## Project
- Git worktree of $SOURCE_NAME on `$BRANCH_NAME` branch
- Build spec: `.buildrunner/builds/$BUILD_PLAN_FILE`
- Shares DB + .env with $SOURCE_ROOT (symlinked)
- Dev server port: $PORT

## Completed Phases
[Read from build plan — list any phases marked as complete/done]

## Current Phase
[Read from build plan — identify the current in-progress or next phase]
```

---

## Step 9: Add Shell Alias

**CRITICAL:** Use `--dangerously-skip-permissions` to match the existing BR3 alias pattern.

Detect shell config:
```bash
SHELL_RC="$HOME/.zshrc"
[ ! -f "$SHELL_RC" ] && SHELL_RC="$HOME/.bashrc"
```

**Check for conflicts before writing:**
```bash
# Check if alias already exists in shell config
grep "^alias $ALIAS_NAME=" "$SHELL_RC" 2>/dev/null
# Check if it's a system command
which "$ALIAS_NAME" 2>/dev/null
```

If no conflict, insert into the **BuildRunner Project Aliases** section:
```bash
# Find the "# End BuildRunner Project Aliases" marker and insert before it
# If no marker, append to end of file
```

The alias line:
```
alias $ALIAS_NAME='cd $WORKTREE_PATH && claude --dangerously-skip-permissions'
```

Also create the launcher script:
```bash
mkdir -p "$HOME/.claude/worktree-aliases"
cat > "$HOME/.claude/worktree-aliases/$PROJECT_NAME.sh" << 'SCRIPT'
#!/bin/bash
cd "$WORKTREE_PATH" && claude --dangerously-skip-permissions
SCRIPT
chmod +x "$HOME/.claude/worktree-aliases/$PROJECT_NAME.sh"
```

---

## Step 10: Verify Setup

Run ALL verification checks:

```bash
echo "=== Worktree Verification ==="
echo ""
echo "1. Directory:"
ls -d "$WORKTREE_PATH" && echo "   OK" || echo "   FAIL"
echo ""
echo "2. Branch:"
cd "$WORKTREE_PATH" && git branch --show-current
echo ""
echo "3. .env symlink:"
ls -la "$WORKTREE_PATH/.env" | grep -q "\->" && echo "   OK (symlinked)" || echo "   FAIL"
echo ""
echo "4. node_modules:"
[ -d "$WORKTREE_PATH/node_modules" ] && echo "   OK" || echo "   MISSING"
echo ""
echo "5. Claude project config:"
[ -f "$CLAUDE_PROJECT_DIR/CLAUDE.md" ] && echo "   OK" || echo "   MISSING"
echo ""
echo "6. Claude memory:"
[ -f "$CLAUDE_PROJECT_DIR/memory/MEMORY.md" ] && echo "   OK" || echo "   MISSING"
echo ""
echo "7. Shell alias:"
grep "$ALIAS_NAME=" "$SHELL_RC" && echo "   OK" || echo "   MISSING"
echo ""
echo "8. Build plan in worktree:"
[ -f "$WORKTREE_PATH/.buildrunner/builds/$BUILD_PLAN_FILE" ] && echo "   OK" || echo "   MISSING"
echo ""
echo "9. All worktrees:"
git worktree list
```

If any check fails, report it clearly and suggest the fix.

---

## Step 11: Report

```markdown
## Worktree Created

| Setting | Value |
|---------|-------|
| **Project** | $PROJECT_NAME |
| **Directory** | `$WORKTREE_PATH` |
| **Branch** | `$BRANCH_NAME` (auto-detected from build plan) |
| **Build Plan** | `$BUILD_PLAN_FILE` |
| **Dev Port** | $PORT |
| **Shell Alias** | `$ALIAS_NAME` |

### Quick Start

1. **Open a new terminal** (to load the alias)
2. Type **`$ALIAS_NAME`** to launch Claude Code in the worktree
3. Or: `cd $WORKTREE_PATH && claude`
4. Dev server: `npx vite --port $PORT`
5. Run `/begin` to start the next phase of the build plan

### Important
- This worktree shares the **same database** as $SOURCE_NAME
- Branch switching in one worktree does **NOT** affect the other
- Each Claude Code instance is fully independent with its own memory
- The `.env` is symlinked — changes in either location are shared
```

---

## Rules

1. **User's project name drives ALL naming** — directory, alias key, Claude project. Branch is auto-resolved from build plan, never from user input.
2. **Build plan is the entry point** — the argument to `/worktree` is a build plan name, not a branch
3. **Never modify the source repo** during worktree setup
4. **Always symlink .env** — never copy (keeps credentials in sync)
5. **Always install node_modules** — worktrees need their own copy
6. **Always create Claude project config** — this is what makes it a separate Claude Code project with independent memory
7. **Always use `--dangerously-skip-permissions`** on shell aliases — matches existing BR3 alias pattern
8. **Always verify** — run all checks before reporting success
9. **Idempotent aliases** — check before appending to shell config
10. **Seed memory from build plan** — pre-populate completed phases and current state so Claude has context immediately
