# Changelog

All notable changes to BuildRunner will be documented in this file.

## [3.1.0-alpha.3] - TBD (Week 4 Features - Planned)

### Planned - Playwright Visual Debugging System

#### Visual Testing & Debugging
- **Visual Regression Testing:** Screenshot-based diff detection for UI changes
- **E2E Test Recording:** Record and replay user interactions for debugging
- **Component Testing:** Test React/Vue components in isolation with real browser
- **Network Monitoring:** Capture and analyze API calls during test execution
- **Console Log Capture:** Automatically collect browser console errors
- **Interactive Debug Mode:** Pause tests and inspect live browser state
- **Screenshot Gallery:** Auto-generate visual documentation of component library
- **Auto-Test Generated Code:** Verify BuildRunner's code output works in browser

#### Integration Features
- Integration with Error Watcher for auto-debugging
- Visual diffs automatically added to blockers.md
- Screenshots included in AI context for analysis
- Auto-run visual tests when components change
- Responsive testing at multiple viewport sizes

#### CLI Commands
- `br test visual <url> <name>` - Run visual regression test
- `br test record <url> <name>` - Record browser interaction
- `br test replay <recording>` - Replay recorded test
- `br test component <path>` - Test component in isolation
- `br test screenshot-gallery` - Generate component gallery
- `br test network <url>` - Monitor network traffic

#### Technical Details
- Playwright integration (~2,600 lines)
- Perceptual hash-based screenshot comparison
- HAR file export for network analysis
- HTML gallery with search and filter
- Configurable diff thresholds
- Multi-viewport responsive testing

### Dependencies to Add
- `playwright` - Browser automation and testing
- `pytest-playwright` - Pytest integration
- `pillow` - Image processing for visual diffs
- `imagehash` - Perceptual hashing

## [3.1.0-alpha.2] - 2025-01-17

### Added - Week 2 Features

#### AI Code Review System
- AI-powered code review with Claude Sonnet API integration
- Pattern detection (MVC, Repository, Factory, Singleton patterns)
- Architecture analysis against PROJECT_SPEC.md
- Performance analyzer with cyclomatic complexity detection
- N+1 query detection and memory leak analysis
- Code smell detector (long methods, god classes, duplicate code)
- Security scanner (SQL injection, XSS, hardcoded secrets)
- Pre-commit hook integration for automated reviews
- CLI commands: `br review diff`, `br review file`, `br review install-hook`

#### Synapse Profile Integration
- Synapse industry profile database integration (147 profiles planned, 8 implemented)
- Industry discovery system for unknown industries
- Research-based profile generation with Opus API
- Profile migrator for BR3 to Synapse format conversion
- Shared Supabase database connection singleton
- Full compatibility with Synapse infrastructure

### Improved
- AI review can now validate code against industry-specific patterns from Synapse
- Code quality enforcement through pre-commit hooks
- Architecture compliance verification

### Technical
- **New Files:** 16 files (~7,700 lines)
- **Tests:** 765 passing (was 580)
- **Coverage:** 67% overall
  - ai_code_review.py: 80%
  - pattern_analyzer.py: 86%
  - performance_analyzer.py: 77%
  - code_smell_detector.py: 82%
  - security_scanner.py: 81%
  - synapse_profile_manager.py: 82%
  - industry_discovery.py: 88%

### Dependencies Added
- `radon` - Cyclomatic complexity analysis
- `astroid` - AST analysis
- `pylint` - Code quality checking
- `bandit` - Security vulnerability scanning

## [3.1.0-alpha.1] - 2025-01-17

### Added
- Real Opus API integration for PRD wizard
- Model switching protocol (Opus → Sonnet handoff)
- Planning mode auto-detection
- 5 new industry profiles (Government, Legal, Nonprofit, Gaming, Manufacturing)
- 5 new use case patterns (Chat, Video, Calendar, Forms, Search)
- Tailwind 4 integration
- Storybook component library generator
- Visual regression testing with Playwright

### Improved
- PRD wizard test coverage: 17% → 85%
- Design system test coverage: 45% → 85%
- Fixed design profiler to handle nested YAML structures
- Enhanced deep merge for design tokens

### Fixed
- Design profiler now handles both flat and nested color structures
- Components can now be either lists or dictionaries
- Compliance field supports both list and dict formats

### Metrics
- **Tests:** 580 passing
- **Coverage:** 81%
- **New Files:** 20+ files
- **New Lines:** ~4,172 lines

## [3.0.0] - 2025-01-17

### Release Highlights

**Status:** Production/Stable ✅
- **525 tests passing** (exceeds 500+ target)
- **81% code coverage** (target: 85%)
- **163KB comprehensive documentation**
- **All 8 enhancement systems fully implemented**

### Added - 8 Enhancement Systems

#### 1. Completion Assurance System
- Automated gap analysis
- Task dependency tracking
- Pre-push validation
- Real-time progress tracking

#### 2. Code Quality System
- Multi-dimensional quality scoring
- Automated linting and security scans
- Quality gates in git hooks
- Per-project thresholds

#### 3. Architecture Drift Prevention
- Architecture guard validation
- Spec violation detection
- Git hook enforcement
- Design system consistency

#### 4. Automated Debugging System
- Auto-pipe command outputs
- Error pattern detection
- Failure analysis
- Smart retry suggestions

#### 5. Design System with Industry Intelligence
- 8 industry profiles
- 8 use case patterns
- Auto-merge with conflict resolution
- Tailwind config generation
- Compliance requirements

#### 6. Planning Mode + PRD Integration
- Interactive PROJECT_SPEC wizard
- Industry/use case auto-detection
- Opus pre-fill
- Compact handoff packages
- Bidirectional sync

#### 7. Self-Service Execution System
- API key management
- Environment setup automation
- Service detection
- Graceful degradation

#### 8. Global/Local Behavior Configuration
- Config hierarchy
- Global defaults
- Project overrides
- Runtime flags

### Core Features

- Feature-based tracking (replaces phase/step model)
- Git hooks (pre-commit, post-commit, pre-push)
- MCP integration for Claude Code
- FastAPI backend
- Multi-repo dashboard
- BR 2.0 migration tools

### Integrations

- GitHub (issue sync, PR creation)
- Notion (documentation sync)
- Slack (notifications, standups)
- Supabase (optional persistence)

### Breaking Changes from BR 2.0

- `.runner/` → `.buildrunner/` directory structure
- `hrpo.json` → `features.json` format
- `governance.json` → `governance.yaml` format
- Phase/step model removed (use features)
- New CLI command structure

### Migration

Use `br migrate from-v2 <path>` to migrate BR 2.0 projects.

## [2.0.0] - 2024-10-01

- Initial BuildRunner 2.0 release
- HRPO system
- Supabase sync
- Basic governance

## [1.0.0] - 2024-01-01

- Initial release
- Basic runner system
