#!/bin/bash
# BuildRunner 3.0 - Supabase Log Activation
# Detects Vite + Supabase projects and injects supalog components.
# Called by activate-all-systems.sh or run standalone:
#   bash activate-supalog.sh /path/to/project

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_PATH="${1:-$(pwd)}"
cd "$PROJECT_PATH"

# Find BR3 components source
BR3_COMPONENTS=""
for loc in \
    "$HOME/.buildrunner/components" \
    "/Users/byronhudson/.buildrunner/components"; do
    if [ -f "$loc/vite-supabase-log-plugin.ts" ] && [ -f "$loc/supabaseLogger.ts" ]; then
        BR3_COMPONENTS="$loc"
        break
    fi
done

if [ -z "$BR3_COMPONENTS" ]; then
    echo -e "  ${RED}✗${NC} Supabase log components not found in ~/.buildrunner/components/"
    exit 1
fi

# ── Detection ────────────────────────────────────────────
HAS_VITE=false
HAS_SUPABASE=false
VITE_CONFIG=""

# Find vite config (project root or common subdirs)
for cfg in \
    "$PROJECT_PATH/vite.config.ts" \
    "$PROJECT_PATH/vite.config.js" \
    "$PROJECT_PATH/ui/vite.config.ts" \
    "$PROJECT_PATH/web/vite.config.ts" \
    "$PROJECT_PATH/app/vite.config.ts"; do
    if [ -f "$cfg" ]; then
        VITE_CONFIG="$cfg"
        HAS_VITE=true
        break
    fi
done

# Find supabase dependency
for pkg in \
    "$PROJECT_PATH/package.json" \
    "$PROJECT_PATH/ui/package.json" \
    "$PROJECT_PATH/web/package.json" \
    "$PROJECT_PATH/app/package.json"; do
    if [ -f "$pkg" ] && grep -q "@supabase/supabase-js" "$pkg" 2>/dev/null; then
        HAS_SUPABASE=true
        break
    fi
done

# ── Skip if not Vite+Supabase ───────────────────────────
if [ "$HAS_VITE" = false ] || [ "$HAS_SUPABASE" = false ]; then
    if [ "$HAS_VITE" = false ]; then
        echo -e "  ${BLUE}ℹ${NC}  No vite.config found — skipping supalog"
    else
        echo -e "  ${BLUE}ℹ${NC}  No @supabase/supabase-js dependency — skipping supalog"
    fi
    exit 0
fi

echo -e "  ${GREEN}✓${NC} Detected Vite + Supabase project"

# ── Determine component destination ─────────────────────
# Components go alongside existing BR3 components
VITE_DIR="$(dirname "$VITE_CONFIG")"
COMP_DIR="$VITE_DIR/.buildrunner/components"
mkdir -p "$COMP_DIR"

# ── Copy components ──────────────────────────────────────
PLUGIN_DEST="$COMP_DIR/vite-supabase-log-plugin.ts"
LOGGER_DEST="$COMP_DIR/supabaseLogger.ts"

# Only copy if missing or outdated
if [ ! -f "$PLUGIN_DEST" ] || ! diff -q "$BR3_COMPONENTS/vite-supabase-log-plugin.ts" "$PLUGIN_DEST" > /dev/null 2>&1; then
    cp "$BR3_COMPONENTS/vite-supabase-log-plugin.ts" "$PLUGIN_DEST"
    echo -e "  ${GREEN}✓${NC} Copied vite-supabase-log-plugin.ts"
else
    echo -e "  ${BLUE}ℹ${NC}  vite-supabase-log-plugin.ts already up to date"
fi

if [ ! -f "$LOGGER_DEST" ] || ! diff -q "$BR3_COMPONENTS/supabaseLogger.ts" "$LOGGER_DEST" > /dev/null 2>&1; then
    cp "$BR3_COMPONENTS/supabaseLogger.ts" "$LOGGER_DEST"
    echo -e "  ${GREEN}✓${NC} Copied supabaseLogger.ts"
else
    echo -e "  ${BLUE}ℹ${NC}  supabaseLogger.ts already up to date"
fi

# ── Inject Vite plugin import + usage ────────────────────
# Check if already injected
if grep -q "supabaseLogPlugin" "$VITE_CONFIG" 2>/dev/null; then
    echo -e "  ${BLUE}ℹ${NC}  supabaseLogPlugin already in vite.config.ts"
else
    # Determine relative import path from vite config to component
    VITE_CONFIG_DIR="$(dirname "$VITE_CONFIG")"
    REL_PATH="$(python3 -c "import os.path; print(os.path.relpath('$PLUGIN_DEST', '$VITE_CONFIG_DIR'))" 2>/dev/null || echo "./.buildrunner/components/vite-supabase-log-plugin")"
    # Remove .ts extension for import
    REL_IMPORT="${REL_PATH%.ts}"
    # Ensure starts with ./
    [[ "$REL_IMPORT" != ./* ]] && REL_IMPORT="./$REL_IMPORT"

    # Add import line after last existing import
    LAST_IMPORT_LINE=$(grep -n "^import " "$VITE_CONFIG" | tail -1 | cut -d: -f1)
    if [ -n "$LAST_IMPORT_LINE" ]; then
        sed -i '' "${LAST_IMPORT_LINE}a\\
import { supabaseLogPlugin } from '${REL_IMPORT}';
" "$VITE_CONFIG"
        echo -e "  ${GREEN}✓${NC} Added supabaseLogPlugin import to vite.config.ts"
    fi

    # Add plugin to plugins array — insert after existing plugins
    # Find "plugins: [" and add supabaseLogPlugin() after the last existing plugin call
    if grep -q "plugins:" "$VITE_CONFIG"; then
        # Add supabaseLogPlugin() to the plugins array
        sed -i '' 's/\(brLoggerPlugin()\)/\1, supabaseLogPlugin()/' "$VITE_CONFIG" 2>/dev/null || \
        sed -i '' 's/\(react()\)/\1, supabaseLogPlugin()/' "$VITE_CONFIG" 2>/dev/null
        echo -e "  ${GREEN}✓${NC} Added supabaseLogPlugin() to plugins array"
    fi
fi

# ── Ensure .gitignore excludes supabase.log ──────────────
GITIGNORE_FILE="$VITE_DIR/.gitignore"
if [ -f "$GITIGNORE_FILE" ]; then
    if ! grep -q "supabase.log" "$GITIGNORE_FILE" 2>/dev/null; then
        # Check if *.log already covers it
        if ! grep -q "^\*\.log$" "$GITIGNORE_FILE" 2>/dev/null; then
            echo "" >> "$GITIGNORE_FILE"
            echo "# BR3 Supabase logs" >> "$GITIGNORE_FILE"
            echo ".buildrunner/supabase.log" >> "$GITIGNORE_FILE"
            echo -e "  ${GREEN}✓${NC} Added supabase.log to .gitignore"
        else
            echo -e "  ${BLUE}ℹ${NC}  *.log in .gitignore already covers supabase.log"
        fi
    else
        echo -e "  ${BLUE}ℹ${NC}  supabase.log already in .gitignore"
    fi
fi

# ── Report ───────────────────────────────────────────────
echo -e "  ${GREEN}✓${NC} Supabase log system activated"
echo -e "  ${BLUE}ℹ${NC}  Logs write to: .buildrunner/supabase.log"
echo -e "  ${BLUE}ℹ${NC}  Auto-rotation at 500KB"
echo -e "  ${BLUE}ℹ${NC}  Debug with: /sdb"
echo ""
echo -e "  ${YELLOW}⚠${NC}  MANUAL STEP: Add instrumented fetch to your Supabase client."
echo -e "     Import from .buildrunner/components/supabaseLogger.ts:"
echo -e "       import { createInstrumentedFetch, logEvent } from '...supabaseLogger'"
echo -e "     Then in createClient options:"
echo -e "       global: { fetch: import.meta.env.DEV ? createInstrumentedFetch(fetch, url) : undefined }"
