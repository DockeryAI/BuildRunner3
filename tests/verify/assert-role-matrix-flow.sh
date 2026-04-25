#!/usr/bin/env bash
set -euo pipefail

LOG_PATH="${1:-}"

if [[ -z "$LOG_PATH" ]]; then
  echo "Usage: $0 <decisions.log>" >&2
  exit 2
fi

if [[ ! -f "$LOG_PATH" ]]; then
  echo "ERROR: decisions.log not found: $LOG_PATH" >&2
  exit 2
fi

count_dispatch_builder() {
  local phase="$1"
  local builder="$2"
  grep -Ec "dispatch: phase=${phase} builder=${builder}( |$)" "$LOG_PATH"
}

phase1_builder_count="$(count_dispatch_builder 1 codex)"
phase2_builder_count="$(count_dispatch_builder 2 codex)"

if [[ "$phase1_builder_count" -ne 1 ]]; then
  echo "ERROR: expected exactly one codex dispatch for phase 1, found $phase1_builder_count" >&2
  exit 1
fi

if [[ "$phase2_builder_count" -ne 1 ]]; then
  echo "ERROR: expected exactly one codex dispatch for phase 2, found $phase2_builder_count" >&2
  exit 1
fi

if ! grep -Eq "phase-review build=.* phase=1 revision=0 verdict=approve" "$LOG_PATH"; then
  echo "ERROR: phase 1 approve verdict missing" >&2
  exit 1
fi

if ! grep -Eq "phase-review build=.* phase=2 revision=0 verdict=reject" "$LOG_PATH"; then
  echo "ERROR: phase 2 initial reject missing" >&2
  exit 1
fi

if grep -Eq "phase-review build=.* phase=2 revision=1 verdict=approve" "$LOG_PATH"; then
  exit 0
fi

if grep -Eq "phase-review build=.* phase=2 revision=1 verdict=arbiter-(approve|reject)" "$LOG_PATH"; then
  exit 0
fi

echo "ERROR: phase 2 is missing the revision-1 terminal verdict (approve or arbiter-*)" >&2
exit 1
