#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/srv/jimmy/backups"
LOG_FILE="$BACKUP_DIR/nightly.log"
ARCHIVE_PATH="$BACKUP_DIR/$(date +%F).tar.zst"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--dry-run]" >&2
  exit 1
fi

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  local message="$1"
  local line
  line="[$(timestamp)] $message"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    printf '%s\n' "$line" >> "$LOG_FILE"
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '%s\n' "$line"
  fi
}

run() {
  local description="$1"
  shift

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "[DRY] $description"
    return 0
  fi

  log "$description"
  "$@" >> "$LOG_FILE" 2>&1
}

if [[ "$DRY_RUN" -eq 0 ]]; then
  mkdir -p "$BACKUP_DIR"
  touch "$LOG_FILE"
fi

log "nightly backup start"
run "creating archive $ARCHIVE_PATH from /srv/jimmy/research-library and /srv/jimmy/lancedb" \
  tar -I 'zstd -T0 --long' -cf "$ARCHIVE_PATH" -C /srv/jimmy research-library lancedb
run "pushing /srv/jimmy/research-library to muddy remote (Muddy will mirror to GitHub on its next sync)" \
  git -C /srv/jimmy/research-library push muddy main
run "deleting backup archives older than 14 days from $BACKUP_DIR" \
  find "$BACKUP_DIR" -maxdepth 1 -name '*.tar.zst' -mtime +14 -delete
log "nightly backup complete"
