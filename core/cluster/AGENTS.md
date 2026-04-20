# core/cluster — AGENTS.md

## Quality firewall

- Below (Windows + dual RTX 3090) NEVER drafts final diagnoses, final code, frontend/UX, or architecture decisions.
- Below is pre-summary and first-pass only: summarize diffs >12KB, draft test scaffolding, emit initial inference for later Claude/Codex refinement.
- NEVER route final output from Below directly to the user or to git.

## Dispatcher fallback contract

- On any node-health check failure, the dispatcher reroutes silently to the next healthy node (order: otis, lomax, below).
- NEVER surface node-offline errors to the user.
- IMPORTANT: Walter is reserved for testing unless explicitly assigned — do not auto-dispatch build work to Walter.
- Muddy → Jimmy/Lomax/Otis: rsync. Muddy → Below (Windows/WSL): tar+scp (rsync unreliable over Windows OpenSSH).

## Below dual-GPU rules (Phase 2 invariants)

- NVLink NV# health = `nvidia-smi nvlink --status` reports ≥4 active Link rows at non-zero GB/s. Otherwise dispatch falls back to single-GPU path.
- `OLLAMA_KEEP_ALIVE=24h` — primary 70B (llama3.3 or deepseek-r1) stays hot across sequential same-model calls (warm load <200 ms). Co-residency with 8B is not feasible on 2×24 GB; qwen3:8b is fast-cold-load (~8 s).
- Dual-GPU 70B requires `num_ctx≤2048` and `num_gpu=99` (all layers offloaded). Default `num_ctx=4096` OOMs KV cache across 48 GB total VRAM.

## Summarize-before-escalate

- Any diff >12KB dispatched to Below/Jimmy MUST pass through the summarizer first. Raw large diffs never go to remote nodes.
- Summarizer output is ≤2KB, structured as `{files_changed, net_lines, risk_surfaces, summary}`.

## Feature flags (default OFF until Phase 13)

All five flags are named verbatim:

- `BR3_RUNTIME_OLLAMA`
- `BR3_GATEWAY_LITELLM`
- `BR3_CACHE_BREAKPOINTS`
- `BR3_ADVERSARIAL_3WAY`
- `BR3_AUTO_CONTEXT`

NEVER default any flag to ON before Phase 13 shadow validation completes.

## Node registry source of truth

- `~/.buildrunner/cluster.json` is the ONLY source of truth for node IPs, ports, and roles.
- NEVER hardcode a node IP in Python. Import from `load_cluster_config()` helper.
- Heartbeat path for autopilot phases: `.buildrunner/locks/phase-<N>/heartbeat` (ISO-8601 UTC, updated every ≤60 s while running).

## Per-file validation

- `pytest tests/cluster/test_<file>.py -x`
- `ruff check core/cluster/<file>.py`
- Shell helpers: `shellcheck core/cluster/scripts/<file>.sh`
