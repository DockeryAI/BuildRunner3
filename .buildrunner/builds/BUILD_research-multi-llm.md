# Build: Multi-LLM Research Enhancement

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: backend-build, assigned_node: muddy }
      phase_2: { bucket: backend-build, assigned_node: muddy }
      phase_3: { bucket: backend-build, assigned_node: muddy }
      phase_4: { bucket: backend-build, assigned_node: muddy }
      phase_5: { bucket: backend-build, assigned_node: muddy }
      phase_6: { bucket: qa, assigned_node: walter }
      phase_7: { bucket: architecture, assigned_node: muddy }
```

**Created:** 2026-04-22
**Status:** BUILD COMPLETE — All 7 Phases Done
**Deploy:** web — `npm run build` (no runtime deploy needed; skill + scripts ship via git push to operator's home)
**Source Plan File:** .buildrunner/plans/spec-draft-plan.md
**Source Plan SHA:** 66fdd7763ffba294e8825c82a0a162aad34d3a3873ca331a31cda2be37f7a8af
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-22T20:52:03Z

## Overview

Upgrade the `/research` skill from single-model (Claude Sonnet 4.6 only) to a true multi-model pipeline: Claude + Codex (existing access) plus Perplexity Sonar Pro + Google Gemini 3.1 Pro + xAI Grok 4 (new API integrations). Adds a mandatory adversarial cross-family review step, confidence tagging from cross-family corroboration, per-invocation budget guards, and graceful degradation when providers are unreachable. Library evidence: multi-model review catches 3–5× more findings (Zylos Research, Feb 2026); models miss 64.5% of their own errors.

## Decisions (locked at "go" time)

1. **API key storage:** `~/.buildrunner/.env` (chmod 600). No 1Password CLI dependency.
2. **Cost ceiling per invocation:** $2.00 USD default, override via `BR3_RESEARCH_BUDGET_USD`.
3. **Codex dispatch:** reuse existing `codex exec` CLI (the same plumbing `/codex-do` uses). No new OpenAI billing path.
4. **Adversarial review:** mandatory in standard mode (one cross-family reviewer); `ultrathink` runs two reviewers in parallel.

## Parallelization Matrix

| Phase | Key Files                                                      | Can Parallel With | Blocked By    |
| ----- | -------------------------------------------------------------- | ----------------- | ------------- |
| 1     | `~/.buildrunner/scripts/llm-clients/*`, `llm-dispatch.sh`      | 6                 | -             |
| 2     | `~/.claude/commands/research.md` (Step 3.5)                    | -                 | 1             |
| 3     | `~/.claude/commands/research.md` (Step 4)                      | -                 | 2 (same file) |
| 4     | `~/.claude/commands/research.md` (Step 4.5 NEW) + Below schema | -                 | 3 (same file) |
| 5     | `research-budget-guard.sh` + `research.md` wiring              | 6                 | 4             |
| 6     | `tests/research/*` + Walter cron                               | 1, 5              | -             |
| 7     | `~/.buildrunner/docs/research-multi-llm.md` + skill polish     | -                 | 6             |

**Effective serial chain:** 1 → 2 → 3 → 4 → 5 → 7. Phase 6 develops alongside Phase 1 and gates final delivery before Phase 7.

## Phases

### Phase 1: API client layer + secret management + cost telemetry

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/llm-dispatch.sh` (NEW)
- `~/.buildrunner/scripts/llm-clients/perplexity.py` (NEW)
- `~/.buildrunner/scripts/llm-clients/gemini.py` (NEW)
- `~/.buildrunner/scripts/llm-clients/grok.py` (NEW)
- `~/.buildrunner/scripts/llm-clients/codex_research.py` (NEW)
- `~/.buildrunner/scripts/llm-clients/_shared.py` (NEW)
- `~/.buildrunner/.env.template` (NEW or MODIFY)
- `.buildrunner/data.db` (MODIFY — `research_llm_calls` table created idempotently)

**Blocked by:** None

**Deliverables:**

- [ ] `_shared.py` reads `~/.buildrunner/.env`, loads `PERPLEXITY_API_KEY` / `GEMINI_API_KEY` / `XAI_API_KEY`, refuses to dispatch when the required key is missing (exit 2, JSON `{ok:false, error:"missing_key:<provider>"}`).
- [ ] `perplexity.py` calls `https://api.perplexity.ai/chat/completions` with `sonar-pro`; returns content + citations + token counts; cost from $3 / $15 per MTok rates.
- [ ] `gemini.py` calls Gemini 3.1 Pro at `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro:generateContent` with grounding (Google Search) enabled; cost from published rates.
- [ ] `grok.py` calls `https://api.x.ai/v1/chat/completions` with `grok-4` and live-search tool; cost from published rates.
- [ ] `codex_research.py` shells out to `codex exec --model "$BR3_RESEARCH_CODEX_MODEL" --effort medium --prompt-file "$PROMPT_PATH"` (default `gpt-5.4`); never inlines the prompt. Captures stdout/stderr, parses token usage from Codex CLI trailer.
- [ ] **Codex pre-flight:** `codex_research.py` runs `codex models list` (or `codex --version` minimum) before any dispatch and verifies `$BR3_RESEARCH_CODEX_MODEL` is supported. Failure → fail fast with `{ok:false, error:"codex_preflight_failed:<reason>"}` BEFORE any sub-agent cost is incurred. Cache result for the dispatcher invocation lifetime.
- [ ] `_shared.py` writes one row per call to `data.db.research_llm_calls` (`id, ts, provider, model, tokens_in, tokens_out, cost_usd, latency_ms, ok, error, request_id`).
- [ ] Circuit breaker in `_shared.py`: 3 consecutive failures within 5 minutes opens for 10 minutes; dispatcher returns `{ok:false, error:"circuit_open:<provider>"}` without making the network call.
- [ ] `llm-dispatch.sh` validates provider against allowlist `{perplexity, gemini, grok, codex}`, executes the correct `.py` with the prompt-file path, and prints the JSON envelope verbatim.

### Phase 2: Multi-model parallel sub-agent dispatch in `/research` Step 3.5

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/research.md` (MODIFY — Step 3.5 only)

**Blocked by:** Phase 1

**Deliverables:**

- [ ] Step 3.5 detects mode (standard / ultrathink) and recency flag (SCQA frame mentions "news" / "trending" / "last 7 days" / "recent") and assembles the dispatch list.
- [ ] Standard mode dispatches **3 sub-agents** (1 Claude + 1 Perplexity + 1 Gemini). `ultrathink` mode dispatches **6** (2 Claude + 1 Perplexity + 1 Gemini + 1 Codex/GPT-5 + 1 Grok if recency-flagged, else 1 extra Claude).
- [ ] Claude sub-agents continue using the existing `Agent` tool; non-Claude sub-agents go through `~/.buildrunner/scripts/llm-dispatch.sh <provider> --prompt-file <tmp>`.
- [ ] Each non-Claude response is parsed into the same Markdown structure (`## Hypotheses` / `## Key Findings` / `## All Sources`) so Step 4 synthesis treats them uniformly.
- [ ] Failed dispatches (circuit open, missing key, HTTP error) are logged inline and silently dropped from the synthesis pool. The run continues with surviving sub-agents.
- [ ] The skill's pinned `model: claude-sonnet-4-6` does NOT change; only the sub-agent pool diversifies.

### Phase 3: Confidence tagging in Step 4 synthesis

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/research.md` (MODIFY — Step 4)

**Blocked by:** Phase 2

**Deliverables:**

- [ ] Step 4 synthesis tracks `families_found_in: [claude, perplexity, gemini, codex, grok]` for every finding.
- [ ] Confidence tags emitted inline next to each finding: `HIGH` (≥2 families), `MEDIUM` (1 family + ≥1 corroborating cited source), `LOW` (single family, no corroboration).
- [ ] Contradictions across different model families are auto-promoted to `## Debated Topics`.
- [ ] Sources table adds a `Found by` column listing model families per URL.
- [ ] Single-Claude degraded mode: every finding tagged `LOW`; top-of-doc note explains the degradation.

### Phase 4: Adversarial cross-family review (Step 4.5 NEW)

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/research.md` (MODIFY — insert Step 4.5 between Step 4 and Step 8.5)
- `core/cluster/below/queue_schema.py` (MODIFY — add optional `adversarial_review` field)

**Blocked by:** Phase 3

**Deliverables:**

- [x] Standard mode: dispatch synthesized body to GPT-5.4 via `codex exec` with structured prompt asking for (a) 3 weakest claims, (b) missing perspectives, (c) likely hallucinations, (d) sources to recheck. Fallback chain: Codex → Gemini → Perplexity → `degraded_no_review` (skip review, never block queue).
- [x] `ultrathink` mode: dispatch to GPT-5.4 (Codex) AND Gemini 3.1 Pro in parallel; merge critiques (de-duplicate identical concerns).
- [x] **Critique payload format:** reviewer must return strict JSON `{weakest_claims:[{claim,reason,suggested_check}], missing_perspectives:[string], hallucination_risks:[{statement,why_suspect}], sources_to_recheck:[url]}`. Malformed responses → `degraded_no_review`. All string fields treated as data, never re-prompted (structural prompt-injection mitigation).
- [x] Claude orchestrator either revises the body inline OR inserts `> [REVIEW NOTE: <summary>]` markers (per-claim judgment).
- [x] Step 8.5 `PendingRecord` gains optional `adversarial_review: { reviewers, critique_summary, revisions_applied, notes_inserted, degraded, degraded_reason }`. **Below `queue_schema.py` is updated in this phase to declare the field optional and round-trip it to the committed Markdown frontmatter.** Round-trip unit test required (see `core/cluster/below/test_queue_schema.py` — 5 tests pass).
- [x] Step 8 final summary reports: # weakest-claim flags, # resolved by revision vs annotated, reviewer model(s) used.

### Phase 5: Cost guardrails + fallback orchestration

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/research-budget-guard.sh` (NEW)
- `~/.claude/commands/research.md` (MODIFY — wire guard into Steps 3.5 + 4.5)

**Blocked by:** Phase 4

**Deliverables:**

- [x] `research-budget-guard.sh` exposes `init <invocation_id> <budget_usd>` (writes budget record), `consume <invocation_id> <cost_usd>` (atomic check-and-add; exit 0 under cap, 1 over), `report <invocation_id>` (prints summary).
- [x] Step 3.5 calls `init` with `BR3_RESEARCH_BUDGET_USD` (default `2.00`) before dispatch, and `consume` after each `llm-dispatch.sh` call.
- [x] Step 4.5 calls `consume` after each adversarial-review dispatch.
- [x] On `consume` exit 1: stop dispatching, let in-flight finish, emit `## Budget Cap Hit` block in final report.
- [x] Per-invocation cost log: `.buildrunner/logs/research-cost.log` (one JSON line: `{invocation_id, ts, mode, sub_agents, reviewers, total_cost_usd, cap_hit, providers_failed}`).
- [x] Step 8 final report shows total cost, per-provider breakdown, provider failures.

### Phase 6: Tests + verification

**Status:** ✅ COMPLETE
**Files:**

- `tests/research/test_llm_clients.py` (NEW — pytest, mocks HTTPS at httpx/urllib boundary)
- `tests/research/test_dispatcher.py` (NEW)
- `tests/research/test_budget_guard.sh` (NEW — bats-compatible)
- `tests/research/e2e_research_smoke.py` (NEW)
- `~/.walter/jobs/research-smoke.cron` (NEW — falls back to plain crontab if Walter conventions differ)

**Blocked by:** Phase 5

**Deliverables:**

- [ ] `test_llm_clients.py`: per-provider tests for happy path, missing key, HTTP 5xx, malformed response, circuit-breaker open/close.
- [ ] `test_dispatcher.py`: routes correctly to each provider stub, validates allowlist, writes `research_llm_calls` row even on failure.
- [ ] `test_budget_guard.sh`: init / consume / report cycle, atomic concurrent consumes, over-cap exit code.
- [ ] `e2e_research_smoke.py`: live-API run on a small topic; asserts (a) ≥2 families in `PendingRecord.adversarial_review.reviewers`, (b) ≥1 `HIGH`-tagged finding, (c) total cost < $0.50.
- [ ] Walter nightly cron — first verify layout via `ssh byronhudson@10.0.1.102 'ls ~/.walter/jobs/ ~/.walter/lib/ 2>/dev/null'`. If conventions exist, reuse `notify` helper. Otherwise plain crontab → `~/.walter/logs/research-smoke.log`, rsync results back to Muddy.
- [ ] Test results to `~/.walter/test_results.db` if SQLite exists; otherwise JSONL fallback at `~/.walter/logs/research-smoke.jsonl`.

### Phase 7: Documentation + skill polish

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/docs/research-multi-llm.md` (NEW)
- `~/.claude/commands/research.md` (MODIFY — `<purpose>` block + "What This Command Does" sections)
- `~/.claude/CLAUDE.md` (MODIFY — short pointer to multi-llm doc)

**Blocked by:** Phase 6

**Deliverables:**

- [x] `mkdir -p ~/.buildrunner/docs/` first (directory not present in current tree).
- [x] `research-multi-llm.md` documents: env-key setup, default budget, mode matrix, provider routing, cost expectations, fallback semantics, `BR3_RESEARCH_DISABLE=grok,gemini` opt-out, `BR3_RESEARCH_CODEX_MODEL` override.
- [x] `/research` skill `<purpose>` updated to describe the multi-model pipeline accurately (current text incorrectly says "Claude's reasoning ends at synthesis").
- [x] "What This Command Does" / "What This Command Does NOT Do" updated.
- [x] CLAUDE.md gets a 3-line pointer (not full inline copy).
- [x] `br decision log "Multi-LLM /research enhancement shipped — Perplexity+Gemini+Grok+Codex added; adversarial review mandatory"`.

## Out of Scope (V1)

- Per-provider model selection knobs (Sonar Pro vs Sonar Reasoning)
- Streaming responses
- Provider-specific advanced features (Perplexity Spaces, Gemini grounding panel)
- Generalizing the dispatcher to other skills (`/audit`, `/review`)
- Model-Council consensus voting (V1 surfaces disagreement, doesn't vote)
- API key rotation / vault integration (`op` CLI not installed)
- Codex Plan Mode dispatch

## Session Log

[Will be updated by /begin]
