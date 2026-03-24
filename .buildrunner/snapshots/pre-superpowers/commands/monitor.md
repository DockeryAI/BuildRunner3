---
description: Monitor user flows - capture network/console activity and generate diagnostic report
allowed-tools: Read, Bash, Grep, Glob
model: opus
---

# Flow Monitoring: /monitor

**PURPOSE:** Capture and analyze user flows end-to-end.

---

## Usage

```
/monitor "flow name"              # Start monitoring (current project)
/monitor marba "flow name"        # Start monitoring MARBA project (from anywhere)
/monitor stop                     # Stop and generate report
/monitor marba stop               # Stop MARBA monitoring (from anywhere)
/monitor report                   # Generate report from last session
```

---

## Step 0: Resolve Project (if alias provided)

If command includes a project alias (e.g., `/monitor marba "scan"`):

1. **Check if first argument is a known project alias:**

```bash
# Check ~/Projects/[alias]/.buildrunner exists
ls ~/Projects/{{ALIAS}}/.buildrunner 2>/dev/null && echo "PROJECT_FOUND"
```

2. **If found, set PROJECT_ROOT:**
   - `PROJECT_ROOT=~/Projects/{{ALIAS}}`
   - The flow name is the second argument

3. **If not found or no alias:**
   - `PROJECT_ROOT=.` (current directory)
   - The flow name is the first argument

**All subsequent commands use `$PROJECT_ROOT/.buildrunner/` instead of `.buildrunner/`**

---

## Step 1: Determine Mode

Parse the command arguments (after resolving project):

- **Start mode:** `/monitor "flow name"` or `/monitor alias "flow name"`
- **Stop mode:** `/monitor stop` or `/monitor alias stop`
- **Report mode:** `/monitor report` or `/monitor alias report`

---

## Step 2A: Start Mode

If starting a new monitoring session:

1. **Inject session marker into browser.log:**

```bash
echo "" >> $PROJECT_ROOT/.buildrunner/browser.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MONITOR] Starting session" >> $PROJECT_ROOT/.buildrunner/browser.log
echo '{"type":"MONITOR","message":"[MONITOR_START] {{FLOW_NAME}}","details":{"startTime":"'$(date -Iseconds)'","stateSnapshot":{}}}' >> $PROJECT_ROOT/.buildrunner/browser.log
```

Replace `{{FLOW_NAME}}` with the user's flow name and `$PROJECT_ROOT` with resolved path.

2. **Save session state:**

```bash
echo '{"flow_name":"{{FLOW_NAME}}","start_time":"'$(date -Iseconds)'","status":"active","project":"$PROJECT_ROOT"}' > $PROJECT_ROOT/.buildrunner/monitor_session.json
```

3. **Confirm to user:**

> "Monitoring started for: **{{FLOW_NAME}}**
>
> Go perform your actions in the browser. The BRLogger will capture:
> - Network requests and responses
> - Console errors and warnings
> - State changes
>
> When done, run `/monitor stop` to see the report."

**STOP HERE** - Wait for user to perform actions and run `/monitor stop`.

---

## Step 2B: Stop Mode

If stopping an active session:

1. **Check for active session:**

```bash
cat $PROJECT_ROOT/.buildrunner/monitor_session.json 2>/dev/null || echo "No active session"
```

If no session exists, tell user: "No active monitoring session. Start one with `/monitor \"flow name\"`"

2. **Inject stop marker:**

```bash
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MONITOR] Ending session" >> $PROJECT_ROOT/.buildrunner/browser.log
echo '{"type":"MONITOR","message":"[MONITOR_STOP] {{FLOW_NAME}}","details":{"endTime":"'$(date -Iseconds)'","duration":0,"stateSnapshot":{}}}' >> $PROJECT_ROOT/.buildrunner/browser.log
```

3. **Clear session state:**

```bash
rm -f $PROJECT_ROOT/.buildrunner/monitor_session.json
```

4. **Proceed to Step 3** to generate report.

---

## Step 2C: Report Mode

If generating report only (no stop):

- Proceed directly to Step 3
- Uses the most recent completed session in browser.log

---

## Step 3: Generate Report

Read the browser.log and find the monitoring session:

@$PROJECT_ROOT/.buildrunner/browser.log

Look for entries between `[MONITOR_START]` and `[MONITOR_STOP]` markers.

---

## Step 4: Analyze Session

For each entry in the session:

### Network Requests (NET type)
Categorize as:
- **Worked:** Status 200-399
- **Failed:** Status 400+ or error
- **Slow:** Duration > 2000ms

### Console Errors (ERROR type)
- Collect all error messages

### Data Gaps
- Null responses
- Empty objects (but NOT empty arrays - those are often valid)

---

## Step 5: Output Report

**Format (STRICT - no code, no tables):**

```markdown
# Monitor Report: {{FLOW_NAME}}

**Duration:** X.XXs
**Requests:** N

## What Worked
- METHOD /path (Xms)
- METHOD /path (Xms)

## What Failed
- METHOD /path (status XXX) - error message

## Console Errors
- Error message here

## Bottlenecks
- METHOD /path - X.XXs (slowest)
- METHOD /path - X.XXs

## Timing Breakdown
- Successful requests: X.XXs (XX%)
- Failed requests: X.XXs (XX%)
- Slow requests: X.XXs (XX%)

## Data Gaps
- /path - Response is null
- /path - Response is empty object

---

**Status:** X failed requests, Y console errors
```

---

## Rules

1. **NO CODE in report** - Plain English only
2. **NO TABLES** - Use bullet points
3. **CONCISE** - One line per item
4. **CATEGORIZE** - Worked/Failed/Slow only
5. **ACTIONABLE** - Report issues that need fixing

---

## Session State

Session stored in `$PROJECT_ROOT/.buildrunner/monitor_session.json`:
```json
{
  "flow_name": "website scan",
  "start_time": "2025-01-15T10:30:00",
  "status": "active",
  "project": "/Users/you/Projects/marba"
}
```

Cleared on `/monitor stop` or navigation.

---

## Examples

**Start monitoring (current project):**
```
/monitor "synapse scan"
```
> Monitoring started for: **synapse scan**

**Start monitoring (remote project):**
```
/monitor marba "website scan"
```
> Monitoring MARBA project at ~/Projects/marba
> Monitoring started for: **website scan**

**Stop and report:**
```
/monitor stop
```
> # Monitor Report: synapse scan
> **Duration:** 4.52s
> **Requests:** 12
> ...

**Stop remote project:**
```
/monitor marba stop
```
> # Monitor Report: website scan (MARBA)
> ...

**Report only (no stop):**
```
/monitor report
```
> Generates report from last completed session
