#!/usr/bin/env python3
"""
cross_model_review.py — Cross-model code review engine

Accepts diff text + spec context, calls Codex CLI (primary) or OpenRouter API
(fallback), returns JSON array of {finding, severity} matching adversarial-review.sh format.

Usage:
    python3 cross_model_review.py \
        --diff-file <path> \
        --spec-file <path> \
        --commit-sha <sha> \
        --project-root <path>

Output (stdout): JSON array of findings [{finding, severity}]
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

HOME = Path.home()
CONFIG_PATH = Path(__file__).parent / "cross_model_review_config.json"
CACHE_DIR = HOME / ".buildrunner" / "cache" / "cross-reviews"
SPEND_LOG = HOME / ".buildrunner" / "logs" / "cross-review-spend.json"

REVIEW_PROMPT = """You are a cross-model code reviewer. Your job is to find defects in code changes BEFORE they ship.

Review the diff below against these failure modes:

1. **Bugs** — Logic errors, off-by-one, null/undefined access, wrong variable, broken conditions.
2. **Security Issues** — Injection, XSS, auth bypass, secrets in code, insecure defaults.
3. **Architecture Concerns** — Coupling violations, wrong abstraction layer, breaking existing patterns.
4. **Spec Compliance** — Does the diff deliver what the spec requires? Missing deliverables?
5. **Edge Cases** — Error handling gaps, empty states, race conditions, boundary values.

For EACH finding, output severity:
- **blocker**: Will cause build failure or runtime crash. Must be fixed.
- **warning**: Likely to cause issues. Should be addressed.
- **note**: Minor concern, informational.

Output ONLY a JSON array. No prose outside the JSON. Example:
[
  {"finding": "Line 42: division by zero when count is 0", "severity": "blocker"},
  {"finding": "Auth token stored in localStorage — use httpOnly cookie", "severity": "warning"}
]

If the diff has no issues, output: []
"""


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"backends": {"codex": {"enabled": True, "timeout_seconds": 60}}, "budget": {"monthly_cap_usd": 50}}


def get_cache_path(commit_sha):
    return CACHE_DIR / f"{commit_sha}.json"


def check_cache(commit_sha):
    cache_file = get_cache_path(commit_sha)
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    return None


def write_cache(commit_sha, findings, model_used, duration):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "sha": commit_sha,
        "model": model_used,
        "findings": findings,
        "duration_ms": int(duration * 1000),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    with open(get_cache_path(commit_sha), "w") as f:
        json.dump(entry, f, indent=2)


def load_spend():
    if SPEND_LOG.exists():
        with open(SPEND_LOG) as f:
            return json.load(f)
    return {"month": datetime.utcnow().strftime("%Y-%m"), "total_usd": 0.0, "requests": []}


def record_spend(cost_usd, model):
    SPEND_LOG.parent.mkdir(parents=True, exist_ok=True)
    data = load_spend()
    current_month = datetime.utcnow().strftime("%Y-%m")
    if data.get("month") != current_month:
        data = {"month": current_month, "total_usd": 0.0, "requests": []}
    data["total_usd"] += cost_usd
    data["requests"].append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": model,
        "cost_usd": cost_usd,
    })
    with open(SPEND_LOG, "w") as f:
        json.dump(data, f, indent=2)


def check_budget(config):
    cap = config.get("budget", {}).get("monthly_cap_usd", 50)
    data = load_spend()
    current_month = datetime.utcnow().strftime("%Y-%m")
    if data.get("month") != current_month:
        return True  # New month, budget reset
    return data.get("total_usd", 0) < cap


class CodexAuthError(Exception):
    """Raised when Codex CLI auth is missing or expired — should NOT fallback to OpenRouter."""
    pass


def check_codex_auth():
    """
    Verify Codex CLI is authenticated before attempting review.
    Returns (True, None) if valid, (False, error_message) if not.
    """
    auth_file = HOME / ".codex" / "auth.json"

    # Check auth file exists
    if not auth_file.exists():
        return False, "Codex not authenticated. Run: codex"

    # Check tokens exist
    try:
        with open(auth_file) as f:
            auth = json.load(f)
        if not auth.get("tokens", {}).get("access_token"):
            return False, "Codex tokens missing. Run: codex"
    except (json.JSONDecodeError, KeyError):
        return False, "Codex auth.json corrupted. Run: codex"

    # Quick auth test — run minimal prompt
    try:
        result = subprocess.run(
            ["codex", "exec", "--", "reply with only: ok"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0 and "ok" in result.stdout.lower():
            return True, None
        # Check for auth-specific errors
        stderr = result.stderr.lower() if result.stderr else ""
        if "auth" in stderr or "login" in stderr or "token" in stderr or "401" in stderr:
            return False, "Codex auth expired. Run: codex"
        # Other error — might still work for full prompt
        return True, None
    except subprocess.TimeoutExpired:
        return True, None  # Timeout on test doesn't mean auth is bad
    except FileNotFoundError:
        return False, "Codex CLI not installed. Install from: https://github.com/openai/codex"


def parse_findings(text):
    """Extract JSON array of findings from model output."""
    import re
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            arr = json.loads(match.group())
            for item in arr:
                if "finding" not in item or "severity" not in item:
                    raise ValueError("Invalid finding structure")
                if item["severity"] not in ("blocker", "warning", "note"):
                    item["severity"] = "note"
            return arr
        except (json.JSONDecodeError, ValueError):
            return [{"finding": "Cross-model review returned malformed output", "severity": "warning"}]
    # No JSON array found — wrap raw text
    return [{"finding": text.strip()[:500], "severity": "note"}]


def review_via_codex(prompt, config):
    """Run review through Codex CLI (GPT-4o, free with ChatGPT Plus)."""
    # Pre-flight auth check — fail fast with clear message, don't fallback
    auth_valid, auth_error = check_codex_auth()
    if not auth_valid:
        raise CodexAuthError(auth_error)

    timeout = config.get("backends", {}).get("codex", {}).get("timeout_seconds", 60)
    try:
        result = subprocess.run(
            ["codex", "exec", "--", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return parse_findings(result.stdout), "codex/gpt-4o", 0.0
        # Check for auth errors in output
        stderr = result.stderr.lower() if result.stderr else ""
        if "auth" in stderr or "login" in stderr or "token" in stderr or "401" in stderr:
            raise CodexAuthError("Codex auth expired during review. Run: codex")
        # Other failure
        stderr = result.stderr.strip()[:200] if result.stderr else "no output"
        raise RuntimeError(f"Codex exit {result.returncode}: {stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Codex timed out after {timeout}s")
    except FileNotFoundError:
        raise CodexAuthError("Codex CLI not found in PATH")


def review_via_openrouter(prompt, config):
    """Fallback: call OpenRouter API for GPT-4o review."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    if not check_budget(config):
        raise RuntimeError("Monthly OpenRouter budget exceeded")

    or_config = config.get("backends", {}).get("openrouter", {})
    model = or_config.get("model", "openai/gpt-4o")
    api_url = or_config.get("api_url", "https://openrouter.ai/api/v1/chat/completions")
    timeout = or_config.get("timeout_seconds", 60)

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://buildrunner.dev",
            "X-Title": "BR3 Cross-Model Review",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            # Estimate cost (GPT-4o: ~$2.50/M input, $10/M output)
            usage = data.get("usage", {})
            cost = (usage.get("prompt_tokens", 0) * 2.5 + usage.get("completion_tokens", 0) * 10) / 1_000_000
            record_spend(cost, model)
            return parse_findings(content), model, cost
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenRouter HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenRouter connection failed: {e.reason}")


def run_review(diff_text, spec_text, commit_sha, config):
    """Run review through backends in priority order."""
    full_prompt = f"{REVIEW_PROMPT}\n\n---\n\n## Build Spec Context:\n{spec_text[:3000]}\n\n---\n\n## Diff to Review:\n{diff_text[:8000]}"

    backends = config.get("backends", {})
    errors = []

    # Sort by priority
    ordered = sorted(
        [(name, cfg) for name, cfg in backends.items() if cfg.get("enabled", False)],
        key=lambda x: x[1].get("priority", 99),
    )

    for name, _ in ordered:
        try:
            if name == "codex":
                return review_via_codex(full_prompt, config)
            elif name == "openrouter":
                return review_via_openrouter(full_prompt, config)
            # below/future backends would go here
        except CodexAuthError as e:
            # Auth errors should NOT fallback — fail immediately with clear message
            print(f"\n⚠️  CODEX AUTH REQUIRED: {e}", file=sys.stderr)
            print("   To authenticate, run: codex", file=sys.stderr)
            print("   (This ensures reviews use your ChatGPT Plus, not paid OpenRouter)\n", file=sys.stderr)
            return [{"finding": f"Codex auth required: {e}", "severity": "blocker"}], "auth_required", 0.0
        except RuntimeError as e:
            errors.append(f"{name}: {e}")
            continue

    # All backends failed
    return [{"finding": f"All review backends failed: {'; '.join(errors)}", "severity": "warning"}], "none", 0.0


def main():
    parser = argparse.ArgumentParser(description="Cross-model code review")
    parser.add_argument("--check-auth", action="store_true", help="Just verify Codex auth and exit")
    parser.add_argument("--diff-file", help="Path to diff text file")
    parser.add_argument("--spec-file", help="Path to build spec file")
    parser.add_argument("--commit-sha", help="Commit SHA for caching")
    parser.add_argument("--project-root", help="Project root path")
    args = parser.parse_args()

    # Auth check mode — verify and exit
    if args.check_auth:
        auth_valid, auth_error = check_codex_auth()
        if auth_valid:
            print("✓ Codex CLI authenticated")
            sys.exit(0)
        else:
            print(f"✗ {auth_error}", file=sys.stderr)
            sys.exit(1)

    # Normal review mode — require all args
    if not all([args.diff_file, args.spec_file, args.commit_sha, args.project_root]):
        parser.error("--diff-file, --spec-file, --commit-sha, and --project-root are required for review")

    # Read inputs (handle binary/non-UTF-8 diffs gracefully)
    with open(args.diff_file, encoding="utf-8", errors="replace") as f:
        diff_text = f.read()
    with open(args.spec_file, encoding="utf-8", errors="replace") as f:
        spec_text = f.read()

    config = load_config()

    # Ensure cache dir exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache
    cached = check_cache(args.commit_sha)
    if cached:
        print(json.dumps(cached["findings"], indent=2))
        return

    # Run review
    start = time.time()
    findings, model_used, cost = run_review(diff_text, spec_text, args.commit_sha, config)
    duration = time.time() - start

    # Cache result
    write_cache(args.commit_sha, findings, model_used, duration)

    # Output JSON findings to stdout
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
