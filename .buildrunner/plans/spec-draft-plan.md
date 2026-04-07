# DRAFT: Self-QA Enforcement Layer

## Summary
Add enforcement hooks, autonomous browser exploration, visual regression baselines, and a mandatory self-QA verification step to BR3 so Claude cannot mark work done without visually verifying it in a browser.

## Phases

### Phase 1: Enforcement Hooks
- Add Stop hook (agent type) that forces Playwright MCP browser verification before Claude can finish
- Add PreCompact hook that re-injects testing/verification rules after context compaction
- Add stop_hook_active guard to prevent infinite loops
- Verify all hooks actually persist in settings.json (PLAYWRIGHT_INTEGRATION Phase 3 claimed complete but hooks missing)
- Files: ~/.claude/settings.json (MODIFY)

### Phase 2: Explore-QA Command
- Create /explore-qa slash command
- Claude autonomously crawls entire app via Playwright MCP
- Visits every page, clicks every interactive element, fills forms, checks console errors
- Tests mobile viewport (375x667)
- Outputs structured qa-report.md
- Files: ~/.claude/commands/explore-qa.md (NEW)

### Phase 3: Self-QA Step in /begin
- Add Step 4.7 Visual Browser Verification between TDD Re-run (4.5) and Two-Stage Review (5)
- Claude opens browser via Playwright MCP, navigates all pages touched by the phase
- Takes screenshots, checks for visual issues, console errors, broken layouts
- Blocks phase on visual issues (fix loop, max 3 attempts)
- Create reference doc for the step
- Files: ~/.claude/commands/begin.md (MODIFY), ~/.claude/docs/begin-self-qa.md (NEW)

### Phase 4: Visual Regression Baselines
- Add toHaveScreenshot() infrastructure to BR3 project template
- Create baseline screenshot tests for all major pages/views
- Configure odiff for fast comparison (6.6x faster than pixelmatch)
- Add animation disabling, font loading waits, dynamic content masking
- Docker-based baseline generation for cross-platform consistency
- Files: playwright.config.ts (MODIFY), tests/e2e/visual/*.spec.ts (NEW), Dockerfile.playwright (NEW)

### Phase 5: Visual Regression Tracker on Lomax
- Deploy VRT via Docker Compose on Lomax (10.0.1.104)
- Configure odiff as comparison engine
- Wire Playwright integration
- Branch-based baselines per git branch
- Files: cluster scripts, Lomax Docker Compose (remote)
