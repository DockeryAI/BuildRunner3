#!/bin/bash
# Install BR3 Enforced Git Hooks
# These hooks CANNOT be bypassed

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "🔒 Installing BR3 Enforced Git Hooks"
echo "====================================="
echo ""

# Check if .git exists
if [ ! -d ".git" ]; then
    echo "❌ Not a git repository"
    echo "   Initialize git first: git init"
    exit 1
fi

# Create .git/hooks if it doesn't exist
mkdir -p .git/hooks

# Install pre-commit hook
echo "Installing pre-commit hook..."
cp .buildrunner/hooks/pre-commit-enforced .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "  ✅ pre-commit hook installed"

# Install pre-push hook
echo "Installing pre-push hook..."
cp .buildrunner/hooks/pre-push-enforced .git/hooks/pre-push
chmod +x .git/hooks/pre-push
echo "  ✅ pre-push hook installed"

echo ""
echo "✅ Enforced hooks installed successfully!"
echo ""
echo "What this means:"
echo "  • --no-verify is now BLOCKED"
echo "  • Raw 'git push' is now BLOCKED (use 'br github push')"
echo "  • All BR3 checks are REQUIRED (no skipping)"
echo "  • Missing configs will be auto-generated"
echo ""
echo "From now on:"
echo "  git commit → Runs full BR3 validation (NO BYPASS)"
echo "  git push   → BLOCKED (use 'br github push' instead)"
echo "  br github push → Smart push with readiness checks"
echo ""
