#!/usr/bin/env bash
# scripts/load-role-matrix.sh — Parse the role_matrix YAML block from a BUILD spec
# and export per-phase dispatch variables.
#
# Usage:
#   source scripts/load-role-matrix.sh <build_spec_path> <phase_num>
#   OR:
#   eval "$(scripts/load-role-matrix.sh <build_spec_path> <phase_num>)"
#
# Arguments:
#   build_spec_path  Path to a BUILD_*.md file containing a role_matrix YAML block
#   phase_num        Integer phase number (e.g. 3 for phase_3)
#
# Exports (set on success):
#   BR3_PHASE_BUILDER        claude | codex | below | human
#   BR3_PHASE_CODEX_MODEL    e.g. gpt-5.4 (empty if builder != codex)
#   BR3_PHASE_CODEX_EFFORT   low | medium | high | xhigh (empty if builder != codex)
#   BR3_PHASE_ASSIGNED_NODE  muddy | otis | walter | lomax | below | jimmy | lockwood
#   BR3_PHASE_REVIEWERS      space-separated list of reviewer models
#   BR3_PHASE_ARBITER        arbiter model (or empty)
#   BR3_PHASE_CONTEXT        space-separated list of context paths
#   BR3_ROLE_MATRIX_LOADED   "1" — sentinel that signals successful load
#
# Exit codes:
#   0 — success (exports printed/set)
#   1 — BUILD spec not found or unreadable
#   2 — No role_matrix block found in BUILD spec
#   3 — Phase not found in role_matrix
#   4 — Required field missing (builder or assigned_node)
#
# Idempotent: re-sourcing with the same args is safe (all vars overwritten).
#
# Phase 3 — cluster-activation build

set -uo pipefail

# ── Validate arguments ────────────────────────────────────────────────────────
BUILD_SPEC="${1:-}"
PHASE_NUM="${2:-}"

if [[ -z "$BUILD_SPEC" || -z "$PHASE_NUM" ]]; then
  echo "ERROR [load-role-matrix] Usage: load-role-matrix.sh <build_spec_path> <phase_num>" >&2
  exit 1
fi

if [[ ! -f "$BUILD_SPEC" ]]; then
  echo "ERROR [load-role-matrix] BUILD spec not found: $BUILD_SPEC" >&2
  exit 1
fi

# ── Resolution priority ──────────────────────────────────────────────────────
# 1. Canonical resolved cache phases.phase_N — authored by /spec emitting
#    `role-matrix: inherit: default-role-matrix / overrides: phases: phase_N{...}`.
#    This is the preferred path; fully specified per-phase routing.
# 2. Legacy inline `role_matrix:` YAML block with `phases.phase_N.*` — the
#    cluster-activation / cluster-max pattern that predates phase overrides.
# 3. Heuristic bucket-from-heading fallback — last resort; hardcodes muddy,
#    empty context. Emits a deprecation warning on use.
_HAS_OLD_ROLE_MATRIX=0
if grep -qE '^[[:space:]]*role_matrix:' "$BUILD_SPEC"; then
  _HAS_OLD_ROLE_MATRIX=1
fi

_CANONICAL_LOADER="${HOME}/.buildrunner/scripts/load-role-matrix.sh"
_CANONICAL_CACHE="${HOME}/.buildrunner/config/.resolved-role-matrix.json"

_run_canonical_loader() {
  # Re-resolve the spec into the canonical cache so phases.* is fresh.
  # Safe to fail silently — downstream steps will surface a cache-missing error.
  if [[ -x "$_CANONICAL_LOADER" ]]; then
    "$_CANONICAL_LOADER" "$BUILD_SPEC" >/dev/null 2>&1 || \
      "$_CANONICAL_LOADER" >/dev/null 2>&1 || true
  fi
}

_emit_canonical_phase_entry() {
  # PRIORITY 1: read phases.phase_N directly from the resolved cache.
  # Returns 0 on success (output printed), 2 if cache missing, 3 if phase_N
  # not in the resolved phases map (falls through to other priorities).
  _run_canonical_loader

  if [[ ! -f "$_CANONICAL_CACHE" ]]; then
    return 2
  fi

  python3 - "$_CANONICAL_CACHE" "$PHASE_NUM" <<'PYEOF'
import json, sys
cache_path, phase_num = sys.argv[1], int(sys.argv[2])
with open(cache_path, "r", encoding="utf-8") as fh:
    cache = json.load(fh)
phases = cache.get("phases") or {}
key = f"phase_{phase_num}"
entry = phases.get(key)
if not isinstance(entry, dict):
    sys.exit(3)
builder = entry.get("builder", "") or ""
codex_model = entry.get("codex_model", "") or ""
codex_effort = entry.get("codex_effort", "") or ""
assigned_node = entry.get("assigned_node", "muddy") or "muddy"
reviewers = entry.get("reviewers") or []
arbiter = entry.get("arbiter", "") or ""
context = entry.get("context") or []
bucket = entry.get("bucket", "") or ""
print(f"BR3_PHASE_BUILDER={builder!r}")
print(f"BR3_PHASE_CODEX_MODEL={codex_model!r}")
print(f"BR3_PHASE_CODEX_EFFORT={codex_effort!r}")
print(f"BR3_PHASE_ASSIGNED_NODE={assigned_node!r}")
print(f"BR3_PHASE_REVIEWERS={' '.join(reviewers)!r}")
print(f"BR3_PHASE_ARBITER={arbiter!r}")
print(f"BR3_PHASE_CONTEXT={' '.join(context)!r}")
print(f"BR3_PHASE_BUCKET={bucket!r}")
print(f"BR3_ROLE_MATRIX_LOADED=1")
print(f"BR3_ROLE_MATRIX_SOURCE={'resolved-phases'!r}")
PYEOF
}

_emit_canonical_fallback() {
  # PRIORITY 3: heuristic bucket inference from phase heading keywords.
  # Fires only when neither resolved phases.* nor inline role_matrix: exists.
  _run_canonical_loader

  if [[ ! -f "$_CANONICAL_CACHE" ]]; then
    echo "ERROR [load-role-matrix] canonical role-matrix cache missing: $_CANONICAL_CACHE" >&2
    return 2
  fi

  echo "WARN [load-role-matrix] spec has no phases block — using heuristic bucket inference for phase $PHASE_NUM. Fix: add overrides.phases.phase_$PHASE_NUM.bucket to the spec's role-matrix header." >&2

  # Classify phase into a bucket by scanning the phase section heading for
  # known bucket keywords; default to backend-build if no match.
  local bucket
  bucket="$(python3 - "$BUILD_SPEC" "$PHASE_NUM" "$_CANONICAL_CACHE" <<'PYEOF'
import json, re, sys
spec_path, phase_num, cache_path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
with open(spec_path, "r", encoding="utf-8") as fh:
    body = fh.read()
with open(cache_path, "r", encoding="utf-8") as fh:
    cache = json.load(fh)
buckets = list(cache.get("buckets", {}).keys()) or ["backend-build"]
m = re.search(
    rf'^###\s+Phase\s+{phase_num}:\s*(.*)$', body, re.MULTILINE | re.IGNORECASE
)
header = (m.group(1) if m else "").lower()
bucket_aliases = {
    "planning": ["planner", "inheritance", "spec generator"],
    "architecture": ["architect ", "design", "contract", "source of truth"],
    "terminal-build": [
        "hook", "cli ", "shell", "bats", "terminal",
        "pretooluse", " gate", "boundary", "writer tool",
    ],
    "ui-build": ["ui", "panel", "dashboard", "frontend", "react", "observability"],
    "classification": ["classifier", "front-door"],
    "review": ["cross-model review", "arbiter", "adversarial"],
    "retrieval": ["retriev", "semantic", "embedding"],
    "qa": ["test", " qa", "verification", "rollout", "flip", "enforcement"],
    "backend-build": ["backend", "api", " route", "server", "service", "bundl"],
}
chosen = "backend-build"
for bucket, keywords in bucket_aliases.items():
    if bucket not in buckets:
        continue
    if any(k in header for k in keywords):
        chosen = bucket
        break
print(chosen)
PYEOF
)"
  [[ -z "$bucket" ]] && bucket="backend-build"

  local _OUT
  _OUT="$(python3 - "$_CANONICAL_CACHE" "$bucket" <<'PYEOF'
import json, sys
cache_path, bucket = sys.argv[1], sys.argv[2]
with open(cache_path, "r", encoding="utf-8") as fh:
    cache = json.load(fh)
b = cache.get("buckets", {}).get(bucket) or {}
primary = (b.get("primary") or "").strip()
effort = (b.get("effort") or "").strip()
reviewers = b.get("reviewers") or []
arbiter = (b.get("arbiter") or "").strip()
if primary.startswith("gpt-"):
    builder, model = "codex", primary
elif primary.startswith("claude-"):
    builder, model = "claude", primary
else:
    builder, model = "codex", primary or "gpt-5.4"
codex_model = model if builder == "codex" else ""
codex_effort = effort if builder == "codex" else ""
print(f"BR3_PHASE_BUILDER={builder!r}")
print(f"BR3_PHASE_CODEX_MODEL={codex_model!r}")
print(f"BR3_PHASE_CODEX_EFFORT={codex_effort!r}")
print(f"BR3_PHASE_ASSIGNED_NODE={'muddy'!r}")
print(f"BR3_PHASE_REVIEWERS={' '.join(reviewers)!r}")
print(f"BR3_PHASE_ARBITER={arbiter!r}")
print(f"BR3_PHASE_CONTEXT={''!r}")
print(f"BR3_PHASE_BUCKET={bucket!r}")
print(f"BR3_ROLE_MATRIX_LOADED=1")
print(f"BR3_ROLE_MATRIX_SOURCE={'canonical-fallback'!r}")
PYEOF
)"
  printf '%s\n' "$_OUT"
  return 0
}

_emit_result() {
  # Given $_EXTRACT_OUTPUT (newline-separated KEY=value assignments),
  # either eval-export (when sourced) or prefix with `export ` (when executed).
  if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    eval "$_EXTRACT_OUTPUT"
    export BR3_PHASE_BUILDER BR3_PHASE_CODEX_MODEL BR3_PHASE_CODEX_EFFORT
    export BR3_PHASE_ASSIGNED_NODE BR3_PHASE_REVIEWERS BR3_PHASE_ARBITER
    export BR3_PHASE_CONTEXT BR3_PHASE_BUCKET BR3_ROLE_MATRIX_LOADED BR3_ROLE_MATRIX_SOURCE
  else
    while IFS= read -r line; do
      echo "export $line"
    done <<< "$_EXTRACT_OUTPUT"
  fi
}

# ── PRIORITY 1: resolved cache phases.phase_N (new canonical) ────────────────
if _EXTRACT_OUTPUT="$(_emit_canonical_phase_entry)"; then
  _PRIORITY_1_EXIT=0
else
  _PRIORITY_1_EXIT=$?
fi

if [[ $_PRIORITY_1_EXIT -eq 0 && -n "$_EXTRACT_OUTPUT" ]]; then
  _emit_result
  return 0 2>/dev/null || exit 0
fi

# Priority 1 missed (exit 2 = cache missing, 3 = phase not in phases.*).
# Fall through to priority 2 (legacy inline) or priority 3 (heuristic).

if [[ "$_HAS_OLD_ROLE_MATRIX" -eq 0 ]]; then
  # ── PRIORITY 3: heuristic fallback (no inline, no resolved phases) ─────────
  if _EXTRACT_OUTPUT="$(_emit_canonical_fallback)"; then
    _EXIT=0
  else
    _EXIT=$?
  fi

  if [[ $_EXIT -ne 0 ]]; then
    exit $_EXIT
  fi

  _emit_result
  return 0 2>/dev/null || exit 0
fi

# ── PRIORITY 2: legacy inline `role_matrix:` YAML block ─────────────────────
# Parses the cluster-activation / cluster-max pattern. Deprecated in favor of
# overrides.phases.phase_N in the spec header — emits a one-line notice.
echo "NOTE [load-role-matrix] parsing legacy inline role_matrix: block in $BUILD_SPEC (phase $PHASE_NUM). Prefer the resolved overrides.phases.* path. Run ~/.buildrunner/scripts/migrate-inline-role-matrix.py to convert." >&2

_EXTRACT_OUTPUT=$(python3 - "$BUILD_SPEC" "$PHASE_NUM" <<'PYEOF'
import sys, re

build_spec_path = sys.argv[1]
phase_num = int(sys.argv[2])

with open(build_spec_path, 'r') as fh:
    content = fh.read()

# Find the yaml code block containing the role_matrix key.
# The block is inside a markdown ```yaml ... ``` fence.
yaml_blocks = re.findall(r'```yaml\s*\n(.*?)```', content, re.DOTALL)
role_matrix_yaml = None
for block in yaml_blocks:
    if 'role_matrix:' in block:
        role_matrix_yaml = block
        break

if not role_matrix_yaml:
    print("ERROR: No role_matrix block found in BUILD spec", file=sys.stderr)
    sys.exit(2)

# Parse the YAML using stdlib (avoid requiring PyYAML in every env)
try:
    import yaml  # type: ignore
    data = yaml.safe_load(role_matrix_yaml)
except ImportError:
    # Fallback: minimal YAML parser for the subset we need
    # (handles the role_matrix structure without requiring pyyaml)
    import re as _re

    def _parse_simple_yaml(text):
        """Parse simple YAML subset: nested mappings and lists."""
        lines = text.splitlines()
        result = {}
        stack = [(result, -1)]

        def get_parent(indent):
            while len(stack) > 1 and stack[-1][1] >= indent:
                stack.pop()
            return stack[-1][0]

        for line in lines:
            if not line.strip() or line.strip().startswith('#'):
                continue
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if stripped.startswith('- '):
                # List item
                parent = get_parent(indent)
                val = stripped[2:].strip()
                if isinstance(parent, list):
                    parent.append(val)
                else:
                    # Convert last key to list
                    for k, v in reversed(list(parent.items())):
                        if v is None:
                            parent[k] = [val]
                            stack.append((parent[k], indent))
                            break
            elif ':' in stripped:
                key, _, rest = stripped.partition(':')
                key = key.strip()
                val = rest.strip()
                parent = get_parent(indent)
                if isinstance(parent, dict):
                    if val:
                        # Handle inline list [a, b, c]
                        if val.startswith('[') and val.endswith(']'):
                            items = [x.strip().strip("'\"") for x in val[1:-1].split(',')]
                            parent[key] = items
                        else:
                            parent[key] = val.strip("'\"")
                    else:
                        parent[key] = None
                        stack.append((parent, indent))
                        new_dict = {}
                        parent[key] = new_dict
                        stack.append((new_dict, indent))
        return result

    data = _parse_simple_yaml(role_matrix_yaml)

if not isinstance(data, dict) or 'role_matrix' not in data:
    print("ERROR: role_matrix key not found after YAML parse", file=sys.stderr)
    sys.exit(2)

rm = data['role_matrix']
phases = rm.get('phases', {})

phase_key = f'phase_{phase_num}'
if phase_key not in phases:
    print(f"ERROR: Phase '{phase_key}' not found in role_matrix. Available: {list(phases.keys())}", file=sys.stderr)
    sys.exit(3)

p = phases[phase_key]

builder = p.get('builder', '').strip()
if not builder:
    print(f"ERROR: 'builder' field missing for {phase_key}", file=sys.stderr)
    sys.exit(4)

assigned_node = p.get('assigned_node', '').strip()
if not assigned_node:
    print(f"ERROR: 'assigned_node' field missing for {phase_key}", file=sys.stderr)
    sys.exit(4)

codex_model = p.get('codex_model', '') or ''
codex_effort = p.get('codex_effort', '') or ''

reviewers = p.get('reviewers', []) or []
if isinstance(reviewers, str):
    reviewers = [r.strip() for r in reviewers.split(',')]

arbiter = p.get('arbiter', '') or ''

context = p.get('context', []) or []
if isinstance(context, str):
    context = [c.strip() for c in context.split(',')]

bucket = p.get('bucket', '') or ''

# Print shell variable assignments (safe for eval / source)
print(f'BR3_PHASE_BUILDER={builder!r}')
print(f'BR3_PHASE_CODEX_MODEL={codex_model!r}')
print(f'BR3_PHASE_CODEX_EFFORT={codex_effort!r}')
print(f'BR3_PHASE_ASSIGNED_NODE={assigned_node!r}')
print(f'BR3_PHASE_REVIEWERS={" ".join(reviewers)!r}')
print(f'BR3_PHASE_ARBITER={arbiter!r}')
print(f'BR3_PHASE_CONTEXT={" ".join(context)!r}')
print(f'BR3_PHASE_BUCKET={bucket!r}')
print(f'BR3_ROLE_MATRIX_LOADED=1')
print(f'BR3_ROLE_MATRIX_SOURCE={"inline-legacy"!r}')

PYEOF
)
_EXIT=$?

if [[ $_EXIT -ne 0 ]]; then
  # Errors already printed to stderr by Python
  exit $_EXIT
fi

# ── Emit or eval the exports ──────────────────────────────────────────────────
# When sourced directly (. ./load-role-matrix.sh ...) the eval below sets vars
# in the caller's environment.  When executed standalone it prints export lines.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  # Being sourced — eval assignments directly
  eval "$_EXTRACT_OUTPUT"
  export BR3_PHASE_BUILDER BR3_PHASE_CODEX_MODEL BR3_PHASE_CODEX_EFFORT
  export BR3_PHASE_ASSIGNED_NODE BR3_PHASE_REVIEWERS BR3_PHASE_ARBITER
  export BR3_PHASE_CONTEXT BR3_PHASE_BUCKET BR3_ROLE_MATRIX_LOADED BR3_ROLE_MATRIX_SOURCE
else
  # Being executed — print as export statements for eval
  while IFS= read -r line; do
    echo "export $line"
  done <<< "$_EXTRACT_OUTPUT"
fi
