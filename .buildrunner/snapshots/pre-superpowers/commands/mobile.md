---
description: Start a tmux session for remote phone access via SSH
allowed-tools: Bash, Read
---

# Mobile Session Setup

Set up a tmux session so the user can SSH in from their phone and run Claude Code.

---

## Step 1: Preflight Checks

Run these checks:

```bash
# Check tmux installed
which tmux

# Check if Tailscale is running
pgrep -x Tailscale >/dev/null 2>&1 && echo "TAILSCALE_RUNNING" || echo "TAILSCALE_NOT_RUNNING"

# Get Tailscale IP if available
/Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4 2>/dev/null || echo "NO_TAILSCALE_IP"
```

If tmux is missing: `brew install tmux`
If Tailscale not running: tell user to open Tailscale app and sign in
If no Tailscale IP: tell user to sign in to Tailscale first

**Do NOT proceed until all checks pass.**

---

## Step 2: Check for Existing Session

```bash
tmux has-session -t mobile 2>/dev/null && echo "SESSION_EXISTS" || echo "NO_SESSION"
```

If session exists, ask the user if they want to kill it and start fresh or keep it.

---

## Step 3: Create tmux Session

```bash
# Start detached tmux session named "mobile" in the current project directory
tmux new-session -d -s mobile -c "$(pwd)"

# Send the claude command to start Claude Code in the session
tmux send-keys -t mobile 'claude' Enter
```

---

## Step 4: Report Connection Info

Get connection details and display them:

```bash
TAILSCALE_IP=$(/Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4 2>/dev/null)
LOCAL_USER=$(whoami)
echo "TAILSCALE_IP=$TAILSCALE_IP"
echo "USER=$LOCAL_USER"
```

Display to the user:

```markdown
## Mobile Session Ready

**Session:** `mobile` (tmux)
**Claude Code is running** in the tmux session.

### Connect from your phone:

ssh <user>@<tailscale-ip>

**Then attach to the session:**

tmux attach -t mobile

**You're now in Claude Code.** Give it instructions like normal.

### When done:
- Just close the terminal app — session stays alive
- Reconnect anytime with the same two commands

### To kill the session later:
tmux kill-session -t mobile
```

Replace `<user>` and `<tailscale-ip>` with the actual values from the commands above.
