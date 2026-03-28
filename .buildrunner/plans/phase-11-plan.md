# Phase 11 Plan: Content Structure + Copy Intelligence

## Tasks

### Task 11.1: SKILL.md Content Structure section

Add compact Content Structure section (~20 lines) with rules for max-w-prose, paragraph length, heading frequency, padding, bullet lists, line-height, letter-spacing.

### Task 11.2: dais.types.ts — copyIntelligence field

Add `DaisCopyIntelligence` interface and optional `copyIntelligence` field to `DaisDeriveRequest`.

### Task 11.3: design-derive EF — copyIntelligence prompt injection

If copyIntelligence provided in request, include pain vocabulary, voice gap, psychology profile, and tone keywords in the Claude prompt.

### Task 11.4: design-spec EF — Content Structure & Voice output

Expand the system prompt to include "Content Structure & Voice" section in the output spec covering text density, microcopy tone, case conventions, CTA style, etc.

### Task 11.5: website-build.md — pass copyIntelligence

Map WebsiteIntelligenceBrief fields to copyIntelligence in the DAIS call.

## Tests

Non-testable (config/docs/edge function prompt changes). Skip TDD.
