#!/bin/bash
# BuildRunner 3.0 - Hook Installation Script
# Installs pre-commit and pre-push hooks into a project's .git/hooks directory
#
# Usage: ./install-hooks.sh [project-path]
#        If no path provided, installs in current directory

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "🔧 BuildRunner 3.0 - Hook Installer"
echo "==================================="
echo ""

# Determine target project
if [ -n "$1" ]; then
    PROJECT_PATH="$1"
else
    PROJECT_PATH="$(pwd)"
fi

cd "$PROJECT_PATH"

# Verify this is a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Not a git repository${NC}"
    echo "   $PROJECT_PATH"
    exit 1
fi

PROJECT_NAME=$(basename "$PROJECT_PATH")
echo "📂 Installing hooks for: $PROJECT_NAME"
echo "   Path: $PROJECT_PATH"
echo ""

# Find BuildRunner3 hooks directory
BR3_HOOKS_DIR=""

# Check common locations
for loc in \
    "/Users/byronhudson/Projects/BuildRunner3/.buildrunner/hooks" \
    "$(dirname "$0")" \
    "$PROJECT_PATH/.buildrunner/hooks" \
    "$PROJECT_PATH/../BuildRunner3/.buildrunner/hooks"; do

    if [ -f "$loc/pre-commit" ]; then
        BR3_HOOKS_DIR="$loc"
        break
    fi
done

if [ -z "$BR3_HOOKS_DIR" ]; then
    echo -e "${RED}❌ Error: Could not find BR3 hooks directory${NC}"
    echo "   Looked in:"
    echo "   - /Users/byronhudson/Projects/BuildRunner3/.buildrunner/hooks"
    echo "   - $PROJECT_PATH/.buildrunner/hooks"
    echo "   - $PROJECT_PATH/../BuildRunner3/.buildrunner/hooks"
    exit 1
fi

echo "✅ Found BR3 hooks at: $BR3_HOOKS_DIR"
echo ""

# Create .git/hooks directory if it doesn't exist
mkdir -p "$PROJECT_PATH/.git/hooks"

# Install pre-commit hook
echo "📦 Installing pre-commit hook..."
if [ -f "$PROJECT_PATH/.git/hooks/pre-commit" ] && [ ! -L "$PROJECT_PATH/.git/hooks/pre-commit" ]; then
    echo -e "   ${YELLOW}⚠️  Existing pre-commit hook found (backing up)${NC}"
    mv "$PROJECT_PATH/.git/hooks/pre-commit" "$PROJECT_PATH/.git/hooks/pre-commit.backup.$(date +%Y%m%d_%H%M%S)"
fi

cp "$BR3_HOOKS_DIR/pre-commit" "$PROJECT_PATH/.git/hooks/pre-commit"
chmod +x "$PROJECT_PATH/.git/hooks/pre-commit"
echo -e "   ${GREEN}✅ pre-commit installed${NC}"

# Install pre-push hook
echo "📦 Installing pre-push hook..."
if [ -f "$PROJECT_PATH/.git/hooks/pre-push" ] && [ ! -L "$PROJECT_PATH/.git/hooks/pre-push" ]; then
    echo -e "   ${YELLOW}⚠️  Existing pre-push hook found (backing up)${NC}"
    mv "$PROJECT_PATH/.git/hooks/pre-push" "$PROJECT_PATH/.git/hooks/pre-push.backup.$(date +%Y%m%d_%H%M%S)"
fi

cp "$BR3_HOOKS_DIR/pre-push" "$PROJECT_PATH/.git/hooks/pre-push"
chmod +x "$PROJECT_PATH/.git/hooks/pre-push"
echo -e "   ${GREEN}✅ pre-push installed${NC}"

echo ""
echo "================================="
echo -e "${GREEN}✅ Hooks successfully installed!${NC}"
echo ""
echo "🔒 Enforcement Status:"
echo "   - Pre-commit: Tests will run before EVERY commit"
echo "   - Pre-push: Full test suite runs before EVERY push"
echo "   - Cannot be bypassed with --no-verify (per BR3 policy)"
echo ""
echo "📚 Test Configuration:"

# Provide project-specific guidance
if [ -d "$PROJECT_PATH/scripts" ]; then
    echo "   ✅ Test scripts detected in scripts/"
    ls -1 "$PROJECT_PATH/scripts"/test-*.sh 2>/dev/null | sed 's/^/      - /'
elif [ -d "$PROJECT_PATH/tests" ] && [ -f "$PROJECT_PATH/pytest.ini" ]; then
    echo "   ✅ pytest configuration detected"
elif [ -d "$PROJECT_PATH/supabase/functions" ]; then
    echo "   ✅ Supabase functions detected"
    echo "   ⚠️  Remember to run 'supabase start' before committing"
elif [ -d "$PROJECT_PATH/backend" ]; then
    echo "   ✅ Backend project detected"
    if [ ! -f "$PROJECT_PATH/backend/test.sh" ]; then
        echo -e "   ${YELLOW}⚠️  Create backend/test.sh to enable automatic testing${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  No test configuration detected${NC}"
    echo "   Create one of the following to enable automatic testing:"
    echo "      - scripts/test-local-integration.sh"
    echo "      - pytest.ini + tests/"
    echo "      - backend/test.sh"
fi

echo ""
echo "🎯 Next Steps:"
echo "   1. Try making a commit - hooks will run automatically"
echo "   2. Fix any issues the hooks report"
echo "   3. Commit will succeed when all checks pass"
echo ""

exit 0
