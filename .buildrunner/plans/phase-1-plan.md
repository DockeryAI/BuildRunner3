# Phase 1 Implementation Plan: API client layer + secret management + cost telemetry

**Phase:** 1 of 7  
**Date:** 2026-04-22  
**Runtime:** Python 3.14, urllib.request (no new heavy deps)

## Tasks (9 total)

1. _shared.py — env loader, DB writer, circuit breaker
2. perplexity.py — Perplexity Sonar Pro client
3. gemini.py — Gemini 3.1 Pro client with grounding
4. grok.py — Grok-4 client with live-search
5. codex_research.py — codex exec wrapper with preflight
6. llm-dispatch.sh — shell entrypoint / allowlist router
7. .env.template — documented key template
8. research_llm_calls table — idempotent CREATE in data.db (handled by _shared.py on first call)
9. Commits — ~/.buildrunner repo + BR3 repo

## JSON envelope contract
{ok, provider, model, content, tokens_in, tokens_out, cost_usd, latency_ms, request_id, error?}

## Cost Rates (hardcoded in each client)
- Perplexity Sonar Pro: $3.00/MTok in, $15.00/MTok out
- Gemini 3.1 Pro: $1.25/MTok in, $5.00/MTok out
- Grok-4: $3.00/MTok in, $15.00/MTok out
- GPT-5.4 (Codex): $10.00/MTok in, $30.00/MTok out (parse from CLI trailer)
