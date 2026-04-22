# Spec Draft Plan: Multi-LLM Research Enhancement (`/research`)

**Created:** 2026-04-22
**Author:** Byron + Claude (4.7) via `/spec`

---

## Purpose

Upgrade the `/research` skill from single-model (Claude Sonnet 4.6 only) to a true multi-model research pipeline using Claude + Codex (existing access) plus Perplexity Sonar Pro + Google Gemini 3.1 Pro + xAI Grok 4 (new API integrations). Library evidence: multi-model review catches **3–5× more bugs** (Zylos Research, Feb 2026), models miss **64.5%** of their own errors, and Perplexity ships _Model Council_ as a product because of this exact effect.

## Target user

Single operator (Byron) running `/research` against the BR3 cluster + research library on Jimmy.

## Tech stack

- **Skill surface:** `~/.claude/commands/research.md` (Markdown skill, pinned `model: claude-sonnet-4-6`).
- **API client layer:** Python 3.14 thin wrappers under `~/.buildrunner/scripts/llm-clients/`, dispatched by a single shell entrypoint `~/.buildrunner/scripts/llm-dispatch.sh`. (Codebase runs Python 3.14 — verified via `__pycache__/*.cpython-314.pyc`.)
- **Codex:** existing `codex exec` CLI (no new auth — relies on the user's Codex plan).
- **Persistence:** `.buildrunner/data.db` (existing SQLite) — new table `research_llm_calls` for per-call cost telemetry.
- **Secrets:** `~/.buildrunner/.env` (already exists, chmod 600). New keys: `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`. No 1Password CLI is installed; do not depend on `op`.
- **Tests:** pytest under `tests/research/` (new), Walter sentinel for nightly smoke.

## Paths outside the BR3 repo tree this spec touches

- `~/.claude/commands/research.md` — skill body (Phases 2–5 modify; Phase 7 polish).
- `~/.buildrunner/scripts/llm-clients/` (NEW dir) — per-provider client wrappers.
- `~/.buildrunner/scripts/llm-dispatch.sh` (NEW) — single dispatch entrypoint.
- `~/.buildrunner/scripts/research-budget-guard.sh` (NEW) — per-invocation budget enforcement.
- `~/.buildrunner/.env` (MODIFY) — add three new key entries.
- `~/.buildrunner/.env.template` (NEW or MODIFY if exists) — checked-in template documenting required keys.
- `~/.buildrunner/docs/research-multi-llm.md` (NEW) — operator docs, cost defaults, fallback semantics.

---

## Decisions (confirmed at "go" time)

The user surfaced four open questions in the `/spec` invocation. Defaults below; flip during review if undesired.

1. **API key storage:** `~/.buildrunner/.env` (already chmod 600). No 1Password CLI on this machine — do not introduce that dependency. Each client wrapper sources the env file and refuses to dispatch if its required key is missing.
2. **Cost ceiling per `/research` invocation:** **$2.00 USD default**, overridable via env `BR3_RESEARCH_BUDGET_USD`. Standard mode targets ~$0.50–1.00; `ultrathink` mode is allowed up to the ceiling. Hard stop when ceiling is hit — finish in-flight sub-agents, skip the rest, surface the cap event in the final report.
3. **Codex dispatch:** **Reuse the existing `codex exec` CLI** (the same plumbing `/codex-do` uses), not a new OpenAI API integration. Reasons: (a) the user already has a Codex plan, no new billing; (b) `codex exec` already produces structured stdout the dispatcher can capture; (c) avoids a duplicate auth path.
4. **Adversarial review scope:** **Mandatory in standard mode** (one cross-family review pass — typically Claude synthesis → GPT-5.4 critique via `codex exec`). `ultrathink` mode runs **two** adversarial reviewers (GPT-5 + Gemini 3.1 Pro) in parallel and reconciles. Reasoning: the documented 64.5% self-blindness rate makes a single-model `/research` output unreliable enough that the review step should not be opt-in.

---

## Phase Plan

Seven phases. Phases 2/3/4 all modify `~/.claude/commands/research.md` so they cannot parallelize with each other; everything else can run alongside Phase 1 once the API surface is stable.

---

### Phase 1: API client layer + secret management + cost telemetry

**Goal:** A single dispatcher (`~/.buildrunner/scripts/llm-dispatch.sh <provider> --prompt-file <path> [--max-tokens N]`) that returns a JSON envelope `{ok, provider, model, content, tokens_in, tokens_out, cost_usd, latency_ms, error?}`. Each provider wrapper handles its own auth, request shaping, and cost calculation.

**Files:**

- `~/.buildrunner/scripts/llm-dispatch.sh` (NEW)
- `~/.buildrunner/scripts/llm-clients/perplexity.py` (NEW)
- `~/.buildrunner/scripts/llm-clients/gemini.py` (NEW)
- `~/.buildrunner/scripts/llm-clients/grok.py` (NEW)
- `~/.buildrunner/scripts/llm-clients/codex_research.py` (NEW — wraps `codex exec` for non-interactive research returns)
- `~/.buildrunner/scripts/llm-clients/_shared.py` (NEW — env loader, cost record writer, circuit breaker)
- `~/.buildrunner/.env.template` (NEW or MODIFY — document `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`)
- `.buildrunner/data.db` (MODIFY — `research_llm_calls` table created via idempotent `CREATE TABLE IF NOT EXISTS` on first dispatch)

**Blocked by:** None.

**Deliverables:**

- [ ] `_shared.py` reads `~/.buildrunner/.env`, loads `PERPLEXITY_API_KEY` / `GEMINI_API_KEY` / `XAI_API_KEY`, refuses to dispatch when the required key is missing (exit 2, JSON `{ok:false, error:"missing_key:<provider>"}`).
- [ ] `perplexity.py` calls `https://api.perplexity.ai/chat/completions` with `sonar-pro`, returns content + citations + token counts; cost computed from published rates ($3 / $15 per MTok input / output).
- [ ] `gemini.py` calls Gemini 3.1 Pro via `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro:generateContent` with grounding (Google Search) enabled; cost computed from published rates.
- [ ] `grok.py` calls `https://api.x.ai/v1/chat/completions` with `grok-4` and live-search tool; cost computed from published rates.
- [ ] `codex_research.py` shells out to `codex exec --model "$BR3_RESEARCH_CODEX_MODEL" --effort medium --prompt-file "$PROMPT_PATH"` (default model `gpt-5.4`, override via env). Reads the prompt from the same temp-file path the dispatcher passes — never inlines the prompt into the shell command (avoids quoting/injection issues). Captures stdout/stderr, parses returned token usage from the trailer Codex CLI prints; cost computed from GPT-5.4 published rates.
- [ ] **Codex pre-flight check**: before any Codex dispatch, `codex_research.py` runs `codex models list 2>/dev/null` (or `codex --version` as a minimum probe) and verifies `$BR3_RESEARCH_CODEX_MODEL` appears in the supported list. If the auth is stale or the model is unsupported, fail fast with `{ok:false, error:"codex_preflight_failed:<reason>"}` BEFORE any other sub-agent dispatch incurs cost. Cache the pre-flight result for the lifetime of the dispatcher invocation.
- [ ] `_shared.py` writes one row per call to `data.db.research_llm_calls` (`id, ts, provider, model, tokens_in, tokens_out, cost_usd, latency_ms, ok, error, request_id`).
- [ ] Circuit breaker in `_shared.py`: after 3 consecutive failures for a provider within 5 minutes, dispatcher returns `{ok:false, error:"circuit_open:<provider>"}` for 10 minutes without making the network call.
- [ ] `llm-dispatch.sh` validates provider name against the allowlist `{perplexity, gemini, grok, codex}`, locates the corresponding `.py` under `llm-clients/`, executes with the prompt file path, and prints the JSON envelope verbatim to stdout.

**Success Criteria:** `~/.buildrunner/scripts/llm-dispatch.sh perplexity --prompt-file /tmp/q.txt` returns a valid JSON envelope with `ok:true` when the key is set, `ok:false` with a structured error when the key is missing or the API is unreachable. A row appears in `research_llm_calls` for every dispatch attempt (success or failure).

**Parallelizable with:** Phase 6 (tests can stub the HTTP layer once the JSON envelope contract is fixed).

---

### Phase 2: Multi-model parallel sub-agent dispatch in `/research` Step 3.5

**Goal:** Replace the current "all sub-agents are Claude" pattern with a mixed pool. Standard mode: **3 sub-agents** (1 Claude + 1 Perplexity + 1 Gemini). `ultrathink` mode: **6 sub-agents** (2 Claude + 1 Perplexity + 1 Gemini + 1 Codex/GPT-5 + 1 Grok if recency-flagged, else 1 extra Claude).

**Files:**

- `~/.claude/commands/research.md` (MODIFY — Step 3.5 only)

**Blocked by:** Phase 1 (needs the dispatcher).

**Deliverables:**

- [ ] Step 3.5 detects mode (standard / ultrathink) and recency flag (does the SCQA frame mention "news", "trending", "last 7 days", "recent"? — keyword match) and assembles the dispatch list.
- [ ] Claude sub-agents continue to use the existing `Agent` tool (no change to their dispatch path).
- [ ] Non-Claude sub-agents are dispatched by writing the per-agent prompt (built from the existing `<sub_agent_prompt_template>` with one hypotheses + findings + sources block) to a temp file and calling `~/.buildrunner/scripts/llm-dispatch.sh <provider> --prompt-file <tmp>`.
- [ ] Each non-Claude response is parsed into the same Markdown structure the Claude sub-agents return (`## Hypotheses` / `## Key Findings` / `## All Sources`) so Step 4 synthesis treats them uniformly.
- [ ] Failed dispatches (circuit open, missing key, HTTP error) are logged inline in the run summary and silently dropped from the synthesis pool — the run continues with the surviving sub-agents.
- [ ] The skill's pinned `model: claude-sonnet-4-6` does NOT change; only the _sub-agent_ pool diversifies.

**Success Criteria:** A standard-mode `/research` invocation dispatches exactly 3 sub-agents (1 Claude + 1 Perplexity + 1 Gemini) when all keys are present, and gracefully degrades to surviving sub-agents when any provider is unreachable. The synthesis at Step 4 receives uniformly-shaped Markdown from all surviving agents.

**Parallelizable with:** None (modifies the same file as Phases 3 and 4).

---

### Phase 3: Confidence tagging in Step 4 synthesis

**Goal:** Every finding in the synthesized body carries a confidence label derived from how many _distinct model families_ surfaced it. This is the documented mechanism by which multi-model recall improves quality — making it visible to the reader is the whole point of the upgrade.

**Files:**

- `~/.claude/commands/research.md` (MODIFY — Step 4 synthesis protocol + raw body output template)

**Blocked by:** Phase 2.

**Deliverables:**

- [ ] Step 4 synthesis protocol is updated to track `families_found_in: [claude, perplexity, gemini, codex, grok]` for every finding.
- [ ] Confidence tags emitted in the raw body: `HIGH` (≥2 families), `MEDIUM` (1 family + ≥1 corroborating cited source), `LOW` (single family + no corroboration). Tag appears inline next to each finding heading.
- [ ] Contradictions found across _different_ model families are auto-promoted to the `## Debated Topics` section (existing convention in the skill — this just makes the cross-family signal explicit).
- [ ] Sources section adds a `Found by` column listing which model families surfaced each URL.
- [ ] Existing single-Claude behavior remains valid: if only Claude sub-agents survive (all APIs down), every finding is tagged `LOW` and a top-of-doc note explains the degraded mode.

**Success Criteria:** A synthesized body produced from 3 surviving sub-agents shows confidence tags on every finding, with `HIGH` tags only on findings that ≥2 families surfaced. Sources table includes the `Found by` column.

**Parallelizable with:** None (same file as Phases 2 and 4).

---

### Phase 4: Adversarial cross-family review (Step 4.5 NEW)

**Goal:** Insert a new step between Step 4 (synthesis) and Step 8.5 (queue) that sends the synthesized body to a _different model family_ for a structured critique. Standard mode runs one reviewer; `ultrathink` runs two reviewers in parallel and reconciles their critiques.

**Files:**

- `~/.claude/commands/research.md` (MODIFY — insert new Step 4.5 between existing Step 4 and Step 8.5)

**Blocked by:** Phase 3.

**Deliverables:**

- [ ] Standard mode: dispatch the synthesized body to GPT-5.4 via `codex exec` with a structured prompt asking for (a) 3 weakest claims, (b) missing perspectives, (c) likely hallucinations to verify, (d) sources that should be cross-checked. If Codex is unavailable, fall back to Gemini; if Gemini is also down, fall back to Perplexity; if all three are down, log a `degraded_no_review` event and skip review (do not block the queue).
- [ ] `ultrathink` mode: dispatch the body to GPT-5.4 (Codex) AND Gemini 3.1 Pro in parallel; merge their critiques into a single annotated review payload (de-duplicate identical concerns).
- [ ] Claude (the orchestrator) reads the critique(s) and either (a) revises the body inline to address the concerns, or (b) inserts inline `> [REVIEW NOTE: <critique summary>]` markers next to claims it chose not to revise (with a short rationale). Both paths are valid — Claude judges per-claim.
- [ ] The Step 8.5 queue record gains a new field `adversarial_review: { reviewers: [...], critique_summary: "...", revisions_applied: N, notes_inserted: N }`. **Phase 4 also updates `core/cluster/below/queue_schema.py` (or the equivalent PendingRecord schema definition) to declare the field as optional + preserve it through to the committed Markdown frontmatter.** Without this schema update, Below's Pydantic / typed deserialization will silently strip the field on every run. A unit test on the Below side asserts the round-trip preserves `adversarial_review`.
- [ ] **Critique payload format**: the adversarial reviewer is instructed to return a strict JSON object matching schema `{weakest_claims:[{claim,reason,suggested_check}], missing_perspectives:[string], hallucination_risks:[{statement,why_suspect}], sources_to_recheck:[url]}`. The orchestrator parses this JSON (rejects malformed responses → degraded_no_review) and treats every string field as data, never as an instruction. This makes the prompt-injection mitigation structural rather than purely behavioral.
- [ ] The final summary report (Step 8) calls out: number of weakest-claim flags, number resolved by revision vs annotated, and the reviewer model(s) used.

**Success Criteria:** Every standard-mode `/research` invocation produces a synthesized body that has been reviewed by at least one non-Claude model family before queueing (or carries a `degraded_no_review` marker if all alternates were unreachable). `ultrathink` invocations carry critique from two independent reviewers.

**Parallelizable with:** None (same file as Phases 2 and 3).

---

### Phase 5: Cost guardrails + fallback orchestration

**Goal:** Enforce the per-invocation budget cap, emit clean degradation messages when providers fail, and produce per-run telemetry the operator can review.

**Files:**

- `~/.buildrunner/scripts/research-budget-guard.sh` (NEW)
- `~/.claude/commands/research.md` (MODIFY — wire the guard into Steps 3.5 and 4.5)

**Blocked by:** Phase 4.

**Deliverables:**

- [ ] `research-budget-guard.sh` exposes three commands: `init <invocation_id> <budget_usd>` (writes a budget record), `consume <invocation_id> <cost_usd>` (atomic check-and-add against the budget; returns exit 0 if under cap, 1 if over), `report <invocation_id>` (prints summary).
- [ ] Step 3.5 calls `init` with `BR3_RESEARCH_BUDGET_USD` (default `2.00`) before dispatching sub-agents, and `consume` after each `llm-dispatch.sh` call.
- [ ] Step 4.5 calls `consume` after each adversarial-review dispatch.
- [ ] If `consume` returns exit 1, the skill stops dispatching new sub-agents/reviewers, lets in-flight work complete, and emits a `## Budget Cap Hit` block in the final report listing what was skipped.
- [ ] Per-invocation cost log written to `.buildrunner/logs/research-cost.log` (one JSON line per invocation: `{invocation_id, ts, mode, sub_agents, reviewers, total_cost_usd, cap_hit, providers_failed}`).
- [ ] Final summary report (Step 8) shows total cost, per-provider cost breakdown, and any provider failures.

**Success Criteria:** Setting `BR3_RESEARCH_BUDGET_USD=0.10` and invoking `/research` causes the run to hit the cap mid-dispatch, finish in-flight sub-agents only, and report `cap_hit:true` in both the user-visible report and the cost log. An invocation with all providers reachable shows actual per-provider spend in the report.

**Parallelizable with:** Phase 6.

---

### Phase 6: Tests + verification

**Goal:** Mock-API tests for the client layer, an end-to-end smoke test for the multi-model pipeline, and a Walter sentinel that runs the smoke nightly.

**Files:**

- `tests/research/test_llm_clients.py` (NEW — pytest, mocks HTTPS at `urllib.request` / `httpx` boundary)
- `tests/research/test_dispatcher.py` (NEW — exercises `llm-dispatch.sh` against mocked clients)
- `tests/research/test_budget_guard.sh` (NEW — bats or shellcheck-compatible)
- `tests/research/e2e_research_smoke.py` (NEW — runs `/research "test topic"` against live APIs, asserts ≥2 model families in the synthesis, and a non-empty critique)
- `~/.walter/jobs/research-smoke.cron` (NEW on Walter — nightly run of `e2e_research_smoke.py`)

**Blocked by:** Phase 5.

**Deliverables:**

- [ ] `test_llm_clients.py`: per-provider tests for happy path, missing key, HTTP 5xx, malformed response, circuit-breaker open/close transition.
- [ ] `test_dispatcher.py`: dispatcher routes correctly to each provider stub, validates provider allowlist, writes a `research_llm_calls` row even on failure.
- [ ] `test_budget_guard.sh`: init / consume / report cycle, atomic concurrent consumes, over-cap exit code.
- [ ] `e2e_research_smoke.py`: dry-run topic, asserts (a) ≥2 families present in the queued `PendingRecord.adversarial_review.reviewers`, (b) ≥1 `HIGH`-tagged finding, (c) total cost < $0.50 for the smoke topic.
- [ ] Walter nightly cron — first verify the actual sentinel layout via `ssh byronhudson@10.0.1.102 'ls ~/.walter/jobs/ ~/.walter/lib/ 2>/dev/null'`. If `~/.walter/jobs/` exists and a `notify` helper is present, reuse them. Otherwise fall back to a plain crontab entry that writes to `~/.walter/logs/research-smoke.log` and rsyncs results back to Muddy. Do not assume undocumented Walter conventions.
- [ ] Test results land in `~/.walter/test_results.db` if the SQLite file already exists; otherwise the cron writes a JSONL fallback at `~/.walter/logs/research-smoke.jsonl` and the spec follow-up is to migrate to the SQLite store once Walter conventions are documented.

**Success Criteria:** `pytest tests/research/` passes locally with all providers mocked. `e2e_research_smoke.py` passes against live APIs with budget < $0.50. Walter records nightly results in `test_results.db`.

**Parallelizable with:** Phase 5 once Phase 4 lands.

---

### Phase 7: Documentation + skill polish

**Goal:** Operator docs, CLAUDE.md notes, and final review of the modified `/research` skill body.

**Files:**

- `~/.buildrunner/docs/research-multi-llm.md` (NEW)
- `~/.claude/commands/research.md` (MODIFY — top-of-file `<purpose>` block + `## What This Command Does` section)
- `~/.claude/CLAUDE.md` (MODIFY — short note under "Research Library — Jimmy Only" pointing at the multi-LLM doc)

**Blocked by:** Phase 6.

**Deliverables:**

- [ ] **Pre-create the docs directory**: `mkdir -p ~/.buildrunner/docs/` as the first step of Phase 7 (the directory is not present in the current tree).
- [ ] `research-multi-llm.md` documents: env-key setup, default budget, mode matrix (standard vs ultrathink), provider routing matrix (which model handles which lens), cost expectations, fallback semantics, how to disable a provider (`BR3_RESEARCH_DISABLE=grok,gemini`), and how to override the Codex model via `BR3_RESEARCH_CODEX_MODEL`.
- [ ] `/research` skill `<purpose>` updated to describe the multi-model pipeline accurately (current text says "Claude's reasoning ends at synthesis").
- [ ] `## What This Command Does` and `## What This Command Does NOT Do` sections updated to reflect the new behavior.
- [ ] CLAUDE.md gets a 3-line pointer to `research-multi-llm.md` (not a full inline copy — keep CLAUDE.md tight).
- [ ] `br decision log "Multi-LLM /research enhancement shipped — Perplexity+Gemini+Grok+Codex added; adversarial review mandatory"` recorded.

**Success Criteria:** A new operator can read `research-multi-llm.md` and successfully configure the three API keys + run `/research` with the multi-model pipeline working. The `/research` skill's documentation matches its actual behavior.

**Parallelizable with:** None (depends on Phase 6 verification).

---

## Out of Scope (Future)

- **Per-provider model selection knobs** (e.g. swap Sonar Pro for Sonar Reasoning) — V1 picks one model per provider.
- **Streaming responses** — V1 buffers full responses; streaming is unnecessary for research synthesis.
- **Provider-specific advanced features** (Perplexity Spaces, Gemini grounding sources panel) — V1 uses each provider's basic completion endpoint.
- **A general "multi-model dispatch" skill for other commands** (`/audit`, `/review`, etc.) — explicitly out of scope; the dispatcher is a building block but the rollout is `/research`-only in V1.
- **Model-Council-style consensus voting** (force N models to agree before publishing a finding) — V1 surfaces disagreement to the reader; voting is a future enhancement.
- **API key rotation / vault integration** — `~/.buildrunner/.env` chmod 600 is the V1 baseline; no `op` CLI dependency.
- **Codex _plan_ dispatch** (Plan Mode in `codex exec`) — V1 uses `codex exec` in non-interactive single-turn mode only.

---

## Parallelization Matrix

| Phase | Key Files                                                 | Can Parallel With    | Blocked By    |
| ----- | --------------------------------------------------------- | -------------------- | ------------- |
| 1     | `~/.buildrunner/scripts/llm-clients/*`, `llm-dispatch.sh` | 6 (test scaffolding) | -             |
| 2     | `~/.claude/commands/research.md` (Step 3.5)               | -                    | 1             |
| 3     | `~/.claude/commands/research.md` (Step 4)                 | -                    | 2 (same file) |
| 4     | `~/.claude/commands/research.md` (Step 4.5 NEW)           | -                    | 3 (same file) |
| 5     | `research-budget-guard.sh`, `research.md` wiring          | 6                    | 4             |
| 6     | `tests/research/*`                                        | 1, 5                 | -             |
| 7     | `research-multi-llm.md`, `research.md` polish, CLAUDE.md  | -                    | 6             |

**Effective serial chain:** 1 → 2 → 3 → 4 → 5 → 7. Phase 6 (tests) develops alongside 1, gates final delivery before 7.

---

## Cluster routing (preview — formalized in Step 4.5 of /spec)

| Phase | Bucket        | Node   | Rationale                                                        |
| ----- | ------------- | ------ | ---------------------------------------------------------------- |
| 1     | backend-build | muddy  | New scripts under `~/.buildrunner/scripts/` (operator's machine) |
| 2     | backend-build | muddy  | Skill body lives on operator's machine                           |
| 3     | backend-build | muddy  | Same                                                             |
| 4     | backend-build | muddy  | Same                                                             |
| 5     | backend-build | muddy  | Budget guard + skill wiring                                      |
| 6     | qa            | walter | Walter is the sentinel test node                                 |
| 7     | architecture  | muddy  | Docs + final skill polish                                        |

---

## Risks + Mitigations

- **Provider rate limits** during a single `/research` run: each wrapper backs off on 429 (one retry with 2× delay), then surfaces failure cleanly. Circuit breaker prevents repeated dispatches into a known-bad provider in the same invocation.
- **Token cost runaway**: budget guard is the hard stop. Each provider also has a per-call `max_tokens` ceiling (default 8K out) that the dispatcher enforces.
- **Provider response parsing drift** (Perplexity / Gemini / Grok APIs evolve their JSON shapes): each wrapper isolates the shape into a single `_parse_response` function with a small unit test. Schema drift fails the wrapper test before it touches `/research`.
- **Adversarial-review prompt injection** (a critique that says "ignore all prior instructions"): structurally mitigated by the strict JSON schema in Phase 4 (`weakest_claims`, `missing_perspectives`, `hallucination_risks`, `sources_to_recheck`). Reviewer responses that don't parse against the schema are rejected (`degraded_no_review`), and every string field is treated as data, never re-prompted. Schema validation is the enforcement mechanism, not behavioral framing.
- **Sub-agent shape mismatch**: every non-Claude sub-agent gets the same `<sub_agent_prompt_template>` with explicit `## Hypotheses` / `## Key Findings` / `## All Sources` headers. The synthesis step ignores any agent that didn't produce the required headers (and logs the violation).
- **Below worker queue contract change**: the new `adversarial_review` field on `PendingRecord` is _additive_. Below ignores unknown fields today; we file a follow-up note for the Below worker to preserve the new field in the committed Markdown's frontmatter.

---

## Success Definition (V1 done)

A standard-mode `/research <topic>` invocation:

1. Dispatches 3 sub-agents (1 Claude + 1 Perplexity + 1 Gemini) when all keys are present.
2. Synthesizes their findings with confidence tags (`HIGH` / `MEDIUM` / `LOW`).
3. Sends the synthesized body to GPT-5.4 (via `codex exec`) for an adversarial critique.
4. Revises or annotates the body based on the critique.
5. Queues the body to Below with the new `adversarial_review` audit field populated.
6. Reports total cost, per-provider breakdown, reviewer used, and any cap/failure events.
7. Stays under the $2.00 default budget on a typical topic, and under $0.50 on a smoke topic.

If any provider is down, the run completes with the surviving providers and surfaces the degradation cleanly. If _all_ alternates are down, the run produces a Claude-only result tagged `degraded_no_review` and queues normally.
