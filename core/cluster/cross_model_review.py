#!/usr/bin/env python3
"""
cross_model_review.py — Cross-model code review engine

Accepts diff text + spec context, runs Sonnet (via `claude` CLI) and GPT-5.4
(via `codex` CLI) in parallel, and returns a JSON array of
{finding, severity} matching the adversarial-review.sh format. No paid APIs
are called — both reviewers run through their authenticated CLI plans.

Usage:
    python3 cross_model_review.py \
        --mode plan --plan <plan_file> --project-root <root>

Output (stdout): JSON array of findings [{finding, severity}]
"""

import argparse
import asyncio
import atexit
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from core.cluster.arbiter import arbitrate
from core.cluster.cluster_config import get_below_host, get_below_model, get_ollama_port
from core.cluster.log_utils import _append_decision_log, get_decisions_log_path
from core.cluster.review_verdict import Verdict

HOME = Path.home()
CONFIG_PATH = Path(__file__).parent / "cross_model_review_config.json"
CACHE_DIR = HOME / ".buildrunner" / "cache" / "cross-reviews"
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
    return {"backends": {"codex": {"enabled": True, "timeout_seconds": 360}}}


# ---------------------------------------------------------------------------
# Phase 6: Non-blocking telemetry emit for adversarial_review_ran
# ---------------------------------------------------------------------------

def _emit_adversarial_review_ran(mode: str, verdict: str, findings_count: int, commit_sha: str = "") -> None:
    """Emit adversarial_review_ran event to telemetry.db. Swallows all errors."""
    try:
        import sqlite3 as _sqlite3
        import uuid as _uuid
        from datetime import datetime as _dt

        db_candidates = [
            Path.cwd() / ".buildrunner" / "telemetry.db",
            Path.home() / "Projects" / "BuildRunner3" / ".buildrunner" / "telemetry.db",
        ]
        db_path = next((p for p in db_candidates if p.exists()), None)
        if db_path is None:
            return

        metadata = {
            "mode": mode[:32],
            "verdict": verdict[:32],
            "findings_count": findings_count,
            "commit_sha": (commit_sha or "")[:40],
        }
        conn = _sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "INSERT INTO events (event_id, event_type, timestamp, metadata, success) VALUES (?, ?, ?, ?, ?)",
                (
                    str(_uuid.uuid4()),
                    "adversarial_review_ran",
                    _dt.now(__import__('datetime').timezone.utc).isoformat(),
                    json.dumps(metadata),
                    1 if verdict in ("APPROVED", "REVIEWER_ERROR") else 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        pass  # Non-blocking — swallow all emit errors


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


class CodexAuthError(Exception):
    """Raised when Codex CLI auth is missing or expired."""
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
            return [{"finding": "Cross-model review returned malformed output", "severity": "warning", "fix_type": "fixable"}]
    # No JSON array found — wrap raw text (no hard truncation; callers may summarize upstream)
    return [{"finding": text.strip(), "severity": "note", "fix_type": "fixable"}]


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


_DIFF_SIZE_THRESHOLD = 12 * 1024  # 12 KB — summarize-before-escalate threshold


def build_review_prompt(diff_text: str, spec_text: str, system_prompt: str | None = None) -> str:
    """Build the review prompt using cache_policy breakpoints.

    Breakpoint layout (per AGENTS.md 3-breakpoint contract):
      1. system + tools       — system_prompt or REVIEW_PROMPT (stable, cached)
      2. project/skill context — spec text (stable within a session, cached)
      3. task payload          — diff text (per-request, not cached)

    Callers that require the fix_type schema (three-way adversarial review)
    must pass ``system_prompt=THREE_WAY_REVIEW_PROMPT``; the default
    REVIEW_PROMPT omits that schema.

    If diff_text exceeds 12KB (summarize-before-escalate threshold), it is
    compressed via summarizer.summarize_diff() before being placed into
    breakpoint 3.  Below offline → original diff used, no truncation.

    NEVER inline timestamps, UUIDs, or other dynamic values into breakpoints 1–2.
    """
    from core.cluster.summarizer import summarize_diff
    from core.runtime.cache_policy import build_cached_prompt

    diff_payload = diff_text
    if len(diff_text.encode("utf-8")) > _DIFF_SIZE_THRESHOLD:
        result = summarize_diff(diff_text)
        # Use the summary as the payload; if truncated=True (Below offline),
        # result["summary"] is the original diff — no content is lost.
        diff_payload = result["summary"]
        if result["excerpts"]:
            diff_payload += (
                "\n\n--- CRITICAL EXCERPTS (preserved verbatim) ---\n"
                + "\n".join(result["excerpts"])
            )

    blocks = build_cached_prompt(
        system_text=system_prompt or REVIEW_PROMPT,
        skill_context=f"## Build Spec Context:\n{spec_text}",
        task_payload=f"## Diff to Review:\n{diff_payload}",
    )
    # Flatten to a plain string for the CLI reviewers, which pipe the prompt
    # to the `claude` and `codex` CLIs via stdin.
    return "\n\n---\n\n".join(block["text"] for block in blocks)


def review_via_codex(prompt, config, project_root=None, commit_sha=None):
    """Run review through Codex CLI (GPT-5.4, authenticated via ChatGPT plan)."""
    timeout = config.get("backends", {}).get("codex", {}).get("timeout_seconds", 360)
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
                    "-",
                ],
                input=prompt,
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
            stderr = result.stderr.strip() if result.stderr else "no output"
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


async def run_review_spike_async(
    diff_text,
    spec_text,
    commit_sha,
    project_root,
    runtimes=None,
    config=None,
):
    """Run runtime adapters in parallel without modifying the live review flow."""
    from core.runtime.context_compiler import compile_review_task
    from core.runtime.runtime_registry import create_phase1_runtime_registry

    config = config or load_config()
    runtime_names = runtimes or ["claude", "codex"]

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
        "mode": "parallel",
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


# ---------------------------------------------------------------------------
# One-round cross-model review pipeline
# ---------------------------------------------------------------------------
# Two reviewers run in parallel exactly once. Disagreement or abstention routes
# to the Opus arbiter, which always commits a final verdict.
# ---------------------------------------------------------------------------

_THREE_WAY_DECISIONS_LOG = get_decisions_log_path()  # single source of truth — core/cluster/log_utils.py

THREE_WAY_REVIEW_PROMPT = REVIEW_PROMPT + """

## Required Output Schema

Every finding MUST include ALL of these fields:
- finding: <string>
- severity: blocker | warning | note
- location: <file path or function name, "global" if not localized>
- claim: <one sentence stating what is wrong>
- evidence: <specific line/code excerpt or "inferred from context">
- confidence: high | medium | low
- fix_type: fixable | structural

Findings missing fix_type will be REJECTED. Findings missing any field will be
rejected. Output ONLY the JSON array.
"""


def _normalize_finding(text):
    """Normalize a finding string for comparison (dedup/persistent detection)."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _has_fix_type(findings):
    """Return True if all findings have a fix_type field."""
    return all("fix_type" in item for item in findings if isinstance(item, dict))


def _reject_missing_fix_type(findings, reviewer_name):
    """Raise ValueError if any finding is missing fix_type."""
    missing = [
        i for i, item in enumerate(findings)
        if isinstance(item, dict) and "fix_type" not in item
    ]
    if missing:
        raise ValueError(
            f"Reviewer '{reviewer_name}' output rejected: findings at indices "
            f"{missing} are missing required 'fix_type' field."
        )


def _detect_structural_blocker(findings):
    """Return the first structural blocker finding, or None."""
    for item in findings:
        if (
            isinstance(item, dict)
            and item.get("severity") == "blocker"
            and item.get("fix_type") == "structural"
        ):
            return item
    return None


def _detect_persistent_blockers(round1_findings, round2_findings):
    """Return normalized texts of blockers that appear in both rounds."""
    def blocker_norms(findings):
        return {
            _normalize_finding(item.get("finding", ""))
            for item in findings
            if isinstance(item, dict) and item.get("severity") == "blocker"
        }
    return blocker_norms(round1_findings) & blocker_norms(round2_findings)


def _merge_two_way_findings(claude_findings, codex_findings):
    """Merge findings from two reviewers with consensus detection."""
    merged = {}
    for source, findings in (("claude", claude_findings), ("codex", codex_findings)):
        for item in findings:
            if not isinstance(item, dict):
                continue
            finding = (item.get("finding") or "").strip()
            if not finding:
                continue
            key = _normalize_finding(finding)
            record = merged.setdefault(key, {
                "finding": finding,
                "severity": item.get("severity", "note"),
                "location": item.get("location", "global"),
                "claim": item.get("claim", finding),
                "evidence": item.get("evidence", "inferred from context"),
                "confidence": item.get("confidence", "medium"),
                "fix_type": item.get("fix_type", "fixable"),
                "sources": [],
                "consensus": False,
            })
            # Escalate severity: take the highest
            sev_rank = {"note": 0, "warning": 1, "blocker": 2}
            if sev_rank.get(item.get("severity", "note"), 0) > sev_rank.get(record["severity"], 0):
                record["severity"] = item["severity"]
                record["finding"] = finding
            # Structural is stickier
            if item.get("fix_type") == "structural":
                record["fix_type"] = "structural"
            if source not in record["sources"]:
                record["sources"].append(source)

    items = list(merged.values())
    for item in items:
        item["sources"].sort()
        item["consensus"] = len(item["sources"]) > 1

    return items


def _check_consensus(merged_findings):
    """Return (has_consensus, blockers, disagreements)."""
    blockers = [f for f in merged_findings if f.get("severity") == "blocker"]
    consensus_blockers = [f for f in blockers if f.get("consensus")]
    solo_blockers = [f for f in blockers if not f.get("consensus")]
    # Consensus = no solo blockers (all blockers agreed on, or no blockers)
    has_consensus = len(solo_blockers) == 0
    return has_consensus, consensus_blockers, solo_blockers


def review_via_claude_inline(prompt, config, timeout=120):
    """
    Run review through Claude CLI (Sonnet 4.6 per config.reviewers.claude_model).
    Returns (findings, model_id).
    """
    reviewer_cfg = config.get("reviewers", {})
    model = reviewer_cfg.get("claude_model", "claude-sonnet-4-6")
    start = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="br3-claude-review-") as tmpdir:
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
                timeout=timeout,
                cwd=tmpdir,
            )
            stdout = (result.stdout or "").strip()
            if result.returncode != 0:
                raise RuntimeError(
                    f"Claude review failed (exit {result.returncode}): {result.stderr or ''}"
                )
            findings = parse_findings(stdout)
            _reject_missing_fix_type(findings, f"claude/{model}")
            return findings, model
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Claude review timed out after {timeout}s")
    except FileNotFoundError:
        raise RuntimeError("claude CLI not found in PATH")


async def _review_with_sonnet(prompt, config, timeout_seconds):
    """Sonnet 4.6 via the `claude` CLI on the authenticated Claude plan."""
    findings, _model = await asyncio.to_thread(
        review_via_claude_inline, prompt, config, timeout_seconds
    )
    return findings


async def _review_with_gpt(prompt, config, timeout_seconds):
    """GPT-5.4 via the `codex` CLI on the authenticated ChatGPT plan."""

    def _blocking():
        codex_cfg = config.setdefault("backends", {}).setdefault("codex", {})
        codex_cfg["timeout_seconds"] = max(
            int(codex_cfg.get("timeout_seconds", 360)), int(timeout_seconds)
        )
        findings, _model, _cost = review_via_codex(prompt, config)
        return findings

    return await asyncio.to_thread(_blocking)


async def _run_reviewer(name, reviewer_coro, prompt, config, timeout_seconds):
    """Execute a single reviewer with a hard timeout."""
    start = time.perf_counter()
    try:
        findings = await asyncio.wait_for(
            reviewer_coro(prompt, config, timeout_seconds), timeout=timeout_seconds
        )
        return {
            "name": name,
            "findings": findings,
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "status": "ok",
        }
    except asyncio.TimeoutError:
        return {
            "name": name,
            "findings": [],
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "status": "timeout",
        }
    except Exception as exc:
        print(f"[three-way] reviewer error: {name}: {exc}", file=sys.stderr)
        return {
            "name": name,
            "findings": [],
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "status": "error",
        }


async def _run_parallel_reviewers_one_round(prompt, config, timeout_seconds=360):
    """Run Sonnet 4.6 (claude CLI) and GPT-5.4 (codex CLI) in parallel."""
    return await asyncio.gather(
        _run_reviewer("sonnet-4-6", _review_with_sonnet, prompt, config, timeout_seconds),
        _run_reviewer("gpt-5.4", _review_with_gpt, prompt, config, timeout_seconds),
    )


def _log_three_way_decision(event, details=""):
    """Append a three-way review event to decisions.log via log_utils (flock-guarded)."""
    _append_decision_log("THREE_WAY_REVIEW", event, details)


# --- Plan-context builder (canonical replacement for adversarial-review.sh file-tree + excerpts) ---
#
# Full repo visibility locally — no rsync, no Otis truncation. The reviewers see
# every source file the plan references plus a budgeted tree of src/ + supabase/
# + top-level config files. This eliminates "file missing" false-positive
# blockers that plagued the Otis-dispatched path.

_PLAN_EXCERPT_BUDGET_BYTES = 180_000
_PLAN_EXCERPT_PER_FILE_LINES = 180
_PLAN_TREE_FILES_PER_CATEGORY = {"src": 1200, "supabase": 400, "top": 200}
_PLAN_PATH_REGEX = re.compile(
    r"(src|supabase|public|scripts|tests|core|api|ui|\.buildrunner)/[A-Za-z0-9_./-]+"
    r"|(?:package\.json|tsconfig\.json|vite\.config\.(?:ts|js)|playwright\.config\.(?:ts|js))"
)
_PLAN_CITED_REGEX = re.compile(
    r"(src|supabase|scripts|tests|core|api|ui)/[A-Za-z0-9_./-]+\.(?:ts|tsx|js|jsx|py|sql)"
    r"|vite\.config\.(?:ts|js)|playwright\.config\.(?:ts|js)"
)
_PLAN_EXCLUDE_PATH_FRAGMENTS = (
    "/node_modules/", "/.git/", "/dist/", "/.next/",
    "/.buildrunner/build-reports/", "/.buildrunner/telemetry",
    "/.runner", "/coverage/", "/.vercel/", "/.netlify/", "/.turbo/",
)
_PLAN_EXCLUDE_SUFFIXES = (".lock", ".log", ".map", ".tsbuildinfo", ".db")


def _walk_project_files(project_root):
    """Yield relative file paths under project_root matching filter rules."""
    root = Path(project_root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir_check = "/" + rel_dir + "/" if rel_dir != "." else "/"
        if any(frag in rel_dir_check for frag in _PLAN_EXCLUDE_PATH_FRAGMENTS):
            dirnames[:] = []
            continue
        for name in filenames:
            if name.endswith(_PLAN_EXCLUDE_SUFFIXES):
                continue
            rel = Path(dirpath, name).relative_to(root).as_posix()
            yield rel


def build_project_file_tree(plan_text, project_root):
    """Produce a budgeted file tree so reviewers can verify file existence."""
    try:
        all_rel = sorted(_walk_project_files(project_root))
    except OSError:
        return "no-project-files"

    referenced = sorted({m.group(0) for m in _PLAN_PATH_REGEX.finditer(plan_text or "")})
    always_include = [r for r in referenced if (Path(project_root) / r).exists()]

    src_files = [r for r in all_rel if r.startswith("src/")][:_PLAN_TREE_FILES_PER_CATEGORY["src"]]
    supabase_files = [r for r in all_rel if r.startswith("supabase/")][:_PLAN_TREE_FILES_PER_CATEGORY["supabase"]]
    top_files = [r for r in all_rel if "/" not in r][:_PLAN_TREE_FILES_PER_CATEGORY["top"]]
    core_files = [r for r in all_rel if r.startswith("core/")][:1200]
    api_files = [r for r in all_rel if r.startswith("api/")][:400]
    ui_files = [r for r in all_rel if r.startswith("ui/")][:400]
    tests_files = [r for r in all_rel if r.startswith("tests/")][:400]

    combined = set(always_include) | set(top_files) | set(src_files) | set(supabase_files)
    combined |= set(core_files) | set(api_files) | set(ui_files) | set(tests_files)
    return "\n".join(sorted(combined))


def _extract_signatures(text):
    """Pull export/interface/function/CREATE lines from a file body."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if (stripped.startswith(("export ", "interface ", "type ", "class ",
                                 "async function ", "function ", "def ", "class "))
                or stripped.upper().startswith(("CREATE TABLE", "ALTER ", "CREATE INDEX", "CREATE POLICY"))):
            out.append(f"{i}:{line}")
        if len(out) >= 120:
            break
    return "\n".join(out)


def build_cited_file_excerpts(plan_text, project_root):
    """Emit file excerpts for every source path cited in plan_text."""
    if not plan_text:
        return ""
    cited = sorted({m.group(0) for m in _PLAN_CITED_REGEX.finditer(plan_text)})
    if not cited:
        return ""

    sized = []
    for rel in cited:
        abs_path = Path(project_root) / rel
        if not abs_path.is_file():
            continue
        try:
            sized.append((abs_path.stat().st_size, rel, abs_path))
        except OSError:
            continue
    sized.sort()  # smallest first

    parts = ["## Cited File Excerpts (generated locally — ground truth for API/schema verification)", ""]
    total = 0
    for size, rel, abs_path in sized:
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if total >= _PLAN_EXCERPT_BUDGET_BYTES:
            parts.append(f"### {rel} (exports only — {size} bytes total, over excerpt budget)")
            parts.append("```")
            parts.append(_extract_signatures(content))
            parts.append("```\n")
            continue
        parts.append(f"### {rel}")
        parts.append("```")
        if size > 25_000:
            head = "\n".join(content.splitlines()[:_PLAN_EXCERPT_PER_FILE_LINES])
            parts.append(head)
            parts.append(f"\n... [truncated, {size} bytes total — full exports/signatures below] ...\n")
            parts.append(_extract_signatures(content))
        else:
            parts.append(content)
        parts.append("```\n")
        total += size
    return "\n".join(parts)


PLAN_ADVERSARIAL_PROMPT = """You are an adversarial reviewer. Your job is to find defects in a build plan BEFORE code is written. You are deliberately looking for problems — not being helpful, not being encouraging. Find what will break.

Review the plan below against these measured failure modes (ranked by frequency in LLM-generated plans):

1. **Requirement Conflicts (43.53%)** — Tasks that contradict each other, or conflict with the existing codebase.
2. **Fabricated APIs (20.41%)** — References to functions/imports/endpoints that DO NOT EXIST. The prompt includes a "Cited File Excerpts" section below with actual source contents — treat those excerpts as ground truth. Do NOT flag an API as fabricated when it appears in an excerpt. Only flag when absent from BOTH the file tree AND excerpts.
3. **Broken Execution Order** — Tasks listed in an order that will fail.
4. **Missing Edge Cases** — Error handling gaps, null states, race conditions, auth failures.
5. **Nonexistent Files** — Plan references files not on disk. Check against BOTH the tree AND excerpts.

## Required Output Schema

Every finding MUST include ALL of these fields:
- finding: <string>
- severity: blocker | warning | note
- location: <file path, function name, or "global">
- claim: <one sentence stating what is wrong>
- evidence: <specific line/code excerpt or "inferred from context">
- confidence: high | medium | low
- fix_type: fixable | structural

fix_type rules:
- **fixable**: Can be resolved by editing the plan text (wrong path, missing step, typo, reordered tasks). A targeted edit resolves it.
- **structural**: Requires redesigning the phase — changing boundaries, swapping tech, altering phase-level order. Plan-text edits will NOT resolve it.

Be strict: if two successive rounds of plan edits would not resolve the issue without reorganizing phases, it is structural. When in doubt, mark as structural.

Output ONLY a JSON array. No prose outside the JSON. Findings missing any field will be REJECTED.
"""


def build_plan_review_prompt(plan_text, project_root):
    """Assemble the full plan-review prompt with tree + excerpts + plan."""
    file_tree = build_project_file_tree(plan_text, project_root)
    excerpts = build_cited_file_excerpts(plan_text, project_root)
    return (
        f"{PLAN_ADVERSARIAL_PROMPT}\n\n"
        f"---\n\n"
        f"## Project File Tree (generated locally):\n{file_tree}\n\n"
        f"---\n\n"
        f"{excerpts}\n\n"
        f"---\n\n"
        f"## Plan to Review:\n{plan_text}\n"
    )


# --- Tracking artifact writer (canonical location for all review modes) ---
#
# Writes to <project_root>/.buildrunner/adversarial-reviews/phase-N-<ts>.json
# with the schema the commit hook (require-adversarial-review.sh) expects.
# For diff/commit modes, writes to .buildrunner/adversarial-reviews/commit-<sha>-<ts>.json.

_ARTIFACT_SCHEMA_VERSION = "br3.adversarial_review.v1"


def _extract_phase_numbers(plan_text):
    """Find '### Phase N:' headers in the plan."""
    return sorted({int(m.group(1)) for m in re.finditer(r"^### Phase (\d+):", plan_text or "", re.MULTILINE)})


def _classify_findings_for_artifact(merged_findings):
    """Split merged findings into consensus_blockers, unresolved, status."""
    consensus_blockers = [x for x in merged_findings
                          if x.get("severity") == "blocker" and x.get("consensus")]
    unresolved = [x for x in merged_findings
                  if x.get("severity") == "blocker" and not x.get("consensus")]
    warnings = [x for x in merged_findings
                if x.get("severity") not in ("blocker",)]
    if consensus_blockers or unresolved:
        status = "blocked"
    elif warnings:
        status = "warning"
    else:
        status = "pass"
    return consensus_blockers, unresolved, status


def write_tracking_artifact(project_root, plan_file, task_id, result, mode="plan"):
    """Write a canonical tracking artifact for the review result.

    In plan mode, writes one phase-N-<ts>.json per phase the plan declares.
    In diff/commit mode, writes a single commit-<sha>-<ts>.json file.
    Returns list of written paths.
    """
    reviews_dir = Path(project_root) / ".buildrunner" / "adversarial-reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    merged_findings = result.get("findings") or []
    consensus_blockers, unresolved, status = _classify_findings_for_artifact(merged_findings)
    verdict = result.get("verdict", "UNKNOWN")
    pass_flag = bool(result.get("pass"))

    import hashlib as _hashlib
    plan_file_abs = str(Path(plan_file).resolve()) if plan_file else None
    plan_path_sha = (
        _hashlib.sha256(plan_file_abs.encode("utf-8")).hexdigest()[:16]
        if plan_file_abs
        else None
    )
    base_record = {
        "schema_version": _ARTIFACT_SCHEMA_VERSION,
        "task_id": task_id or f"review-{timestamp}",
        "artifact_path": str(plan_file) if plan_file else None,
        "plan_file": str(plan_file) if plan_file else None,
        "plan_file_abs": plan_file_abs,
        "plan_path_sha": plan_path_sha,
        "mode": mode,
        "status": status,
        "pass": bool(pass_flag),
        "verdict": verdict,
        "reviewers": result.get("reviewers", []),
        "arbiter": result.get("arbiter", {}),
        "arbiter_invoked": bool(result.get("arbiter_invoked")),
        "arbiter_ruling": result.get("arbiter"),
        "merged_findings": merged_findings,
        "consensus_blockers": consensus_blockers,
        "unresolved_disagreements": unresolved,
        "blockers": result.get("blockers", consensus_blockers + unresolved),
        "arbiter_reasoning": result.get("arbiter_reasoning") or ((result.get("arbiter") or {}).get("reasoning", "")),
        "circuit_state": result.get("circuit_state", "closed"),
        "plan_hash": result.get("plan_hash"),
        "reason": result.get("reason"),
        "fallback_logic": result.get("fallback_logic"),
        "last_opus_payload": result.get("last_opus_payload"),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "review_round": 1,
        "escalated": bool(result.get("escalated")),
    }

    written = []
    if mode == "plan" and plan_file and Path(plan_file).exists():
        plan_text = Path(plan_file).read_text(encoding="utf-8", errors="replace")
        phases = _extract_phase_numbers(plan_text) or [0]
        for phase_number in phases:
            record = dict(base_record)
            record["phase_number"] = phase_number
            out_path = reviews_dir / f"phase-{phase_number}-{timestamp}.json"
            out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            written.append(str(out_path))
    else:
        commit_sha = result.get("commit_sha") or "unknown"
        out_path = reviews_dir / f"commit-{commit_sha}-{timestamp}.json"
        out_path.write_text(json.dumps(base_record, indent=2) + "\n", encoding="utf-8")
        written.append(str(out_path))

    return written


_ACTIVE_REVIEW_LOCKS = set()
_REVIEW_LOCK_CLEANUP_REGISTERED = False


def _review_lock_path(plan_hash):
    return Path(os.path.expanduser("~")) / ".buildrunner" / "locks" / f"review-{plan_hash}.lock"


def _release_review_locks():
    for lock_path in list(_ACTIVE_REVIEW_LOCKS):
        try:
            Path(lock_path).unlink(missing_ok=True)
        except OSError:
            pass
        finally:
            _ACTIVE_REVIEW_LOCKS.discard(lock_path)


def _register_review_lock_cleanup():
    global _REVIEW_LOCK_CLEANUP_REGISTERED
    if _REVIEW_LOCK_CLEANUP_REGISTERED:
        return
    atexit.register(_release_review_locks)
    _REVIEW_LOCK_CLEANUP_REGISTERED = True


def _compute_plan_hash(diff_text, plan_file=None):
    if plan_file and Path(plan_file).exists():
        source = Path(plan_file).read_text(encoding="utf-8", errors="replace")
    else:
        source = diff_text or ""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _enforce_one_review_per_plan(plan_hash):
    if os.environ.get("BR3_REVIEW_ALLOW_RERUN") == "1":
        return
    lock_path = _review_lock_path(plan_hash)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic open-exclusive: O_CREAT|O_EXCL is a single syscall — no TOCTOU window.
    # FileExistsError is raised atomically if another process/thread beat us here.
    try:
        with open(lock_path, "x", encoding="utf-8") as f:
            f.write(
                json.dumps({"pid": os.getpid(), "plan_hash": plan_hash, "created_at": utc_now_iso()}, indent=2) + "\n"
            )
    except FileExistsError:
        sys.stderr.write("ONE-REVIEW-PER-PLAN: rerun not permitted\n")
        raise SystemExit(3)
    _ACTIVE_REVIEW_LOCKS.add(str(lock_path))
    _register_review_lock_cleanup()


def _reviewer_index(findings):
    indexed = {}
    for item in findings:
        if not isinstance(item, dict):
            continue
        key = _normalize_finding(item.get("finding", ""))
        if not key:
            continue
        indexed[key] = {
            "severity": item.get("severity", "note"),
            "fix_type": item.get("fix_type", "fixable"),
        }
    return indexed


def _below_prescreen_obvious_pass(diff_text: str, spec_text: str) -> bool:
    """
    Use Below qwen3:8b to pre-screen for obvious PASS before running the full
    expensive two-reviewer pipeline.

    Returns True only when Below is online AND the model returns verdict=PASS
    with confidence=high.  Any error, offline condition, or uncertain result
    returns False (fall through to full review).

    Skipped entirely when:
      - BR3_BELOW_PRESCREEN=off
      - diff_text exceeds 8 KB (too large for a quick pre-screen)
      - diff contains security-sensitive keywords (RLS, auth, migrate, GRANT, DROP)
    """
    import json as _json
    import urllib.request as _urlreq

    if os.environ.get("BR3_BELOW_PRESCREEN", "on").lower() == "off":
        return False

    # Skip pre-screen on large or security-sensitive diffs
    SECURITY_RE = re.compile(
        r"\b(RLS|GRANT|REVOKE|DROP TABLE|ALTER TABLE|migration|auth\.users|supabase_auth)\b",
        re.IGNORECASE,
    )
    if len(diff_text.encode("utf-8")) > 8 * 1024 or SECURITY_RE.search(diff_text):
        return False

    _below_host = get_below_host()    # single source of truth — core/cluster/cluster_config.py
    _below_model = get_below_model()  # single source of truth — core/cluster/cluster_config.py
    _ollama_port = get_ollama_port()  # single source of truth — core/cluster/cluster_config.py
    schema = {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["PASS", "BLOCK", "UNCERTAIN"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "reason": {"type": "string"},
        },
        "required": ["verdict", "confidence", "reason"],
    }
    prompt = (
        "You are a code-review pre-screener. Given this diff and spec context, "
        "decide if this change is OBVIOUSLY SAFE (verdict=PASS) or needs full review "
        "(verdict=UNCERTAIN or BLOCK).\n\n"
        f"SPEC SUMMARY (first 500 chars):\n{spec_text[:500]}\n\n"
        f"DIFF:\n{diff_text[:3000]}\n\n"
        "Only return PASS+high if you are highly confident no issues exist. "
        "When in doubt, return UNCERTAIN."
    )
    body = _json.dumps({
        "model": _below_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": schema,
        "options": {"num_predict": 128},
    }).encode()

    t0 = time.time()
    try:
        req = _urlreq.Request(
            f"http://{_below_host}:{_ollama_port}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _urlreq.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode()
        parsed = _json.loads(raw)
        content = (parsed.get("message") or {}).get("content", "")
        result = _json.loads(content)
        verdict = result.get("verdict")
        confidence = result.get("confidence")
        latency_ms = int((time.time() - t0) * 1000)
        _log_three_way_decision(
            "below_prescreen",
            f"verdict={verdict} confidence={confidence} latency_ms={latency_ms}",
        )
        # Record metric
        _metrics_file = Path(os.environ.get("HOME", "~")).expanduser() / ".buildrunner" / "schema-classifier-metrics.jsonl"
        try:
            with open(_metrics_file, "a", encoding="utf-8") as _mf:
                _mf.write(_json.dumps({
                    "ts": utc_now_iso(),
                    "model": _below_model,
                    "site": "cross-model-review-prescreen",
                    "verdict": verdict,
                    "confidence": confidence,
                    "latency_ms": latency_ms,
                    "tier": 1,
                }) + "\n")
        except OSError:
            pass
        return verdict == "PASS" and confidence == "high"
    except Exception as exc:  # noqa: BLE001
        logger.debug("Below prescreen unavailable: %s", exc)
        return False


def _reviewers_disagree(reviewers):
    ok_reviewers = [item for item in reviewers if item.get("status") == "ok"]
    if len(ok_reviewers) < 2:
        return True
    left = _reviewer_index(ok_reviewers[0].get("findings", []))
    right = _reviewer_index(ok_reviewers[1].get("findings", []))
    return left != right


def _build_consensus_verdict(reviewers, merged_findings, plan_hash):
    blockers = [item for item in merged_findings if item.get("severity") == "blocker"]
    verdict = "BLOCK" if blockers else "PASS"
    reasoning = (
        "Reviewers agreed on blocking findings."
        if blockers
        else "Reviewers agreed the plan passes one-round review."
    )
    result = Verdict(
        pass_=verdict == "PASS",
        verdict=verdict,
        reviewers=reviewers,
        arbiter={"reasoning": reasoning, "duration_ms": 0, "status": "not-needed"},
        circuit_state="closed",
        plan_hash=plan_hash,
        review_round=1,
        escalated=False,
        blockers=blockers,
        arbiter_reasoning=reasoning,
        reason="consensus-blockers" if blockers else "consensus-pass",
    ).as_dict()
    result["arbiter_invoked"] = False
    result["consensus"] = True
    return result


def run_three_way_review(
    diff_text,
    spec_text,
    commit_sha,
    project_root,
    plan_file=None,
    config=None,
    review_round=1,
    prior_findings=None,
):
    """Run one parallel review round and commit a final verdict."""
    config = config or load_config()
    artifact = plan_file or diff_text[:80]
    plan_hash = _compute_plan_hash(diff_text, plan_file=plan_file)
    _enforce_one_review_per_plan(plan_hash)

    # Below pre-screen: skip full review for obvious PASS (advisory, fail-open).
    if _below_prescreen_obvious_pass(diff_text, spec_text):
        _log_three_way_decision(
            "below_prescreen_pass",
            f"plan_hash={plan_hash} artifact={artifact!r} — skipping full review",
        )
        _emit_adversarial_review_ran(
            mode="below-prescreen",
            verdict="APPROVED",
            findings_count=0,
            commit_sha=commit_sha,
        )
        return {
            "pass": True,
            "verdict": "APPROVED",
            "findings": [],
            "arbiter_invoked": False,
            "consensus": True,
            "below_prescreen": True,
            "review_round": 1,
            "escalated": False,
            "commit_sha": commit_sha,
            "exit_code": 0,
            "arbiter_ruling": None,
        }

    full_prompt = build_review_prompt(diff_text, spec_text, system_prompt=THREE_WAY_REVIEW_PROMPT)
    _log_three_way_decision(
        "review_start",
        f"plan_hash={plan_hash} artifact={artifact!r} commit={commit_sha}",
    )
    reviewer_timeout = int(os.environ.get("BR3_REVIEWER_TIMEOUT", "360"))
    reviewers = asyncio.run(
        _run_parallel_reviewers_one_round(full_prompt, config, timeout_seconds=reviewer_timeout)
    )
    merged = _merge_two_way_findings(
        reviewers[0].get("findings", []),
        reviewers[1].get("findings", []),
    )

    if _reviewers_disagree(reviewers):
        _log_three_way_decision("arbiter_invoked", f"plan_hash={plan_hash} reviewers=2")
        result = arbitrate(
            plan=Path(plan_file).read_text(encoding="utf-8", errors="replace") if plan_file and Path(plan_file).exists() else diff_text,
            reviewer_findings=reviewers,
            config={**config, "plan_hash": plan_hash},
        )
        result["arbiter_invoked"] = True
        result["consensus"] = False
    else:
        result = _build_consensus_verdict(reviewers, merged, plan_hash)

    result["findings"] = merged
    result["arbiter_ruling"] = result.get("arbiter")
    result["review_round"] = 1
    result["escalated"] = False
    result["commit_sha"] = commit_sha
    result["exit_code"] = 0 if result.get("pass") else 1
    _emit_adversarial_review_ran(
        mode="3-way",
        verdict=result.get("verdict", "BLOCK"),
        findings_count=len(merged),
        commit_sha=commit_sha,
    )
    return result


def _resolve_default_spec_file(project_root):
    """Find the authoritative BUILD spec under <project_root>/.buildrunner/builds/."""
    builds_dir = Path(project_root) / ".buildrunner" / "builds"
    if not builds_dir.is_dir():
        return None
    candidates = sorted(builds_dir.glob("BUILD_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else None


def _mode_plan(args, parser):
    """Run canonical plan review: one parallel round plus arbiter if needed."""
    if not args.plan or not args.project_root:
        parser.error("--mode plan requires --plan <plan_file> and --project-root <root>")
    if not Path(args.plan).is_file():
        parser.error(f"plan file not found: {args.plan}")
    if not Path(args.project_root).is_dir():
        parser.error(f"project root not found: {args.project_root}")

    plan_text = Path(args.plan).read_text(encoding="utf-8", errors="replace")
    augmented_prompt = build_plan_review_prompt(plan_text, args.project_root)
    commit_sha = args.commit_sha or f"plan-{int(time.time())}"

    config = load_config()
    result = run_three_way_review(
        diff_text=augmented_prompt,
        spec_text="",
        commit_sha=commit_sha,
        project_root=args.project_root,
        plan_file=args.plan,
        config=config,
    )

    written = write_tracking_artifact(
        project_root=args.project_root,
        plan_file=args.plan,
        task_id=args.task_id,
        result=result,
        mode="plan",
    )
    result["tracking_artifacts"] = written

    print(json.dumps(result, indent=2))
    sys.exit(result.get("exit_code", 0))


def _mode_diff(args, parser):
    """Run canonical diff review: one parallel round plus arbiter if needed."""
    if not args.diff_file or not args.project_root:
        parser.error("--mode diff requires --diff-file and --project-root")
    if not Path(args.diff_file).is_file():
        parser.error(f"diff file not found: {args.diff_file}")

    spec_file = args.spec_file or _resolve_default_spec_file(args.project_root)
    diff_text = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
    spec_text = Path(spec_file).read_text(encoding="utf-8", errors="replace") if spec_file else ""
    commit_sha = args.commit_sha or f"diff-{int(time.time())}"

    config = load_config()
    result = run_three_way_review(
        diff_text=diff_text,
        spec_text=spec_text,
        commit_sha=commit_sha,
        project_root=args.project_root,
        plan_file=None,
        config=config,
    )
    result["commit_sha"] = commit_sha

    written = write_tracking_artifact(
        project_root=args.project_root,
        plan_file=None,
        task_id=args.task_id,
        result=result,
        mode="diff",
    )
    result["tracking_artifacts"] = written

    print(json.dumps(result, indent=2))
    sys.exit(result.get("exit_code", 0))


def _mode_commit(args, parser):
    """Run canonical commit review: derive diff from git HEAD~1..HEAD, 2-way + arbiter."""
    if not args.project_root:
        parser.error("--mode commit requires --project-root")

    project_root = args.project_root
    head_rev = args.commit_sha or "HEAD"
    diff_proc = subprocess.run(
        ["git", "diff", f"{head_rev}~1", head_rev],
        cwd=project_root, capture_output=True, text=True,
    )
    diff_text = diff_proc.stdout or "# No diff available"

    sha_proc = subprocess.run(
        ["git", "rev-parse", "--short", head_rev],
        cwd=project_root, capture_output=True, text=True,
    )
    commit_sha = (sha_proc.stdout or "").strip() or f"commit-{int(time.time())}"

    spec_file = args.spec_file or _resolve_default_spec_file(project_root)
    spec_text = Path(spec_file).read_text(encoding="utf-8", errors="replace") if spec_file else ""

    config = load_config()
    result = run_three_way_review(
        diff_text=diff_text,
        spec_text=spec_text,
        commit_sha=commit_sha,
        project_root=project_root,
        plan_file=None,
        config=config,
    )
    result["commit_sha"] = commit_sha

    written = write_tracking_artifact(
        project_root=project_root,
        plan_file=None,
        task_id=args.task_id,
        result=result,
        mode="commit",
    )
    result["tracking_artifacts"] = written

    print(json.dumps(result, indent=2))
    sys.exit(result.get("exit_code", 0))


def main():
    parser = argparse.ArgumentParser(description="Cross-model code review — canonical entry point")
    parser.add_argument("--check-auth", action="store_true", help="Just verify Codex auth and exit")
    parser.add_argument("--runtime-preflight", choices=["claude", "codex"], help="Run runtime preflight and exit")
    parser.add_argument(
        "--mode",
        choices=["plan", "diff", "commit", "direct", "shadow"],
        default=None,
        help=(
            "Review mode: plan | diff | commit. "
            "Legacy values 'direct'/'shadow' are only valid with --runtime-preflight."
        ),
    )
    parser.add_argument("--json-output", action="store_true", help="Emit machine-readable JSON for runtime preflight")
    parser.add_argument("--no-probe", action="store_true", help="Skip runtime probe command for runtime preflight")
    parser.add_argument("--command", help="Override runtime CLI command for runtime preflight")
    parser.add_argument("--node-name", help="Override node name in runtime preflight output")
    parser.add_argument("--auth-file", help="Override Codex auth file path for runtime preflight")
    parser.add_argument("--diff-file", help="Path to diff text file")
    parser.add_argument("--spec-file", help="Path to build spec file (auto-detected from .buildrunner/builds/ if omitted)")
    parser.add_argument("--commit-sha", help="Commit SHA for caching and artifacts")
    parser.add_argument("--project-root", help="Project root path")
    parser.add_argument("--three-way", action="store_true", help="[legacy] Alias for --mode plan when --plan is set, else --mode diff")
    parser.add_argument("--plan", help="Path to plan file (plan mode input)")
    parser.add_argument("--task-id", help="Task identifier recorded in tracking artifact")
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
        preflight_mode = args.mode if args.mode in ("direct", "shadow") else "direct"
        preflight = build_runtime_preflight(
            runtime=args.runtime_preflight,
            mode=preflight_mode,
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

    # Resolve effective mode: explicit --mode wins; else --three-way + --plan → plan; --three-way → diff
    effective_mode = args.mode if args.mode in ("plan", "diff", "commit") else None
    if effective_mode is None and args.three_way:
        effective_mode = "plan" if args.plan else "diff"

    if effective_mode == "plan":
        _mode_plan(args, parser)
    if effective_mode == "diff":
        _mode_diff(args, parser)
    if effective_mode == "commit":
        _mode_commit(args, parser)

    parser.error("one of --mode {plan,diff,commit} or --three-way is required")


if __name__ == "__main__":
    main()
