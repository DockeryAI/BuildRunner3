# Phase 10 Plan: /design Skill + Mockup Architecture

## Tasks

1. **Create ~/.claude/commands/design.md** — frontmatter (description, allowed-tools, model: opus)
2. **Project type auto-detection** — detect website/dashboard/app from file structure
3. **Redesign gate** — .design-declined logic, existing spec check, explicit /design override
4. **Research step** — extract signals, call designResearch(), present summary, wait for input
5. **Three directions step** — call designDerive() 3x with project-type-adapted constraint sets
6. **Three mockups step** — build real pages in .buildrunner/design/mockups/option-{a,b,c}/, instructions for real components
7. **Selection step** — user picks/mixes, feedback loop, designSpec(), write DESIGN_SPEC.md, cleanup

## Approach

Single file: ~/.claude/commands/design.md. Follow conventions from appdesign.md and brainstorm.md:

- Frontmatter with description, allowed-tools, model
- Step-by-step numbered structure
- Clear gate points where user input is required
- Rules section at the end

## Tests

Non-testable (this is a markdown skill file). TDD step will be skipped.
