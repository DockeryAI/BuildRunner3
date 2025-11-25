"""
Automatic Post-Build Debugging Pipeline
Context-aware testing and validation after builds
"""

import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.build_context_detector import (
    BuildContextDetector,
    BuildContext,
    BuildType,
    TechStack
)
from core.typescript_checker import TypeScriptChecker, TypeScriptCheckResult
from core.code_quality import QualityGate
from core.gap_analyzer import GapAnalyzer
import re
from collections import defaultdict
from typing import Tuple


@dataclass
class CheckResult:
    """Result of a single check"""
    name: str
    passed: bool
    duration_ms: float
    errors: List[str]
    warnings: List[str]
    info: List[str]
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class AutoDebugReport:
    """Complete auto-debug report"""
    timestamp: str
    build_context: BuildContext
    checks_run: List[CheckResult]
    overall_success: bool
    total_duration_ms: float
    critical_failures: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]


@dataclass
class RetryStrategy:
    """Strategy for retrying a failed command"""
    type: str  # timeout, import_error, type_error, network_error, generic
    actions: Dict[str, bool]  # Actions to take
    confidence: float  # 0.0 to 1.0
    explanation: str  # Human-readable explanation


@dataclass
class ErrorContext:
    """Context of an error from a debug session"""
    command: str
    exit_code: int
    log: str
    working_dir: str
    timestamp: str
    file: Optional[str] = None


@dataclass
class HotSpot:
    """A location with frequent failures"""
    location: str  # file path or command
    type: str  # 'file' or 'cmd'
    failure_count: int
    severity: str  # 'high', 'medium', 'low'


@dataclass
class TrendReport:
    """Error trends over time"""
    weekly_breakdown: Dict[str, Dict[str, int]]
    most_common_type: str
    trend_direction: str  # 'improving' or 'worsening'


@dataclass
class ProjectInsights:
    """Comprehensive project debugging insights"""
    hot_spots: List[HotSpot]
    error_trends: TrendReport
    success_rates: Dict[str, float]
    recommendations: List[str]


class RetryAnalyzer:
    """Analyze failures and suggest intelligent retry strategies"""

    PATTERNS = {
        'timeout': {
            'detection': r'(timeout|timed out|deadline exceeded|ETIMEDOUT)',
            'strategy': {
                'increase_timeout': True,
                'exponential_backoff': True,
                'max_retries': 3
            },
            'explanation': 'Operation timed out. Try increasing timeout and adding exponential backoff.'
        },
        'import_error': {
            'detection': r'(ModuleNotFoundError|ImportError|Cannot find module|cannot resolve|ENOENT.*node_modules)',
            'strategy': {
                'check_dependencies': True,
                'install_missing': True,
                'verify_paths': True
            },
            'explanation': 'Module/package not found. Check dependencies and install missing packages.'
        },
        'type_error': {
            'detection': r'(TypeError|type error|expected .+ got|Property .* does not exist)',
            'strategy': {
                'run_type_checker': True,
                'suggest_type_hints': True
            },
            'explanation': 'Type mismatch detected. Run type checker to identify all type issues.'
        },
        'network_error': {
            'detection': r'(ConnectionError|NetworkError|ECONNREFUSED|ENOTFOUND|fetch failed|network)',
            'strategy': {
                'retry_with_backoff': True,
                'check_connectivity': True,
                'max_retries': 5
            },
            'explanation': 'Network connection failed. Verify connectivity and retry with exponential backoff.'
        },
        'permission_error': {
            'detection': r'(PermissionError|EACCES|permission denied|access denied)',
            'strategy': {
                'check_permissions': True,
                'suggest_sudo': True
            },
            'explanation': 'Permission denied. Check file/directory permissions or run with appropriate privileges.'
        },
        'syntax_error': {
            'detection': r'(SyntaxError|Unexpected token|Unexpected identifier|Parse error)',
            'strategy': {
                'run_linter': True,
                'check_syntax': True
            },
            'explanation': 'Syntax error in code. Run linter to identify all syntax issues.'
        }
    }

    def analyze_failure(self, error_log: str, context: ErrorContext) -> RetryStrategy:
        """
        Analyze error log and return actionable retry strategy

        Args:
            error_log: Full error output
            context: Error context with command, exit code, etc.

        Returns:
            RetryStrategy with specific actions to take
        """
        # Check each pattern
        for pattern_type, config in self.PATTERNS.items():
            if re.search(config['detection'], error_log, re.IGNORECASE):
                return RetryStrategy(
                    type=pattern_type,
                    actions=config['strategy'],
                    confidence=self._calculate_confidence(error_log, config),
                    explanation=config['explanation']
                )

        # No specific pattern match - generic retry
        return RetryStrategy(
            type='generic',
            actions={'retry_as_is': True},
            confidence=0.3,
            explanation="No specific pattern detected. Consider reviewing the full error log."
        )

    def _calculate_confidence(self, error_log: str, config: dict) -> float:
        """Calculate confidence score for pattern match"""
        # Count number of pattern matches
        matches = len(re.findall(config['detection'], error_log, re.IGNORECASE))

        # More matches = higher confidence (capped at 0.95)
        confidence = min(0.95, 0.6 + (matches * 0.1))
        return confidence

    def suggest_fix_command(self, strategy: RetryStrategy, context: ErrorContext) -> str:
        """Generate specific fix command based on strategy"""
        if strategy.type == 'import_error':
            # Detect package manager from context
            if 'package.json' in context.log or 'npm' in context.command:
                return f"cd {context.working_dir} && npm install"
            elif 'requirements.txt' in context.log or 'pip' in context.command:
                return f"cd {context.working_dir} && pip install -r requirements.txt"
            else:
                return f"cd {context.working_dir} && npm install"  # default

        elif strategy.type == 'timeout':
            # Add timeout flag if not present
            if '--timeout' in context.command:
                return context.command.replace('--timeout', '--timeout 120')
            else:
                return f"{context.command} --timeout 60"

        elif strategy.type == 'type_error':
            # Run type checker
            if 'tsc' in context.log or '.ts' in context.log:
                return f"cd {context.working_dir} && npx tsc --noEmit"
            else:
                return f"cd {context.working_dir} && mypy ."

        elif strategy.type == 'permission_error':
            return f"sudo {context.command}"

        elif strategy.type == 'syntax_error':
            if '.py' in context.log:
                return f"cd {context.working_dir} && ruff check ."
            else:
                return f"cd {context.working_dir} && npx eslint ."

        else:
            # Generic retry
            return context.command


class SessionAnalyzer:
    """Analyze patterns across multiple debug sessions"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.sessions_dir = self.project_root / '.buildrunner' / 'debug-sessions'

    def analyze_project_patterns(self) -> ProjectInsights:
        """
        Analyze all debug sessions for a project

        Returns:
            ProjectInsights with hot spots, trends, success rates
        """
        sessions = self._load_all_sessions()

        if not sessions:
            return ProjectInsights(
                hot_spots=[],
                error_trends=TrendReport(
                    weekly_breakdown={},
                    most_common_type='none',
                    trend_direction='stable'
                ),
                success_rates={},
                recommendations=["No debug sessions found. Run 'br autodebug run' to start tracking."]
            )

        return ProjectInsights(
            hot_spots=self._find_hot_spots(sessions),
            error_trends=self._analyze_trends(sessions),
            success_rates=self._calculate_rates(sessions),
            recommendations=self._generate_recommendations(sessions)
        )

    def _load_all_sessions(self) -> List[Dict[str, Any]]:
        """Load all debug session reports"""
        if not self.sessions_dir.exists():
            return []

        sessions = []
        for report_file in self.sessions_dir.glob('autodebug_*.json'):
            try:
                with open(report_file) as f:
                    sessions.append(json.load(f))
            except Exception as e:
                print(f"Warning: Could not load {report_file}: {e}")
                continue

        return sessions

    def _find_hot_spots(self, sessions: List[Dict]) -> List[HotSpot]:
        """Find files/commands that fail frequently"""
        failure_counts = defaultdict(int)

        for session in sessions:
            checks = session.get('checks_run', [])
            for check in checks:
                if not check.get('passed', True) and not check.get('skipped', False):
                    # Track by check name
                    check_name = check.get('name', 'unknown')
                    failure_counts[f"check:{check_name}"] += 1

                    # Track by file if error mentions a file
                    for error in check.get('errors', []):
                        # Try to extract file path from error message
                        file_match = re.search(r'([a-zA-Z0-9_/.-]+\.(py|ts|tsx|js|jsx)):', str(error))
                        if file_match:
                            file_path = file_match.group(1)
                            failure_counts[f"file:{file_path}"] += 1

        # Return top 10 hot spots
        hot_spots = []
        for key, count in sorted(failure_counts.items(), key=lambda x: -x[1])[:10]:
            parts = key.split(':', 1)
            spot_type = parts[0]
            location = parts[1] if len(parts) > 1 else 'unknown'

            severity = 'high' if count > 10 else 'medium' if count > 5 else 'low'

            hot_spots.append(HotSpot(
                location=location,
                type=spot_type,
                failure_count=count,
                severity=severity
            ))

        return hot_spots

    def _analyze_trends(self, sessions: List[Dict]) -> TrendReport:
        """Analyze error trends over time"""
        weekly_errors = defaultdict(lambda: defaultdict(int))

        for session in sessions:
            # Parse timestamp
            timestamp_str = session.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                week = timestamp.strftime('%Y-W%W')
            except:
                week = 'unknown'

            # Classify errors
            checks = session.get('checks_run', [])
            for check in checks:
                if not check.get('passed', True):
                    check_type = check.get('name', 'unknown').split('_')[0]
                    weekly_errors[week][check_type] += 1

        # Find most common error type
        all_errors = defaultdict(int)
        for week_data in weekly_errors.values():
            for error_type, count in week_data.items():
                all_errors[error_type] += count

        most_common = max(all_errors.items(), key=lambda x: x[1])[0] if all_errors else 'none'

        # Determine trend direction
        trend = self._calculate_trend(weekly_errors)

        return TrendReport(
            weekly_breakdown=dict(weekly_errors),
            most_common_type=most_common,
            trend_direction=trend
        )

    def _calculate_trend(self, weekly_errors: Dict[str, Dict[str, int]]) -> str:
        """Determine if errors are improving or worsening"""
        if len(weekly_errors) < 2:
            return 'stable'

        # Get sorted weeks
        weeks = sorted(weekly_errors.keys())

        # Compare recent vs older
        recent_total = sum(weekly_errors[weeks[-1]].values()) if weeks else 0
        older_total = sum(weekly_errors[weeks[0]].values()) if len(weeks) > 1 else recent_total

        if recent_total < older_total * 0.8:
            return 'improving'
        elif recent_total > older_total * 1.2:
            return 'worsening'
        else:
            return 'stable'

    def _calculate_rates(self, sessions: List[Dict]) -> Dict[str, float]:
        """Calculate success rates by check type"""
        check_stats = defaultdict(lambda: {'passed': 0, 'total': 0})

        for session in sessions:
            checks = session.get('checks_run', [])
            for check in checks:
                if not check.get('skipped', False):
                    check_name = check.get('name', 'unknown')
                    check_stats[check_name]['total'] += 1
                    if check.get('passed', False):
                        check_stats[check_name]['passed'] += 1

        # Calculate success rates
        success_rates = {}
        for check_name, stats in check_stats.items():
            if stats['total'] > 0:
                success_rates[check_name] = (stats['passed'] / stats['total']) * 100

        return success_rates

    def _generate_recommendations(self, sessions: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on patterns"""
        recommendations = []

        # Check if any sessions exist
        if not sessions:
            return ["No debug sessions found. Run 'br autodebug run' to start tracking."]

        # Analyze recent failures
        recent_session = sessions[-1] if sessions else {}
        checks = recent_session.get('checks_run', [])
        failed_checks = [c for c in checks if not c.get('passed', True) and not c.get('skipped', False)]

        if failed_checks:
            recommendations.append(f"Fix {len(failed_checks)} failing checks before next build")

        # Check success rates
        success_rates = self._calculate_rates(sessions)
        for check_name, rate in success_rates.items():
            if rate < 50:
                recommendations.append(f"Low success rate for {check_name} ({rate:.0f}%) - consider investigation")

        # Check for consistent failures
        hot_spots = self._find_hot_spots(sessions)
        high_severity_spots = [h for h in hot_spots if h.severity == 'high']
        if high_severity_spots:
            recommendations.append(f"Address {len(high_severity_spots)} high-severity failure hot spots")

        if not recommendations:
            recommendations.append("No critical issues detected. Keep up the good work!")

        return recommendations


class ToolSelector:
    """Selects appropriate tools based on build context"""

    def __init__(self, context: BuildContext):
        self.context = context

    def select_immediate_checks(self) -> List[str]:
        """Select checks that run in < 5 seconds"""
        checks = ["syntax", "imports"]

        if self.context.has_frontend_changes:
            checks.append("typescript_quick")

        if self.context.has_backend_changes:
            checks.append("python_syntax")

        return checks

    def select_quick_checks(self) -> List[str]:
        """Select checks that run in < 30 seconds"""
        checks = []

        # Python tests
        if self.context.has_backend_changes and self.context.has_test_changes:
            checks.append("pytest_changed")

        # TypeScript/Linting
        if self.context.has_frontend_changes:
            checks.append("typescript_full")
            checks.append("eslint")

        # Code quality on changed files only
        if self.context.python_files:
            checks.append("quality_changed")

        return checks

    def select_deep_checks(self) -> List[str]:
        """Select comprehensive checks that run in < 2 minutes"""
        checks = []

        # Full test suites
        if TechStack.PYTEST in self.context.tech_stack:
            checks.append("pytest_full")

        if TechStack.JEST in self.context.tech_stack:
            checks.append("jest_full")

        # Gap analysis
        if self.context.has_backend_changes or self.context.has_frontend_changes:
            checks.append("gap_analysis")

        # Full quality scan
        checks.append("quality_full")

        # Integration tests if full-stack
        if self.context.build_type == BuildType.FULL_STACK:
            checks.append("integration_tests")

        return checks

    def should_skip_check(self, check_name: str) -> tuple[bool, str]:
        """Determine if a check should be skipped"""
        # Skip TypeScript checks for Python-only changes
        if check_name.startswith("typescript") or check_name == "eslint":
            if not self.context.has_frontend_changes:
                return True, "No frontend changes"

        # Skip Python checks for TypeScript-only changes
        if check_name.startswith("python") or check_name.startswith("pytest"):
            if not self.context.has_backend_changes:
                return True, "No backend changes"

        # Skip API tests for CSS-only changes
        if check_name == "integration_tests":
            if all(f.suffix in {'.css', '.scss', '.sass'} for f in self.context.changed_files):
                return True, "CSS-only changes"

        # Skip database checks if no database changes
        if check_name == "database_migration":
            if not self.context.has_database_changes:
                return True, "No database changes"

        # Skip tests if only docs changed
        if self.context.build_type == BuildType.DOCUMENTATION:
            if check_name in {"pytest_full", "jest_full", "integration_tests"}:
                return True, "Documentation-only changes"

        return False, ""


class AutoDebugPipeline:
    """Main auto-debug pipeline orchestrator"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.context_detector = BuildContextDetector(project_root)
        self.ts_checker = TypeScriptChecker(project_root)
        self.quality_gate = QualityGate()  # Fixed: QualityGate doesn't take project_root
        self.gap_analyzer = GapAnalyzer(project_root)

    def run(
        self,
        files: Optional[List[str]] = None,
        skip_deep: bool = False
    ) -> AutoDebugReport:
        """
        Run the complete auto-debug pipeline

        Args:
            files: Specific files to check (None = detect from git)
            skip_deep: Skip deep verification checks
        """
        start_time = time.time()

        # Detect build context
        if files:
            context = self.context_detector.detect_from_files(files)
        else:
            context = self.context_detector.detect_from_git()

        print(f"🔍 Detected build type: {context.build_type.value}")
        print(f"📦 Tech stack: {', '.join(t.value for t in context.tech_stack)}")
        print(f"📝 Changed files: {len(context.changed_files)}")

        # Select tools
        selector = ToolSelector(context)
        immediate_checks = selector.select_immediate_checks()
        quick_checks = selector.select_quick_checks()
        deep_checks = selector.select_deep_checks() if not skip_deep else []

        # Run checks in tiers
        results = []

        # Tier 1: Immediate (< 5s)
        print("\n⚡ Running immediate checks...")
        results.extend(self._run_checks(immediate_checks, selector))

        # Check for critical failures
        critical = [r for r in results if not r.passed and not r.skipped]
        if critical:
            print(f"\n❌ Critical failures detected: {len(critical)}")
            return self._generate_report(context, results, start_time, critical)

        # Tier 2: Quick (< 30s)
        print("\n🚀 Running quick validation...")
        results.extend(self._run_checks(quick_checks, selector))

        # Tier 3: Deep (< 2min)
        if deep_checks:
            print("\n🔬 Running deep verification...")
            results.extend(self._run_checks(deep_checks, selector))

        # Generate final report
        total_duration = (time.time() - start_time) * 1000
        critical_failures = [r.name for r in results if not r.passed and not r.skipped]

        return self._generate_report(context, results, start_time, critical_failures)

    def _run_checks(
        self,
        check_names: List[str],
        selector: ToolSelector
    ) -> List[CheckResult]:
        """Run a list of checks in parallel where possible"""
        results = []

        # Separate parallel-safe from sequential checks
        parallel_checks = []
        sequential_checks = []

        for check_name in check_names:
            # Skip if not applicable
            should_skip, reason = selector.should_skip_check(check_name)
            if should_skip:
                results.append(CheckResult(
                    name=check_name,
                    passed=True,
                    duration_ms=0,
                    errors=[],
                    warnings=[],
                    info=[],
                    skipped=True,
                    skip_reason=reason
                ))
                continue

            # Categorize
            if check_name in {"pytest_full", "jest_full", "integration_tests"}:
                sequential_checks.append(check_name)
            else:
                parallel_checks.append(check_name)

        # Run parallel checks
        if parallel_checks:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(self._run_single_check, check): check
                    for check in parallel_checks
                }

                for future in as_completed(futures):
                    results.append(future.result())

        # Run sequential checks
        for check in sequential_checks:
            results.append(self._run_single_check(check))

        return results

    def _run_single_check(self, check_name: str) -> CheckResult:
        """Run a single check"""
        print(f"  ▸ {check_name}...", end=" ", flush=True)
        start = time.time()

        try:
            if check_name == "syntax":
                result = self._check_syntax()
            elif check_name == "imports":
                result = self._check_imports()
            elif check_name == "typescript_quick":
                result = self._check_typescript_quick()
            elif check_name == "typescript_full":
                result = self._check_typescript_full()
            elif check_name == "python_syntax":
                result = self._check_python_syntax()
            elif check_name == "pytest_changed":
                result = self._run_pytest_changed()
            elif check_name == "pytest_full":
                result = self._run_pytest_full()
            elif check_name == "eslint":
                result = self._run_eslint()
            elif check_name == "jest_full":
                result = self._run_jest()
            elif check_name == "quality_changed":
                result = self._check_quality_changed()
            elif check_name == "quality_full":
                result = self._check_quality_full()
            elif check_name == "gap_analysis":
                result = self._run_gap_analysis()
            elif check_name == "integration_tests":
                result = self._run_integration_tests()
            else:
                result = CheckResult(
                    name=check_name,
                    passed=False,
                    duration_ms=0,
                    errors=[f"Unknown check: {check_name}"],
                    warnings=[],
                    info=[]
                )

            duration = (time.time() - start) * 1000
            result.duration_ms = duration

            status = "✓" if result.passed else "✗"
            print(f"{status} ({duration:.0f}ms)")

            return result

        except Exception as e:
            duration = (time.time() - start) * 1000
            print(f"✗ Error ({duration:.0f}ms)")
            return CheckResult(
                name=check_name,
                passed=False,
                duration_ms=duration,
                errors=[f"Check failed: {str(e)}"],
                warnings=[],
                info=[]
            )

    def _check_syntax(self) -> CheckResult:
        """Check for syntax errors in all files"""
        errors = []

        for file in self.context_detector.detect_from_git().changed_files:
            if file.suffix == '.py':
                try:
                    compile(file.read_text(), str(file), 'exec')
                except SyntaxError as e:
                    errors.append(f"{file}:{e.lineno}: {e.msg}")

        return CheckResult(
            name="syntax",
            passed=len(errors) == 0,
            duration_ms=0,
            errors=errors,
            warnings=[],
            info=[]
        )

    def _check_imports(self) -> CheckResult:
        """Check if imports resolve"""
        context = self.context_detector.detect_from_git()
        errors = []

        # Check TypeScript imports
        if context.typescript_files:
            ts_errors = self.ts_checker.check_imports(context.typescript_files)
            errors.extend([f"{e.file}:{e.line}: {e.message}" for e in ts_errors])

        return CheckResult(
            name="imports",
            passed=len(errors) == 0,
            duration_ms=0,
            errors=errors,
            warnings=[],
            info=[]
        )

    def _check_typescript_quick(self) -> CheckResult:
        """Quick TypeScript check (incremental)"""
        context = self.context_detector.detect_from_git()
        result = self.ts_checker.check(
            files=context.typescript_files,
            incremental=True,
            strict=False
        )

        errors = [f"{e.file}:{e.line}: {e.message}" for e in result.errors]
        warnings = [f"{w.file}:{w.line}: {w.message}" for w in result.warnings]

        return CheckResult(
            name="typescript_quick",
            passed=result.success,
            duration_ms=0,
            errors=errors,
            warnings=warnings,
            info=[f"Checked {result.files_checked} files"]
        )

    def _check_typescript_full(self) -> CheckResult:
        """Full TypeScript check with strict mode"""
        result = self.ts_checker.check(incremental=False, strict=True)

        errors = [f"{e.file}:{e.line}: {e.message}" for e in result.errors]
        warnings = [f"{w.file}:{w.line}: {w.message}" for w in result.warnings]

        # Add type coverage info
        coverage = self.ts_checker.calculate_type_coverage()
        info = [
            f"Checked {result.files_checked} files",
            f"Type coverage: {coverage:.1f}%"
        ]

        return CheckResult(
            name="typescript_full",
            passed=result.success,
            duration_ms=0,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def _check_python_syntax(self) -> CheckResult:
        """Check Python syntax"""
        return self._check_syntax()  # Reuse syntax check

    def _run_pytest_changed(self) -> CheckResult:
        """Run pytest on changed test files only"""
        context = self.context_detector.detect_from_git()
        test_files = [str(f) for f in context.test_files if f.suffix == '.py']

        if not test_files:
            return CheckResult(
                name="pytest_changed",
                passed=True,
                duration_ms=0,
                errors=[],
                warnings=[],
                info=["No test files changed"]
            )

        # Check if pytest is available
        try:
            pytest_result = subprocess.run(
                ["pytest", "--version"],
                capture_output=True,
                text=True
            )
            if pytest_result.returncode != 0:
                return CheckResult(
                    name="pytest_changed",
                    passed=True,
                    duration_ms=0,
                    errors=[],
                    warnings=["pytest not available"],
                    info=["Skipping tests - pytest not installed"],
                    skipped=True,
                    skip_reason="pytest not available"
                )
        except FileNotFoundError:
            return CheckResult(
                name="pytest_changed",
                passed=True,
                duration_ms=0,
                errors=[],
                warnings=["pytest not available"],
                info=["Skipping tests - pytest not installed"],
                skipped=True,
                skip_reason="pytest not available"
            )

        result = subprocess.run(
            ["pytest"] + test_files + ["-v", "--tb=short"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        return CheckResult(
            name="pytest_changed",
            passed=result.returncode == 0,
            duration_ms=0,
            errors=[result.stdout + result.stderr] if result.returncode != 0 else [],
            warnings=[],
            info=[f"Ran {len(test_files)} test files"]
        )

    def _run_pytest_full(self) -> CheckResult:
        """Run full pytest suite"""
        result = subprocess.run(
            ["pytest", "-v", "--tb=short"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        return CheckResult(
            name="pytest_full",
            passed=result.returncode == 0,
            duration_ms=0,
            errors=[result.stdout + result.stderr] if result.returncode != 0 else [],
            warnings=[],
            info=["Full test suite"]
        )

    def _run_eslint(self) -> CheckResult:
        """Run ESLint on changed files"""
        context = self.context_detector.detect_from_git()
        ts_files = [str(f) for f in context.typescript_files]

        if not ts_files:
            return CheckResult(
                name="eslint",
                passed=True,
                duration_ms=0,
                errors=[],
                warnings=[],
                info=["No TypeScript files to lint"]
            )

        result = subprocess.run(
            ["npx", "eslint"] + ts_files,
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        return CheckResult(
            name="eslint",
            passed=result.returncode == 0,
            duration_ms=0,
            errors=[result.stdout] if result.returncode != 0 else [],
            warnings=[],
            info=[f"Linted {len(ts_files)} files"]
        )

    def _run_jest(self) -> CheckResult:
        """Run Jest test suite"""
        result = subprocess.run(
            ["npm", "test", "--", "--passWithNoTests"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        return CheckResult(
            name="jest_full",
            passed=result.returncode == 0,
            duration_ms=0,
            errors=[result.stdout + result.stderr] if result.returncode != 0 else [],
            warnings=[],
            info=["Jest test suite"]
        )

    def _check_quality_changed(self) -> CheckResult:
        """Run quality checks on changed files only"""
        context = self.context_detector.detect_from_git()
        python_files = [str(f) for f in context.python_files]

        if not python_files:
            return CheckResult(
                name="quality_changed",
                passed=True,
                duration_ms=0,
                errors=[],
                warnings=[],
                info=["No Python files changed"]
            )

        # Quality checks on individual files not implemented yet
        # For now, just skip this check
        # TODO: Implement per-file quality checking using CodeQualityAnalyzer
        return CheckResult(
            name="quality_changed",
            passed=True,
            duration_ms=0,
            errors=[],
            warnings=[],
            info=[f"Quality check skipped for {len(python_files)} files (not implemented)"],
            skipped=True,
            skip_reason="Per-file quality checking not implemented"
        )

    def _check_quality_full(self) -> CheckResult:
        """Run full quality checks"""
        # Quality checks not implemented in autodebug yet
        # Use 'br quality check' command instead
        # TODO: Implement full quality checking using CodeQualityAnalyzer
        return CheckResult(
            name="quality_full",
            passed=True,
            duration_ms=0,
            errors=[],
            warnings=[],
            info=["Full quality check skipped (not implemented)"],
            skipped=True,
            skip_reason="Full quality checking not implemented - use 'br quality check'"
        )

    def _run_gap_analysis(self) -> CheckResult:
        """Run gap analysis vs PRD"""
        try:
            gaps = self.gap_analyzer.analyze()

            warnings = []
            # Collect warnings from various gap types
            if gaps.missing_features:
                warnings.extend([f"Missing feature: {f.get('name', 'Unknown')}" for f in gaps.missing_features[:5]])
            if gaps.incomplete_features:
                warnings.extend([f"Incomplete feature: {f.get('name', 'Unknown')}" for f in gaps.incomplete_features[:5]])

            # Consider passing if only low-severity gaps
            passed = gaps.severity_high == 0

            errors = []
            if gaps.severity_high > 0:
                errors.append(f"{gaps.severity_high} high-severity gaps detected")

            return CheckResult(
                name="gap_analysis",
                passed=passed,
                duration_ms=0,
                errors=errors,
                warnings=warnings[:10],  # Limit warnings
                info=[f"Total gaps: {gaps.total_gaps} (High: {gaps.severity_high}, Med: {gaps.severity_medium}, Low: {gaps.severity_low})"]
            )
        except Exception as e:
            return CheckResult(
                name="gap_analysis",
                passed=False,
                duration_ms=0,
                errors=[f"Check failed: {str(e)}"],
                warnings=[],
                info=[]
            )

    def _run_integration_tests(self) -> CheckResult:
        """Run integration tests"""
        # Placeholder for integration tests
        # Would integrate with actual test framework
        return CheckResult(
            name="integration_tests",
            passed=True,
            duration_ms=0,
            errors=[],
            warnings=[],
            info=["Integration tests not yet configured"]
        )

    def _generate_report(
        self,
        context: BuildContext,
        results: List[CheckResult],
        start_time: float,
        critical_failures: List[str]
    ) -> AutoDebugReport:
        """Generate final report"""
        total_duration = (time.time() - start_time) * 1000
        overall_success = all(r.passed or r.skipped for r in results)

        # Generate suggestions
        suggestions = []
        if not overall_success:
            suggestions.append("Fix errors before committing")

        for result in results:
            if not result.passed and result.warnings:
                suggestions.append(f"Address warnings in {result.name}")

        return AutoDebugReport(
            timestamp=datetime.now().isoformat(),
            build_context=context,
            checks_run=results,
            overall_success=overall_success,
            total_duration_ms=total_duration,
            critical_failures=critical_failures,
            suggestions=suggestions,
            metadata={
                "files_changed": len(context.changed_files),
                "checks_run": len([r for r in results if not r.skipped]),
                "checks_skipped": len([r for r in results if r.skipped]),
                "total_errors": sum(len(r.errors) for r in results),
                "total_warnings": sum(len(r.warnings) for r in results)
            }
        )

    def save_report(self, report: AutoDebugReport) -> Path:
        """Save report to disk"""
        reports_dir = self.project_root / ".buildrunner" / "build-reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"autodebug_{timestamp}.json"

        # Convert dataclasses to dict for JSON serialization
        report_dict = asdict(report)
        report_dict['build_context'] = str(report.build_context.build_type.value)

        with open(report_file, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)

        return report_file
