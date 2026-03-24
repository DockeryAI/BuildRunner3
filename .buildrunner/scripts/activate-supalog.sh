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

# ── Detect non-Vite project types ─────────────────────────
HAS_RN=false
HAS_ELECTRON=false
HAS_FLUTTER=false
HAS_NODE_BACKEND=false
HAS_DENO=false
HAS_SWIFT=false
HAS_KOTLIN=false
HAS_TAURI=false
HAS_CAPACITOR=false

[ -f "$PROJECT_PATH/package.json" ] && grep -q '"react-native"' "$PROJECT_PATH/package.json" 2>/dev/null && HAS_RN=true
[ -f "$PROJECT_PATH/package.json" ] && grep -q '"electron"' "$PROJECT_PATH/package.json" 2>/dev/null && HAS_ELECTRON=true
[ -f "$PROJECT_PATH/package.json" ] && grep -q '"@capacitor/core"' "$PROJECT_PATH/package.json" 2>/dev/null && HAS_CAPACITOR=true
[ -f "$PROJECT_PATH/pubspec.yaml" ] && HAS_FLUTTER=true
([ -f "$PROJECT_PATH/tauri.conf.json" ] || [ -f "$PROJECT_PATH/src-tauri/tauri.conf.json" ]) && HAS_TAURI=true
([ -f "$PROJECT_PATH/deno.json" ] || [ -f "$PROJECT_PATH/deno.jsonc" ]) && HAS_DENO=true
(ls "$PROJECT_PATH"/*.xcodeproj > /dev/null 2>&1 || [ -f "$PROJECT_PATH/Package.swift" ]) && HAS_SWIFT=true
(grep -rql "com.android" "$PROJECT_PATH/build.gradle"* "$PROJECT_PATH/app/build.gradle"* 2>/dev/null) && HAS_KOTLIN=true
[ -f "$PROJECT_PATH/package.json" ] && ! grep -q '"react"' "$PROJECT_PATH/package.json" 2>/dev/null && grep -qE '"express"|"fastify"|"koa"|"hapi"|"nestjs"' "$PROJECT_PATH/package.json" 2>/dev/null && HAS_NODE_BACKEND=true

# Check if any supported project type detected
HAS_ANY=false
for flag in "$HAS_VITE" "$HAS_RN" "$HAS_ELECTRON" "$HAS_FLUTTER" "$HAS_NODE_BACKEND" "$HAS_DENO" "$HAS_SWIFT" "$HAS_KOTLIN" "$HAS_TAURI" "$HAS_CAPACITOR"; do
    [ "$flag" = true ] && HAS_ANY=true && break
done

if [ "$HAS_ANY" = false ]; then
    echo -e "  ${BLUE}ℹ${NC}  No supported project type detected — skipping BR3 logger"
    exit 0
fi

[ "$HAS_VITE" = true ] && echo -e "  ${GREEN}✓${NC} Detected Vite project"
[ "$HAS_SUPABASE" = true ] && echo -e "  ${GREEN}✓${NC} Detected Supabase"
[ "$HAS_RN" = true ] && echo -e "  ${GREEN}✓${NC} Detected React Native"
[ "$HAS_ELECTRON" = true ] && echo -e "  ${GREEN}✓${NC} Detected Electron"
[ "$HAS_FLUTTER" = true ] && echo -e "  ${GREEN}✓${NC} Detected Flutter"
[ "$HAS_TAURI" = true ] && echo -e "  ${GREEN}✓${NC} Detected Tauri"
[ "$HAS_CAPACITOR" = true ] && echo -e "  ${GREEN}✓${NC} Detected Capacitor"
[ "$HAS_NODE_BACKEND" = true ] && echo -e "  ${GREEN}✓${NC} Detected Node.js backend"
[ "$HAS_DENO" = true ] && echo -e "  ${GREEN}✓${NC} Detected Deno"
[ "$HAS_SWIFT" = true ] && echo -e "  ${GREEN}✓${NC} Detected Swift/iOS"
[ "$HAS_KOTLIN" = true ] && echo -e "  ${GREEN}✓${NC} Detected Kotlin/Android"

# ── Determine component destination ─────────────────────
# Components go alongside existing BR3 components
if [ -n "$VITE_CONFIG" ]; then
    VITE_DIR="$(dirname "$VITE_CONFIG")"
else
    VITE_DIR="$PROJECT_PATH"
fi
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

# ── Copy BRLogger v2 components ──────────────────────────
# Transport layer
V2_FILES="brLoggerTransport.ts vite-br-unified-plugin.ts"
for f in $V2_FILES; do
    DEST="$COMP_DIR/$f"
    if [ ! -f "$DEST" ] || ! diff -q "$BR3_COMPONENTS/$f" "$DEST" > /dev/null 2>&1; then
        cp "$BR3_COMPONENTS/$f" "$DEST"
        echo -e "  ${GREEN}✓${NC} Copied $f"
    else
        echo -e "  ${BLUE}ℹ${NC}  $f already up to date"
    fi
done

# Standalone log listener (works without Vite dev server)
LISTEN_SRC="$BR3_COMPONENTS/br-listen.mjs"
LISTEN_DEST="$PROJECT_PATH/.buildrunner/br-listen.mjs"
if [ -f "$LISTEN_SRC" ]; then
    if [ ! -f "$LISTEN_DEST" ] || ! diff -q "$LISTEN_SRC" "$LISTEN_DEST" > /dev/null 2>&1; then
        cp "$LISTEN_SRC" "$LISTEN_DEST"
        echo -e "  ${GREEN}✓${NC} Copied br-listen.mjs"
    else
        echo -e "  ${BLUE}ℹ${NC}  br-listen.mjs already up to date"
    fi
    # Inject "listen" script into package.json if missing
    if [ -f "$PROJECT_PATH/package.json" ] && ! grep -q '"listen"' "$PROJECT_PATH/package.json"; then
        if command -v node > /dev/null 2>&1; then
            node -e "
              const fs = require('fs');
              const p = '$PROJECT_PATH/package.json';
              const pkg = JSON.parse(fs.readFileSync(p, 'utf-8'));
              if (pkg.scripts && !pkg.scripts.listen) {
                pkg.scripts.listen = 'node .buildrunner/br-listen.mjs';
                fs.writeFileSync(p, JSON.stringify(pkg, null, 2) + '\n');
              }
            " 2>/dev/null && echo -e "  ${GREEN}✓${NC} Added 'listen' script to package.json"
        fi
    fi
fi

# Capture modules
CAPTURES_DIR="$COMP_DIR/captures"
mkdir -p "$CAPTURES_DIR"
if [ -d "$BR3_COMPONENTS/captures" ]; then
    for f in "$BR3_COMPONENTS/captures/"*.ts; do
        FNAME="$(basename "$f")"
        DEST="$CAPTURES_DIR/$FNAME"
        if [ ! -f "$DEST" ] || ! diff -q "$f" "$DEST" > /dev/null 2>&1; then
            cp "$f" "$DEST"
            echo -e "  ${GREEN}✓${NC} Copied captures/$FNAME"
        else
            echo -e "  ${BLUE}ℹ${NC}  captures/$FNAME already up to date"
        fi
    done
fi

# Updated BRLogger and README
for f in BRLogger.tsx README.md; do
    DEST="$COMP_DIR/$f"
    if [ ! -f "$DEST" ] || ! diff -q "$BR3_COMPONENTS/$f" "$DEST" > /dev/null 2>&1; then
        cp "$BR3_COMPONENTS/$f" "$DEST"
        echo -e "  ${GREEN}✓${NC} Copied $f (v2)"
    fi
done

# ── Inject Vite plugin import + usage (only for Vite projects) ──
if [ "$HAS_VITE" = false ]; then
    echo -e "  ${BLUE}ℹ${NC}  Non-Vite project — skipping Vite plugin injection"
elif grep -q "supabaseLogPlugin" "$VITE_CONFIG" 2>/dev/null; then
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

# ── Inject unified plugin (v2) ───────────────────────────
if [ "$HAS_VITE" = false ]; then
    : # Skip — no Vite config
elif grep -q "brUnifiedLogPlugin" "$VITE_CONFIG" 2>/dev/null; then
    echo -e "  ${BLUE}ℹ${NC}  brUnifiedLogPlugin already in vite.config.ts"
else
    VITE_CONFIG_DIR="$(dirname "$VITE_CONFIG")"
    UNIFIED_IMPORT="./.buildrunner/components/vite-br-unified-plugin"

    # Add import
    LAST_IMPORT_LINE=$(grep -n "^import " "$VITE_CONFIG" | tail -1 | cut -d: -f1)
    if [ -n "$LAST_IMPORT_LINE" ]; then
        sed -i '' "${LAST_IMPORT_LINE}a\\
import { brUnifiedLogPlugin } from '${UNIFIED_IMPORT}';
" "$VITE_CONFIG"
        echo -e "  ${GREEN}✓${NC} Added brUnifiedLogPlugin import to vite.config.ts"
    fi

    # Add to plugins array
    if grep -q "supabaseLogPlugin()" "$VITE_CONFIG"; then
        sed -i '' 's/\(supabaseLogPlugin()\)/\1, brUnifiedLogPlugin()/' "$VITE_CONFIG" 2>/dev/null
    elif grep -q "brLoggerPlugin()" "$VITE_CONFIG"; then
        sed -i '' 's/\(brLoggerPlugin()\)/\1, brUnifiedLogPlugin()/' "$VITE_CONFIG" 2>/dev/null
    fi
    echo -e "  ${GREEN}✓${NC} Added brUnifiedLogPlugin() to plugins array"
fi

# ── Deploy devLog.ts to edge functions _shared ────────────
FUNCTIONS_SHARED=""
for fdir in \
    "$PROJECT_PATH/supabase/functions/_shared" \
    "$VITE_DIR/supabase/functions/_shared"; do
    if [ -d "$fdir" ]; then
        FUNCTIONS_SHARED="$fdir"
        break
    fi
done

if [ -n "$FUNCTIONS_SHARED" ] && [ -f "$BR3_COMPONENTS/devLog.ts" ]; then
    DEVLOG_DEST="$FUNCTIONS_SHARED/devLog.ts"
    if [ ! -f "$DEVLOG_DEST" ] || ! diff -q "$BR3_COMPONENTS/devLog.ts" "$DEVLOG_DEST" > /dev/null 2>&1; then
        cp "$BR3_COMPONENTS/devLog.ts" "$DEVLOG_DEST"
        echo -e "  ${GREEN}✓${NC} Copied devLog.ts to supabase/functions/_shared/"
    else
        echo -e "  ${BLUE}ℹ${NC}  devLog.ts already up to date in _shared/"
    fi
elif [ -n "$FUNCTIONS_SHARED" ]; then
    echo -e "  ${YELLOW}⚠${NC}  devLog.ts template not found in BR3 components"
else
    echo -e "  ${BLUE}ℹ${NC}  No supabase/functions/_shared/ directory found — skipping devLog"
fi

# ── Ensure .gitignore excludes all BR3 log files ─────────
GITIGNORE_FILE="${VITE_DIR:-.}/.gitignore"
if [ -f "$GITIGNORE_FILE" ]; then
    # Check if *.log already covers everything
    if grep -qF '*.log' "$GITIGNORE_FILE" 2>/dev/null; then
        echo -e "  ${BLUE}ℹ${NC}  *.log in .gitignore already covers BR3 logs"
    else
        BR3_LOGS_ADDED=false
        for logfile in browser.log supabase.log device.log query.log; do
            if ! grep -qF ".buildrunner/$logfile" "$GITIGNORE_FILE" 2>/dev/null; then
                if [ "$BR3_LOGS_ADDED" = false ]; then
                    echo "" >> "$GITIGNORE_FILE"
                    echo "# BR3 logs" >> "$GITIGNORE_FILE"
                    BR3_LOGS_ADDED=true
                fi
                echo ".buildrunner/$logfile" >> "$GITIGNORE_FILE"
            fi
        done
        if [ "$BR3_LOGS_ADDED" = true ]; then
            echo -e "  ${GREEN}✓${NC} Added BR3 log files to .gitignore"
        else
            echo -e "  ${BLUE}ℹ${NC}  BR3 log files already in .gitignore"
        fi
    fi
fi

# ── Platform-Specific Capture Modules (v2) ────────────────
# Auto-detect project type and copy the right capture modules
CAPTURES_SRC="$BR3_COMPONENTS/captures"
CAPTURES_DEST="$COMP_DIR/captures"
DETECTED_PLATFORMS=""

copy_platform_captures() {
    local platform="$1"
    local src_dir="$CAPTURES_SRC/$platform"
    if [ ! -d "$src_dir" ]; then return; fi
    local dest_dir="$CAPTURES_DEST/$platform"
    mkdir -p "$dest_dir"
    for f in "$src_dir"/*; do
        [ -f "$f" ] || continue
        local fname=$(basename "$f")
        local dest="$dest_dir/$fname"
        if [ ! -f "$dest" ] || ! diff -q "$f" "$dest" > /dev/null 2>&1; then
            cp "$f" "$dest"
        fi
    done
    DETECTED_PLATFORMS="$DETECTED_PLATFORMS $platform"
}

# Always copy shared web captures (base for all web-based platforms)
if [ -d "$CAPTURES_SRC" ]; then
    mkdir -p "$CAPTURES_DEST"
    for f in "$CAPTURES_SRC"/*.ts; do
        [ -f "$f" ] || continue
        fname=$(basename "$f")
        dest="$CAPTURES_DEST/$fname"
        if [ ! -f "$dest" ] || ! diff -q "$f" "$dest" > /dev/null 2>&1; then
            cp "$f" "$dest"
        fi
    done
fi

# Copy platform captures using flags already detected above
[ "$HAS_RN" = true ] && copy_platform_captures "react-native" && echo -e "  ${GREEN}✓${NC} Copied React Native captures"
[ "$HAS_ELECTRON" = true ] && copy_platform_captures "electron" && echo -e "  ${GREEN}✓${NC} Copied Electron captures"
[ "$HAS_CAPACITOR" = true ] && copy_platform_captures "capacitor" && echo -e "  ${GREEN}✓${NC} Copied Capacitor captures"
[ "$HAS_TAURI" = true ] && copy_platform_captures "tauri" && echo -e "  ${GREEN}✓${NC} Copied Tauri captures"
[ "$HAS_FLUTTER" = true ] && copy_platform_captures "flutter" && echo -e "  ${GREEN}✓${NC} Copied Flutter captures"
[ "$HAS_SWIFT" = true ] && copy_platform_captures "swift" && echo -e "  ${GREEN}✓${NC} Copied Swift captures"
[ "$HAS_KOTLIN" = true ] && copy_platform_captures "kotlin" && echo -e "  ${GREEN}✓${NC} Copied Kotlin captures"
[ "$HAS_NODE_BACKEND" = true ] && copy_platform_captures "node" && echo -e "  ${GREEN}✓${NC} Copied Node.js captures"
[ "$HAS_DENO" = true ] && copy_platform_captures "deno" && echo -e "  ${GREEN}✓${NC} Copied Deno captures"

# ── Auto-Wire BRLogger into App Entry Points ─────────────
autowire_web() {
    # Find React entry point (main.tsx, main.ts, index.tsx)
    local entry=""
    for f in src/main.tsx src/main.ts src/index.tsx src/index.ts app/main.tsx; do
        if [ -f "$PROJECT_PATH/$f" ]; then entry="$PROJECT_PATH/$f"; break; fi
    done

    if [ -n "$entry" ] && ! grep -q "BRLogger" "$entry" 2>/dev/null; then
        # Add BRLogger import
        local rel_path
        rel_path=$(python3 -c "import os.path; print(os.path.relpath('$COMP_DIR/BRLogger.tsx', '$(dirname "$entry")'))" 2>/dev/null || echo "../.buildrunner/components/BRLogger")
        rel_path="${rel_path%.tsx}"
        [[ "$rel_path" != ./* ]] && rel_path="./$rel_path"

        # Insert import after last import line
        local last_import
        last_import=$(grep -n "^import " "$entry" | tail -1 | cut -d: -f1)
        if [ -n "$last_import" ]; then
            sed -i '' "${last_import}a\\
import { BRLogger } from '${rel_path}'
" "$entry"
        fi

        # Insert <BRLogger /> before closing </StrictMode> or after <App />
        if grep -q "</StrictMode>" "$entry"; then
            sed -i '' 's|</StrictMode>|<BRLogger />\n    </StrictMode>|' "$entry"
        elif grep -q "<App" "$entry"; then
            sed -i '' 's|<App \/>|<App />\n    <BRLogger />|' "$entry"
            sed -i '' 's|<App/>|<App/>\n    <BRLogger />|' "$entry"
        fi
        echo -e "  ${GREEN}✓${NC} Auto-wired BRLogger into $(basename "$entry")"
    fi

    # Find Supabase client and wire instrumented fetch
    local supa_client=""
    for f in $(grep -rl "createClient" "$PROJECT_PATH/src" 2>/dev/null | grep -E "supabase|client" | head -1); do
        supa_client="$f"
    done

    if [ -n "$supa_client" ] && ! grep -q "createInstrumentedFetch" "$supa_client" 2>/dev/null; then
        local supa_rel
        supa_rel=$(python3 -c "import os.path; print(os.path.relpath('$COMP_DIR/supabaseLogger.ts', '$(dirname "$supa_client")'))" 2>/dev/null || echo "")
        supa_rel="${supa_rel%.ts}"
        [[ "$supa_rel" != ./* ]] && supa_rel="./$supa_rel"

        local transport_rel
        transport_rel=$(python3 -c "import os.path; print(os.path.relpath('$COMP_DIR/brLoggerTransport.ts', '$(dirname "$supa_client")'))" 2>/dev/null || echo "")
        transport_rel="${transport_rel%.ts}"
        [[ "$transport_rel" != ./* ]] && transport_rel="./$transport_rel"

        if [ -n "$supa_rel" ] && [ -n "$transport_rel" ]; then
            # Add imports
            local last_imp
            last_imp=$(grep -n "^import " "$supa_client" | tail -1 | cut -d: -f1)
            if [ -n "$last_imp" ]; then
                sed -i '' "${last_imp}a\\
import { createInstrumentedFetch, logEvent } from '${supa_rel}'\\
import { isBRDebugActive } from '${transport_rel}'
" "$supa_client"
            fi
            echo -e "  ${GREEN}✓${NC} Auto-wired instrumented fetch into $(basename "$supa_client")"
        fi
    fi

    # Find QueryProvider and wire query capture
    local qprov=""
    for f in $(grep -rl "QueryClient" "$PROJECT_PATH/src" 2>/dev/null | grep -iE "provider|query" | head -1); do
        qprov="$f"
    done

    if [ -n "$qprov" ] && ! grep -q "initQueryCapture" "$qprov" 2>/dev/null; then
        local qcap_rel
        qcap_rel=$(python3 -c "import os.path; print(os.path.relpath('$CAPTURES_DEST/queryCapture.ts', '$(dirname "$qprov")'))" 2>/dev/null || echo "")
        qcap_rel="${qcap_rel%.ts}"
        [[ "$qcap_rel" != ./* ]] && qcap_rel="./$qcap_rel"

        if [ -n "$qcap_rel" ]; then
            local last_imp
            last_imp=$(grep -n "^import " "$qprov" | tail -1 | cut -d: -f1)
            if [ -n "$last_imp" ]; then
                sed -i '' "${last_imp}a\\
import { initQueryCapture } from '${qcap_rel}'
" "$qprov"
            fi
            echo -e "  ${GREEN}✓${NC} Auto-wired query capture into $(basename "$qprov")"
        fi
    fi
}

autowire_react_native() {
    local entry=""
    for f in App.tsx App.js index.js src/App.tsx; do
        if [ -f "$PROJECT_PATH/$f" ]; then entry="$PROJECT_PATH/$f"; break; fi
    done
    if [ -n "$entry" ] && ! grep -q "BRLoggerRN" "$entry" 2>/dev/null; then
        local rel_path
        rel_path=$(python3 -c "import os.path; print(os.path.relpath('$CAPTURES_DEST/react-native/BRLoggerRN.tsx', '$(dirname "$entry")'))" 2>/dev/null || echo "")
        rel_path="${rel_path%.tsx}"
        [[ "$rel_path" != ./* ]] && rel_path="./$rel_path"
        local last_imp
        last_imp=$(grep -n "^import " "$entry" | tail -1 | cut -d: -f1)
        if [ -n "$last_imp" ] && [ -n "$rel_path" ]; then
            sed -i '' "${last_imp}a\\
import { BRLoggerRN } from '${rel_path}'
" "$entry"
            # Add <BRLoggerRN /> after first component in JSX
            if grep -q "</>" "$entry" || grep -q "</SafeAreaProvider>" "$entry" || grep -q "</NavigationContainer>" "$entry"; then
                sed -i '' '0,/<\/>/s|<\/>|<BRLoggerRN />\n      </>|' "$entry" 2>/dev/null
            fi
            echo -e "  ${GREEN}✓${NC} Auto-wired BRLoggerRN into $(basename "$entry")"
        fi
    fi
}

autowire_electron() {
    local main_entry=""
    for f in src/main.ts src/main/index.ts electron/main.ts main.ts; do
        if [ -f "$PROJECT_PATH/$f" ]; then main_entry="$PROJECT_PATH/$f"; break; fi
    done
    if [ -n "$main_entry" ] && ! grep -q "BRLoggerElectron" "$main_entry" 2>/dev/null; then
        local rel_path
        rel_path=$(python3 -c "import os.path; print(os.path.relpath('$CAPTURES_DEST/electron/BRLoggerElectron.ts', '$(dirname "$main_entry")'))" 2>/dev/null || echo "")
        rel_path="${rel_path%.ts}"
        [[ "$rel_path" != ./* ]] && rel_path="./$rel_path"
        if [ -n "$rel_path" ]; then
            # Add import + init at top of main
            sed -i '' "1i\\
import { initBRLoggerElectron } from '${rel_path}'\\
const _brCleanup = initBRLoggerElectron()
" "$main_entry"
            echo -e "  ${GREEN}✓${NC} Auto-wired BRLoggerElectron into $(basename "$main_entry")"
        fi
    fi
}

autowire_node() {
    local entry=""
    for f in src/index.ts src/server.ts src/app.ts index.ts server.ts app.ts; do
        if [ -f "$PROJECT_PATH/$f" ]; then entry="$PROJECT_PATH/$f"; break; fi
    done
    if [ -n "$entry" ] && ! grep -q "BRLoggerNode" "$entry" 2>/dev/null; then
        local rel_path
        rel_path=$(python3 -c "import os.path; print(os.path.relpath('$CAPTURES_DEST/node/BRLoggerNode.ts', '$(dirname "$entry")'))" 2>/dev/null || echo "")
        rel_path="${rel_path%.ts}"
        [[ "$rel_path" != ./* ]] && rel_path="./$rel_path"
        if [ -n "$rel_path" ]; then
            sed -i '' "1i\\
import { initBRLoggerNode } from '${rel_path}'\\
const _brCleanup = initBRLoggerNode()
" "$entry"
            echo -e "  ${GREEN}✓${NC} Auto-wired BRLoggerNode into $(basename "$entry")"
        fi
    fi
}

autowire_flutter() {
    local main_dart="$PROJECT_PATH/lib/main.dart"
    if [ -f "$main_dart" ] && ! grep -q "BRLogger" "$main_dart" 2>/dev/null; then
        # Copy br_logger.dart to lib/
        if [ -f "$CAPTURES_DEST/flutter/br_logger.dart" ]; then
            cp "$CAPTURES_DEST/flutter/br_logger.dart" "$PROJECT_PATH/lib/br_logger.dart"
            # Add import + init
            sed -i '' "1i\\
import 'br_logger.dart';
" "$main_dart"
            # Add BRLogger.init() in main() before runApp
            sed -i '' 's/runApp(/BRLogger.init(supabaseUrl: const String.fromEnvironment("SUPABASE_URL"), supabaseAnonKey: const String.fromEnvironment("SUPABASE_ANON_KEY"));\n  runApp(/' "$main_dart" 2>/dev/null
            echo -e "  ${GREEN}✓${NC} Auto-wired BRLogger into main.dart"
        fi
    fi
}

autowire_swift() {
    # Find AppDelegate.swift
    local appdelegate=""
    for f in $(find "$PROJECT_PATH" -name "AppDelegate.swift" -not -path "*/Pods/*" 2>/dev/null | head -1); do
        appdelegate="$f"
    done
    if [ -n "$appdelegate" ] && ! grep -q "BRLogger" "$appdelegate" 2>/dev/null; then
        # Copy BRLogger.swift next to AppDelegate
        local dest_dir
        dest_dir=$(dirname "$appdelegate")
        if [ -f "$CAPTURES_DEST/swift/BRLogger.swift" ]; then
            cp "$CAPTURES_DEST/swift/BRLogger.swift" "$dest_dir/BRLogger.swift"
            # Add BRLogger.shared.start() in didFinishLaunchingWithOptions
            sed -i '' '/didFinishLaunchingWithOptions/a\
        BRLogger.shared.start(projectName: Bundle.main.infoDictionary?["CFBundleName"] as? String ?? "unknown")
' "$appdelegate" 2>/dev/null
            echo -e "  ${GREEN}✓${NC} Auto-wired BRLogger.swift into AppDelegate"
        fi
    fi
}

autowire_kotlin() {
    # Find Application class
    local app_class=""
    for f in $(grep -rl "class.*Application\b" "$PROJECT_PATH/app/src" 2>/dev/null | head -1); do
        app_class="$f"
    done
    if [ -n "$app_class" ] && ! grep -q "BRLogger" "$app_class" 2>/dev/null; then
        local dest_dir
        dest_dir=$(dirname "$app_class")
        if [ -f "$CAPTURES_DEST/kotlin/BRLogger.kt" ]; then
            cp "$CAPTURES_DEST/kotlin/BRLogger.kt" "$dest_dir/BRLogger.kt"
            # Add init in onCreate
            sed -i '' '/super.onCreate/a\
        BRLogger.init(this)
' "$app_class" 2>/dev/null
            echo -e "  ${GREEN}✓${NC} Auto-wired BRLogger.kt into Application class"
        fi
    fi
}

autowire_deno() {
    local entry=""
    for f in main.ts src/main.ts server.ts src/server.ts mod.ts; do
        if [ -f "$PROJECT_PATH/$f" ]; then entry="$PROJECT_PATH/$f"; break; fi
    done
    if [ -n "$entry" ] && ! grep -q "BRLoggerDeno" "$entry" 2>/dev/null; then
        local rel_path
        rel_path=$(python3 -c "import os.path; print(os.path.relpath('$CAPTURES_DEST/deno/BRLoggerDeno.ts', '$(dirname "$entry")'))" 2>/dev/null || echo "")
        [[ "$rel_path" != ./* ]] && rel_path="./$rel_path"
        if [ -n "$rel_path" ]; then
            sed -i '' "1i\\
import { initBRLoggerDeno } from '${rel_path}'\\
const _br = initBRLoggerDeno()
" "$entry"
            echo -e "  ${GREEN}✓${NC} Auto-wired BRLoggerDeno into $(basename "$entry")"
        fi
    fi
}

# Run auto-wiring based on detected platforms
if [ "$HAS_VITE" = true ]; then
    autowire_web
fi
echo "$DETECTED_PLATFORMS" | grep -q "react-native" && autowire_react_native
echo "$DETECTED_PLATFORMS" | grep -q "electron" && autowire_electron
echo "$DETECTED_PLATFORMS" | grep -q "node" && autowire_node
echo "$DETECTED_PLATFORMS" | grep -q "deno" && autowire_deno
echo "$DETECTED_PLATFORMS" | grep -q "flutter" && autowire_flutter
echo "$DETECTED_PLATFORMS" | grep -q "swift" && autowire_swift
echo "$DETECTED_PLATFORMS" | grep -q "kotlin" && autowire_kotlin

# ── Auto-Commit + Deploy ──────────────────────────────────
# BRLogger must be in prod immediately — never leave it on a branch
if command -v git >/dev/null 2>&1 && [ -d "$PROJECT_PATH/.git" ]; then
    cd "$PROJECT_PATH"
    # Stage all BRLogger files
    git add .buildrunner/components/ vite.config.ts vite.config.js src/ supabase/ 2>/dev/null
    if ! git diff --cached --quiet 2>/dev/null; then
        git commit -m "feat: BR3 Logger v2 — universal observability (auto-activated)" 2>/dev/null
        echo -e "  ${GREEN}✓${NC} Committed BRLogger v2 to current branch"

        # Auto-deploy if Netlify is configured
        if command -v npx >/dev/null 2>&1 && [ -f "$PROJECT_PATH/netlify.toml" ]; then
            echo -e "  ${BLUE}ℹ${NC}  Building and deploying to prod..."
            npm run build 2>/dev/null && npx netlify deploy --dir=dist --prod --message="BR3 Logger v2 auto-deploy" 2>/dev/null | grep -E "Deploy|live|URL" && \
                echo -e "  ${GREEN}✓${NC} Deployed to prod — logging active immediately" || \
                echo -e "  ${YELLOW}⚠${NC}  Auto-deploy failed — deploy manually: npm run build && npx netlify deploy --dir=dist --prod"
        fi
    fi
fi

# ── Report ───────────────────────────────────────────────
echo -e "  ${GREEN}✓${NC} BR3 Universal Logger v2 activated and wired"
echo -e "  ${BLUE}ℹ${NC}  Log files: browser.log, supabase.log, device.log, query.log"
echo -e "  ${BLUE}ℹ${NC}  Platforms:${DETECTED_PLATFORMS:- web (default)}"
echo -e "  ${BLUE}ℹ${NC}  Commands: /dbg, /sdb, /device, /query, /diag"
echo -e "  ${BLUE}ℹ${NC}  Prod debug: ?br_debug=1 (web) or BR_DEBUG=1 (native)"
