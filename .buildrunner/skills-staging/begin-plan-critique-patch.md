# Plan Critique Gate Patch for begin.md

Add this section AFTER "## Step 3: Plan" approval gate and BEFORE "## Step 3.5: TDD Gate":

---

## Step 3.4: Plan Critique Gate (Cross-Model Review)

Before phase execution begins, run cross-model review against the BUILD spec + plan. This provides an independent second opinion from GPT-4o on the design approach.

```bash
CROSS_REVIEW="$HOME/.buildrunner/scripts/cross-model-review.sh"
BUILD_FILE=$(ls -t .buildrunner/builds/BUILD_*.md 2>/dev/null | head -1)
PLAN_FILE=".buildrunner/plans/phase-${PHASE_NUM}-plan.md"

# Run cross-model review against BUILD spec + plan (in parallel with adversarial if available)
if [ -x "$CROSS_REVIEW" ] && [ -f "$BUILD_FILE" ]; then
  echo "Running cross-model plan critique..."

  # Combine BUILD spec + plan for review
  COMBINED_CONTEXT=$(cat "$BUILD_FILE" "$PLAN_FILE" 2>/dev/null)

  # Run review (timeout 90s)
  CRITIQUE_RESULT=$("$CROSS_REVIEW" "$BUILD_FILE" "$(pwd)" 2>&1 | head -100)
  CRITIQUE_EXIT=$?

  if [ $CRITIQUE_EXIT -eq 0 ]; then
    # Check for blockers in the response
    if echo "$CRITIQUE_RESULT" | grep -qi '"severity".*"blocker"'; then
      echo "================================================================"
      echo "PLAN CRITIQUE: Blockers Found"
      echo "================================================================"
      echo "$CRITIQUE_RESULT" | python3 -c "import json,sys; [print(f'- [{f.get(\"severity\",\"?\").upper()}] {f.get(\"finding\",\"\")}') for f in json.load(sys.stdin).get('findings',[])]" 2>/dev/null || echo "$CRITIQUE_RESULT"
      echo ""
      echo "  1. Address blockers and re-submit plan"
      echo "  2. Override — proceed despite blockers (logged)"
      echo "================================================================"
      # STOP and wait for user response
    else
      # Warnings only — report and proceed
      echo "Plan critique: PASS (warnings below if any)"
      echo "$CRITIQUE_RESULT" | python3 -c "import json,sys; [print(f'- [{f.get(\"severity\",\"?\").upper()}] {f.get(\"finding\",\"\")}') for f in json.load(sys.stdin).get('findings',[]) if f.get('severity') != 'info']" 2>/dev/null || true
    fi
  else
    echo "Plan critique: SKIPPED (review unavailable — exit $CRITIQUE_EXIT)"
  fi
else
  echo "Plan critique: SKIPPED (cross-model-review.sh not available)"
fi
```

Different model = uncorrelated blind spots on design decisions. Blockers require user override; warnings proceed.

---
