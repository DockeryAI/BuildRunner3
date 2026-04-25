#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/.buildrunner"
LOG_FILE="${BUILD_DIR}/godot.log"
GODOT_BIN="${GODOT_BIN:-godot4}"

mkdir -p "${BUILD_DIR}"

project_name="$(sed -n 's/^config\/name=//p' "${PROJECT_ROOT}/project.godot" | head -n 1 | tr -d '"')"
if [[ -z "${project_name}" ]]; then
  project_name="$(basename "${PROJECT_ROOT}")"
fi

# TODO: extend user:// resolution for Linux and Windows installs.
user_logs_dir="${HOME}/Library/Application Support/Godot/app_userdata/${project_name}/logs"
copied_logs_dir="${BUILD_DIR}/godot-user-logs"

echo "==> running Godot project ${project_name}" | tee -a "${LOG_FILE}"
"${GODOT_BIN}" --path "${PROJECT_ROOT}" "$@" 2>&1 | tee -a "${LOG_FILE}"
exit_code=${PIPESTATUS[0]}

if [[ ${exit_code} -ne 0 ]]; then
  printf '\n===== GODOT CRASH BANNER (exit %s) =====\n' "${exit_code}" | tee -a "${LOG_FILE}"
fi

if [[ -d "${user_logs_dir}" ]]; then
  rm -rf "${copied_logs_dir}"
  mkdir -p "${copied_logs_dir}"
  cp -R "${user_logs_dir}/." "${copied_logs_dir}/"
else
  echo "user:// logs not found at ${user_logs_dir}" | tee -a "${LOG_FILE}"
fi

exit "${exit_code}"
