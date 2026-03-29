# Phase 10 Plan: External Website Redesign Mode

## Overview

Add URL-based external website redesign to /design, change mockup output location for all modes, and auto-open mockups in browser.

## Tasks

### Task 1: URL detection + mode routing

Add a new section before Step 0 that detects if the argument is a URL. If URL → set `EXTERNAL_MODE=true`, extract domain, skip Step 0 (project detection) and Step 1 (redesign gate), go straight to new Step 0.5.

### Task 2: New Step 0.5 — Site Audit

Insert between Step 0 and Step 1. Only runs in external mode. Sub-steps:

- **0.5a: Crawl** — WebFetch the URL. Extract nav links, fetch up to 5 internal pages. Collect HTML, content, styles.
- **0.5b: SPA fallback** — If body has < 500 chars of real content or is mostly `<script>` tags, fall back to Playwright: launch browser, wait for render, extract rendered DOM + take screenshots.
- **0.5c: Extract design DNA** — From crawled pages extract: color palette, typography, layout structure, component inventory, content inventory (headings, body, stats, testimonials), logo URL/image.
- **0.5d: Map onto 10 axes + content audit** — Position current site on axis system. Run content audit. Output Site DNA Report.

### Task 3: Modified Step 1.5a — pre-filled discovery for URL mode

Add conditional: in external mode, pre-fill inferable questions from crawl data. Present with "[inferred]" tags, user confirms or overrides.

### Task 4: Modified Step 3.5 — Direction D = current site in URL mode

Add conditional: in external mode, Direction D uses crawled site's actual design DNA instead of competitor cluster zone. Label "CURRENT SITE."

### Task 5: Modified Step 4.2 — exact content from crawl in URL mode

Add conditional: in external mode, mockup content from crawled site's actual content + logo.

### Task 6: Mockup output location + auto-open (ALL modes)

Change build rule #1 from `.buildrunner/design/mockups/` to `~/Projects/Websites/Mockups/<identifier>/option-{a,b,c,d}/`. Auto-open each mockup in browser after build. Applies to both local and URL modes.

### Task 7: Output scaffolding for URL mode

In external mode, scaffold Vite+React+Tailwind project in output directory before building mockups.

## Tests

Non-testable (skill file modification). Skip TDD gate.

## Execution Order

Sequential — all tasks modify the same file.
