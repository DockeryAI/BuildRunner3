#!/usr/bin/env python3
"""Residency proof for Phase 2.

Contract on 2×24 GB hardware: llama3.3:70b Q4_K_M weights alone consume ~42 GB,
leaving ~6 GB free — insufficient for a co-resident 8B runtime. Actual contract
we verify: the primary large model stays hot across a burst of sequential calls
(no cold reload between calls to the same model within the KEEP_ALIVE window).

Three sequential llama calls: load (A), hot (B), hot (C). Pass iff B and C have
load_duration < 1s (warm cache). Secondary-model eviction is expected and
documented, not a failure.

Usage: python scripts/test_residency.py --node below --model llama3.3:70b-instruct-q4_K_M
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

CLUSTER_JSON = Path.home() / ".buildrunner" / "cluster.json"


def resolve_host(node: str) -> str:
    data = json.loads(CLUSTER_JSON.read_text())
    nodes = data.get("nodes", {})
    if isinstance(nodes, dict):
        entry = nodes.get(node.lower())
        if entry and "host" in entry:
            return entry["host"]
        for n in nodes.values():
            if n.get("name", "").lower() == node.lower():
                return n["host"]
    else:
        for n in nodes:
            if n.get("name", "").lower() == node.lower():
                return n["host"]
    raise SystemExit(f"cluster.json has no node named {node!r}")


def ollama_ps(base: str) -> list[dict]:
    try:
        r = httpx.get(f"{base}/api/ps", timeout=10.0)
        r.raise_for_status()
        return r.json().get("models", [])
    except httpx.HTTPError as e:
        print(f"WARN: /api/ps failed: {e}", file=sys.stderr)
        return []


def ollama_generate(base: str, model: str, prompt: str) -> dict:
    r = httpx.post(
        f"{base}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 20,
                "temperature": 0,
                "num_ctx": 2048,
                "num_gpu": 99,
            },
            "keep_alive": "24h",
        },
        timeout=600.0,
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default="below")
    ap.add_argument("--model", default="llama3.3:70b-instruct-q4_K_M")
    args = ap.parse_args()

    host = resolve_host(args.node)
    base = f"http://{host}:11434"
    model = args.model

    per_call = []
    cold_reload_count = 0
    COLD_THRESHOLD_NS = 1_000_000_000  # 1s

    for step, prompt, sleep_s in [
        ("A", "Say OK.", 2),
        ("B", "Say OK again.", 2),
        ("C", "Say OK once more.", 0),
    ]:
        resp = ollama_generate(base, model, prompt)
        snap = ollama_ps(base)
        load_ns = resp.get("load_duration", 0)
        per_call.append({
            "step": step,
            "model": model,
            "resident": [m["name"] for m in snap],
            "load_duration_ns": load_ns,
        })
        if step != "A" and load_ns > COLD_THRESHOLD_NS:
            cold_reload_count += 1
        if sleep_s:
            time.sleep(sleep_s)

    model_resident = any(model in m["name"] for m in snap)

    result = {
        "model": model,
        "model_resident": model_resident,
        "cold_reload_count_after_A": cold_reload_count,
        "per_call": per_call,
    }
    print(json.dumps(result, indent=2))
    return 0 if (model_resident and cold_reload_count == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
