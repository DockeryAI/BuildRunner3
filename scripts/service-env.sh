#!/usr/bin/env bash
# scripts/service-env.sh — BR3 service launch environment
#
# Source this file before starting the Jimmy retrieval service or any
# context-bundle caller that uses the BR3_AUTO_CONTEXT flag.
#
# Usage:
#   source scripts/service-env.sh
#   uvicorn core.cluster.node_semantic:app --host 0.0.0.0 --port 8100
#
# Flag behaviour:
#   BR3_AUTO_CONTEXT=on   — enables bge-reranker-v2-m3 on every /retrieve call
#                           and on every context-bundle call that supplies a query.
#   BR3_AUTO_CONTEXT=off  — reranker is a no-op (passthrough, no model load).
#
# DO NOT set this flag in .claude/settings.json — it is read from process
# environment at import time (core.cluster.reranker, api.routes.retrieve).

# ── Core feature gate ────────────────────────────────────────────────────────
export BR3_AUTO_CONTEXT="${BR3_AUTO_CONTEXT:-on}"

# ── Reranker config ──────────────────────────────────────────────────────────
# top_k: number of results returned after cross-encoder reranking.
# Tune this value to trade latency (lower) vs recall (higher).
# No similarity threshold exists — tune top_k only.
export RERANKER_TOP_K="${RERANKER_TOP_K:-5}"

# Model path — reads from HuggingFace cache or local mirror.
# Override with RERANKER_MODEL=path/to/local/model for air-gapped envs.
export RERANKER_MODEL="${RERANKER_MODEL:-BAAI/bge-reranker-v2-m3}"

# ── Metrics ──────────────────────────────────────────────────────────────────
# Reranker metrics are appended to ~/.buildrunner/reranker-metrics.jsonl.
# Each line: {"ts":"...","event":"rerank","top_k":5,"candidates":20,"latency_ms":42}
# Consume with: tail -f ~/.buildrunner/reranker-metrics.jsonl | jq .

# ── Cluster endpoints ─────────────────────────────────────────────────────────
export JIMMY_HOST="${JIMMY_HOST:-10.0.1.106}"
export JIMMY_PORT="${JIMMY_PORT:-8100}"
export BELOW_HOST="${BELOW_HOST:-10.0.1.105}"
export BELOW_OLLAMA_PORT="${BELOW_OLLAMA_PORT:-11434}"

echo "[service-env] BR3_AUTO_CONTEXT=${BR3_AUTO_CONTEXT} RERANKER_MODEL=${RERANKER_MODEL} top_k=${RERANKER_TOP_K}" >&2
