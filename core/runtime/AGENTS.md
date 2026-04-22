# core/runtime — AGENTS.md

## Contract

- `RuntimeTask` and `RuntimeResult` shapes are defined in `types.py`. NEVER add fields without updating both sides and the schema in `result_schema.py`.
- `BaseRuntime.execute(task) -> RuntimeResult` is the single entry point for every runtime. Subclasses override this and NOTHING else in `base.py`.
- IMPORTANT: On Ollama 503 or timeout, `OllamaRuntime.execute` MUST fall back to `ClaudeRuntime` silently. No user-visible error. Log the fallback; do not raise.

## SUPPORTED_RUNTIMES ordering

Declared in `runtime_registry.py`. Ordering is semantic (selection priority):

1. `claude` — always available, default floor.
2. `codex` — workflow-gated commands only (see `command_capabilities.json`).
3. `ollama` — local inference via Jimmy/Below when `BR3_LOCAL_ROUTING=1`.

NEVER reorder this list without a cross-model review entry.

## Capability levels (command_capabilities.json)

Exactly four levels. Commands carry exactly one:

- `claude_only` — Claude executes; never route elsewhere.
- `codex_workflow_only` — Codex executes only inside a workflow (begin/spec/autopilot).
- `codex_ready` — Codex may execute on explicit invocation.
- `local_ready` — Ollama (Below or Jimmy) may execute when runtime is enabled.

NEVER add a fifth level. NEVER promote a command without a matching decisions.log entry.

## Prompt cache (3-breakpoint contract)

Every Claude request builds a cacheable prompt with exactly 3 breakpoints:

1. System + tools (cache_control: ephemeral)
2. Stable context (CLAUDE.md + AGENTS.md scope) (cache_control: ephemeral)
3. Rolling conversation tail (no cache_control)

IMPORTANT: NEVER inline changing timestamps, random IDs, or user input into breakpoints 1–2. Cache hit rate target ≥70%.

## Per-file validation

- `pytest tests/runtime/test_<file>.py -x`
- `ruff check core/runtime/<file>.py`
- NEVER run `pytest` with no path.

## Postflight / Preflight

- `preflight.py` validates task shape before dispatch. On invalid shape: raise `InvalidTaskError`.
- `postflight.py` validates result shape before returning to caller. On invalid shape: log and return `RuntimeResult(status="error", error="postflight_schema_mismatch")` — NEVER raise upward.

## OllamaRuntime (Phase 6)

- `OllamaRuntime` host from cluster.json role=inference (default 10.0.1.105:11434).
- Model: `llama3.3:70b`. Health: `cluster-check.sh inference`.
- Silent-fallback: 503/timeout/fail → `ClaudeRuntime`, no user error, WARNING log only.
- `local_ready`: plan-draft, structural-review, governance-lint, intel-scoring, summarize. Enabled by `BR3_LOCAL_ROUTING=1`.
- `BR3_RUNTIME_OLLAMA=1` remains as a deprecated one-release alias shim. Do not use it in new code or docs.

## Cache + Summarizer Contract (Phase 8)

- **3-breakpoint rule**: every Claude request uses `cache_policy.build_cached_prompt(system, skill_context, task_payload)`. No inline `cache_control` dicts anywhere else.
- **12KB threshold**: if diff exceeds 12KB, call `summarizer.summarize_diff(diff)` before placing into breakpoint 3. Below offline → original returned, `truncated=True`.
- **Summarizer is pre-summary only**: `summarizer.py` NEVER produces final-form code, diagnoses, or authoritative reviews. All summarizer output is tagged `draft=True` by RuntimeRegistry.
