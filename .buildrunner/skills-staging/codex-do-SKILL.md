---
name: codex-do
description: Delegate terminal/DevOps tasks to Codex CLI (GPT-4o). For shell scripts, CI/CD, Dockerfiles, deploy scripts. Codex scores 77.3% vs Claude 65.4% on Terminal-Bench 2.0.
user_invocable: true
triggers:
  - codex-do
  - codex do
---

# /codex-do — Terminal Task Delegation to Codex

Delegate pure terminal/DevOps work to Codex CLI. Research shows Codex outperforms Claude on terminal tasks (77.3% vs 65.4% on Terminal-Bench 2.0).

## Usage

```
/codex-do <task description>
```

Examples:

- `/codex-do write a deploy script for the React app to Cloudflare Pages`
- `/codex-do create a Dockerfile for the Node.js API with multi-stage build`
- `/codex-do set up GitHub Actions CI for TypeScript with caching`
- `/codex-do write a backup script that rsyncs to the NAS nightly`

## Scope Limitation

**DO use for:**

- Shell scripts (bash, zsh)
- CI/CD pipelines (GitHub Actions, GitLab CI, CircleCI)
- Dockerfiles and docker-compose
- Deployment scripts
- System administration tasks
- Cron jobs and scheduled tasks
- Build tooling configuration
- Infrastructure-as-code (Terraform, Pulumi basics)

**DO NOT use for:**

- Application logic (use Claude)
- Frontend/UI work (use Claude)
- Database queries or migrations (use Claude)
- API design (use Claude)
- Complex multi-file refactoring (use Claude)

If the task involves application code, use Claude directly. `/codex-do` is specifically for terminal-shaped tasks where Codex has demonstrated superiority.

## Step 1: Validate Task Scope

Before delegating, verify the task is terminal-shaped:

```bash
# Check if task mentions terminal keywords
TERMINAL_KEYWORDS="script|bash|shell|docker|ci|cd|deploy|cron|systemd|ansible|terraform|makefile|github.actions|gitlab-ci|workflow|rsync|ssh|nginx|apache|kubernetes|k8s|helm"

# If task doesn't match, warn user
if ! echo "$TASK" | grep -iE "$TERMINAL_KEYWORDS" > /dev/null; then
  echo "WARNING: This task may not be terminal-shaped. Consider using Claude directly."
  echo "Proceed anyway? (y/n)"
  # Wait for confirmation
fi
```

## Step 2: Build Context

Gather project context for Codex:

```bash
cd "$(git rev-parse --show-toplevel)"
PROJECT_ROOT=$(pwd)
PROJECT_NAME=$(basename "$PROJECT_ROOT")

# Detect project type
CONTEXT=""
[ -f "package.json" ] && CONTEXT="$CONTEXT\n--- package.json ---\n$(cat package.json)"
[ -f "Dockerfile" ] && CONTEXT="$CONTEXT\n--- Dockerfile ---\n$(cat Dockerfile)"
[ -f ".github/workflows/"*.yml ] && CONTEXT="$CONTEXT\n--- GitHub Actions ---\n$(cat .github/workflows/*.yml 2>/dev/null | head -100)"
[ -f "docker-compose.yml" ] && CONTEXT="$CONTEXT\n--- docker-compose.yml ---\n$(cat docker-compose.yml)"
[ -f "Makefile" ] && CONTEXT="$CONTEXT\n--- Makefile ---\n$(cat Makefile)"
```

## Step 3: Invoke Codex

```bash
PROMPT="You are a DevOps engineer working on the project '$PROJECT_NAME'.

Task: $TASK

Project context:
$CONTEXT

Instructions:
1. Write production-quality code (not examples or placeholders)
2. Include error handling and logging
3. Add comments explaining non-obvious parts
4. If creating a script, make it executable and idempotent where possible
5. Output ONLY the code/config — no explanations before or after

If you need to create multiple files, clearly separate them with headers:
--- filename.sh ---
<content>
--- another-file.yml ---
<content>"

codex exec --model gpt-4o --approval auto --timeout 180 "$PROMPT" 2>&1
```

## Step 4: Present Output and Confirm

After Codex responds, present the output:

```
================================================================
CODEX OUTPUT — Terminal Task
================================================================
Task: {task description}

{Codex output — script/config/etc}

================================================================
Actions available:
  1. Apply — write files and make executable
  2. Edit — request changes
  3. Cancel — discard
================================================================
```

**Wait for user confirmation before applying.**

## Step 5: Apply (on user approval)

If the user approves:

```bash
# Parse Codex output for file sections
# For each --- filename --- section:
#   1. Create the file
#   2. Make executable if it's a script (.sh, no extension)
#   3. Report what was created

# Example for a single script:
SCRIPT_PATH="$PROJECT_ROOT/scripts/deploy.sh"
mkdir -p "$(dirname "$SCRIPT_PATH")"
cat > "$SCRIPT_PATH" << 'CODEX_OUTPUT'
{parsed script content}
CODEX_OUTPUT
chmod +x "$SCRIPT_PATH"

echo "Created: $SCRIPT_PATH (executable)"
```

## Step 6: Commit (optional)

Ask if the user wants to commit:

```
Files created:
- scripts/deploy.sh

Commit these changes? (y/n)
```

If yes:

```bash
git add -A
git commit -m "chore: add {description} via codex-do

Co-Authored-By: Codex (GPT-4o) <noreply@openai.com>"
```

## Error Handling

**Codex timeout (>180s):**

```
Codex timed out. The task may be too complex.
Try breaking it into smaller pieces or use Claude directly.
```

**Codex auth failure:**

```
Codex CLI not authenticated. Run: codex auth
```

**Invalid output (no code detected):**

```
Codex returned explanations instead of code.
Retrying with stricter prompt...
```

Then retry with: "Output ONLY code. No explanations. No markdown. Just the raw file contents."
