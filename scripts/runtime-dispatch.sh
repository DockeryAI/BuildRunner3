#!/usr/bin/env bash
# scripts/runtime-dispatch.sh — Project-local bash wrapper around the Python
# runtime_registry CLI.
#
# Usage:
#   runtime-dispatch.sh <builder> <spec_path>
#
#   builder:   claude | codex | ollama
#   spec_path: path to a non-empty Markdown spec file
#
# This is DISTINCT from ~/.buildrunner/scripts/runtime-dispatch.sh (infra-level).
# This file shells into `python -m core.runtime.runtime_registry execute` and is
# the canonical in-repo dispatch entrypoint used by scripts/below-route.sh and
# any phase executor.
#
# Exit codes mirror the Python CLI:
#   0 — success
#   2 — unknown builder
#   3 — malformed spec (file not found or empty)
#
# Feature flag: BR3_LOCAL_ROUTING (canonical) — alias BR3_RUNTIME_OLLAMA (deprecated,
# removed next release). When dispatching ollama builder, the flag must be "on".
#
# Phase 2 — cluster-activation build

set -uo pipefail

# ── Locate Python interpreter ────────────────────────────────────────────────
# Prefer the project venv; fall back to system python3.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PYTHON="${BR3_PYTHON:-}"
if [ -z "$PYTHON" ]; then
  if [ -x "$PROJECT_ROOT/.venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python3"
  elif command -v python3 &>/dev/null; then
    PYTHON="python3"
  else
    echo "ERROR: python3 not found. Set BR3_PYTHON to the interpreter path." >&2
    exit 2
  fi
fi

# ── Validate arguments ───────────────────────────────────────────────────────
BUILDER="${1:-}"
SPEC_PATH="${2:-}"

if [ -z "$BUILDER" ] || [ -z "$SPEC_PATH" ]; then
  echo "Usage: $(basename "$0") <builder> <spec_path>" >&2
  echo "  builder:   claude | codex | ollama" >&2
  echo "  spec_path: path to a non-empty Markdown spec file" >&2
  exit 2
fi

# ── Feature flag shim: BR3_RUNTIME_OLLAMA → BR3_LOCAL_ROUTING ───────────────
# BR3_RUNTIME_OLLAMA is the deprecated alias. It is aliased here for one
# release, then will be removed. BR3_LOCAL_ROUTING is canonical.
# See AGENTS.md § Feature flags for removal timeline.
if [ "${BR3_RUNTIME_OLLAMA:-}" = "on" ] && [ "${BR3_LOCAL_ROUTING:-}" != "on" ]; then
  export BR3_LOCAL_ROUTING="on"
fi

# When dispatching ollama builder, BR3_LOCAL_ROUTING must be on.
if [ "$BUILDER" = "ollama" ] && [ "${BR3_LOCAL_ROUTING:-off}" != "on" ]; then
  echo "ERROR: BR3_LOCAL_ROUTING must be 'on' to dispatch ollama builder." >&2
  exit 2
fi

# ── Delegate to Python CLI ───────────────────────────────────────────────────
exec "$PYTHON" -m core.runtime.runtime_registry execute "$BUILDER" "$SPEC_PATH"
