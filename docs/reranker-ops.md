# Reranker Operations Guide

## Overview

The bge-reranker-v2-m3 cross-encoder runs on Jimmy (10.0.1.106) as part of the
BR3 two-stage retrieval pipeline. Stage 1 is vector search (LanceDB); Stage 2 is
cross-encoder reranking via this model.

## Feature Gate

The reranker is controlled by the `BR3_AUTO_CONTEXT` environment variable.

**Correct location:** `scripts/service-env.sh` (sourced by the Jimmy retrieval
service at startup). **Never** set this in `.claude/settings.json` — the flag
is read from process environment at import time.

```bash
# Enable
export BR3_AUTO_CONTEXT=on

# Disable (passthrough — no model loaded, <1ms overhead)
export BR3_AUTO_CONTEXT=off
```

## Activation

```bash
# Source before starting the retrieval service
source scripts/service-env.sh
uvicorn core.cluster.node_semantic:app --host 0.0.0.0 --port 8100
```

## Tuning

### top_k (the only tuning knob)

The reranker has **no similarity threshold**. The sole tuning parameter is `top_k`:
the number of results returned after cross-encoder scoring.

| top_k | Use case                            |
| ----- | ----------------------------------- |
| 3     | Tight context budgets (autopilot)   |
| 5     | Default — balanced latency + recall |
| 10    | Research-heavy tasks                |

Set via environment variable before sourcing `service-env.sh`:

```bash
export RERANKER_TOP_K=5   # default
```

Or pass `top_k` in the `/retrieve` request body.

### Context-bundle callers

The reranker fires for context-bundle calls **only when a non-empty query is
supplied**. Callers that omit `query` receive mtime-ranked results (no reranking).

```python
# context_router.py — correct
bundle = router.get_bundle(model="claude", token_budget=48000, query="embed batch latency")

# NO query → falls back to mtime ordering
bundle = router.get_bundle(model="claude", token_budget=48000)
```

Confirm your call site supplies a query. Check `context_router.py:get_bundle()`.

## Metrics

Metrics are appended to `~/.buildrunner/reranker-metrics.jsonl` after every
rerank call. Fields:

| Field      | Description                                |
| ---------- | ------------------------------------------ |
| ts         | UTC ISO timestamp                          |
| event      | `rerank` or `rerank_error`                 |
| top_k      | Configured top_k for this call             |
| candidates | Stage 1 candidate count passed to reranker |
| returned   | Actual results returned (≤ top_k)          |
| latency_ms | Wall-clock ms for model.predict()          |
| model      | Model name (BAAI/bge-reranker-v2-m3)       |

### Live monitoring

```bash
tail -f ~/.buildrunner/reranker-metrics.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    r = json.loads(line)
    print(f\"{r['ts']} {r['event']:15s} top_k={r.get('top_k','?')} candidates={r.get('candidates','?')} latency={r.get('latency_ms','?')}ms\")
"
```

### Aggregated stats

```bash
# Mean latency and invocation count
python3 -c "
import json, statistics
from pathlib import Path
lines = [json.loads(l) for l in Path('~/.buildrunner/reranker-metrics.jsonl').expanduser().read_text().splitlines() if l]
reranks = [l for l in lines if l.get('event') == 'rerank']
errors = [l for l in lines if l.get('event') == 'rerank_error']
latencies = [l['latency_ms'] for l in reranks]
print(f'Invocations: {len(reranks)}  Errors: {len(errors)}')
if latencies:
    print(f'Latency — mean: {statistics.mean(latencies):.1f}ms  p95: {sorted(latencies)[int(len(latencies)*0.95)]:.1f}ms')
"
```

## Smoke Test (recorded /retrieve fixture)

Run against a recorded fixture to verify the reranker fires:

```bash
# Start service with flag on
source scripts/service-env.sh && uvicorn core.cluster.node_semantic:app --port 8100 &

# POST the fixture
curl -s -X POST http://localhost:8100/retrieve \
  -H 'Content-Type: application/json' \
  -d '{"query": "embedding latency below offload", "top_k": 5}' | python3 -m json.tool

# Verify flag_active=true in response and rerank event in metrics
tail -1 ~/.buildrunner/reranker-metrics.jsonl | python3 -m json.tool
```

## Health Check

```bash
curl http://10.0.1.106:8100/rerank/health
# {"status": "ok", "model": "BAAI/bge-reranker-v2-m3", "device": "cpu", "score_sample": 0.94}
```

## Troubleshooting

| Symptom                           | Likely cause                            | Fix                                                                    |
| --------------------------------- | --------------------------------------- | ---------------------------------------------------------------------- |
| `"status": "disabled"`            | `BR3_AUTO_CONTEXT` not set              | Source `service-env.sh` before starting service                        |
| `"status": "error"`               | sentence-transformers not installed     | `pip install sentence-transformers` in service venv                    |
| High latency (>500ms)             | CPU-only model on large candidate pools | Reduce `candidates_per_source` in `retrieve.py` or reduce Stage 1 pool |
| `flag_active: false` in /retrieve | Module loaded before env set            | Restart service after sourcing `service-env.sh`                        |
