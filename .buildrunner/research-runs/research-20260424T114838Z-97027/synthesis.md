## TL;DR

GPT-5.5 (codename "Spud") launched **April 23, 2026** — the day before this research — as OpenAI's current flagship. It is a fully retrained model (not a 5.4 fine-tune), and it is the recommended default in Codex CLI. **Critical blocker for BR3 today: API key access is not yet available.** GPT-5.5 is only accessible via ChatGPT subscription sign-in through Codex; the standard `OPENAI_API_KEY` pathway returns an auth error. OpenAI says API key access is coming "very soon."

When API access opens: the case for migration is real but not urgent. GPT-5.5 is meaningfully better for BR3's terminal-first, multi-tool agentic workloads (Terminal-Bench 2.0: +7.6pp) and dramatically better for large-context tasks (long-context recall at 256K+: +52pp). Pricing is a wash on batch endpoints. The risks — elevated hallucination rate in self-grading loops, xhigh reasoning cost explosion, and complete absence of a 5.5-specific prompting guide one day after launch — argue for a measured pilot, not a wholesale flip.

---

## Problem Statement

BR3's Codex dispatch infrastructure (`codex-do` skill, `runtime-dispatch.sh`, `autopilot-dispatch-prefix.sh`) is built around GPT-5.4. The `/codex` skill references "OpenAI Codex 5.4 best practices." GPT-5.5 launched yesterday, is already the recommended model in Codex CLI 0.124.0, and has measurably different performance characteristics. This research answers: what changed, how to prompt it, and whether and when to migrate.

---

## What Is GPT-5.5

**Release:** April 23, 2026. OpenAI codename: "Spud." First fully retrained base model since GPT-4.5 — not a fine-tune of 5.4. The architecture was co-designed with NVIDIA GB200/GB300 NVL72 rack-scale systems (100,000-GPU cluster), with GPT-5.5 itself used to rewrite OpenAI's serving infrastructure. NVIDIA reports 35x lower cost per million tokens and 50x higher token output per second per megawatt vs prior-gen hardware.

**Position in lineup (April 2026):**
- GPT-5.5 Pro — flagship, max quality
- GPT-5.5 — current recommended for Codex
- GPT-5.4 — previous flagship, still available (Codex fallback)
- GPT-5.3-Codex — coding-specialized via API (API-key accessible)
- GPT-5.4 mini — cost-efficient subagent model

**Access:** ChatGPT (Plus/Pro/Business/Enterprise) + Codex (with ChatGPT sign-in). Standard API key: **not yet available** as of April 23, 2026.

---

## Benchmarks: Where 5.5 Wins and Where It Doesn't

Cross-family confidence: HIGH for all rows marked ★ (confirmed by Claude sub-agents + Perplexity independently).

| Benchmark | GPT-5.4 | GPT-5.5 | Delta | Relevant to BR3? |
|---|---|---|---|---|
| Terminal-Bench 2.0 (CLI/planning) ★ | 75.1% | **82.7%** | +7.6pp | ✅ HIGH — agentic CLI work |
| SWE-Bench Pro (real GitHub issues) ★ | 57.7% | **58.6%** | +0.9pp | ✅ MODERATE — minimal gain |
| Expert-SWE (OpenAI internal) ★ | 68.5% | **73.1%** | +4.6pp | ✅ but internal benchmark |
| ARC-AGI-2 ★ | 73.3% | **85.0%** | +11.7pp | ⬜ low relevance |
| MCP Atlas (multi-tool use) ★ | 67.2% | **75.3%** | +8.1pp | ✅ HIGH — multi-tool agentic |
| MRCR v2 (512K–1M context) ★ | 36.6% | **74.0%** | +37.4pp | ✅ large codebase phases |
| Graphwalks BFS (256K) ★ | 21.4% | **73.7%** | +52.3pp | ✅ large codebase phases |
| SWE-Bench Pro vs Claude Opus 4.7 ★ | — | 58.6% | vs **64.3%** (Opus 4.7) | ⚠ Opus 4.7 still leads |
| AA-Omniscience (hallucination rate) | — | **86%** | vs 36% (Opus 4.7) | ⚠ HIGH risk for self-verify |
| Terminal-Bench vs Claude Opus 4.7 ★ | — | **82.7%** | vs 69.4% (Opus 4.7) | ✅ GPT-5.5 wins here |
| API input price | $2.50/M | $5.00/M | 2× | — |
| API output price | $15.00/M | $30.00/M | 2× | — |
| Batch input price | $1.25/M | $2.50/M | = 5.4 standard | ✅ use batch |
| Context (API) | 1M | 1M | same | — |
| Context (Codex CLI) | — | 400K | new | ✅ |
| Output tokens per Codex task | baseline | -40% (claimed) | [MEDIUM — unverified] | ✅ if true |

**The task-axis split is critical for BR3:** GPT-5.5 leads on terminal-execution/planning/tool-use tasks. Claude Opus 4.7 leads on codebase-resolution/PR-review tasks. BR3's autopilot uses Claude Opus 4.7 for orchestration and Codex (GPT-5.x) for execution — this hybrid is the correct architecture and should continue.

---

## Prompting GPT-5.5

**Compatibility:** Drop-in with GPT-5.4 prompts. Same API surface: Responses API + Chat Completions, same `reasoning.effort` parameter, same tool call schemas, same `apply_patch`/`shell_command` tool names in Codex. No breaking prompt changes documented. [HIGH — confirmed by Claude + Perplexity + official docs]

**No GPT-5.5-specific prompting guide exists yet.** The OpenAI Cookbook has guides for GPT-5, 5.1, 5.2, and a Codex guide targeting `gpt-5.3-codex`. The 5.5 guide is expected alongside API key rollout. Use the GPT-5.4 guide as the current reference.

### Reasoning Effort Levels (unchanged from 5.4)

```
none    — no reasoning tokens (fastest/cheapest; good for simple instruction following)
low     — minimal reasoning
medium  — PRODUCTION DEFAULT for agentic coding
high    — significant reasoning  
xhigh   — maximum thinking (4–10 min execution, 9,322 vs 39 tokens in practice)
```

**xhigh is dangerous in production.** Simon Willison measured 9,322 reasoning tokens at xhigh vs 39 at default on a single GPT-5.5 prompt — a 239× difference. At $30/M output tokens, one xhigh prompt can cost $0.28–$1.00+. BR3's autopilot dispatches that cascade `ultrathink` (→ xhigh) to every phase will see significant cost blowback. Reserve xhigh for genuinely hard single steps only.

**`minimal` reasoning effort note:** GPT-5.5 API supports a `minimal` effort tier (faster, fewer tokens, good for coding/instruction-following). The Codex CLI does NOT yet expose this (GitHub issue #2296). Missing optimization lever for high-volume dispatch.

### Critical API Constraints (same as 5.4, must be audited in BR3)

```python
# CORRECT — reasoning active, no temperature
response = client.responses.create(
    model="gpt-5.4",  # stay on 5.4 until API key access opens for 5.5
    reasoning={"effort": "medium"},
    tools=[...],
    input=[{"role": "user", "content": prompt}]
)

# BREAKS SILENTLY — temperature+reasoning conflict
response = client.responses.create(
    model="gpt-5.4",
    reasoning={"effort": "medium"},
    temperature=0.7,  # ❌ invalid when reasoning != "none"; silently fails or errors
    ...
)
```

**Audit target:** `autopilot-dispatch-prefix.sh` — check for any residual `temperature` or `top_p`. These are hard-disabled when reasoning effort is anything other than `none`.

### Production System Prompt Pattern (5.4 / forward-compatible with 5.5)

```
You are an autonomous coding agent. Once the user gives a direction, proactively 
gather context, plan, implement, test, and refine without waiting for additional 
prompts.

TOOL USE:
- Prefer: rg, read_file, apply_patch over raw shell
- Batch all reads: before any tool call, decide ALL files you need, then issue 
  them in parallel using multi_tool_use.parallel
- parallel_tool_calls: true

SCOPE:
- Implement EXACTLY and ONLY what is requested
- No extra features, no UX embellishments unless asked

UPDATES:
- Send 1–2 sentence updates only when starting a new phase or discovering a plan change
- Each update must include a concrete outcome ("Found X", "Confirmed Y")

DONE WHEN:
- Deliverables are working code, not plans
- All stated intentions/TODOs are marked Done, Blocked, or Cancelled
```

**Parallel tool calls require explicit instruction** — `parallel_tool_calls: true` in the API params is necessary but not sufficient. The system prompt must also say "decide ALL files/resources you need before any tool call, then batch them using `multi_tool_use.parallel`."

### AGENTS.md (unchanged best practice for 5.5)

- Human-authored only: +4% task success vs -3% (LLM-generated actively harmful)
- 32KB hard cap with silent truncation
- Injected as user-role messages root → leaf (deeper files override root)
- Keep under 100 lines; only document non-obvious architecture, commands, critical constraints

### The `phase` Parameter (5.4 carries forward to 5.5)

```python
phase="commentary"     # intermediate tool-calling turns
phase="final_answer"   # terminal completion signal
```

### Codex CLI Model Flag

```bash
codex --model gpt-5.5   # available via ChatGPT sign-in
codex --model gpt-5.4   # use this for API key auth (current BR3)
# or in config.toml: model = "gpt-5.5"
```

---

## Cost Analysis for BR3

| Scenario | GPT-5.4 | GPT-5.5 | Net |
|---|---|---|---|
| Standard tier, same tokens | $2.50/$15 | $5.00/$30 | +100% |
| Standard tier, -40% tokens | $2.50/$15 | $3.00/$18 (est.) | +20% |
| Batch tier, same tokens | $1.25/$7.50 | $2.50/$15 | +100% |
| Batch tier, -40% tokens | $1.25/$7.50 | $1.50/$9 (est.) | +20% |
| Batch tier vs 5.4 standard | $2.50/$15 | $2.50/$15 | **flat** |

**Bottom line:** Use Batch API for async Codex phases. The token efficiency gain at batch pricing makes migration cost-neutral vs 5.4 standard pricing. The 40% token reduction claim is unverified — it comes from OpenAI and should be measured in production.

---

## Risks and Failure Modes

### Risk 1: Hallucination Rate 86% [MEDIUM confidence — single source citing Artificial Analysis]

AA-Omniscience benchmark shows GPT-5.5 at 86% hallucination rate vs Claude Opus 4.7's 36%. The risk for BR3: in agentic loops where Codex self-verifies its own work (build validation, compliance checks), the model confidently produces wrong answers. This is not a chat quality issue — it's a production architecture risk. Mitigation: keep Claude Opus 4.7 as the verifier/orchestrator and use GPT-5.5 only as the executor. Never use GPT-5.5 to grade its own output.

> [REVIEW NOTE: The 86% hallucination figure is from a single blog source (ofox.ai) citing Artificial Analysis data. Verify at artificialanalysis.ai before treating as definitive.]

### Risk 2: xhigh Reasoning Cost Explosion

Simon Willison measured 9,322 reasoning tokens at xhigh vs 39 at default for GPT-5.5. At $30/M output, this is $0.28 per prompt at xhigh vs $0.001 at default — 280× cost difference. BR3's autopilot uses `ultrathink` (→ xhigh) for the hardest phases. Review which phases actually warrant xhigh vs using medium as the production default.

### Risk 3: API Timeout at xhigh

The default SDK timeout (15 minutes) is insufficient for xhigh reasoning. Measured execution time: 4–10 minutes per prompt at xhigh. In BR3's parallel phase dispatch with default timeouts, xhigh phases will silently time out. Set custom timeout ≥ 20 minutes for any xhigh dispatch, or cap xhigh usage to one-off manual escalations.

### Risk 4: `minimal` Reasoning Not Available in Codex CLI

The cheapest/fastest reasoning tier isn't accessible via `model_reasoning_effort` in Codex CLI yet (GitHub issue #2296). High-volume batch dispatch can't use this optimization until OpenAI ships it.

### Risk 5: "Rushing" Failure Mode

Inherited from GPT-5.4: on vague task descriptions, the model pushes forward with assumptions rather than asking for clarification, occasionally overwriting working code. Practitioner benchmark (acmesoftware.com, GPT-5.4 Codex): 4.50/5 overall with documented "rushing" tendency. Mitigation: explicit task scoping, `allow`/`exclude` path constraints, conservative `maxDurationMinutes` limits in `codex.toml`, and clear AGENTS.md critical constraints.

### Risk 6: 400K Context Cap in Codex CLI

The API offers 1M context, but Codex CLI is capped at 400K for throughput/cost management. Large-repo cleanup waves (BR3's P5 had 268 import removals across a large codebase) should be profiled for context usage. If a phase regularly approaches 400K in Codex, chunk it into smaller worktree tasks.

---

## Debated Topics

**Hallucination "60% drop" vs 86% rate:** OpenAI and press coverage claim "60% drop in hallucinations versus GPT-5.4." AA-Omniscience shows 86% hallucination rate. These measure different things — the 60% drop refers to factual response hallucinations in chat contexts; AA-Omniscience tests self-knowledge/calibration. Both can be true. The 86% figure is the relevant one for agentic self-verification loops.

**Real cost impact of "40% token reduction":** OpenAI's claim of 40% fewer output tokens on Codex tasks would make 5.5 roughly cost-neutral at standard pricing despite 2x per-token price. This claim is unverified independently — community reports of "CRAZY credit depletion" suggest the reduction applies only to standard reasoning mode, while xhigh explodes costs. Until measured in production, assume 20% net cost increase at standard tier.

**SWE-Bench Pro reliability:** OpenAI flags that "Anthropic reported signs of memorization on a subset of problems" in Claude Opus 4.7's 64.3% score. This is an attempt to discount Claude's lead. The score stands as the best publicly available contamination-resistant benchmark result until an independent retest is conducted.

---

## Recommendations for BR3

### Today (April 24, 2026): No migration possible
The API key blocker is absolute. Keep `gpt-5.4` in all production dispatch paths. Do not set `model = "gpt-5.5"` in config — it will fail with an auth error for API key users.

### When API key access opens (expected "very soon" per OpenAI):

**Step 1 — Config changes:**
```bash
# In runtime-dispatch.sh / codex.toml
# Change: model = "gpt-5.4"
# To:     model = "gpt-5.5"

# In .buildrunner/scripts/ or codex.toml
# Add:    api_tier = "batch"   # neutralizes 2x price via token efficiency
```

**Step 2 — Targeted pilot (don't flip all phases at once):**
- Start with terminal-heavy execution phases (cleanup waves, import removal, dead code deletion) where Terminal-Bench gains are most relevant
- Keep Claude Opus 4.7 as orchestrator/verifier — never use GPT-5.5 to grade its own output
- Measure actual token usage on 3–5 phases before committing to full migration

**Step 3 — Update the codex skill:**
- Update CLAUDE.md reference from "OpenAI Codex 5.4 best practices" to 5.5
- Add the hallucination/self-verification warning to the codex skill
- Update model ID references in `/codex-do`, `codex` skill

**Step 4 — Audit dispatch prefix:**
- Run `grep -r 'temperature\|top_p' ~/.buildrunner/scripts/` — remove any occurrence in dispatch paths where reasoning.effort is non-null
- Verify xhigh usage is limited to `BR3_CLAUDE_PHASE_WEIGHT=hardest` phases only

### Promptless migration checklist:
- [ ] `temperature`/`top_p` removed from all reasoning-enabled dispatch paths
- [ ] `xhigh` scoped to genuine blockers only (not default for all autopilot phases)
- [ ] Custom SDK timeout ≥ 20 min for any xhigh usage
- [ ] Batch API pricing enabled for async/offline Codex phases
- [ ] Context profiling on large-codebase phases vs 400K Codex CLI cap
- [ ] AGENTS.md verified human-authored (not generated) per repo
- [ ] Claude Opus 4.7 retained as orchestrator/verifier role — GPT-5.5 as executor only

---

## Sources

Cross-family corroboration column shows which families confirmed each finding.

| # | Title | URL | Credibility | Found by | Key Contribution |
|---|-------|-----|-------------|----------|-----------------|
| 1 | Introducing GPT-5.5 — OpenAI | https://openai.com/index/introducing-gpt-5-5/ | [Official] | claude, perplexity | Primary announcement, availability, API timeline |
| 2 | GPT-5.5 System Card — OpenAI | https://openai.com/index/gpt-5-5-system-card/ | [Official] | claude | Safety ratings, benchmark scores |
| 3 | Codex Models — OpenAI Developers | https://developers.openai.com/codex/models | [Official] | claude | Model lineup, API key restriction, `--model gpt-5.5` |
| 4 | Codex Changelog — OpenAI Developers | https://developers.openai.com/codex/changelog | [Official] | claude | CLI 0.124.0 release, GPT-5.5 default recommendation |
| 5 | Codex Prompting Guide — OpenAI Cookbook | https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide | [Official] | claude | System prompt patterns, AGENTS.md, parallel tool calls |
| 6 | Prompt Guidance for GPT-5.4 — OpenAI API | https://developers.openai.com/api/docs/guides/prompt-guidance | [Official] | claude | reasoning.effort levels, phase parameter, temperature block |
| 7 | GPT-5.5 vs GPT-5.4 Comparison | https://llm-stats.com/blog/research/gpt-5-5-vs-gpt-5-4 | [Community Analysis] | claude, perplexity | Best head-to-head benchmark table |
| 8 | Artificial Analysis: GPT-5.5 Profile | https://artificialanalysis.ai/models/gpt-5-5 | [Benchmarking] | claude | Measured context ~922K, modalities, Intelligence Index rank |
| 9 | Simon Willison: GPT-5.5 via Codex backdoor | https://simonwillison.net/2026/Apr/23/gpt-5-5/ | [Community/Expert] | claude | xhigh token consumption (39→9,322), 4-min execution, model ID `openai-codex/gpt-5.5` |
| 10 | Terminal-Bench agentic coding gains | https://interestingengineering.com/ai-robotics/opanai-gpt-5-5-agentic-coding-gains | [News] | claude, perplexity | 82.7% Terminal-Bench, 58.6% SWE-Bench Pro |
| 11 | The Decoder: double API price analysis | https://the-decoder.com/openai-unveils-gpt-5-5-claims-a-new-class-of-intelligence-at-double-the-api-price/ | [News/Analysis] | claude | Competitor comparisons, where 5.5 lags, GDPval marginal gains |
| 12 | NVIDIA Blog: GPT-5.5 + GB200 | https://blogs.nvidia.com/blog/openai-codex-gpt-5-5-ai-agents/ | [Official-NVIDIA] | claude | Hardware co-design, 35x cost reduction, NVIDIA enterprise deployment |
| 13 | OpenAI Developer Community thread | https://community.openai.com/t/gpt-5-5-is-here-available-in-codex-and-chatgpt-today/1379630 | [Official thread] | claude | API key restriction confirmation, "very soon" statement, cost reports |
| 14 | GitHub Codex issue #2296 | https://github.com/openai/codex/issues/2296 | [Official-GitHub] | claude | `minimal` reasoning effort not in Codex CLI |
| 15 | Kingy AI GPT-5.5 benchmark analysis | https://kingy.ai/ai/gpt-5-5-benchmarks-revealed | [Blog/Analysis] | perplexity | Long-context benchmarks, token efficiency corroboration |
| 16 | Every: Senior Engineer Benchmark | https://www.youtube.com/watch?v=GROt1Nd4asY | [Community] | perplexity | GPT-5.5 62.5/100 vs Claude ~32.5/100 |
| 17 | shumer.dev GPT-5.5 Review | https://shumer.dev/gpt55review | [Blog-independent] | claude | Most balanced review: wins and regressions, code readability |
| 18 | ofox.ai GPT-5.5 Release Guide | https://ofox.ai/blog/gpt-5-5-release-guide-2026/ | [Blog] | claude | 86% AA-Omniscience hallucination rate, ~40% token reduction |
| 19 | acmesoftware Codex GPT-5.4 practitioner | https://acmesoftware.com/blogs/codex-gpt-5-4-a-practitioners-benchmark-of-the-2026-agentic-coding-frontier/ | [Blog-hands-on] | claude | "Rushing" failure mode, 47% token reduction via Tool Search |
| 20 | Lushbinary: GPT-5.5 vs Claude Opus 4.7 | https://lushbinary.com/blog/gpt-5-5-vs-claude-opus-4-7-comparison-benchmarks-pricing/ | [Blog] | claude | Task-axis routing: terminal → GPT-5.5, codebase-resolution → Opus 4.7 |
| 21 | APIdog GPT-5.5 pricing breakdown | https://apidog.com/blog/gpt-5-5-pricing/ | [Community] | claude | Detailed pricing tiers, thinking multipliers, $0.345 per task example |

---

## Research Log

**SCQA Frame:** BR3's Codex dispatch uses GPT-5.4. GPT-5.5 launched yesterday (April 23, 2026). Complication: API key access blocked, hallucination risks, unknown prompting deltas. Question: what changed and should we migrate?

**Sub-agent pool:** 3 Claude (opus) + Perplexity Sonar Pro + Gemini 2.5 Pro (limited — training data predates 5.5 release) + Codex (failed — empty output). 4 effective agents across 2 families (Claude + Perplexity). `DEGRADED_POOL` partial — Gemini data-cutoff limited, Codex failed; confidence tags adjusted.

**Gaps for future research:**
- The 86% AA-Omniscience hallucination rate should be independently verified at artificialanalysis.ai — currently single-source
- 40% token efficiency claim needs production measurement in BR3's actual workloads
- GPT-5.5 `minimal` reasoning effort: watch GitHub issue #2296 for CLI support
- Official GPT-5.5 prompting guide (expected alongside API key rollout) should be retrieved and enriched into this document
- Claude Opus 4.7 SWE-Bench memorization claims from OpenAI: monitor for independent retests

**Surprises:**
- API key not available on launch day — unusual for OpenAI model releases
- Long-context recall improvement (256K: 21.4% → 73.7%) is qualitatively larger than expected — transforms large-codebase viability
- xhigh reasoning: 9,322 tokens vs 39 at default — 239× cost multiplier; this is a genuine production cost risk for BR3's autopilot

**Failed approaches:** Direct Gemini 2.5 Pro research produced no GPT-5.5 data (training cutoff predates release). Codex dispatch returned empty output (auth/tooling issue). Neither failure blocked synthesis — Claude + Perplexity provided complete coverage.
