# Build 4D: Playwright Visual Debugging System

**Week:** 4
**Duration:** 1 week
**Branch:** `build/v3.1-playwright-debug`
**Worktree:** `../br3-playwright-debug`
**Parallel With:** Other Week 4 builds

## Overview

Integrate Playwright into BuildRunner's Automated Debugging System to provide browser-based testing, visual regression testing, and interactive debugging capabilities for generated code.

## Objectives

1. **Visual Regression Testing** - Auto-detect UI changes via screenshot diffs
2. **E2E Test Recording** - Record user flows for debugging playback
3. **Network Monitoring** - Capture API calls during test runs
4. **Interactive Debugging** - Pause tests and inspect browser state
5. **Component Testing** - Test components in real browser
6. **Auto-Test Generated Code** - Verify BuildRunner's code output works
7. **Screenshot Gallery** - Document component libraries visually

## Prerequisites

```bash
cd /Users/byronhudson/Projects/BuildRunner3
```

## Git Worktree Setup

```bash
git worktree add ../br3-playwright-debug -b build/v3.1-playwright-debug
cd ../br3-playwright-debug
```

## Dependencies

```bash
pip install playwright pytest-playwright pillow -q
playwright install  # Install browser binaries
```

---

## BATCH 1: Core Playwright Integration (Tasks 1-3, 6 hours)

### Task 1: Create Playwright Test Runner (2 hours)

**File:** `core/testing/playwright_runner.py`

```python
"""
Playwright Test Runner - Browser-based testing system

Integrates with BuildRunner's test infrastructure to provide:
- Visual regression testing
- E2E test execution
- Network traffic capture
- Console log monitoring
- Screenshot management
"""

class PlaywrightRunner:
    """Manages Playwright test execution"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.screenshots_dir = project_root / ".buildrunner" / "screenshots"
        self.network_logs_dir = project_root / ".buildrunner" / "network"
        self.console_logs_dir = project_root / ".buildrunner" / "console"

    async def run_visual_regression_test(
        self,
        url: str,
        test_name: str,
        baseline_screenshot: Optional[Path] = None
    ) -> VisualRegressionResult:
        """
        Run visual regression test

        1. Take screenshot of current state
        2. Compare with baseline (if exists)
        3. Generate diff image if changes detected
        4. Return result with diff percentage
        """

    async def run_e2e_test(
        self,
        test_script: str,
        record: bool = False
    ) -> E2ETestResult:
        """
        Run end-to-end test

        If record=True:
        - Records all actions to .buildrunner/recordings/
        - Captures network traffic
        - Saves console logs
        - Takes screenshots at key steps
        """

    async def test_component(
        self,
        component_path: str,
        props: Dict[str, Any]
    ) -> ComponentTestResult:
        """
        Test a React/Vue component in isolation

        1. Create test harness HTML
        2. Mount component with props
        3. Run interaction tests
        4. Verify rendering
        5. Check accessibility
        """

    async def capture_network_traffic(
        self,
        url: str,
        duration_seconds: int = 30
    ) -> List[NetworkRequest]:
        """
        Monitor network traffic

        Captures:
        - All HTTP requests/responses
        - Headers
        - Timing data
        - Payloads
        """

    async def get_console_logs(
        self,
        url: str,
        filter_level: str = "error"
    ) -> List[ConsoleMessage]:
        """
        Capture browser console logs

        Filters: error, warning, info, debug
        """
```

**Tests:** `tests/test_playwright_runner.py`

---

### Task 2: Create Visual Regression System (2 hours)

**File:** `core/testing/visual_regression.py`

```python
"""
Visual Regression Testing System

Compares screenshots over time to detect unintended UI changes.
"""

from PIL import Image, ImageChops
import imagehash

class VisualRegressionTester:
    """Manages visual regression testing"""

    def __init__(self, baseline_dir: Path):
        self.baseline_dir = baseline_dir
        self.diff_threshold = 0.05  # 5% difference triggers failure

    def compare_screenshots(
        self,
        current: Path,
        baseline: Path
    ) -> RegressionResult:
        """
        Compare two screenshots

        Returns:
        - Pixel difference count
        - Percentage difference
        - Diff image (highlights changes)
        - Pass/fail based on threshold
        """

    def generate_diff_image(
        self,
        current: Image,
        baseline: Image
    ) -> Image:
        """
        Create visual diff image

        Changed pixels highlighted in red
        """

    def create_baseline(
        self,
        screenshot: Path,
        test_name: str
    ) -> Path:
        """Save screenshot as new baseline"""

    def get_perceptual_hash(
        self,
        image: Path
    ) -> str:
        """
        Generate perceptual hash for fast comparison

        Uses pHash algorithm - detects visually similar images
        even if pixels differ slightly
        """

    def generate_regression_report(
        self,
        test_results: List[RegressionResult]
    ) -> Path:
        """
        Create HTML report showing all regressions

        Side-by-side comparison:
        - Baseline image
        - Current image
        - Diff overlay
        - Percentage changed
        """
```

**Tests:** `tests/test_visual_regression.py`

---

### Task 3: Create Test Recording System (2 hours)

**File:** `core/testing/test_recorder.py`

```python
"""
Test Recording System

Records user interactions for debugging and replay.
"""

class TestRecorder:
    """Records and replays browser interactions"""

    def __init__(self, recordings_dir: Path):
        self.recordings_dir = recordings_dir

    async def start_recording(
        self,
        page: Page,
        recording_name: str
    ) -> Recording:
        """
        Start recording user actions

        Captures:
        - Mouse clicks
        - Keyboard input
        - Navigation
        - Network requests
        - Screenshots at each step
        - Console logs
        """

    async def stop_recording(
        self,
        recording: Recording
    ) -> Path:
        """
        Stop recording and save

        Saves to: .buildrunner/recordings/{name}/
        - actions.json (all recorded actions)
        - network.har (HAR file with network traffic)
        - screenshots/ (step-by-step screenshots)
        - console.log (browser console output)
        """

    async def replay_recording(
        self,
        recording_path: Path,
        speed: float = 1.0
    ) -> ReplayResult:
        """
        Replay a recorded test

        Args:
            speed: Playback speed (1.0 = normal, 2.0 = double speed)

        Returns:
            - Success/failure
            - Screenshots from replay
            - Any errors encountered
        """

    def export_to_playwright_script(
        self,
        recording_path: Path
    ) -> str:
        """
        Convert recording to Playwright Python script

        Generates executable test code from recording
        """
```

**Tests:** `tests/test_recorder.py`

---

## BATCH 2: CLI & Integration (Tasks 4-6, 6 hours)

### Task 4: Create CLI Commands (2 hours)

**File:** `cli/playwright_commands.py`

```python
"""
Playwright CLI commands for BuildRunner
"""

@app.command()
def visual_test(
    url: str,
    test_name: str,
    update_baseline: bool = False
):
    """
    Run visual regression test

    Examples:
        br test visual http://localhost:3000 homepage
        br test visual http://localhost:3000/dashboard dashboard --update-baseline
    """

@app.command()
def record(
    url: str,
    name: str,
    duration: int = 60
):
    """
    Record browser interaction

    Opens browser and records all actions for specified duration

    Example:
        br test record http://localhost:3000 user-login
    """

@app.command()
def replay(
    recording_name: str,
    speed: float = 1.0
):
    """
    Replay recorded test

    Example:
        br test replay user-login --speed 2.0
    """

@app.command()
def component(
    component_path: str,
    props_json: Optional[str] = None
):
    """
    Test component in isolation

    Example:
        br test component src/components/Button.tsx '{"label": "Click me"}'
    """

@app.command()
def screenshot_gallery():
    """
    Generate screenshot gallery of all components

    Creates HTML gallery: .buildrunner/gallery/index.html
    """

@app.command()
def network_monitor(
    url: str,
    duration: int = 30,
    filter_domain: Optional[str] = None
):
    """
    Monitor network traffic

    Example:
        br test network http://localhost:3000 --filter-domain api.example.com
    """
```

---

### Task 5: Create Integration with Error Watcher (2 hours)

**File:** `core/testing/playwright_integration.py`

```python
"""
Integration between Playwright and BuildRunner debugging system
"""

class PlaywrightDebugIntegration:
    """Links Playwright with error watcher and auto-debugging"""

    def __init__(
        self,
        error_watcher: ErrorWatcher,
        playwright_runner: PlaywrightRunner
    ):
        self.error_watcher = error_watcher
        self.playwright_runner = playwright_runner

    async def auto_test_on_file_change(
        self,
        changed_files: List[Path]
    ):
        """
        Automatically run visual tests when files change

        Triggered by error watcher file monitoring
        """

    async def debug_failed_test(
        self,
        test_result: TestResult
    ) -> DebugReport:
        """
        Auto-debug failed test

        1. Replay test in debug mode
        2. Capture network traffic
        3. Collect console logs
        4. Take screenshots at failure point
        5. Generate report with AI suggestions
        """

    async def generate_screenshot_on_error(
        self,
        error: Exception,
        url: str
    ) -> Path:
        """
        Auto-screenshot when error occurs

        Helps visualize what user was seeing when error happened
        """

    async def update_blockers_with_visual_diff(
        self,
        regression_result: RegressionResult
    ):
        """
        Add visual regression to blockers.md

        Includes diff image for AI to analyze
        """
```

---

### Task 6: Create Screenshot Gallery Generator (2 hours)

**File:** `core/testing/gallery_generator.py`

```python
"""
Screenshot Gallery Generator

Creates visual documentation of components and pages.
"""

class GalleryGenerator:
    """Generates HTML gallery of screenshots"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    async def generate_component_gallery(
        self,
        components_dir: Path
    ) -> Path:
        """
        Screenshot all components

        1. Find all component files
        2. For each component:
           - Render with default props
           - Render with various states (hover, active, disabled, etc.)
           - Take screenshots
        3. Generate HTML gallery with organized sections
        """

    async def generate_page_gallery(
        self,
        pages: List[str]
    ) -> Path:
        """
        Screenshot all pages/routes

        Useful for documentation and change tracking
        """

    def generate_responsive_gallery(
        self,
        urls: List[str],
        viewports: List[Tuple[int, int]] = [
            (1920, 1080),  # Desktop
            (768, 1024),   # Tablet
            (375, 667),    # Mobile
        ]
    ) -> Path:
        """
        Screenshot at multiple viewport sizes

        Tests responsive design
        """

    def create_html_gallery(
        self,
        screenshots: List[ScreenshotMetadata]
    ) -> Path:
        """
        Generate HTML gallery page

        Features:
        - Grid layout
        - Filtering by component type
        - Search
        - Comparison view
        - Responsive design
        """
```

---

## BATCH 3: Documentation & Testing (Tasks 7-8, 4 hours)

### Task 7: Create Documentation (2 hours)

**File:** `docs/PLAYWRIGHT_DEBUGGING.md`

```markdown
# Playwright Visual Debugging

## Overview

BuildRunner integrates Playwright for browser-based testing and visual debugging.

## Quick Start

### Visual Regression Testing

```bash
# Take baseline screenshot
br test visual http://localhost:3000 homepage

# Make UI changes, then check for regressions
br test visual http://localhost:3000 homepage

# Update baseline if changes are intentional
br test visual http://localhost:3000 homepage --update-baseline
```

### Recording Tests

```bash
# Start recording (opens browser)
br test record http://localhost:3000 user-signup

# Interact with app in browser
# Recording stops after 60 seconds or when you close browser

# Replay recording
br test replay user-signup

# Convert to Playwright script
br test export user-signup
```

### Component Testing

```bash
# Test single component
br test component src/components/Button.tsx

# Test with custom props
br test component src/components/Card.tsx '{"title": "Test", "body": "Content"}'
```

### Screenshot Gallery

```bash
# Generate gallery of all components
br test screenshot-gallery

# Opens: .buildrunner/gallery/index.html
```

## Integration with Debugging

Playwright automatically integrates with BuildRunner's debugging system:

- **File Changes**: Visual tests auto-run when components change
- **Failed Tests**: Auto-capture screenshots and network logs
- **Error Reports**: Include visual diffs in blockers.md
- **AI Context**: Screenshots added to .buildrunner/context/ for AI analysis

## Configuration

**.buildrunner/playwright.yaml:**

```yaml
visual_regression:
  diff_threshold: 0.05  # 5% difference triggers failure
  update_baseline_on_approve: true

recording:
  default_duration: 60  # seconds
  capture_network: true
  capture_console: true
  screenshot_every_step: true

component_testing:
  auto_discover: true  # Auto-find components
  test_states: [default, hover, active, disabled]
  viewports:
    - [1920, 1080]  # Desktop
    - [768, 1024]   # Tablet
    - [375, 667]    # Mobile

gallery:
  auto_generate: true
  update_on_change: true
  organize_by: component_type  # or: directory, alphabetical
```

## Examples

### Auto-Test Generated Code

When BuildRunner generates a new component:

```python
from core.testing import PlaywrightRunner

# BuildRunner automatically:
runner = PlaywrightRunner(project_root)

# 1. Tests component renders without errors
result = await runner.test_component("src/components/NewButton.tsx")

# 2. Takes baseline screenshot
await runner.run_visual_regression_test(
    "http://localhost:3000/storybook/NewButton",
    "new-button-baseline"
)

# 3. Adds to screenshot gallery
await gallery.add_component("NewButton", result.screenshot)
```

### Debugging Failed Tests

```bash
# Test fails - BuildRunner auto-debugs:
br test visual http://localhost:3000/dashboard dashboard

# Output:
# ❌ Visual regression detected (12.5% difference)
# 📸 Diff: .buildrunner/screenshots/dashboard-diff.png
# 🌐 Network: .buildrunner/network/dashboard.har
# 📝 Console: .buildrunner/console/dashboard.log
# 🤖 AI Analysis: See .buildrunner/context/blockers.md
```

## Best Practices

1. **Baseline Management**
   - Store baselines in git
   - Update baselines intentionally (not automatically)
   - Review diffs carefully before approving

2. **Test Organization**
   - Group related tests
   - Use descriptive names
   - Keep recordings under 2 minutes

3. **Performance**
   - Run visual tests on critical paths only
   - Use perceptual hashing for fast comparisons
   - Cache browser binaries

4. **CI/CD Integration**
   - Run visual tests in headless mode
   - Fail builds on regressions
   - Archive screenshots as artifacts

## API Reference

See `core/testing/playwright_runner.py` for full API documentation.
```

---

### Task 8: Write Comprehensive Tests (2 hours)

**Files:**
- `tests/test_playwright_runner.py` (150+ lines)
- `tests/test_visual_regression.py` (120+ lines)
- `tests/test_recorder.py` (100+ lines)
- `tests/test_gallery_generator.py` (80+ lines)

**Coverage Target:** 90%+

**Test Scenarios:**
- Visual regression detection (with/without changes)
- Screenshot comparison accuracy
- Recording and replay functionality
- Component isolation testing
- Network traffic capture
- Console log collection
- Gallery generation with multiple viewports
- Integration with error watcher
- CLI command execution
- Configuration loading

---

## Verification Gates

### Verification Gate 1 (After Batch 1)
- [ ] PlaywrightRunner class created with all methods
- [ ] VisualRegressionTester working
- [ ] TestRecorder can record and replay
- [ ] All unit tests passing
- [ ] 90%+ code coverage

### Verification Gate 2 (After Batch 2)
- [ ] CLI commands functional
- [ ] Integration with error watcher working
- [ ] Screenshot gallery generates correctly
- [ ] Auto-testing on file changes works
- [ ] All tests passing

### Final Verification
- [ ] All documentation complete
- [ ] Integration tests passing
- [ ] Example recordings created
- [ ] CLAUDE.md updated
- [ ] No import errors
- [ ] Performance acceptable (tests run in < 30s)

---

## Acceptance Criteria

✅ **Visual Regression:**
- Detects UI changes accurately
- Generates useful diff images
- Configurable threshold
- Baseline management works

✅ **Recording:**
- Records all user actions
- Captures network traffic
- Saves screenshots
- Replays accurately
- Exports to Playwright scripts

✅ **Component Testing:**
- Tests components in isolation
- Verifies rendering
- Checks accessibility
- Multiple viewport sizes

✅ **Integration:**
- Works with error watcher
- Updates blockers.md
- Adds to AI context
- Auto-runs on file changes

✅ **Gallery:**
- Screenshots all components
- Responsive layouts
- Search and filter
- Auto-updates

✅ **Performance:**
- Visual tests run in < 10s
- Recording starts in < 3s
- Gallery generates in < 30s

---

## Commit & Push

```bash
git add .
git commit -m "feat: Add Playwright visual debugging system

- Visual regression testing with screenshot diffs
- E2E test recording and replay
- Component isolation testing
- Network traffic monitoring
- Console log capture
- Screenshot gallery generator
- Integration with error watcher
- CLI commands for all features
- 90%+ test coverage

🤖 Generated with Claude Code"

git push -u origin build/v3.1-playwright-debug
```

---

## Metrics

**Files Created:** 11
- core/testing/playwright_runner.py (~400 lines)
- core/testing/visual_regression.py (~300 lines)
- core/testing/test_recorder.py (~250 lines)
- core/testing/playwright_integration.py (~200 lines)
- core/testing/gallery_generator.py (~300 lines)
- cli/playwright_commands.py (~200 lines)
- docs/PLAYWRIGHT_DEBUGGING.md (~500 lines)
- tests/test_playwright_runner.py (~150 lines)
- tests/test_visual_regression.py (~120 lines)
- tests/test_recorder.py (~100 lines)
- tests/test_gallery_generator.py (~80 lines)

**Total Lines:** ~2,600 lines
**Test Coverage:** 90%+
**Duration:** 16 hours (1 week)

---

## Next Steps

After merging:
1. Add Playwright to BUILD_PLAN.md enhancement features ✅ (Already done)
2. Update CHANGELOG.md
3. Tag as part of v3.1.0-alpha.3
4. Test integration with Design System (Week 4 Build 4C)

---

*This build plan follows the atomic task methodology from BUILD_PLAN_V3.1-V3.4_ATOMIC.md*
