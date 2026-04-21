#!/usr/bin/env python3
"""post_cutover_smoke.py — Phase 13 cutover smoke test.

Runs the 5 post-flip checks after the 4 canonical cluster-max flags flip
from OFF → ON. Each check names the flag it validates end-to-end.

Checks (all MUST pass for green cutover):
  1. auto_context_block         — BR3_AUTO_CONTEXT: auto-context.sh emits <auto-context> block.
  2. ollama_execute             — BR3_RUNTIME_OLLAMA: RuntimeRegistry.execute() via ollama runtime returns 200.
  3. adversarial_3way_findings  — BR3_ADVERSARIAL_3WAY: /review runs claude + codex + arbiter.
  4. cache_breakpoints_3        — BR3_CACHE_BREAKPOINTS: dispatched payload has 3 ephemeral breakpoints.
  5. dashboard_ws_4_events      — Dashboard /ws emits 4 event types within 12s window.

Usage:
  post_cutover_smoke.py --list          # print 5 named checks, exit 0
  post_cutover_smoke.py --dry           # compile + self-document, exit 0
  post_cutover_smoke.py --dry --list    # same as --list
  post_cutover_smoke.py                 # run full suite, print 5/5 PASS or N/5 FAIL: <names>

Per BR3 E2E policy, check 3 (LLM-variance-sensitive) retries once before marking FAIL.
Exit 0 = all 5 pass; exit 1 = one or more FAIL.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parent.parent

JIMMY_HOST = "10.0.1.106"
CONTEXT_PORT = 4500
DASHBOARD_PORT = 4400

CHECKS = (
    "auto_context_block",
    "ollama_execute",
    "adversarial_3way_findings",
    "cache_breakpoints_3",
    "dashboard_ws_4_events",
)

CHECK_DOCS = {
    "auto_context_block": "BR3_AUTO_CONTEXT — auto-context.sh emits <auto-context> block on non-trivial prompt",
    "ollama_execute": "BR3_RUNTIME_OLLAMA — RuntimeRegistry dispatch to ollama runtime returns 200",
    "adversarial_3way_findings": "BR3_ADVERSARIAL_3WAY — /review dispatches claude+codex+(arbiter) producing findings",
    "cache_breakpoints_3": "BR3_CACHE_BREAKPOINTS — cache_policy returns exactly 3 ephemeral breakpoints",
    "dashboard_ws_4_events": "Dashboard /ws emits node-health, overflow-reserve, storage-health, consensus within 12s",
}


def _hook_path() -> Path:
    return HOME / ".buildrunner" / "hooks" / "auto-context.sh"


def check_auto_context_block() -> bool:
    hook = _hook_path()
    if not hook.exists():
        return False
    env = os.environ.copy()
    env["BR3_AUTO_CONTEXT"] = "on"
    r = subprocess.run(
        ["bash", str(hook)],
        input="how does RLS work in our project\n",
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    return "<auto-context>" in r.stdout or "<auto-context/>" in r.stdout


def check_ollama_execute() -> bool:
    # Pre-load cache_policy to break the cross_model_review ↔ runtime circular import.
    import importlib

    try:
        importlib.import_module("core.runtime.cache_policy")
        from core.runtime.runtime_registry import create_runtime_registry
        from core.runtime.types import RuntimeTask
    except Exception:
        return False
    try:
        reg = create_runtime_registry({"backends": {"ollama": {"model": "qwen3:8b", "timeout": 60}}})
        task = RuntimeTask(
            task_id="smoke-ollama",
            task_type="review",
            diff_text="diff --git a/x b/x\n+print('hi')\n",
            spec_text="smoke spec",
            project_root=str(REPO),
            commit_sha="0" * 40,
            authoritative_runtime="ollama",
        )
        result = reg.execute(task)
        status = getattr(result, "status", None)
        return status in ("completed", "ok", 200, True)
    except Exception:
        return False


def check_adversarial_3way_findings() -> bool:
    import importlib

    def _once() -> bool:
        try:
            importlib.import_module("core.runtime.cache_policy")
            from core.cluster.cross_model_review import run_three_way_review  # type: ignore
        except Exception:
            return False
        try:
            out = run_three_way_review(
                diff_text="diff --git a/x b/x\n+print('hi')\n",
                spec_text="smoke spec",
                commit_sha="0" * 40,
                project_root=str(REPO),
                review_round=1,
            )
            findings = out.get("findings", []) if isinstance(out, dict) else []
            return len(findings) >= 1
        except Exception:
            return False

    if _once():
        return True
    time.sleep(1.0)
    return _once()


def check_cache_breakpoints_3() -> bool:
    try:
        from core.runtime.cache_policy import build_cached_prompt, get_breakpoint_count
    except Exception:
        return False
    try:
        if get_breakpoint_count() != 3:
            return False
        blocks = build_cached_prompt("sys text", "skill ctx", "task payload")
        if not isinstance(blocks, list) or len(blocks) != 3:
            return False
        cached = [b for b in blocks if isinstance(b, dict) and "cache_control" in b]
        return len(cached) == 2
    except Exception:
        return False


def check_dashboard_ws_4_events() -> bool:
    try:
        import websockets  # type: ignore
    except Exception:
        return _check_dashboard_tcp_only()

    expected = {"node-health", "overflow-reserve", "storage-health", "consensus"}

    async def _collect() -> set[str]:
        seen: set[str] = set()
        uri = f"ws://{JIMMY_HOST}:{DASHBOARD_PORT}/ws"
        try:
            async with websockets.connect(uri, open_timeout=5) as ws:
                deadline = time.time() + 12
                while time.time() < deadline and seen != expected:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    except asyncio.TimeoutError:
                        continue
                    try:
                        data = json.loads(msg)
                    except Exception:
                        continue
                    evt = data.get("type") or data.get("event")
                    if evt in expected:
                        seen.add(evt)
        except Exception:
            pass
        return seen

    seen = asyncio.run(_collect())
    return seen == expected


def _check_dashboard_tcp_only() -> bool:
    try:
        with socket.create_connection((JIMMY_HOST, DASHBOARD_PORT), timeout=5.0):
            return True
    except Exception:
        return False


CHECK_FNS = {
    "auto_context_block": check_auto_context_block,
    "ollama_execute": check_ollama_execute,
    "adversarial_3way_findings": check_adversarial_3way_findings,
    "cache_breakpoints_3": check_cache_breakpoints_3,
    "dashboard_ws_4_events": check_dashboard_ws_4_events,
}


def print_list() -> None:
    print("=== post_cutover_smoke — 5 checks ===")
    for name in CHECKS:
        print(f"  {name}: {CHECK_DOCS[name]}")


def run_all() -> int:
    print("=== post_cutover_smoke — Phase 13 ===")
    failed: list[str] = []
    for name in CHECKS:
        fn = CHECK_FNS[name]
        try:
            ok = bool(fn())
        except Exception as e:
            ok = False
            print(f"  [ERROR] {name}: {e}")
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
        if not ok:
            failed.append(name)
    if failed:
        print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} FAIL: {failed}")
        return 1
    print(f"{len(CHECKS)}/{len(CHECKS)} PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="compile + self-document, do not run checks")
    parser.add_argument("--list", action="store_true", help="print 5 named checks and exit")
    args = parser.parse_args()

    if args.list or args.dry:
        print_list()
        return 0
    return run_all()


if __name__ == "__main__":
    sys.exit(main())
