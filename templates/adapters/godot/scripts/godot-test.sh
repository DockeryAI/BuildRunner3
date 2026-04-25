#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/.buildrunner"
LOG_FILE="${BUILD_DIR}/gut.log"
GODOT_BIN="${GODOT_BIN:-godot4}"
GUT_ENTRYPOINT="${PROJECT_ROOT}/addons/gut/gut_cmdln.gd"

mkdir -p "${BUILD_DIR}"

if [[ ! -f "${GUT_ENTRYPOINT}" ]]; then
  echo "GUT not installed; skipping headless test run." | tee -a "${LOG_FILE}"
  exit 0
fi

"${GODOT_BIN}" --headless --path "${PROJECT_ROOT}" -s "${GUT_ENTRYPOINT}" "$@" 2>&1 | tee -a "${LOG_FILE}"
exit "${PIPESTATUS[0]}"
