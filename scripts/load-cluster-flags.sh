#!/usr/bin/env bash
# scripts/load-cluster-flags.sh — Source ~/.buildrunner/config/feature-flags.yaml
# and export all BR3_* cluster feature flags as environment variables.
#
# Usage:
#   source scripts/load-cluster-flags.sh
#   OR (for eval):
#   eval "$(scripts/load-cluster-flags.sh)"
#
# Exports one env var per flag entry:
#   BR3_<FLAG_NAME>   "on" | "off"  (exact value from feature-flags.yaml default field)
#
# Additional sentinels:
#   BR3_FLAGS_LOADED   "1" — set after a successful load
#   BR3_FLAGS_FILE     path to the feature-flags.yaml that was loaded
#
# Idempotent: safe to re-source; all vars are overwritten on each call.
# BR3_CLUSTER=off disables all cluster access — when set, this script still
# exports flags (they may be checked independently) but marks BR3_FLAGS_LOADED.
#
# Exit codes:
#   0 — success (all flags exported)
#   1 — feature-flags.yaml not found (BR3_FLAGS_LOADED remains unset)
#
# Canonical flag: BR3_LOCAL_ROUTING. BR3_RUNTIME_OLLAMA alias removed 2026-04-23.
#
# Phase 3 — cluster-activation build

# ── Locate feature-flags.yaml ─────────────────────────────────────────────────
_FLAGS_CANDIDATES=(
  "${BR3_FLAGS_FILE:-}"
  "$HOME/.buildrunner/config/feature-flags.yaml"
  "$HOME/.buildrunner/feature-flags.yaml"
)

_FLAGS_PATH=""
for _candidate in "${_FLAGS_CANDIDATES[@]}"; do
  if [[ -n "$_candidate" && -f "$_candidate" ]]; then
    _FLAGS_PATH="$_candidate"
    break
  fi
done

if [[ -z "$_FLAGS_PATH" ]]; then
  echo "WARN [load-cluster-flags] feature-flags.yaml not found — cluster flags not loaded" >&2
  exit 1
fi

# ── Parse with Python (handles YAML safely) ───────────────────────────────────
_FLAG_OUTPUT=$(python3 - "$_FLAGS_PATH" <<'PYEOF'
import sys

flags_path = sys.argv[1]

with open(flags_path, 'r') as fh:
    content = fh.read()

# Parse YAML using stdlib when available, fallback to regex
try:
    import yaml  # type: ignore
    data = yaml.safe_load(content)
except ImportError:
    import re
    # Minimal parser: extract flag name + default value
    data = {'flags': {}}
    current_flag = None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # Top-level flag key (2-space indent + key:)
        m = re.match(r'^  ([A-Z_][A-Z0-9_]+):\s*$', line)
        if m:
            current_flag = m.group(1)
            data['flags'][current_flag] = {}
            continue
        # default: field (4-space indent)
        m2 = re.match(r'^    default:\s*(\S+)', line)
        if m2 and current_flag:
            data['flags'][current_flag]['default'] = m2.group(1)

flags = data.get('flags', {})
if not flags:
    print("WARN: No flags found in feature-flags.yaml", file=sys.stderr)

for flag_name, flag_data in flags.items():
    default_val = flag_data.get('default', 'off')
    # Normalize: true/yes/1 → on, false/no/0 → off
    if str(default_val).lower() in ('true', 'yes', '1', 'on'):
        val = 'on'
    else:
        val = 'off'
    print(f'{flag_name}={val!r}')

PYEOF
)
_EXIT=$?

if [[ $_EXIT -ne 0 ]]; then
  echo "ERROR [load-cluster-flags] Failed to parse feature-flags.yaml" >&2
  exit 1
fi

# ── Emit or eval ──────────────────────────────────────────────────────────────
_do_export() {
  while IFS= read -r _line; do
    [[ -z "$_line" ]] && continue
    # Evaluate the assignment so the variable is set
    eval "$_line"
    # Re-export each flag name
    _flag_name="${_line%%=*}"
    export "$_flag_name" 2>/dev/null || true
  done <<< "$_FLAG_OUTPUT"

  BR3_FLAGS_LOADED=1
  BR3_FLAGS_FILE="$_FLAGS_PATH"
  export BR3_FLAGS_LOADED BR3_FLAGS_FILE
}

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  # Being sourced — set vars in caller's environment
  _do_export
else
  # Being executed — print export statements
  while IFS= read -r _line; do
    [[ -z "$_line" ]] && continue
    echo "export $_line"
  done <<< "$_FLAG_OUTPUT"
  echo "export BR3_FLAGS_LOADED=1"
  echo "export BR3_FLAGS_FILE='$_FLAGS_PATH'"
fi
