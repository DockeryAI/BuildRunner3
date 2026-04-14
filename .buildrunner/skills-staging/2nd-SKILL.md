---
name: 2nd
description: Get a second opinion from Codex (GPT-4o) when stuck debugging. Generates a brief, invokes Codex, returns disagreement diff. Advisory only.
user_invocable: true
triggers:
  - 2nd
  - second opinion
  - codex review
---

# /2nd — Second Opinion from Codex

Get an independent second opinion from Codex CLI (GPT-4o) when stuck on a debugging problem. The response highlights where Codex disagrees with Claude's current hypothesis.

Research backing: models fix external errors 64.5% more reliably than their own (Zylos, Feb 2026).

## Usage

- `/2nd` — Generate brief from current context, get Codex opinion
- `/2nd --adversarial` — Force contrary position ("convince me I'm wrong" mode)

## Step 1: Gather Context

Collect the following from the current conversation and project state:

```bash
mkdir -p .buildrunner/codex-briefs
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BRIEF_FILE=".buildrunner/codex-briefs/${TIMESTAMP}.md"
```

**Required context (extract from conversation):**

1. **Goal** — What the user is trying to accomplish
2. **What Claude tried** — Recent Bash commands, file edits, tool calls from this conversation
3. **Suspect files** — Full contents (not diffs) of files likely involved in the bug
4. **Error output** — Raw error messages, stack traces, log snippets
5. **Claude's hypothesis** — What Claude currently believes is wrong and why
6. **User's question** — The one-line question Claude can't answer confidently

**Write the brief:**

```markdown
# Second Opinion Brief — {TIMESTAMP}

## Goal

{What the user is trying to accomplish}

## What Claude Tried

{List of recent actions — commands run, files edited, approaches attempted}

## Suspect Files

{Full file contents of the 1-3 most relevant files}

## Error Output

{Raw error messages, stack traces, relevant log excerpts}

## Claude's Current Hypothesis

{What Claude believes is the issue and why}

## Question for Codex

{The specific question — what should Codex analyze/answer?}
```

Write to `$BRIEF_FILE`.

## Step 2: Invoke Codex

```bash
cd "$(git rev-parse --show-toplevel)"

# Standard mode: ask for diagnosis
PROMPT="You are reviewing another engineer's debugging work. They are stuck. Read the brief below and provide your analysis.

Focus on:
1. Do you agree with their hypothesis? If not, what did they miss?
2. What would you try that they haven't?
3. Rate your confidence (high/medium/low) and explain why.

Brief:
$(cat "$BRIEF_FILE")"

# Adversarial mode: force contrary position
if [ "$ADVERSARIAL" = "true" ]; then
  PROMPT="You are reviewing another engineer's debugging work. Your job is to argue the CONTRARY position.

The prior engineer believes: {Claude's hypothesis}

Assume they are WRONG. What did they miss? What evidence contradicts their theory?

Do not agree with them. Find the flaw in their reasoning. If you cannot find a flaw, explain what would need to be true for their hypothesis to fail.

Brief:
$(cat "$BRIEF_FILE")"
fi

# Run Codex with repo context
codex exec --model gpt-4o --approval auto --timeout 120 "$PROMPT" 2>&1
```

## Step 3: Parse and Present Disagreement Diff

After Codex responds, present the findings as a **disagreement diff**:

```
================================================================
SECOND OPINION — Codex (GPT-4o)
================================================================

### Agreements
{Where Codex confirms Claude's analysis}

### Disagreements
{Where Codex rejects Claude's assumptions — THIS IS THE VALUABLE PART}

### Proposed Next Steps
{What Codex would try}

### Confidence: {high/medium/low}
{Codex's confidence and reasoning}

================================================================
ADVISORY ONLY — Review before applying
================================================================
```

**Never auto-apply Codex suggestions.** Present them to the user for decision.

## --adversarial Mode

When invoked with `--adversarial`, the prompt forces Codex to argue against Claude's position:

> "Assume they are WRONG. What did they miss?"

This exploits external-attribution bias for maximum pushback. Use on:

- Security tradeoffs where Claude is confident
- Architecture decisions that can't be easily tested
- Situations where you need a devil's advocate

The adversarial response should be substantively contrary, not agreement.

## When to Use /2nd

- Stuck for 10+ minutes on the same error
- Claude's fix attempts keep failing
- The bug doesn't match known patterns
- You need a sanity check before a risky change
- Security-sensitive code where you want another set of eyes

## Limitations

- Codex response time: 30-120 seconds
- Requires Codex CLI auth (`codex auth`)
- Limited to text — cannot see screenshots or browser state
- Advisory only — never auto-applies changes
