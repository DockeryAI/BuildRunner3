# Phase 7 Verification

## Deliverable Checklist

- [x] A. RuntimeRegistry.execute(task) — implemented in core/runtime/runtime_registry.py
  - routes by authoritative_runtime, falls back to claude
  - cache_control forwarded verbatim
  - calls cost_ledger when BR3_GATEWAY=on (best-effort, never raises)

- [x] B. core/cluster/cost_ledger.py — 11-field JSONL, weekly rotation
  - LEDGER_FIELDS = (ts, runtime, model, input_tokens, cache_read_tokens, cache_write_tokens, output_tokens, cost_usd, latency_ms, skill, phase)
  - LEDGER_FIELD_COUNT = 11
  - Writes to /srv/jimmy/ledger/ (fallback to ~/.buildrunner/ledger/)
  - /srv/jimmy/ledger/ created via SSH

- [x] C. Pre-commit hook — .buildrunner/hooks/pre-commit-cluster-guard
  - Rejects direct ollama subprocess, requests.post("http://10.0.1.*"), curl to 10.0.1.*
  - Integrated into .buildrunner/hooks/pre-commit (canonical)
  - Appended to live .git/hooks/pre-commit

- [x] D. api/routes/cluster_metrics.py — /cluster/cost and /cluster/cache
  - GET /cluster/cost returns last_24h + last_7d windows
  - GET /cluster/cache returns hit-rate per runtime

- [x] E. Feature flag BR3_GATEWAY — default OFF, _gateway_enabled() in runtime_registry.py

- [x] F. core/cluster/AGENTS.md.append-phase7.txt — 597 bytes (<600)
  - contains "11 fields", gateway routing rule, cache_control, cost_ledger

## Test Results
- tests/cluster/test_cost_ledger.py: 8 passed
- tests/cluster/test_runtime_registry_shim.py: 16 passed
- tests/runtime/ (existing): 66 passed
