# Phase 4: Visual Regression Baselines — Implementation Plan

## Tasks

1. **Modify playwright.config.ts** — Add toHaveScreenshot() config, visual project with @visual tag filtering, exclude visual from normal runs
2. **Create tests/e2e/visual/screenshot.css** — Global animation/transition/caret disabling stylesheet
3. **Create tests/e2e/visual/dashboard.visual.spec.ts** — Visual spec for dashboard with dynamic content masking
4. **Create tests/e2e/visual/login.visual.spec.ts** — Visual spec for login page
5. **Create tests/e2e/visual/analytics.visual.spec.ts** — Visual spec for analytics page with dynamic content masking
6. **Create Dockerfile.playwright** — Docker container for consistent baseline generation
7. **Modify package.json** — Add test:visual, test:visual:docker, test:visual:update scripts

## Tests

Visual spec files ARE the tests. No separate TDD step needed — these are config + test scaffold files.
