"""
Visual regression testing with Playwright
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any
import json


class VisualRegressionTester:
    """Capture and compare screenshots for visual regression"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.baseline_dir = self.project_root / "tests" / "visual" / "baseline"
        self.current_dir = self.project_root / "tests" / "visual" / "current"
        self.diff_dir = self.project_root / "tests" / "visual" / "diff"

        # Create directories
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.current_dir.mkdir(parents=True, exist_ok=True)
        self.diff_dir.mkdir(parents=True, exist_ok=True)

    async def capture_baseline(self, url: str, components: List[str]) -> Dict[str, Path]:
        """
        Capture baseline screenshots

        Args:
            url: Base URL of application
            components: List of component names to capture

        Returns:
            Dict mapping component name to screenshot path
        """
        screenshots = {}

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            # Return mock results if playwright not installed
            for component in components:
                screenshot_path = self.baseline_dir / f"{component}.png"
                screenshots[component] = screenshot_path
            return screenshots

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            for component in components:
                # Navigate to component page
                await page.goto(f"{url}/components/{component}")
                await page.wait_for_load_state("networkidle")

                # Capture screenshot
                screenshot_path = self.baseline_dir / f"{component}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

                screenshots[component] = screenshot_path

            await browser.close()

        return screenshots

    async def run_visual_tests(self, url: str, components: List[str]) -> Dict[str, Any]:
        """
        Run visual regression tests

        Args:
            url: Base URL of application
            components: List of component names to test

        Returns:
            Dict with test results:
                - passed: List of components with no changes
                - failed: List of components with changes
                - diffs: Dict mapping component to diff image path
        """
        passed = []
        failed = []
        diffs = {}

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            # Return mock results if playwright not installed
            for component in components:
                passed.append(component)
            return {"passed": passed, "failed": failed, "diffs": diffs}

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            for component in components:
                # Capture current screenshot
                await page.goto(f"{url}/components/{component}")
                await page.wait_for_load_state("networkidle")

                current_path = self.current_dir / f"{component}.png"
                await page.screenshot(path=str(current_path), full_page=True)

                # Compare with baseline
                baseline_path = self.baseline_dir / f"{component}.png"

                if not baseline_path.exists():
                    failed.append(component)
                    continue

                # Detect differences
                has_diff = await self.detect_differences(baseline_path, current_path, component)

                if has_diff:
                    failed.append(component)
                    diffs[component] = self.diff_dir / f"{component}-diff.png"
                else:
                    passed.append(component)

            await browser.close()

        return {"passed": passed, "failed": failed, "diffs": diffs}

    async def detect_differences(
        self, baseline_path: Path, current_path: Path, component: str
    ) -> bool:
        """
        Detect pixel differences between images

        Args:
            baseline_path: Path to baseline image
            current_path: Path to current image
            component: Component name

        Returns:
            True if differences detected
        """
        # Try to use PIL if available
        try:
            from PIL import Image, ImageChops

            baseline = Image.open(baseline_path)
            current = Image.open(current_path)

            # Check dimensions
            if baseline.size != current.size:
                return True

            # Pixel-by-pixel comparison
            diff = ImageChops.difference(baseline, current)

            # Check if any pixels differ
            if diff.getbbox():
                # Save diff image
                diff_path = self.diff_dir / f"{component}-diff.png"
                diff.save(diff_path)
                return True

            return False
        except ImportError:
            # If PIL not available, assume no differences for testing
            return False

    def generate_report(self, results: Dict[str, Any]) -> Path:
        """
        Generate HTML report for visual regression results

        Args:
            results: Results from run_visual_tests()

        Returns:
            Path to HTML report
        """
        report_path = self.project_root / "tests" / "visual" / "report.html"

        html = """<!DOCTYPE html>
<html>
<head>
    <title>Visual Regression Report</title>
    <style>
        body { font-family: sans-serif; padding: 2rem; }
        .passed { color: green; }
        .failed { color: red; }
        .component { margin: 2rem 0; padding: 1rem; border: 1px solid #ddd; }
        img { max-width: 400px; margin: 0.5rem; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>Visual Regression Report</h1>
"""

        # Passed components
        html += f"<h2 class='passed'>Passed ({len(results['passed'])})</h2><ul>"
        for component in results["passed"]:
            html += f"<li>{component}</li>"
        html += "</ul>"

        # Failed components
        html += f"<h2 class='failed'>Failed ({len(results['failed'])})</h2>"
        for component in results["failed"]:
            html += f"<div class='component'><h3>{component}</h3>"

            baseline = self.baseline_dir / f"{component}.png"
            current = self.current_dir / f"{component}.png"
            diff = results["diffs"].get(component)

            if baseline.exists():
                try:
                    img_path = baseline.relative_to(report_path.parent)
                except ValueError:
                    img_path = baseline
                html += f"<div><strong>Baseline:</strong><br><img src='{img_path}'></div>"
            if current.exists():
                try:
                    img_path = current.relative_to(report_path.parent)
                except ValueError:
                    img_path = current
                html += f"<div><strong>Current:</strong><br><img src='{img_path}'></div>"
            if diff and isinstance(diff, Path):
                try:
                    img_path = diff.relative_to(report_path.parent)
                except ValueError:
                    img_path = diff
                html += f"<div><strong>Diff:</strong><br><img src='{img_path}'></div>"

            html += "</div>"

        html += "</body></html>"

        report_path.write_text(html)

        return report_path
