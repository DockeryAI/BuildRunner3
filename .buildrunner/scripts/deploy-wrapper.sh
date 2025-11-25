#!/bin/bash
# BuildRunner 3.0 - Deployment Wrapper
# Enforces all BR3 checks before deployment
# Usage: ./deploy-wrapper.sh <deploy-command> [args...]

set -e

echo ""
echo "🚀 BuildRunner 3.0 - Pre-Deployment Validation"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if BR3 is available
if ! command -v br &> /dev/null; then
    echo -e "${YELLOW}⚠️  BuildRunner CLI not found - skipping checks${NC}"
    echo ""
    # Still allow deployment but warn
    exec "$@"
    exit $?
fi

# Track overall success
ALL_CHECKS_PASSED=true

# Function to run a check
run_check() {
    local name="$1"
    local command="$2"

    echo "▶ $name"

    if eval "$command" > /tmp/br-deploy-check.log 2>&1; then
        echo -e "  ${GREEN}✅ PASSED${NC}"
        return 0
    else
        echo -e "  ${RED}❌ FAILED${NC}"
        echo ""
        cat /tmp/br-deploy-check.log | head -30
        echo ""
        ALL_CHECKS_PASSED=false
        return 1
    fi
}

# ============================================
# PHASE 1: SECURITY SCANNING
# ============================================
echo "🔒 Phase 1: Security Scanning"
echo "=============================="

run_check "Security Check (Secrets + SQL)" "br security check"

echo ""

# ============================================
# PHASE 2: AUTO-DEBUG PIPELINE
# ============================================
echo "🧪 Phase 2: Auto-Debug Pipeline"
echo "==============================="

run_check "BuildRunner Auto-Debug" "br autodebug run --skip-deep"

echo ""

# ============================================
# PHASE 3: CODE QUALITY
# ============================================
echo "⭐ Phase 3: Code Quality"
echo "======================="

run_check "Quality Check" "br quality check"

echo ""

# ============================================
# FINAL VERDICT
# ============================================
echo "================================================"

if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}✅ ALL PRE-DEPLOYMENT CHECKS PASSED${NC}"
    echo ""
    echo "📊 Systems Validated:"
    echo "   • Security scanning (secrets, SQL injection)"
    echo "   • Auto-debug pipeline (syntax, tests, linting)"
    echo "   • Code quality gates (structure, testing, docs)"
    echo ""
    echo "🚀 Proceeding with deployment..."
    echo ""

    # Execute the actual deployment command
    exec "$@"
    exit $?
else
    echo -e "${RED}❌ PRE-DEPLOYMENT CHECKS FAILED${NC}"
    echo ""
    echo "Cannot deploy code that fails validation."
    echo "Fix the issues above and try again."
    echo ""
    echo "To bypass (NOT RECOMMENDED):"
    echo "  Run the deployment command directly without this wrapper"
    echo ""
    exit 1
fi
