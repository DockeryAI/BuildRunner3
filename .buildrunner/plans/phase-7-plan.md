# Phase 7 Implementation Plan

## SUPERSEDED: LiteLLM → RuntimeRegistry shim

### Tasks (6)
1. RuntimeRegistry.execute(task) shim — core/runtime/runtime_registry.py
2. CostLedger 11-field JSONL — core/cluster/cost_ledger.py
3. Pre-commit cluster-guard hook — .buildrunner/hooks/pre-commit-cluster-guard
4. /cluster/cost + /cluster/cache endpoints — api/routes/cluster_metrics.py
5. BR3_GATEWAY feature flag (default OFF) — in runtime_registry.py
6. AGENTS.md staged snippet — core/cluster/AGENTS.md.append-phase7.txt

### Decisions
- asyncio.run() instead of get_event_loop() for Python 3.14 compatibility
- CostLedger fallback to ~/.buildrunner/ledger/ when /srv/jimmy not mounted
- Hook appended to live .git/hooks/pre-commit via Python (no Edit permission on .git/)
- gateway_client.py DROPPED per Phase 8 note (spec explicitly says skip it)
