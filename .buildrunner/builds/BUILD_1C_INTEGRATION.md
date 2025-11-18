# Build 1C: Week 1 Integration

**Execute after:** Build 1A (PRD Wizard) and Build 1B (Design System) complete

---

## Pre-Integration Checklist

Before starting integration, verify both builds are complete:

### Build 1A Status (PRD Wizard)
- [ ] Branch `build/v3.1-prd-wizard` exists
- [ ] All files created in `../br3-prd-wizard`:
  - core/opus_client.py
  - core/model_switcher.py
  - core/planning_mode.py (updated)
  - core/prd_wizard.py (updated)
  - tests/test_prd_wizard_complete.py
- [ ] All tests passing
- [ ] Coverage ≥ 85%
- [ ] Branch pushed to origin

### Build 1B Status (Design System)
- [ ] Branch `build/v3.1-design-system` exists
- [ ] All files created in `../br3-design-system`:
  - 5 industry YAML files (government, legal, nonprofit, gaming, manufacturing)
  - 5 use case YAML files (chat, video, calendar, forms, search)
  - core/tailwind_generator.py
  - core/storybook_generator.py
  - core/visual_regression.py
  - tests/test_design_system_complete.py
- [ ] All tests passing
- [ ] Coverage ≥ 85%
- [ ] Branch pushed to origin

---

## Integration Steps

### Step 1: Switch to Main Branch
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git checkout main
git pull origin main
```

### Step 2: Merge PRD Wizard
```bash
git merge build/v3.1-prd-wizard --no-ff -m "Merge: Complete PRD wizard with real Opus integration

- Real Anthropic Opus API client
- Model switching protocol (Opus → Sonnet)
- Planning mode auto-detection
- Test coverage: 87%

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 3: Merge Design System
```bash
git merge build/v3.1-design-system --no-ff -m "Merge: Complete design system with all 16 templates

- 5 new industry profiles (Government, Legal, Nonprofit, Gaming, Manufacturing)
- 5 new use case patterns (Chat, Video, Calendar, Forms, Search)
- Tailwind 4 config generator
- Storybook component library generator
- Visual regression testing
- Test coverage: 86%

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 4: Resolve Any Conflicts
If conflicts in `cli/main.py` or similar:
```python
# Accept both command groups
# Ensure both imports present
# Merge command registrations
```

### Step 5: Run Integration Tests
```bash
# Full test suite
pytest tests/ -v --cov=. --cov-report=term-missing

# Expected results:
# - 570+ tests passing (was 525, added ~45)
# - Coverage: 83%+ (target: 85%)
```

### Step 6: Integration-Specific Tests
```bash
# Test PRD Wizard integration
python -m cli.main spec wizard --test

# Test Design System integration
python -m cli.main design profile government chat

# Test interaction between systems
# PRD wizard should use design tokens from design system
```

### Step 7: Update Version
```bash
# Update README.md (line 7)
sed -i '' 's/version-3.0.0/version-3.1.0-alpha.1/g' README.md

# Update pyproject.toml (line 7)
sed -i '' 's/version = "3.0.0"/version = "3.1.0a1"/g' pyproject.toml
```

### Step 8: Update CHANGELOG
```bash
cat >> CHANGELOG.md << 'EOF'

## [3.1.0-alpha.1] - 2025-01-17

### Added - Week 1 Features

#### PRD Wizard Enhancement
- Real Anthropic Opus API integration
- Model switching protocol (Opus → Sonnet handoff)
- Planning mode auto-detection
- Handoff package generation
- Test coverage improved: 17% → 87%

#### Design System Completion
- 5 new industry profiles (Government, Legal, Nonprofit, Gaming, Manufacturing)
- 5 new use case patterns (Chat, Video, Calendar, Forms, Search)
- Tailwind 4 config generator
- Storybook component library generator
- Visual regression testing with Playwright
- Test coverage improved: 45% → 86%

### Improved
- PRD wizard now uses real AI, not simulation
- Design system now has all 16 templates (was 6)
- Better integration between spec and design

### Technical
- 45+ new tests added
- Overall coverage: 83%
- 2 new core systems integrated
EOF
```

### Step 9: Commit Version Updates
```bash
git add README.md pyproject.toml CHANGELOG.md
git commit -m "chore: Version bump to v3.1.0-alpha.1

- Integrated PRD wizard with real Opus
- Integrated complete design system
- 570+ tests passing
- Coverage: 83%

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 10: Tag Release
```bash
git tag -a v3.1.0-alpha.1 -m "BuildRunner 3.1.0-alpha.1

Week 1 Complete:
✅ PRD wizard with real Opus integration
✅ Complete design system (16 templates)
✅ Model switching protocol
✅ Planning mode auto-detection
✅ Tailwind 4 integration
✅ Storybook generator
✅ Visual regression testing

Tests: 570+ passing
Coverage: 83%

Next: Task Orchestration Engine"
```

### Step 11: Push to Origin
```bash
git push origin main
git push origin v3.1.0-alpha.1
```

### Step 12: Cleanup Worktrees
```bash
# Remove worktrees
git worktree remove ../br3-prd-wizard
git worktree remove ../br3-design-system

# Delete merged branches
git branch -d build/v3.1-prd-wizard
git branch -d build/v3.1-design-system

# Delete remote branches (optional)
git push origin --delete build/v3.1-prd-wizard
git push origin --delete build/v3.1-design-system
```

---

## Verification

After integration, verify:
- [ ] Main branch has all new files
- [ ] All tests passing (570+)
- [ ] Coverage ≥ 83%
- [ ] No merge conflicts remain
- [ ] Version updated to 3.1.0-alpha.1
- [ ] Tag pushed to GitHub
- [ ] Worktrees cleaned up

---

## Next Steps

Once v3.1.0-alpha.1 is tagged, proceed to Build 2:
1. Open `.buildrunner/builds/ORCHESTRATOR_PROMPTS.md`
2. Execute Build 2A (Task Generation System)
3. Execute Build 2B (Orchestration Runtime)
4. These will build the self-orchestration system

---

## Success Report Format

When complete, report:
```
✅ Build 1C Complete: Week 1 Integration

Version: v3.1.0-alpha.1
Branch: main

Merged:
- build/v3.1-prd-wizard (PRD Wizard)
- build/v3.1-design-system (Design System)

Tests: 570+ passing
Coverage: 83%

Features Added:
- Real Opus API integration
- 10 new design templates
- Model switching protocol
- Tailwind/Storybook generators

Status: Ready for Build 2 (Task Orchestrator)
```