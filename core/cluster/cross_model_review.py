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
import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
CONFIG_PATH = Path(__file__).parent / "cross_model_review_config.json"
CACHE_DIR = HOME / ".buildrunner" / "cache" / "cross-reviews"
SPEND_LOG = HOME / ".buildrunner" / "logs" / "cross-review-spend.json"
RUNTIME_CAPABILITY_LOG = HOME / ".buildrunner" / "logs" / "runtime-capability.log"

SUPPORTED_CODEX_VERSION_MIN = (0, 48, 0)
SUPPORTED_CODEX_VERSION_MAX = (0, 49, 0)
DEFAULT_CODEX_PROBE_TIMEOUT_SECONDS = 15
DEFAULT_CLAUDE_PROBE_TIMEOUT_SECONDS = 20

REVIEW_PROMPT = """You are a cross-model code reviewer. Your job is to find defects in code changes BEFORE they ship.

Run TWO distinct passes. Do not conflate them.

## Pass 1: FIND — Produce a complete, unfiltered list of every issue you observe

Scan the diff against these failure modes and list EVERY concrete issue you see, no matter how small. Do not self-filter during this pass. Do not skip items because they "might not matter" or "are probably fine." If you noticed it, record it.

1. **Bugs** — Logic errors, off-by-one, null/undefined access, wrong variable, broken conditions.
2. **Security Issues** — Injection, XSS, auth bypass, secrets in code, insecure defaults.
3. **Architecture Concerns** — Coupling violations, wrong abstraction layer, breaking existing patterns.
4. **Spec Compliance** — Does the diff deliver what the spec requires? Missing deliverables?
5. **Edge Cases** — Error handling gaps, empty states, race conditions, boundary values.

## Pass 2: CLASSIFY — Assign severity to each finding from Pass 1

Only after Pass 1 is complete, assign severity to each finding using these concrete rules:

- **blocker**: Will cause build failure, runtime crash, data loss, security breach, or block a deliverable required by the spec. Objective evidence, not judgment.
- **warning**: Likely to cause issues in production (race condition with plausible trigger, unhandled error path, perf regression > 2x). Concrete mechanism required.
- **note**: Minor concern, informational, style, or future-maintenance observation.

## Output

Output ONLY the Pass 2 JSON array. No prose outside the JSON. Include every item from Pass 1 — do not drop "small" findings in Pass 2; classify them as `note` instead. Example:
[
  {"finding": "Line 42: division by zero when count is 0", "severity": "blocker"},
  {"finding": "Auth token stored in localStorage — use httpOnly cookie", "severity": "warning"},
  {"finding": "Unused import on line 7", "severity": "note"}
]

If Pass 1 found no issues, output: []
"""


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"backends": {"codex": {"enabled": True, "timeout_seconds": 60}}, "budget": {"monthly_cap_usd": 50}}


def utc_now_iso():
    """Return a timezone-aware ISO8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_semver(raw_version):
    """Extract a semantic version tuple from Codex CLI version output."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", raw_version or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def detect_node_name():
    """Best-effort short hostname for runtime logs and preflight output."""
    try:
        return socket.gethostname().split(".")[0]
    except OSError:
        return "unknown"


def is_supported_codex_version(parsed_version):
    """Return True when the parsed Codex version is inside the validated Phase 0 range."""
    if parsed_version is None:
        return False
    return SUPPORTED_CODEX_VERSION_MIN <= parsed_version < SUPPORTED_CODEX_VERSION_MAX


def ensure_codex_compatible(command="codex"):
    """Check Codex CLI version against the Phase 0 validated compatibility window."""
    result = subprocess.run(
        [command, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    raw = (result.stdout or result.stderr or "").strip()
    parsed = parse_semver(raw)
    if result.returncode != 0 or not parsed:
        raise RuntimeError(f"Unable to determine Codex version: {raw or 'no output'}")
    if not is_supported_codex_version(parsed):
        raise RuntimeError(
            f"Unsupported Codex version {raw}. Supported range: "
            f">= {'.'.join(map(str, SUPPORTED_CODEX_VERSION_MIN))}, "
            f"< {'.'.join(map(str, SUPPORTED_CODEX_VERSION_MAX))}"
        )
    return {"raw": raw, "parsed": parsed}


def get_runtime_version(command):
    """Return raw version output for a runtime CLI."""
    result = subprocess.run(
        [command, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    raw = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0 or not raw:
        raise RuntimeError(f"Unable to determine runtime version for {command}: {raw or 'no output'}")
    return {"raw": raw}


def log_runtime_capability(entry):
    """Append runtime baseline/spike metadata as JSONL for later analysis."""
    RUNTIME_CAPABILITY_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(entry)
    payload.setdefault("timestamp", utc_now_iso())
    with open(RUNTIME_CAPABILITY_LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


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
        "timestamp": utc_now_iso(),
    }
    with open(get_cache_path(commit_sha), "w") as f:
        json.dump(entry, f, indent=2)


def load_spend():
    if SPEND_LOG.exists():
        with open(SPEND_LOG) as f:
            return json.load(f)
    return {"month": datetime.now(timezone.utc).strftime("%Y-%m"), "total_usd": 0.0, "requests": []}


def record_spend(cost_usd, model):
    SPEND_LOG.parent.mkdir(parents=True, exist_ok=True)
    data = load_spend()
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if data.get("month") != current_month:
        data = {"month": current_month, "total_usd": 0.0, "requests": []}
    data["total_usd"] += cost_usd
    data["requests"].append({
        "timestamp": utc_now_iso(),
        "model": model,
        "cost_usd": cost_usd,
    })
    with open(SPEND_LOG, "w") as f:
        json.dump(data, f, indent=2)


def check_budget(config):
    cap = config.get("budget", {}).get("monthly_cap_usd", 50)
    data = load_spend()
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if data.get("month") != current_month:
        return True  # New month, budget reset
    return data.get("total_usd", 0) < cap


class CodexAuthError(Exception):
    """Raised when Codex CLI auth is missing or expired — should NOT fallback to OpenRouter."""
    pass


def get_codex_auth_file(auth_file=None):
    """Resolve the Codex auth file path used for local CLI auth."""
    return Path(auth_file) if auth_file else HOME / ".codex" / "auth.json"


def check_codex_auth_file(auth_file=None):
    """Validate Codex auth file structure without probing the CLI."""
    auth_path = get_codex_auth_file(auth_file)

    if not auth_path.exists():
        return False, "Codex not authenticated. Run: codex"

    try:
        with open(auth_path, encoding="utf-8") as handle:
            auth = json.load(handle)
        if not auth.get("tokens", {}).get("access_token"):
            return False, "Codex tokens missing. Run: codex"
    except (json.JSONDecodeError, KeyError):
        return False, "Codex auth.json corrupted. Run: codex"
    return True, None


def run_codex_probe(command="codex", timeout=DEFAULT_CODEX_PROBE_TIMEOUT_SECONDS, project_root=None):
    """Run a minimal Codex CLI probe to confirm runtime availability and auth."""
    cwd = project_root if project_root and os.path.isdir(project_root) else None
    try:
        result = subprocess.run(
            [
                command,
                "--ask-for-approval",
                "never",
                "exec",
                "--skip-git-repo-check",
                "--",
                "reply with only: ok",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        auth_error = bool(
            re.search(
                r"not authenticated|auth expired|authentication|required|login|401|unauthorized|invalid token|refresh token",
                stderr,
                flags=re.IGNORECASE,
            )
        )
        ok = result.returncode == 0 and "ok" in stdout.lower()
        return {
            "ok": ok,
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "auth_error": auth_error,
            "timeout_seconds": timeout,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"Codex probe timed out after {timeout}s",
            "auth_error": False,
            "timeout_seconds": timeout,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "Codex CLI not installed. Install from: https://github.com/openai/codex",
            "auth_error": False,
            "timeout_seconds": timeout,
        }


def run_claude_probe(command="claude", timeout=DEFAULT_CLAUDE_PROBE_TIMEOUT_SECONDS):
    """Run a minimal Claude CLI probe in an isolated temp directory."""
    try:
        with tempfile.TemporaryDirectory(prefix="br3-claude-probe-") as temp_dir:
            result = subprocess.run(
                [
                    command,
                    "-p",
                    "--output-format",
                    "text",
                    "--dangerously-skip-permissions",
                    "reply with only READY",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=temp_dir,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            auth_error = bool(re.search(r"auth|login|token|401|subscription", stderr, flags=re.IGNORECASE))
            ok = result.returncode == 0 and "ready" in stdout.lower()
            return {
                "ok": ok,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "auth_error": auth_error,
                "timeout_seconds": timeout,
            }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"Claude probe timed out after {timeout}s",
            "auth_error": False,
            "timeout_seconds": timeout,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "Claude CLI not installed",
            "auth_error": False,
            "timeout_seconds": timeout,
        }


def finalize_runtime_preflight(result):
    """Apply direct/shadow dispatch policy to a runtime preflight result."""
    ok = bool(result["available"] and result["version"]["ok"] and result["auth"]["ok"])
    if result["probe"]["required"]:
        ok = ok and bool(result["probe"]["ok"])
    result["ok"] = ok
    if ok:
        result["policy_action"] = "allow"
        result["dispatch_ok"] = True
        result["failure_reason"] = None
    else:
        result["policy_action"] = "shadow_skipped" if result["mode"] == "shadow" else "fail_fast"
        result["dispatch_ok"] = result["mode"] == "shadow"
        result["failure_reason"] = (
            result["auth"].get("error")
            or result["probe"].get("stderr")
            or result["version"].get("error")
            or "runtime preflight failed"
        )
    log_runtime_capability(
        {
            "event": "runtime_preflight",
            "runtime": result["runtime"],
            "backend": result["runtime"],
            "node": result["node"],
            "mode": result["mode"],
            "status": "ok" if result["ok"] else "error",
            "policy_action": result["policy_action"],
            "dispatch_ok": result["dispatch_ok"],
            "version": result["version"].get("raw"),
            "error_class": result["failure_class"],
            "error_message": result["failure_reason"],
        }
    )
    return result


def build_runtime_preflight(
    runtime,
    mode="direct",
    command=None,
    project_root=None,
    probe=True,
    node_name=None,
    auth_file=None,
):
    """Build a runtime preflight record for local or remote dispatch decisions."""
    runtime = runtime.lower()
    mode = mode.lower()
    command = command or runtime
    node_name = node_name or detect_node_name()

    result = {
        "runtime": runtime,
        "mode": mode,
        "node": node_name,
        "command": command,
        "project_root": project_root,
        "available": bool(shutil.which(command)),
        "version": {"ok": False, "raw": None, "error": None},
        "auth": {"ok": False, "source": None, "error": None},
        "probe": {
            "required": bool(probe),
            "ok": None,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "timeout_seconds": None,
        },
        "ok": False,
        "dispatch_ok": False,
        "policy_action": None,
        "failure_reason": None,
        "failure_class": None,
    }

    if not result["available"]:
        result["auth"] = {"ok": False, "source": None, "error": f"{runtime} CLI not found in PATH"}
        result["failure_class"] = "RuntimeUnavailable"
        return finalize_runtime_preflight(result)

    try:
        if runtime == "codex":
            version = ensure_codex_compatible(command)
            result["version"] = {"ok": True, "raw": version["raw"], "error": None}
            auth_ok, auth_error = check_codex_auth_file(auth_file)
            result["auth"] = {
                "ok": auth_ok,
                "source": str(get_codex_auth_file(auth_file)),
                "error": auth_error,
            }
            if auth_ok and probe:
                probe_result = run_codex_probe(command=command, project_root=project_root)
                result["probe"].update(probe_result)
                if probe_result["auth_error"]:
                    result["auth"] = {
                        "ok": False,
                        "source": str(get_codex_auth_file(auth_file)),
                        "error": "Codex auth expired. Run: codex",
                    }
        elif runtime == "claude":
            version = get_runtime_version(command)
            result["version"] = {"ok": True, "raw": version["raw"], "error": None}
            # Claude auth is verified through the CLI probe because there is no stable file contract.
            result["auth"] = {"ok": True, "source": "claude-cli-session", "error": None}
            if probe:
                probe_result = run_claude_probe(command=command)
                result["probe"].update(probe_result)
                if not probe_result["ok"]:
                    result["auth"] = {
                        "ok": False,
                        "source": "claude-cli-session",
                        "error": probe_result["stderr"] or "Claude probe failed",
                    }
        else:
            result["auth"] = {"ok": False, "source": None, "error": f"Unsupported runtime: {runtime}"}
            result["failure_class"] = "UnsupportedRuntime"
    except Exception as exc:  # pragma: no cover - defensive preflight wrapper
        result["failure_class"] = exc.__class__.__name__
        result["version"]["error"] = str(exc)

    if result["failure_class"] is None and not result["version"]["ok"]:
        result["failure_class"] = "RuntimeCompatibilityError"
    elif result["failure_class"] is None and not result["auth"]["ok"]:
        result["failure_class"] = "RuntimeAuthError"
    elif result["failure_class"] is None and result["probe"]["required"] and not result["probe"]["ok"]:
        result["failure_class"] = "RuntimeProbeError"
    return finalize_runtime_preflight(result)


def check_codex_auth(project_root=None, auth_file=None, command="codex"):
    """
    Verify Codex CLI is authenticated before attempting review.
    Returns (True, None) if valid, (False, error_message) if not.
    """
    auth_ok, auth_error = check_codex_auth_file(auth_file)
    if not auth_ok:
        return False, auth_error

    probe = run_codex_probe(command=command, project_root=project_root)
    if probe["ok"]:
        return True, None
    if probe["auth_error"]:
        return False, "Codex auth expired. Run: codex"
    if "not installed" in probe["stderr"].lower():
        return False, "Codex CLI not installed. Install from: https://github.com/openai/codex"
    return False, probe["stderr"] or "Codex probe failed"


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


def parse_codex_event_stream(stdout):
    """Parse JSONL event output from `codex exec --json`."""
    events = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type"):
            events.append(event)
    return events


def extract_codex_message_and_usage(events):
    """Extract the final assistant message text and usage metadata from Codex JSON events."""
    final_message = ""
    usage = {}
    for event in events:
        if event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                final_message = item.get("text", "") or final_message
        if event.get("type") == "turn.completed":
            usage = event.get("usage", {}) or usage
    return final_message, usage


def build_review_prompt(diff_text, spec_text):
    """Build the review prompt shared by the live helper and the Phase 1 spike."""
    return (
        f"{REVIEW_PROMPT}\n\n---\n\n## Build Spec Context:\n{spec_text[:3000]}"
        f"\n\n---\n\n## Diff to Review:\n{diff_text[:8000]}"
    )


def review_via_codex(prompt, config, project_root=None, commit_sha=None):
    """Run review through Codex CLI (GPT-4o, free with ChatGPT Plus)."""
    timeout = config.get("backends", {}).get("codex", {}).get("timeout_seconds", 60)
    start = time.time()
    version_info = {"raw": None}
    try:
        with tempfile.TemporaryDirectory(prefix="br3-codex-live-review-") as temp_dir:
            # Keep the proven Codex path isolated even in the helper so repo-scoped execution does not return.
            version_info = ensure_codex_compatible()
            auth_valid, auth_error = check_codex_auth(project_root=temp_dir)
            if not auth_valid:
                raise CodexAuthError(auth_error)

            result = subprocess.run(
                [
                    "codex",
                    "--ask-for-approval",
                    "never",
                    "exec",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "workspace-write",
                    "--",
                    prompt,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=temp_dir,
            )
            if result.returncode == 0 and result.stdout.strip():
                findings = parse_findings(result.stdout)
                log_runtime_capability(
                    {
                        "backend": "codex",
                        "commit_sha": commit_sha,
                        "project_root": project_root,
                        "status": "completed",
                        "duration_ms": int((time.time() - start) * 1000),
                        "version": version_info["raw"],
                        "isolated": True,
                    }
                )
                return findings, "codex/gpt-4o", 0.0
            # Check for auth errors in output
            stderr = result.stderr.lower() if result.stderr else ""
            if "auth" in stderr or "login" in stderr or "token" in stderr or "401" in stderr:
                raise CodexAuthError("Codex auth expired during review. Run: codex")
            # Other failure
            stderr = result.stderr.strip()[:200] if result.stderr else "no output"
            raise RuntimeError(f"Codex exit {result.returncode}: {stderr}")
    except subprocess.TimeoutExpired:
        error = RuntimeError(f"Codex timed out after {timeout}s")
        log_runtime_capability(
            {
                "backend": "codex",
                "commit_sha": commit_sha,
                "project_root": project_root,
                "status": "error",
                "duration_ms": int((time.time() - start) * 1000),
                "version": version_info["raw"],
                "error_class": error.__class__.__name__,
                "error_message": str(error),
                "isolated": True,
            }
        )
        raise error
    except FileNotFoundError:
        raise CodexAuthError("Codex CLI not found in PATH")
    except Exception as exc:
        log_runtime_capability(
            {
                "backend": "codex",
                "commit_sha": commit_sha,
                "project_root": project_root,
                "status": "error",
                "duration_ms": int((time.time() - start) * 1000),
                "version": version_info["raw"],
                "error_class": exc.__class__.__name__,
                "error_message": str(exc),
                "isolated": True,
            }
        )
        raise


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
    full_prompt = build_review_prompt(diff_text, spec_text)

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
                return review_via_codex(full_prompt, config, commit_sha=commit_sha)
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


async def run_review_spike_async(
    diff_text,
    spec_text,
    commit_sha,
    project_root,
    runtimes=None,
    config=None,
):
    """
    Explicit Phase 1 scaffold path.

    Runs runtime adapters in parallel shadow mode without modifying the live review flow.
    """
    from core.runtime.context_compiler import compile_review_task
    from core.runtime.runtime_registry import create_phase1_runtime_registry
    from core.runtime.shadow_runner import run_shadow_command_async

    config = config or load_config()
    runtime_names = runtimes or ["claude", "codex"]
    if runtime_names == ["claude", "codex"] or runtime_names == ["codex", "claude"]:
        shadow_run = await run_shadow_command_async(
            diff_text=diff_text,
            spec_text=spec_text,
            commit_sha=commit_sha,
            project_root=project_root,
            command_name="review",
            config=config,
        )
        registry = create_phase1_runtime_registry(config)
        selected_runtimes = registry.create_many(["claude", "codex"])
        results = [shadow_run.primary_result.to_dict()]
        if shadow_run.shadow_result is not None:
            results.append(shadow_run.shadow_result.to_dict())
        return {
            "task_id": shadow_run.task_id,
            "mode": "parallel_shadow",
            "dispatch_mode": "parallel_shadow",
            "live_routing_changed": False,
            "selected_runtimes": [registration.describe() for registration in selected_runtimes],
            "task_metadata": {
                "dispatch_mode": "parallel_shadow",
                "command_name": "review",
                "shadow_status": shadow_run.shadow_status,
                "shadow_metrics": shadow_run.metrics,
            },
            "results": results,
        }
    task, context_summary = compile_review_task(
        diff_text=diff_text,
        spec_text=spec_text,
        project_root=project_root,
        commit_sha=commit_sha,
    )
    registry = create_phase1_runtime_registry(config)
    selected_runtimes = registry.create_many(runtime_names)

    results = await asyncio.gather(*(registration.adapter.run_review(task) for registration in selected_runtimes))
    return {
        "task_id": task.task_id,
        "mode": "parallel_shadow",
        "dispatch_mode": context_summary.dispatch_mode,
        "live_routing_changed": False,
        "selected_runtimes": [registration.describe() for registration in selected_runtimes],
        "task_metadata": task.metadata,
        "results": [result.to_dict() for result in results],
    }


def run_review_spike(diff_text, spec_text, commit_sha, project_root, runtimes=None, config=None):
    """Sync wrapper for CLI/tests around the async Phase 1 review spike."""
    return asyncio.run(
        run_review_spike_async(
            diff_text=diff_text,
            spec_text=spec_text,
            commit_sha=commit_sha,
            project_root=project_root,
            runtimes=runtimes,
            config=config,
        )
    )


def format_runtime_preflight(preflight):
    """Render a compact human-readable runtime preflight summary."""
    lines = [
        f"runtime={preflight['runtime']} mode={preflight['mode']} node={preflight['node']}",
        f"policy_action={preflight['policy_action']} dispatch_ok={preflight['dispatch_ok']}",
        f"version={preflight['version'].get('raw') or 'n/a'}",
        f"auth_ok={preflight['auth']['ok']} auth_source={preflight['auth'].get('source') or 'n/a'}",
    ]
    if preflight["probe"]["required"]:
        lines.append(
            f"probe_ok={preflight['probe']['ok']} exit_code={preflight['probe'].get('exit_code')} stderr={preflight['probe'].get('stderr') or ''}"
        )
    if preflight["failure_reason"]:
        lines.append(f"failure_reason={preflight['failure_reason']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Cross-model code review")
    parser.add_argument("--check-auth", action="store_true", help="Just verify Codex auth and exit")
    parser.add_argument("--runtime-preflight", choices=["claude", "codex"], help="Run runtime preflight and exit")
    parser.add_argument("--mode", choices=["direct", "shadow"], default="direct", help="Dispatch mode for runtime preflight")
    parser.add_argument("--json-output", action="store_true", help="Emit machine-readable JSON for runtime preflight")
    parser.add_argument("--no-probe", action="store_true", help="Skip runtime probe command for runtime preflight")
    parser.add_argument("--command", help="Override runtime CLI command for runtime preflight")
    parser.add_argument("--node-name", help="Override node name in runtime preflight output")
    parser.add_argument("--auth-file", help="Override Codex auth file path for runtime preflight")
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

    if args.runtime_preflight:
        preflight = build_runtime_preflight(
            runtime=args.runtime_preflight,
            mode=args.mode,
            command=args.command,
            project_root=args.project_root,
            probe=not args.no_probe,
            node_name=args.node_name,
            auth_file=args.auth_file,
        )
        if args.json_output:
            print(json.dumps(preflight, indent=2))
        else:
            print(format_runtime_preflight(preflight))
        sys.exit(0 if preflight["dispatch_ok"] else 1)

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
