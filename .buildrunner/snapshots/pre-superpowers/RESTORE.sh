#!/bin/bash
# Restore all BR3 commands/docs to pre-superpowers state
# Usage: bash .buildrunner/snapshots/pre-superpowers/RESTORE.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Restoring BR3 commands and docs to pre-superpowers state..."

# Restore commands
cp "$SCRIPT_DIR/commands/"*.md ~/.claude/commands/
echo "  Restored $(ls "$SCRIPT_DIR/commands/"*.md | wc -l | tr -d ' ') commands"

# Restore docs
cp "$SCRIPT_DIR/docs/"*.md ~/.claude/docs/
echo "  Restored $(ls "$SCRIPT_DIR/docs/"*.md | wc -l | tr -d ' ') docs"

# Restore .bak files if present
cp "$SCRIPT_DIR/commands/"*.bak ~/.claude/commands/ 2>/dev/null
cp "$SCRIPT_DIR/docs/"*.bak ~/.claude/docs/ 2>/dev/null

echo "Done. BR3 skills restored to pre-superpowers snapshot."
