#!/bin/bash
# install-phase5.sh — Install Phase 5 Codex power features
# Run this script to install /2nd and /codex-do skills

set -e

STAGING_DIR="$(dirname "$0")"
SKILLS_DIR="$HOME/.claude/skills"

echo "Installing Phase 5: Codex Power Features..."

# Create skill directories
mkdir -p "$SKILLS_DIR/2nd"
mkdir -p "$SKILLS_DIR/codex-do"

# Install /2nd skill
cp "$STAGING_DIR/2nd-SKILL.md" "$SKILLS_DIR/2nd/SKILL.md"
echo "  Installed: /2nd skill"

# Install /codex-do skill
cp "$STAGING_DIR/codex-do-SKILL.md" "$SKILLS_DIR/codex-do/SKILL.md"
echo "  Installed: /codex-do skill"

# Create codex-briefs directory
mkdir -p "$HOME/Projects/BuildRunner3/.buildrunner/codex-briefs"
echo "  Created: .buildrunner/codex-briefs/"

echo ""
echo "Skills installed. Manual step required:"
echo ""
echo "  Add Step 3.4 (Plan Critique Gate) to ~/.claude/commands/begin.md"
echo "  See: $STAGING_DIR/begin-plan-critique-patch.md"
echo ""
echo "Done."
