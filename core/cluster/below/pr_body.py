"""
pr_body.py — PR body generation via Below qwen2.5-coder.

Three-tier pipeline:
  Tier 1: Below qwen2.5-coder:7b (diff → markdown PR body)
  Tier 2: Claude (architectural keywords detected in diff)
  Tier 3: Static template fallback (Below + Claude unreachable)

Architectural keyword router — escalates to Claude when diff touches:
  - schema migration (*.sql, alembic, migration/)
  - interface changes (API, REST, GraphQL keywords)
  - auth / RLS / security
  - deploy config (Dockerfile, docker-compose, CI/CD, k8s)

Usage (as library):
    from core.cluster.below.pr_body import generate_pr_body

    body = generate_pr_body(diff_stat=diff_stat, commits=commits, branch=branch)

Usage (as CLI):
    python3 -m core.cluster.below.pr_body --diff-stat "..." --commits "..." --branch main

Metrics:
    Appended to ~/.buildrunner/pr-body-metrics.jsonl per call.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BELOW_HOST: str = "10.0.1.105"
BELOW_OLLAMA_PORT: int = 11434
BELOW_GENERATE_URL: str = f"http://{BELOW_HOST}:{BELOW_OLLAMA_PORT}/api/generate"
BELOW_MODEL: str = "qwen2.5-coder:7b"
TIMEOUT_SECONDS: float = 15.0
METRICS_FILE: Path = Path.home() / ".buildrunner" / "pr-body-metrics.jsonl"

# Architectural keywords that trigger Claude escalation
ARCH_KEYWORDS: list[str] = [
    r"schema.migration",
    r"\.sql\b",
    r"\balembic\b",
    r"\bRLS\b",
    r"\brow.level.security\b",
    r"\bauth\b",
    r"\bsecurity.audit\b",
    r"\bDockerfile\b",
    r"docker.compose",
    r"\bkubernetes\b",
    r"\bk8s\b",
    r"\bterraform\b",
    r"\bCI/CD\b",
    r"\binterface.change\b",
    r"\bbreaking.change\b",
    r"BREAKING.CHANGE",
]

_ARCH_PATTERN = re.compile("|".join(ARCH_KEYWORDS), re.IGNORECASE)


def _emit_metric(tier: int, latency_ms: float, accepted: bool) -> None:
    try:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tier": tier,
            "latency_ms": round(latency_ms, 1),
            "accepted": accepted,
        }
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with METRICS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _needs_escalation(diff_stat: str, commits: str) -> bool:
    """Return True if the diff/commits contain architectural keywords."""
    combined = f"{diff_stat}\n{commits}"
    return bool(_ARCH_PATTERN.search(combined))


def _static_template(branch: str, commits: str, diff_stat: str, changed_count: int) -> str:
    """Tier 3: deterministic static template. Never fails."""
    return f"""## Summary

{commits}

## Changes

{diff_stat}

{changed_count} file(s) changed.

## Test plan

- [ ] CI passes
- [ ] Gate sequence completed: preflight → rebase → review → test → docs → log-scan → commit → publish
- [ ] No regressions in affected paths

---

Shipped via [/ship](~/.claude/commands/ship.md) on `{branch}`.
"""


def _tier1_below(
    diff_stat: str,
    commits: str,
    branch: str,
    changed_count: int,
) -> Optional[str]:
    """Tier 1: Below qwen2.5-coder:7b generates the PR body."""
    t0 = time.monotonic()
    prompt = f"""You are a PR body generator. Write a concise GitHub pull request body in Markdown.

Branch: {branch}
Files changed: {changed_count}

Commits:
{commits}

Diff stat:
{diff_stat}

Write a PR body with these sections:
## Summary
(2-4 bullet points summarising what changed and why)

## Changes
(brief technical description of key changes)

## Test plan
(markdown checklist of things to verify)

Keep it under 300 words. Reply with ONLY the markdown, no preamble."""

    try:
        payload = {
            "model": BELOW_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 400},
        }
        resp = httpx.post(BELOW_GENERATE_URL, json=payload, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        body = data.get("response", "").strip()
        latency_ms = (time.monotonic() - t0) * 1000

        if not body or len(body) < 50:
            _emit_metric(1, latency_ms, False)
            return None

        _emit_metric(1, latency_ms, True)
        return body

    except Exception as exc:
        latency_ms = (time.monotonic() - t0) * 1000
        logger.debug("pr_body tier 1 failed: %s", exc)
        _emit_metric(1, latency_ms, False)
        return None


def _tier2_claude(
    diff_stat: str,
    commits: str,
    branch: str,
    changed_count: int,
) -> Optional[str]:
    """
    Tier 2: Claude (used when architectural keywords detected or Below unavailable).
    Returns None if claude CLI is unavailable or times out.
    """
    t0 = time.monotonic()
    try:
        import subprocess

        prompt = f"""Write a concise GitHub PR body in Markdown for this change.
Branch: {branch}  Files changed: {changed_count}

Commits:
{commits}

Diff stat:
{diff_stat}

Sections: ## Summary (2-4 bullets) / ## Changes / ## Test plan (checklist).
Under 300 words. Reply with ONLY the markdown."""

        result = subprocess.run(
            ["claude", "--print", "--model", "claude-haiku-4"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=20,
        )
        body = result.stdout.strip()
        latency_ms = (time.monotonic() - t0) * 1000

        if not body or len(body) < 50:
            _emit_metric(2, latency_ms, False)
            return None

        _emit_metric(2, latency_ms, True)
        return body

    except Exception as exc:
        latency_ms = (time.monotonic() - t0) * 1000
        logger.debug("pr_body tier 2 failed: %s", exc)
        _emit_metric(2, latency_ms, False)
        return None


def generate_pr_body(
    diff_stat: str = "",
    commits: str = "",
    branch: str = "main",
    changed_count: int = 0,
) -> str:
    """
    Generate a PR body using the three-tier pipeline.

    Tier 1 → Below qwen2.5-coder (fast, local inference)
    Tier 2 → Claude (architectural keywords OR Below unavailable)
    Tier 3 → Static template (always succeeds)

    Args:
        diff_stat:     Output of `git diff origin/main...HEAD --stat`.
        commits:       Newline-separated commit summaries.
        branch:        Current branch name.
        changed_count: Number of changed files.

    Returns:
        Markdown string suitable for use as a GitHub PR body.
    """
    # Architectural keyword check — escalate directly to Claude
    if _needs_escalation(diff_stat, commits):
        logger.info("pr_body: architectural keywords detected — escalating to Claude (tier 2)")
        body = _tier2_claude(diff_stat, commits, branch, changed_count)
        if body:
            return body
        # Claude unavailable — fall through to static
        return _static_template(branch, commits, diff_stat, changed_count)

    # Normal path: try Below first
    body = _tier1_below(diff_stat, commits, branch, changed_count)
    if body:
        return body

    # Below failed — try Claude
    body = _tier2_claude(diff_stat, commits, branch, changed_count)
    if body:
        return body

    # Both unavailable — static template
    return _static_template(branch, commits, diff_stat, changed_count)


# ---------------------------------------------------------------------------
# CLI entry point (called by pr-body-gen.sh)
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate PR body via Below/Claude/static")
    parser.add_argument("--diff-stat", default="", help="git diff --stat output")
    parser.add_argument("--commits", default="", help="Newline-separated commit summaries")
    parser.add_argument("--branch", default="main", help="Current branch name")
    parser.add_argument("--changed-count", type=int, default=0, help="Number of changed files")
    args = parser.parse_args()

    body = generate_pr_body(
        diff_stat=args.diff_stat,
        commits=args.commits,
        branch=args.branch,
        changed_count=args.changed_count,
    )
    sys.stdout.write(body)
    if not body.endswith("\n"):
        sys.stdout.write("\n")


if __name__ == "__main__":
    _main()
