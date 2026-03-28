# Phase 10 Verification: /design Skill + Mockup Architecture

## File Created
- ~/.claude/commands/design.md (265 lines) — confirmed exists

## Skill Registration
- Skill appears in available skills list as "design" — confirmed via system reminder

## Deliverable Checklist
- [x] Create /design skill — standalone, invocable on any BR3 project
- [x] Project type auto-detection from file structure (Step 0)
- [x] Redesign gate: .design-declined check, existing spec check, explicit /design override (Step 1)
- [x] Research step: extract signals, designResearch(), present summary, wait (Step 2)
- [x] Three directions: designDerive() 3x with project-type-adapted constraints (Step 3)
- [x] Three mockups: real working pages in actual tech stack (Step 4)
- [x] Selection step: pick/mix/feedback loop, designSpec(), DESIGN_SPEC.md, cleanup (Step 5)
- [x] Skill description for skills table: triggers on "design", "redesign", "mockup", "visual direction"

## Convention Compliance
- Frontmatter matches appdesign.md / brainstorm.md pattern
- allowed-tools includes Read, Write, Edit, Bash, Grep, Glob
- model: opus (consistent with other design skills)
- User gates at Steps 1, 2b, 3, 4, 5
- Rules section (10 rules) covers edge cases
