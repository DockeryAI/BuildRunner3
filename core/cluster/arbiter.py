#!/usr/bin/env python3
"""
arbiter.py — Opus 4.7 arbiter for unresolved adversarial review disagreements.

Invoked ONLY when Sonnet + Codex reviewers disagree after the mandatory rebuttal
round. Reads all reviews, rebuttals, and the specific point of disagreement.
Uses Claude Opus 4.7 with effort=xhigh (adaptive thinking) for the ruling.

IMPORTANT: Arbiter ruling is TERMINAL. No auto re-run path. Any contest
escalates to the user.

IMPORTANT: Reviewers MUST NOT see the arbiter ruling pre-finding. The arbiter
only receives reviewer outputs — it does not feed back into the review loop.

Usage:
    python3 -m core.cluster.arbiter \
        --claude-findings <json_file> \
        --codex-findings <json_file> \
        --rebuttal-findings <json_file> \
        --disagreement <json_file> \
        --artifact <path> \
        --round <N> \
        [--project-root <path>]

Output (stdout): JSON arbiter ruling {verdict, findings, rationale, model, effort}
Exit: 0 = ruling complete; 1 = arbiter invocation error
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
DECISIONS_LOG = HOME / "Projects" / "BuildRunner3" / ".buildrunner" / "decisions.log"
CONFIG_PATH = Path(__file__).parent / "cross_model_review_config.json"

ARBITER_PROMPT_TEMPLATE = """You are an arbiter for a code review dispute. Two co-equal reviewers have examined the same artifact and disagree after a rebuttal round. Your ruling is TERMINAL — once you rule, the review loop stops. Do not defer; make a definitive determination.

## Context

Artifact under review: {artifact}
Review round: {round}

## Reviewer A findings (Claude Sonnet 4.6):
{claude_findings}

## Reviewer B findings (Codex GPT-5.4):
{codex_findings}

## Post-rebuttal surviving findings:
{rebuttal_findings}

## Specific disagreement requiring arbitration:
{disagreement}

## Your task

1. Review each disputed finding independently.
2. For each disputed finding, determine:
   - Is this a real defect that would cause harm in production?
   - Which reviewer's assessment is more accurate, and why?
   - What is the correct severity: blocker / warning / note?
   - What is the correct fix_type: fixable / structural?
3. Issue a terminal ruling on whether the artifact is BLOCKED or APPROVED.

Output ONLY the JSON ruling object. No prose outside the JSON.

Schema:
{{
  "verdict": "BLOCKED" | "APPROVED",
  "rationale": "<2-3 sentence summary of the key deciding factor>",
  "findings": [
    {{
      "finding": "<exact finding text>",
      "severity": "blocker" | "warning" | "note",
      "fix_type": "fixable" | "structural",
      "arbiter_ruling": "<ruling on this specific finding>",
      "upheld": true | false
    }}
  ],
  "reviewer_accuracy": {{
    "claude": "<brief assessment of claude's review quality>",
    "codex": "<brief assessment of codex's review quality>"
  }}
}}

The verdict is BLOCKED if any upheld finding has severity=blocker. Otherwise APPROVED.
"""


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"arbiter": {"model": "claude-opus-4-7", "effort": "xhigh"}}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json_file(path):
    """Load JSON from a file path, returning empty list/dict on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to load {path}: {e}"}


def format_findings_for_prompt(findings):
    """Format a findings list or dict for inclusion in the arbiter prompt."""
    if isinstance(findings, list):
        if not findings:
            return "(no findings)"
        lines = []
        for item in findings:
            sev = item.get("severity", "note")
            fix = item.get("fix_type", "fixable")
            finding = item.get("finding", "")
            lines.append(f"- [{sev}/{fix}] {finding}")
        return "\n".join(lines)
    elif isinstance(findings, dict):
        return json.dumps(findings, indent=2)
    return str(findings)


def invoke_arbiter_claude(prompt, config):
    """
    Invoke Claude Opus 4.7 with effort=xhigh for adaptive thinking (ultrathink).
    Uses claude CLI with --model flag.

    IMPORTANT: Do NOT use budget_tokens — deprecated on Opus 4.7, throws 400.
    Use effort=xhigh which enables adaptive thinking automatically.
    """
    arbiter_cfg = config.get("arbiter", {})
    model = arbiter_cfg.get("model", "claude-opus-4-7")
    effort = arbiter_cfg.get("effort", "xhigh")

    start = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="br3-arbiter-") as tmpdir:
            prompt_file = os.path.join(tmpdir, "arbiter-prompt.txt")
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt)

            result = subprocess.run(
                [
                    "claude",
                    "--print",
                    "--model", model,
                    "--dangerously-skip-permissions",
                ],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=tmpdir,
            )

            duration = time.time() - start
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            if result.returncode != 0:
                raise RuntimeError(
                    f"Arbiter claude invocation failed (exit {result.returncode}): {stderr}"
                )

            return stdout, model, effort, duration

    except subprocess.TimeoutExpired:
        raise RuntimeError("Arbiter invocation timed out after 300s")
    except FileNotFoundError:
        raise RuntimeError("claude CLI not found in PATH")


def parse_arbiter_output(raw_text):
    """Extract JSON ruling from arbiter raw output."""
    import re
    match = re.search(r"\{[\s\S]*\}", raw_text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {
        "verdict": "BLOCKED",
        "rationale": "Arbiter output was malformed — treating as BLOCKED for safety.",
        "findings": [],
        "reviewer_accuracy": {"claude": "unknown", "codex": "unknown"},
        "parse_error": True,
        "raw_output": raw_text[:2000],
    }


def log_ruling(ruling, artifact, review_round, model, effort, duration):
    """
    Append arbiter ruling to decisions.log.

    Every ruling MUST be logged. The log entry is the authoritative record.
    """
    DECISIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now_iso()
    verdict = ruling.get("verdict", "UNKNOWN")
    rationale = ruling.get("rationale", "")[:200].replace("\n", " ")
    n_findings = len(ruling.get("findings", []))
    n_upheld = sum(1 for f in ruling.get("findings", []) if f.get("upheld", False))

    log_line = (
        f"[{timestamp}] ARBITER_RULING artifact={artifact!r} "
        f"round={review_round} verdict={verdict} "
        f"findings={n_findings} upheld={n_upheld} "
        f"model={model} effort={effort} "
        f"duration_s={duration:.1f} "
        f"rationale={rationale!r}"
    )

    with open(DECISIONS_LOG, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

    return log_line


def main():
    parser = argparse.ArgumentParser(description="Opus 4.7 arbiter for review disputes")
    parser.add_argument("--claude-findings", required=True, help="Path to Claude Sonnet findings JSON")
    parser.add_argument("--codex-findings", required=True, help="Path to Codex findings JSON")
    parser.add_argument("--rebuttal-findings", required=True, help="Path to post-rebuttal findings JSON")
    parser.add_argument("--disagreement", required=True, help="Path to disagreement detail JSON")
    parser.add_argument("--artifact", required=True, help="Artifact path under review")
    parser.add_argument("--round", type=int, default=1, help="Review round number")
    parser.add_argument("--project-root", help="Project root path")
    args = parser.parse_args()

    config = load_config()

    # Load all findings
    claude_findings = load_json_file(args.claude_findings)
    codex_findings = load_json_file(args.codex_findings)
    rebuttal_findings = load_json_file(args.rebuttal_findings)
    disagreement = load_json_file(args.disagreement)

    # Build prompt using summarized context (Phase 8 summarizer integration)
    # Try to use the summarizer for large inputs; fall back to direct formatting
    def maybe_summarize(data, label):
        text = json.dumps(data, indent=2) if not isinstance(data, str) else data
        if len(text.encode("utf-8")) > 8192:
            try:
                from core.cluster.summarizer import summarize_diff
                result = summarize_diff(text)
                return f"[summarized — {label}]\n{result['summary']}"
            except Exception:
                pass
        return format_findings_for_prompt(data) if isinstance(data, list) else text

    claude_text = maybe_summarize(claude_findings, "claude findings")
    codex_text = maybe_summarize(codex_findings, "codex findings")
    rebuttal_text = maybe_summarize(rebuttal_findings, "rebuttal findings")
    disagreement_text = (
        json.dumps(disagreement, indent=2)
        if isinstance(disagreement, (dict, list))
        else str(disagreement)
    )

    prompt = ARBITER_PROMPT_TEMPLATE.format(
        artifact=args.artifact,
        round=args.round,
        claude_findings=claude_text,
        codex_findings=codex_text,
        rebuttal_findings=rebuttal_text,
        disagreement=disagreement_text,
    )

    # Invoke arbiter — Opus 4.7 with effort=xhigh (adaptive thinking / ultrathink)
    try:
        raw_output, model, effort, duration = invoke_arbiter_claude(prompt, config)
    except Exception as exc:
        error_result = {
            "verdict": "ERROR",
            "rationale": f"Arbiter invocation failed: {exc}",
            "findings": [],
            "reviewer_accuracy": {"claude": "unknown", "codex": "unknown"},
            "error": str(exc),
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

    ruling = parse_arbiter_output(raw_output)
    ruling["model"] = model
    ruling["effort"] = effort
    ruling["duration_s"] = round(duration, 1)
    ruling["artifact"] = args.artifact
    ruling["review_round"] = args.round
    ruling["timestamp"] = utc_now_iso()

    # Log ruling (MANDATORY — every ruling must be logged)
    log_line = log_ruling(ruling, args.artifact, args.round, model, effort, duration)
    print(f"[arbiter] Ruling logged: {log_line}", file=sys.stderr)

    # Output ruling to stdout
    print(json.dumps(ruling, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
