#!/usr/bin/env python3
"""Phase 2 smoke test: score N synthetic deal items via Below's qwen3:8b.

Emits a JSON array where each element has a numeric `score` in [0, 100].
Used by cluster-max Phase 2 verify:
  python scripts/test_intel_scoring.py --count 5 --node below | \
      jq 'all(.score >= 0 and .score <= 100)'
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

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


SAMPLE_DEALS = [
    ({"name": "RTX 3090 FE", "price": 650, "condition": "used - excellent",
      "seller": "techdealer42", "seller_rating": 99.1},
     {"target_price": 700, "category": "gpu"}),
    ({"name": "Mac Studio M2 Ultra 64GB", "price": 3200, "condition": "new",
      "seller": "apple-authorized", "seller_rating": 100.0},
     {"target_price": 3500, "category": "mac"}),
    ({"name": "Samsung 990 Pro 2TB NVMe", "price": 220, "condition": "new",
      "seller": "bulkpartsinc", "seller_rating": 97.3},
     {"target_price": 200, "category": "storage"}),
    ({"name": "NVLink Bridge (3-slot, 4-way)", "price": 45, "condition": "used",
      "seller": "gpuparts", "seller_rating": 92.5},
     {"target_price": 60, "category": "gpu-accessory"}),
    ({"name": "UPS 1500VA Line-Interactive", "price": 180, "condition": "refurbished",
      "seller": "office_deals", "seller_rating": 88.0},
     {"target_price": 200, "category": "power"}),
]


async def score_one(item: dict, hunt: dict) -> dict:
    from core.cluster import intel_scoring

    prompt = intel_scoring._build_deal_prompt(item, hunt)
    raw = await intel_scoring._call_below_chat(prompt, system="Return only JSON.")
    parsed = intel_scoring._parse_deal_score(raw) if raw else None
    if parsed is None:
        return {
            "item": item["name"],
            "score": -1,
            "verdict": "parse_error",
            "assessment": (raw or "")[:120],
        }
    return {"item": item["name"], **parsed}


async def main_async(count: int, node: str) -> int:
    host = resolve_host(node)
    os.environ["BELOW_OLLAMA_URL"] = f"http://{host}:11434"
    os.environ.setdefault("BELOW_MODEL", "qwen3:8b")
    os.environ["BELOW_REQUEST_TIMEOUT"] = "90"

    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    results = []
    for item, hunt in SAMPLE_DEALS[:count]:
        results.append(await score_one(item, hunt))
    print(json.dumps(results, indent=2))
    return 0 if all(0 <= r["score"] <= 100 for r in results) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--node", default="below")
    args = ap.parse_args()
    return asyncio.run(main_async(args.count, args.node))


if __name__ == "__main__":
    sys.exit(main())
