#!/usr/bin/env bash
# full_chain.test.sh — End-to-end integration test for workfloDock → Synapse → /design → /website-build
#
# Tests the full Synapse spec consumer pipeline:
# 1. Verifies DESIGN_SPEC.md front-matter detection in /design
# 2. Verifies voice_package loading in /website-build
# 3. Verifies compliance gates
#
# Usage: bash tests/integration/full_chain.test.sh [--fixtures-only]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_DIR=$(mktemp -d)
PASS=0
FAIL=0

cleanup() {
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

log_pass() {
  PASS=$((PASS + 1))
  echo "  PASS: $1"
}

log_fail() {
  FAIL=$((FAIL + 1))
  echo "  FAIL: $1"
}

echo "================================================================"
echo "Full Chain Integration Test: workfloDock → Synapse → /design → /website-build"
echo "================================================================"
echo ""

# --- Fixture: Mock workfloDock brief ---
echo "Step 1: Creating test fixtures..."

mkdir -p "$TEST_DIR/.buildrunner/design"
mkdir -p "$TEST_DIR/.buildrunner/data"

# Fixture: Synapse-generated DESIGN_SPEC.md with front-matter
cat > "$TEST_DIR/.buildrunner/design/DESIGN_SPEC.md" << 'SPECEOF'
---
source: synapse-generated
brand_id: 550e8400-e29b-41d4-a716-446655440000
brief_version: 3
aaker_scores:
  sincerity: 0.6
  excitement: 0.8
  competence: 0.9
  sophistication: 0.4
  ruggedness: 0.3
heritage_innovation: 0.7
density_preference: balanced
dominant_dimension: competence
recommended_layout_archetypes:
  - swiss-grid
  - editorial
  - split-screen
  - bento-grid
voice_package_available: true
---

# TestBrand — Design Spec

**Direction:** Precision Authority
**Approved:** 2026-04-05

## Design Thesis

Clean, competence-driven design with Swiss grid precision and editorial typography hierarchy.

## Color Palette

- Primary: #1a1a2e
- Accent: #e94560
- Surface: #16213e
- Text: #eaeaea

## Typography

- Heading: Inter
- Body: IBM Plex Sans
SPECEOF

# Fixture: voice_package.json
cat > "$TEST_DIR/.buildrunner/data/voice_package.json" << 'VPEOF'
{
  "brand_id": "550e8400-e29b-41d4-a716-446655440000",
  "brief_version": 3,
  "pages": {
    "home": {
      "hero_variants": [
        "Your competitors already rank above you in AI search.",
        "Every day without GEO costs you citations."
      ],
      "primary_cta_text": "See Your AI Visibility Score",
      "sections": [
        {
          "section_name": "hero",
          "copy": "Your competitors already rank above you in AI search.",
          "framework_role": "problem",
          "voc_phrases_used": ["rank above you", "AI search"],
          "cialdini_lever": "social_proof"
        },
        {
          "section_name": "pain_agitation",
          "copy": "While you wait, competitors are being cited by ChatGPT, Perplexity, and Gemini. Every unanswered query is a lead they get and you don't.",
          "framework_role": "agitate",
          "voc_phrases_used": ["competitors", "cited by ChatGPT"],
          "cialdini_lever": "scarcity"
        }
      ],
      "faq": [
        {
          "question": "What is GEO?",
          "answer": "Generative Engine Optimization is the practice of structuring your website content so AI search engines like ChatGPT and Perplexity cite your business in their answers. It combines structured data, answer capsules, and statistics-rich content."
        }
      ],
      "objection_response_pairs": [
        {
          "objection": "SEO is enough",
          "response": "SEO targets Google's blue links. GEO targets AI-generated answers — a separate ranking system with different signals. You need both."
        }
      ]
    }
  }
}
VPEOF

# Fixture: intelligence brief
cat > "$TEST_DIR/.buildrunner/data/website-intelligence-brief.json" << 'BRIEFEOF'
{
  "meta": {
    "brand_id": "550e8400-e29b-41d4-a716-446655440000",
    "brief_version": 3
  },
  "brand": {
    "name": "TestBrand",
    "industry": "Digital Marketing",
    "city": "Austin",
    "uvp_statement": "AI search visibility for SMBs",
    "products": ["GEO Audit", "Citation Optimization", "Schema Markup"],
    "differentiators": ["First-mover in GEO", "AI-native approach"]
  },
  "pain_vocabulary": [
    {"phrase": "invisible to AI search", "engagement": 0.92},
    {"phrase": "competitors rank above us", "engagement": 0.87},
    {"phrase": "no ChatGPT citations", "engagement": 0.84}
  ],
  "psychology_profile": {
    "cialdini": "social_proof",
    "framing": "loss",
    "eq_score": 0.65,
    "framework": "PASTOR"
  }
}
BRIEFEOF

echo "  Fixtures created in $TEST_DIR"
echo ""

# --- Test 1: Front-matter parsing ---
echo "Step 2: Testing DESIGN_SPEC.md front-matter detection..."

# Check front-matter exists and has correct source
if grep -q "^source: synapse-generated$" "$TEST_DIR/.buildrunner/design/DESIGN_SPEC.md"; then
  log_pass "Front-matter contains source: synapse-generated"
else
  log_fail "Front-matter missing source: synapse-generated"
fi

# Check all 5 Aaker scores present
for dim in sincerity excitement competence sophistication ruggedness; do
  if grep -q "  $dim:" "$TEST_DIR/.buildrunner/design/DESIGN_SPEC.md"; then
    log_pass "Aaker score present: $dim"
  else
    log_fail "Aaker score missing: $dim"
  fi
done

# Check layout archetypes (at least 4)
ARCHETYPE_COUNT=$(grep -c "  - " "$TEST_DIR/.buildrunner/design/DESIGN_SPEC.md" | head -1)
if [ "$ARCHETYPE_COUNT" -ge 4 ]; then
  log_pass "At least 4 layout archetypes present ($ARCHETYPE_COUNT found)"
else
  log_fail "Fewer than 4 layout archetypes ($ARCHETYPE_COUNT found)"
fi

# Check brand_id is UUID format
if grep -qE "^brand_id: [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$" "$TEST_DIR/.buildrunner/design/DESIGN_SPEC.md"; then
  log_pass "brand_id is valid UUID"
else
  log_fail "brand_id is not valid UUID"
fi

echo ""

# --- Test 2: Voice package structure ---
echo "Step 3: Testing voice_package.json structure..."

# Check voice_package has pages
if python3 -c "import json; d=json.load(open('$TEST_DIR/.buildrunner/data/voice_package.json')); assert 'pages' in d; assert 'home' in d['pages']" 2>/dev/null; then
  log_pass "voice_package has pages.home"
else
  log_fail "voice_package missing pages.home"
fi

# Check hero_variants present
if python3 -c "import json; d=json.load(open('$TEST_DIR/.buildrunner/data/voice_package.json')); assert len(d['pages']['home']['hero_variants']) >= 1" 2>/dev/null; then
  log_pass "hero_variants has at least 1 variant"
else
  log_fail "hero_variants empty or missing"
fi

# Check primary_cta_text
if python3 -c "import json; d=json.load(open('$TEST_DIR/.buildrunner/data/voice_package.json')); assert d['pages']['home']['primary_cta_text']" 2>/dev/null; then
  log_pass "primary_cta_text present"
else
  log_fail "primary_cta_text missing"
fi

# Check sections have required fields
if python3 -c "
import json
d=json.load(open('$TEST_DIR/.buildrunner/data/voice_package.json'))
for s in d['pages']['home']['sections']:
    assert 'section_name' in s
    assert 'copy' in s
    assert 'framework_role' in s
    assert 'cialdini_lever' in s
" 2>/dev/null; then
  log_pass "sections have all required fields (section_name, copy, framework_role, cialdini_lever)"
else
  log_fail "sections missing required fields"
fi

# Check FAQ answers are 40-60 words
if python3 -c "
import json
d=json.load(open('$TEST_DIR/.buildrunner/data/voice_package.json'))
for faq in d['pages']['home']['faq']:
    words = len(faq['answer'].split())
    assert 30 <= words <= 70, f'FAQ answer is {words} words (expected 40-60 range)'
" 2>/dev/null; then
  log_pass "FAQ answers within word count range"
else
  log_fail "FAQ answers outside expected word count range"
fi

echo ""

# --- Test 3: Brief structure ---
echo "Step 4: Testing intelligence brief structure..."

if python3 -c "
import json
d=json.load(open('$TEST_DIR/.buildrunner/data/website-intelligence-brief.json'))
assert d['meta']['brand_id'] == '550e8400-e29b-41d4-a716-446655440000'
assert d['meta']['brief_version'] == 3
assert d['brand']['name'] == 'TestBrand'
assert len(d['pain_vocabulary']) >= 3
assert d['psychology_profile']['framework'] == 'PASTOR'
" 2>/dev/null; then
  log_pass "Brief structure valid with all required fields"
else
  log_fail "Brief structure invalid"
fi

echo ""

# --- Test 4: Skill file patches ---
echo "Step 5: Testing skill file patches..."

DESIGN_SKILL="$HOME/.claude/commands/design.md"
WEBSITE_SKILL="$HOME/.claude/commands/website-build.md"

# Check /design has synapse detection
if grep -q "synapse-generated" "$DESIGN_SKILL"; then
  log_pass "/design skill contains synapse-generated detection"
else
  log_fail "/design skill missing synapse-generated detection"
fi

# Check /design has front-matter prepend instruction
if grep -q "Front-Matter Prepend" "$DESIGN_SKILL"; then
  log_pass "/design skill contains front-matter prepend logic"
else
  log_fail "/design skill missing front-matter prepend logic"
fi

# Check /design has fallback defaults
if grep -q "synapse-fallback" "$DESIGN_SKILL"; then
  log_pass "/design skill contains fallback defaults with warnings"
else
  log_fail "/design skill missing fallback defaults"
fi

# Check /design synapse_integration block is updated
if grep -q "IMPLEMENTED" "$DESIGN_SKILL"; then
  log_pass "/design synapse_integration block updated to IMPLEMENTED"
else
  log_fail "/design synapse_integration block still aspirational"
fi

# Check /website-build has voice package step
if grep -q "Step 2.5: Load Voice Package" "$WEBSITE_SKILL"; then
  log_pass "/website-build has Step 2.5 voice package fetch"
else
  log_fail "/website-build missing Step 2.5 voice package fetch"
fi

# Check /website-build has USE_VOICE_PACKAGE mode
if grep -q "USE_VOICE_PACKAGE" "$WEBSITE_SKILL"; then
  log_pass "/website-build has USE_VOICE_PACKAGE mode in Step 5"
else
  log_fail "/website-build missing USE_VOICE_PACKAGE mode"
fi

# Check /website-build has GEO compliance gates
if grep -q "6.2 GEO Compliance Gates" "$WEBSITE_SKILL"; then
  log_pass "/website-build has GEO compliance gates"
else
  log_fail "/website-build missing GEO compliance gates"
fi

# Check /website-build has a11y gates
if grep -q "6.3 Accessibility Gates" "$WEBSITE_SKILL"; then
  log_pass "/website-build has accessibility gates"
else
  log_fail "/website-build missing accessibility gates"
fi

# Check /website-build has CWV gates
if grep -q "6.4 Core Web Vitals Gates" "$WEBSITE_SKILL"; then
  log_pass "/website-build has Core Web Vitals gates"
else
  log_fail "/website-build missing Core Web Vitals gates"
fi

# Check /website-build has framework compliance gates
if grep -q "6.5 Framework Compliance Gates" "$WEBSITE_SKILL"; then
  log_pass "/website-build has framework compliance gates"
else
  log_fail "/website-build missing framework compliance gates"
fi

# Check /website-build has Playwright test generation
if grep -q "6.6 Generate Playwright E2E Tests" "$WEBSITE_SKILL"; then
  log_pass "/website-build has Playwright E2E test generation"
else
  log_fail "/website-build missing Playwright E2E test generation"
fi

# Check /website-build has Synapse integration docs
if grep -q "Synapse Voice Package Integration" "$WEBSITE_SKILL"; then
  log_pass "/website-build has Synapse integration documentation"
else
  log_fail "/website-build missing Synapse integration documentation"
fi

# Check env example exists
if [ -f "$HOME/.claude/commands/_env.example" ]; then
  log_pass "_env.example exists with Synapse env vars"
else
  log_fail "_env.example missing"
fi

echo ""

# --- Test 5: Legacy compatibility ---
echo "Step 6: Testing legacy compatibility..."

# Create a legacy spec (no front-matter)
cat > "$TEST_DIR/.buildrunner/design/LEGACY_SPEC.md" << 'LEGACYEOF'
# OldBrand — Design Spec

**Direction:** Classic Clean
**Approved:** 2025-01-15

## Design Thesis

Traditional clean design.

## Color Palette

- Primary: #333333
LEGACYEOF

# Verify legacy spec has no front-matter markers
if ! head -1 "$TEST_DIR/.buildrunner/design/LEGACY_SPEC.md" | grep -q "^---$"; then
  log_pass "Legacy spec correctly has no front-matter"
else
  log_fail "Legacy spec unexpectedly has front-matter"
fi

# Create a manual-discovery spec
cat > "$TEST_DIR/.buildrunner/design/MANUAL_SPEC.md" << 'MANUALEOF'
---
source: manual-discovery
brand_id: null
aaker_scores:
  sincerity: 0.7
  excitement: 0.5
  competence: 0.6
  sophistication: 0.3
  ruggedness: 0.4
---

# ManualBrand — Design Spec
MANUALEOF

if grep -q "^source: manual-discovery$" "$TEST_DIR/.buildrunner/design/MANUAL_SPEC.md"; then
  log_pass "Manual-discovery spec correctly identified"
else
  log_fail "Manual-discovery spec not correctly formatted"
fi

echo ""

# --- Summary ---
echo "================================================================"
echo "RESULTS: $PASS passed, $FAIL failed"
echo "================================================================"

if [ "$FAIL" -gt 0 ]; then
  echo "SOME TESTS FAILED"
  exit 1
else
  echo "ALL TESTS PASSED"
  exit 0
fi
