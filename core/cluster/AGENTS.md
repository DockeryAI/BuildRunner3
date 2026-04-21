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

All four flags are named verbatim:

- `BR3_RUNTIME_OLLAMA`
- `BR3_CACHE_BREAKPOINTS`
- `BR3_ADVERSARIAL_3WAY`
- `BR3_AUTO_CONTEXT`

NEVER default any flag to ON before Phase 13 cutover validation completes.

## Node registry source of truth

- `~/.buildrunner/cluster.json` is the ONLY source of truth for node IPs, ports, and roles.
- NEVER hardcode a node IP in Python. Import from `load_cluster_config()` helper.
- Heartbeat path for autopilot phases: `.buildrunner/locks/phase-<N>/heartbeat` (ISO-8601 UTC, updated every ≤60 s while running).

## Per-file validation

- `pytest tests/cluster/test_<file>.py -x`
- `ruff check core/cluster/<file>.py`
- Shell helpers: `shellcheck core/cluster/scripts/<file>.sh`

## Jimmy (10.0.1.106) dispatch rules (Phase 3)

- Muddy → Jimmy: rsync (not tar+scp). NEVER tar+scp to Jimmy.
- systemd units: always named `br3-<role>.service` or `br3-<role>.timer`.
- Jimmy port allocation: 8100 semantic, 8200 staging, 4400 dashboard, 4500 `/context/{model}` API.

## 7-node priority order (Phase 4)

otis > below > jimmy > lockwood > lomax > muddy > walter

Overflow workers (lockwood, lomax): retained in worker-pool and heartbeat contexts.
Only PRIMARY-role refs (semantic-search, intel, staging) for lockwood rewritten to jimmy (10.0.1.106).
`is_overflow_worker()` in `_dispatch-core.sh` is the single classifier for IP substitution decisions.

## Phase 5 Skill Routing (BR3_RUNTIME_OLLAMA=on)

| Skill                             | Route           | Model        |
| --------------------------------- | --------------- | ------------ |
| /begin /autopilot backend plan    | below-route     | llama3.3:70b |
| /review Pass 1 pre-summary        | below-route     | llama3.3:70b |
| /guard governance scan            | below-route     | llama3.3:70b |
| /diag /root /dbg /sdb log summary | below-route     | qwen3:8b     |
| All final output                  | Claude Opus 4.7 | --           |

- `BR3_RUNTIME_OLLAMA=on` required; OFF until Phase 13.
- `below-route.sh` exits 2 offline; skills fall back silently.
- Below never drafts diagnosis, code, or architecture.
- Each call appends `routing:` to `decisions.log`.

## Three-Way Review + Arbiter (Phase 9)

Three-way: Sonnet 4.6 + Codex parallel → rebuttal → consensus done | split → Opus arbiter (effort=xhigh, replaces deprecated budget_tokens 32000 ultrathink). Arbiter post-rebuttal only. Arbiter ruling TERMINAL. No leakage of arbiter ruling to reviewers.

Review Convergence Policy (rules 1–8):

1. Round cap = `BR3_MAX_REVIEW_ROUNDS` (default 1).
2. `fix_type` required (`fixable|structural`); reject output lacking it.
3. Structural blocker → escalate round 1.
4. Persistent blocker (same text 2+ rounds) → escalate.
5. Rebuttal mandatory before arbiter.
6. Escalation: `CONTINUE/OVERRIDE/SIMPLIFY` to stderr, exit 2.
7. Ruling logged to `decisions.log`.
8. User escalation on arbiter contest.

Flag: `BR3_ADVERSARIAL_3WAY` (OFF until Phase 13).

## Auto-Context Hook (Phase 10)

- Flag: `BR3_AUTO_CONTEXT=on` (OFF until Phase 13). Off = no change.
- Sources: research, lockwood-code, lockwood-memory, decisions.
- Budget: 4K via `count-tokens.sh`. Exit 2 = fail-closed.
- Skip conditions: <40 chars, slash commands, single-word, y/n affirmations.
- Ledger: `~/.buildrunner/auto-context-ledger.jsonl` — `{ts, event, prompt_excerpt, sources_injected, tokens_used, top_score}`.
- `/retrieve`: `POST http://10.0.1.106:8100/retrieve {query, top_k}`.
- Auto-context hook injects context before prompt.

## Phase 12: Multi-Model Context Parity

- `context_router.py` is the ONLY path to model bundles. Skills MUST NOT bypass it.
- Budgets via `count-tokens.sh` (NOT bytes): claude=32K, codex=48K, ollama=16K.
- Two-layer `[private]` filter: `filter-private-decisions.sh` strips before rsync; `context_bundle.py` re-filters at extraction.
- `/context/{model}` on Jimmy :4500. Gate: `BR3_AUTO_CONTEXT=on` (default OFF until Phase 13).
- `~/br3-context/` chmod 444. NEVER write to it. (macOS SIP blocks `/srv` writes; home-dir mirror used instead.)
- `count-tokens.sh` exit 2 = fail-closed. No byte fallback.
