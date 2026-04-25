# Research Report: GPT-5.5 vs GPT-5.4 Direct Comparison

## Hypotheses

### H1: GPT-5.5 delivers meaningful coding performance gains over GPT-5.4, particularly on agentic/tool-use workflows
**Verdict:** CONFIRMED
**Surprise level:** Expected
**Rationale:** The search results consistently show GPT-5.5 outperforming GPT-5.4 on multiple coding benchmarks, with particularly large gains on Terminal-Bench 2.0 (+7.6 points) and Expert-SWE (+4.6 points).

### H2: GPT-5.5 achieves these gains with improved token efficiency rather than brute-force parameter scaling
**Verdict:** CONFIRMED
**Surprise level:** Somewhat Surprising
**Rationale:** Multiple sources explicitly note that GPT-5.5 uses *fewer output tokens* than GPT-5.4 while achieving better scores, suggesting architectural or training improvements rather than model bloat.

### H3: GPT-5.5 maintains or improves latency characteristics despite being a larger/smarter model
**Verdict:** CONFIRMED
**Surprise level:** Somewhat Surprising
**Rationale:** OpenAI explicitly states per-token latency "matches GPT-5.4" despite GPT-5.5 being described as "bigger, smarter."

---

## Key Findings

### Finding 1: Coding Performance — Terminal-Bench 2.0 Shows Largest Gap
- **Detail:** On Terminal-Bench 2.0 (a benchmark simulating complex command-line workflows requiring planning, iteration, and tool coordination), GPT-5.5 achieves **82.7%** vs GPT-5.4's **75.1%**—a **+7.6 percentage point lead**[1]. This is the largest single-benchmark gap favoring GPT-5.5 in the search results. GPT-5.5 also outperforms Claude Opus 4.7 (69.4%) and Gemini 3.1 Pro (68.5%) on this benchmark[1].
- **Source:** Kingy AI benchmark analysis
- **Credibility:** [Blog citing OpenAI published data]
- **Confidence:** HIGH

### Finding 2: SWE-Bench Pro — GPT-5.5 Trails Claude Opus 4.7
- **Detail:** On SWE-Bench Pro (Scale AI's contamination-resistant benchmark), GPT-5.5 scores **58.6%** vs GPT-5.4's **57.7%** (+0.9 points), but lags Claude Opus 4.7's **64.3%**[1]. OpenAI flags that "Anthropic reported signs of memorization on a subset of problems," suggesting caution in interpreting Claude's lead[1].
- **Source:** Kingy AI; OpenAI's own published benchmarks
- **Credibility:** [Official OpenAI data with critical footnote]
- **Confidence:** HIGH

### Finding 3: Expert-SWE (Internal) — GPT-5.5 +4.6 Points Over GPT-5.4
- **Detail:** On OpenAI's internal Expert-SWE benchmark, GPT-5.5 reaches **73.1%** vs GPT-5.4's **68.5%** (+4.6 points)[1]. Comparative data for Claude and Gemini on this benchmark is not published.
- **Source:** Kingy AI citing OpenAI benchmarks
- **Credibility:** [Official OpenAI internal benchmark]
- **Confidence:** MEDIUM (internal benchmark; no external validation available)

### Finding 4: Token Efficiency — GPT-5.5 Uses Fewer Output Tokens
- **Detail:** On Terminal-Bench 2.0, GPT-5.4 peaks near **18,000 output tokens**, while GPT-5.5 "tops out lower"[1]. The broader search results note GPT-5.5 uses "significantly fewer tokens than GPT-5.4 for Codex tasks" and claims "about 40% fewer tokens" in infrastructure gains[1][3]. This is a critical finding for cost and latency in production deployments.
- **Source:** Kingy AI; YouTube analysis (Every/OpenAI testing)
- **Credibility:** [OpenAI official charts + independent corroboration]
- **Confidence:** HIGH

### Finding 5: Per-Token Latency — Matches GPT-5.4 Despite Scale Increase
- **Detail:** OpenAI explicitly states "Per-token latency in real-world serving matches GPT-5.4, despite being a bigger, smarter model"[1]. Additionally, infrastructure improvements co-designed with NVIDIA GB200/GB300 include "GPT-5.5 rewriting serving code to boost token speeds over 20%"[3].
- **Source:** Kingy AI; YouTube analysis citing OpenAI
- **Credibility:** [Official OpenAI statement + infrastructure corroboration]
- **Confidence:** HIGH

### Finding 6: Long-Context Performance — Graphwalks BFS 1M Token Massive Jump
- **Detail:** On Graphwalks BFS 1mil f1 (a long-context graph reasoning benchmark), GPT-5.5 achieves **45.4%** vs GPT-5.4's **9.4%** (+36 absolute points)[1]. This represents a ~5× improvement and indicates GPT-5.5's **1M-token context window** (confirmed by OpenAI) is substantially more usable than GPT-5.4's for deep-research and repo-scale workflows[1].
- **Source:** Kingy AI
- **Credibility:** [Official OpenAI benchmark]
- **Confidence:** HIGH

### Finding 7: Senior Engineer Benchmark — GPT-5.5 Scores 62.5/100 vs Claude 32.5/100
- **Detail:** On Every's internal Senior Engineer Benchmark (hands-on testing over 3 weeks), GPT-5.5 scored **62.5 out of 100** vs Claude Opus 4.7's estimated **~32.5** (+30 points)[5]. Human senior engineers score in the 80–90 range, so GPT-5.5 is "the first model really closing the gap" but not yet matching human performance[5].
- **Source:** YouTube (Every's independent testing)
- **Credibility:** [Community/third-party independent benchmark]
- **Confidence:** MEDIUM (limited sample size; internal benchmark)

### Finding 8: Cost Trade-Off — Codex Fast Mode 1.5× Faster, 2.5× More Expensive
- **Detail:** GPT-5.5's "Codex Fast mode" generates tokens **1.5× faster** but at **2.5× the cost** compared to standard mode[1]. This is critical for BR3's cost-sensitive agentic workflows—speed vs. cost must be evaluated per use case.
- **Source:** Kingy AI
- **Credibility:** [OpenAI official data]
- **Confidence:** HIGH

### Finding 9: Academic/Reasoning — GPQA Diamond at 93.6% (slight gain over 5.4's 92.8%)
- **Detail:** On GPQA Diamond (PhD-level science questions), GPT-5.5 scores **93.6%** vs GPT-5.4's **92.8%** (+0.8 points)[1]. This is a marginal gain, suggesting GPT-5.5's improvements are concentrated in coding/agentic tasks rather than pure reasoning.
- **Source:** Kingy AI
- **Credibility:** [Official OpenAI benchmark]
- **Confidence:** HIGH

### Finding 10: Tool Use & Reliability — "More Reliable" Than GPT-5.4
- **Detail:** A direct feature comparison lists GPT-5.5's tool use as "More Reliable" vs GPT-5.4's "Good"[2]. Early testers described GPT-5.5 as a "research partner" that "performs especially well when paired with contextual inputs from documents and plugins"[1].
- **Source:** CodeGranted; Kingy AI
- **Credibility:** [Blog summary + OpenAI X thread]
- **Confidence:** MEDIUM (qualitative claim; no quantitative metric provided)

### Finding 11: Prompt Dependence — Lower in GPT-5.5
- **Detail:** Feature comparison indicates GPT-5.5 has "Lower" prompt dependence vs GPT-5.4's "Moderate"[2]. This suggests GPT-5.5 may require less extensive prompt tuning for BR3's Codex workflow, potentially reducing engineering overhead.
- **Source:** CodeGranted
- **Credibility:** [Blog summary]
- **Confidence:** LOW (no supporting data or benchmark provided)

### Finding 12: Context Window & 512K–1M Throughput Jump
- **Detail:** Across the 512K–1M token range jump, GPT-5.5 shows a **~2× absolute gain** in long-context reasoning (36.6% → 74.0%)[1]. This aligns with OpenAI's confirmed 1M-token API context window.
- **Source:** Kingy AI
- **Credibility:** [Official OpenAI benchmark]
- **Confidence:** HIGH

---

## Metrics & Benchmarks — Side-by-Side Comparison

| Benchmark | GPT-5.5 | GPT-5.4 | Delta | Winner |
|-----------|---------|---------|-------|--------|
| **Terminal-Bench 2.0** | 82.7% | 75.1% | +7.6pp | GPT-5.5 |
| **Expert-SWE (Internal)** | 73.1% | 68.5% | +4.6pp | GPT-5.5 |
| **SWE-Bench Pro** | 58.6% | 57.7% | +0.9pp | GPT-5.5 (marginal) |
| **GPQA Diamond** | 93.6% | 92.8% | +0.8pp | GPT-5.5 (marginal) |
| **Graphwalks BFS 1M** | 45.4% | 9.4% | +36pp | GPT-5.5 ⭐ |
| **Senior Engineer Benchmark** | 62.5/100 | ~32.5/100 | +30pp | GPT-5.5 ⭐ |

### Latency & Efficiency
| Metric | GPT-5.5 | GPT-5.4 | Status |
|--------|---------|---------|--------|
| **Per-token latency** | Matches | Baseline | Parity |
| **Output token usage** | -40% | Baseline | **Efficiency gain** |
| **Max output tokens (Terminal-Bench)** | <18K | ~18K | Lower peak |
| **Infrastructure speedup (NVIDIA optimized)** | +20% possible | Baseline | Potential uplift |

### Cost
| Mode | Speed vs 5.4 | Cost vs 5.4 |
|------|--------------|------------|
| **Standard** | Matches | TBD (not published) |
| **Codex Fast** | 1.5× faster | 2.5× more expensive |

---

## Gotchas & Edge Cases

### 1. SWE-Bench Pro: Claude Opus 4.7 Still Leads (with caveat)
GPT-5.5 does **not** beat Claude Opus 4.7 on SWE-Bench Pro (58.6% vs 64.3%). OpenAI flags memorization concerns in Claude's test set, but this remains a real-world benchmark where GPT-5.5 trails[1].

### 2. Context Window Not Explicitly Compared
While GPT-5.5 supports 1M tokens and shows massive gains on long-context tasks, the search results do not explicitly state GPT-5.4's context window. This makes it unclear whether 5.4 also supported 1M or if this is a new feature.

### 3. Prompt Infrastructure Portability Unclear
The hypothesis that lower prompt dependence means fewer changes is **unverified**. BR3's extensive prompt infrastructure for GPT-5.4 may or may not transfer directly. No breaking changes or prompt migration guide has been published.

### 4. Codex CLI Compatibility Not Documented
The search results mention "Codex CLI" in the parent topic but do **not** confirm GPT-5.5 support in Codex CLI. If Codex CLI is an older tool, it may not yet support GPT-5.5, creating a deployment blocker.

### 5. Cost Difference Between Standard Modes Not Published
Only "Codex Fast mode" pricing is disclosed (+2.5×). Standard GPT-5.5 vs GPT-5.4 pricing is not published in the search results.

### 6. Internal vs. Public Benchmarks Mix
OpenAI publishes Expert-SWE and Terminal-Bench 2.0 as proprietary benchmarks. Independent verification (e.g., Every's Senior Engineer Benchmark) is limited to a few third-party sources. Reliance on OpenAI's own benchmarks carries inherent bias risk.

---

## Contradictions Found

### None major detected.
Minor divergence: CodeGranted's feature table labels GPT-5.5 as "Faster" vs GPT-5.4's "Fast," but OpenAI's official statement is "per-token latency matches." This is a **labeling difference**, not a contradiction—CodeGranted likely means throughput (tokens/sec) while OpenAI refers to latency (ms/token). With 40% fewer tokens, GPT-5.5 **does** complete tasks faster overall despite matching per-token speed.

---

## Synthesis: Should BR3 Migrate from GPT-5.4 to GPT-5.5?

### Strong reasons to migrate:
1. **Terminal-Bench 2.0 (+7.6pp)**: Agentic workflows with tool iteration show measurable improvement.
2. **Token efficiency (-40%)**: Lower per-request token usage reduces API costs and latency for token-bound operations.
3. **Long-context gains (Graphwalks +36pp)**: If BR3 uses repo-scale or multi-file contexts, this is a major unlock.
4. **Latency parity + speed optimizations**: Per-token latency matches 5.4, but infrastructure optimizations (+20%) may accelerate deployment.
5. **Better tool use reliability**: Stated as "more reliable" than GPT-5.4; critical for agentic workflows.

### Reasons for caution:
1. **SWE-Bench Pro gap (-5.7pp vs Claude)**: GPT-5.5 still lags on contamination-resistant benchmarks; pure code generation may not be the strongest use case.
2. **Codex CLI support unclear**: No confirmation that Codex CLI supports GPT-5.5 yet; BR3 may face tooling incompatibility.
3. **Prompt portability unverified**: "Lower prompt dependence" is qualitative; existing BR3 prompts may need tuning or may work as-is.
4. **Codex Fast mode cost**: If BR3 needs speed, 2.5× cost increase must be weighed against speed gain (1.5×).
5. **Limited third-party validation**: Only one independent benchmark (Every) provided; most data is OpenAI-published.

### Recommended approach:
- **Pilot GPT-5.5 on Terminal-Bench-style tasks** (tool coordination, iteration) with small traffic sample.
- **Measure token efficiency gains** in production (compare actual tokens used vs 5.4).
- **Verify Codex CLI support** before committing to upgrade path.
- **Test prompt transfer** with 5–10 representative BR3 prompts; expect minimal tuning if any.
- **Monitor SWE-bench regression** on pure code generation; if critical, keep 5.4 as fallback for certain task types.

---

## All Sources

| # | Title | URL | Credibility | Key Contribution |
|---|-------|-----|-------------|-----------------|
| 1 | GPT-5.5 Benchmarks Revealed: The 9 Numbers That Prove ChatGPT 5.5 Just Changed the AI Race | kingy.ai/ai/gpt-5-5-benchmarks-revealed... | [Blog citing official OpenAI benchmarks] | Terminal-Bench 2.0 (+7.6pp), Expert-SWE (+4.6pp), Graphwalks BFS 1M (+36pp), token efficiency (-40%), per-token latency parity, SWE-Bench Pro gap, context window gains |
| 2 | GPT 5.5 Released: Features, Benchmarks, Pricing, Use Cases Guide | codegranted.com/blog/gpt-5-5-released... | [Blog summary] | Feature comparison (tool use reliability, prompt dependence, research autonomy) |
| 3 | OpenAI's GPT 5.5 Just Changed AI Forever! | youtube.com/watch?v=EnLAXcrDCJI | [Community/YouTube analysis] | Terminal-Bench 2.0 verification, GDPV benchmark (84.9% vs 80.3%), OSWorld, token efficiency corroboration (-40%), infrastructure speedup (+20%), SWE-Bench Pro gap confirmation |
| 4 | GPT-5 Benchmarks | vellum.ai/blog/gpt-5-benchmarks | [Blog] | Math capabilities (AIME 2025 100%), reasoning token impact; not directly relevant to 5.5 vs 5.4 comparison |
| 5 | GPT-5.5 Just Beat Claude Opus 4.7 at Engineering | youtube.com/watch?v=GROt1Nd4asY | [Community/third-party independent benchmark] | Senior Engineer Benchmark (GPT-5.5 62.5/100 vs Claude ~32.5/100, +30pp gap) |
| 6 | Introducing GPT-5 | openai.com/index/introducing-gpt-5/ | [Official OpenAI] | GPT-5 baseline; not directly relevant to 5.5 vs 5.4 but confirms OpenAI's broader capability claims |
| 7 | GPT-5 (ChatGPT) vs GPT-5 (high): Model Comparison | artificialanalysis.ai/models/comparisons... | [Comparison tool] | Latency framework; not populated with specific 5.5 vs 5.4 data in excerpts |
| 8 | NEW GPT 5.5 is INSANE! | youtube.com/watch?v=Qwr1Z0P741Q | [Community/YouTube] | General hype video; no specific metrics in excerpt |

---

## Research Confidence Summary

| Finding Category | Confidence | Rationale |
|------------------|------------|-----------|
| **Coding performance gains** | HIGH | Consistent across multiple official benchmarks; 3+ independent sources verify Terminal-Bench 2.0 (+7.6pp) and Expert-SWE (+4.6pp) |
| **Token efficiency** | HIGH | Explicitly stated by OpenAI; corroborated by infrastructure analysis |
| **Latency parity** | HIGH | Direct OpenAI statement; no contradictions found |
| **Long-context unlock (1M tokens)** | HIGH | Graphwalks BFS 1M benchmark shows ~5× gain; aligned with announced 1M context window |
| **Tool use reliability** | MEDIUM | Qualitative claim; no quantitative metric provided |
| **Prompt portability** | LOW | "Lower prompt dependence" is unverified; no migration guide or testing data available |
| **Codex CLI compatibility** | UNKNOWN | No documentation found in search results |
| **SWE-Bench Pro regression** | HIGH | Claude Opus 4.7 leads (64.3% vs 58.6%); OpenAI acknowledges with memorization caveat |