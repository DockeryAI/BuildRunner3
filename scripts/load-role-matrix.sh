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

# ── Python extractor ─────────────────────────────────────────────────────────
# Uses Python to parse the YAML block from the BUILD spec Markdown.
# The block is fenced in ```yaml ... ``` under the "Role Matrix" section.
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

# Print shell variable assignments (safe for eval / source)
print(f'BR3_PHASE_BUILDER={builder!r}')
print(f'BR3_PHASE_CODEX_MODEL={codex_model!r}')
print(f'BR3_PHASE_CODEX_EFFORT={codex_effort!r}')
print(f'BR3_PHASE_ASSIGNED_NODE={assigned_node!r}')
print(f'BR3_PHASE_REVIEWERS={" ".join(reviewers)!r}')
print(f'BR3_PHASE_ARBITER={arbiter!r}')
print(f'BR3_PHASE_CONTEXT={" ".join(context)!r}')
print(f'BR3_ROLE_MATRIX_LOADED=1')

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
  export BR3_PHASE_CONTEXT BR3_ROLE_MATRIX_LOADED
else
  # Being executed — print as export statements for eval
  while IFS= read -r line; do
    echo "export $line"
  done <<< "$_EXTRACT_OUTPUT"
fi
