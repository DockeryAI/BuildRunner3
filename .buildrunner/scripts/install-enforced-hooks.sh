#!/bin/bash
# install-enforced-hooks.sh — BR3 Enforced Git Hook Installer
# Installs pre-commit-enforced + pre-push-enforced + pre-push.d/50-ship-gate.sh
# into a project's .git/hooks directory.
#
# Usage: install-enforced-hooks.sh [project-path]
#        If no path provided, installs in current directory.
#
# NOTE: Enforced hooks only — there is no --standard mode.
# Both pre-commit and pre-push are enforced; no bypass variants are installed.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "🔒 BR3 Enforced Hook Installer"
echo "==============================="
echo ""

# Determine target project
if [ -n "${1:-}" ]; then
    PROJECT_PATH="$1"
else
    PROJECT_PATH="$(pwd)"
fi

cd "$PROJECT_PATH"

if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Not a git repository: $PROJECT_PATH${NC}"
    exit 1
fi

# Find BR3 hooks source directory
BR3_HOOKS_DIR=""
for loc in \
    "$(dirname "${BASH_SOURCE[0]}")/../hooks" \
    "/Users/byronhudson/Projects/BuildRunner3/.buildrunner/hooks" \
    "$PROJECT_PATH/.buildrunner/hooks" \
    "$PROJECT_PATH/../BuildRunner3/.buildrunner/hooks"; do
    expanded_loc="$(cd "$loc" 2>/dev/null && pwd || echo "")"
    if [ -n "$expanded_loc" ] && [ -f "$expanded_loc/pre-commit-enforced" ]; then
        BR3_HOOKS_DIR="$expanded_loc"
        break
    fi
done

if [ -z "$BR3_HOOKS_DIR" ]; then
    echo -e "${RED}❌ Could not find BR3 hooks directory (looking for pre-commit-enforced)${NC}"
    exit 1
fi

PROJECT_NAME=$(basename "$PROJECT_PATH")
echo "📂 Installing enforced hooks for: $PROJECT_NAME"
echo "   Source hooks: $BR3_HOOKS_DIR"
echo ""

mkdir -p "$PROJECT_PATH/.git/hooks"

# ── Install pre-commit (enforced only) ────────────────────────────────────────
echo "📦 Installing pre-commit hook (enforced)..."
if [ -f "$PROJECT_PATH/.git/hooks/pre-commit" ] && [ ! -L "$PROJECT_PATH/.git/hooks/pre-commit" ]; then
    echo -e "   ${YELLOW}⚠️  Existing pre-commit found (backing up)${NC}"
    mv "$PROJECT_PATH/.git/hooks/pre-commit" "$PROJECT_PATH/.git/hooks/pre-commit.backup.$(date +%Y%m%d_%H%M%S)"
fi
cp "$BR3_HOOKS_DIR/pre-commit-enforced" "$PROJECT_PATH/.git/hooks/pre-commit"
chmod +x "$PROJECT_PATH/.git/hooks/pre-commit"
echo -e "   ${GREEN}✅ pre-commit (enforced) installed${NC}"

# ── Install pre-push (enforced only) ──────────────────────────────────────────
echo "📦 Installing pre-push hook (enforced)..."
if [ -f "$PROJECT_PATH/.git/hooks/pre-push" ] && [ ! -L "$PROJECT_PATH/.git/hooks/pre-push" ]; then
    echo -e "   ${YELLOW}⚠️  Existing pre-push found (backing up)${NC}"
    mv "$PROJECT_PATH/.git/hooks/pre-push" "$PROJECT_PATH/.git/hooks/pre-push.backup.$(date +%Y%m%d_%H%M%S)"
fi
cp "$BR3_HOOKS_DIR/pre-push-enforced" "$PROJECT_PATH/.git/hooks/pre-push"
chmod +x "$PROJECT_PATH/.git/hooks/pre-push"
echo -e "   ${GREEN}✅ pre-push (enforced) installed${NC}"

# ── Install pre-push.d fragments (ship gate) ──────────────────────────────────
PREPUSH_D_SRC="${BR3_HOOKS_DIR}/pre-push.d"
if [ -d "$PREPUSH_D_SRC" ]; then
    echo "📦 Installing pre-push.d fragments..."
    TARGET_PREPUSHD="${PROJECT_PATH}/.git/hooks/pre-push.d"
    mkdir -p "$TARGET_PREPUSHD"
    for fragment in "$PREPUSH_D_SRC"/*.sh; do
        [ -f "$fragment" ] || continue
        fname="$(basename "$fragment")"
        if [ ! -f "${TARGET_PREPUSHD}/${fname}" ] || ! diff -q "$fragment" "${TARGET_PREPUSHD}/${fname}" > /dev/null 2>&1; then
            cp "$fragment" "${TARGET_PREPUSHD}/${fname}"
            chmod +x "${TARGET_PREPUSHD}/${fname}"
            echo -e "   ${GREEN}✅ pre-push.d/${fname} installed${NC}"
        else
            echo -e "   ℹ️  pre-push.d/${fname} unchanged"
        fi
    done
fi

echo ""
echo "================================="
echo -e "${GREEN}✅ Enforced hooks installed!${NC}"
echo ""
echo "🔒 Enforcement Status:"
echo "   - Pre-commit: BR3 enforced checks run before EVERY commit"
echo "   - Pre-push: Enforced checks + /ship gate run before EVERY push"
echo "   - 50-ship-gate.sh: auto-appended via pre-push.d/"
echo "   - No bypass variants installed"
echo ""
