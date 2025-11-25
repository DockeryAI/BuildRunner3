#!/usr/bin/env python3
"""
Pre-commit hook for AI Code Review System

This hook runs AI-powered code review on staged files before commit.
It checks:
- Code patterns and architecture
- Performance issues
- Code smells
- Security vulnerabilities

Returns non-zero exit code if critical issues are found.
"""
import sys
import os
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_code_review import CodeReviewer, CodeReviewError
from core.pattern_analyzer import PatternAnalyzer
from core.performance_analyzer import PerformanceAnalyzer
from core.code_smell_detector import CodeSmellDetector
from core.security_scanner import SecurityScanner


def get_staged_python_files():
    """Get list of staged Python files"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = result.stdout.strip().split("\n")
        return [f for f in files if f.endswith(".py") and f]
    except subprocess.CalledProcessError:
        return []


def analyze_file(file_path: str) -> dict:
    """
    Analyze a single file with all analyzers

    Args:
        file_path: Path to file

    Returns:
        Dict with analysis results and overall pass/fail
    """
    results = {"file": file_path, "passed": True, "issues": []}

    # Pattern analysis
    try:
        pattern_analyzer = PatternAnalyzer()
        pattern_result = pattern_analyzer.analyze_file(file_path)

        if pattern_result["separation_score"] < 50:
            results["passed"] = False
            results["issues"].append(
                f"Low separation score: {pattern_result['separation_score']}/100"
            )

        if pattern_result["violations"]:
            results["passed"] = False
            results["issues"].append(f"{len(pattern_result['violations'])} layer violation(s)")
    except Exception as e:
        results["issues"].append(f"Pattern analysis error: {e}")

    # Performance analysis
    try:
        perf_analyzer = PerformanceAnalyzer()
        perf_result = perf_analyzer.analyze_file(file_path)

        if perf_result["performance_score"] < 50:
            results["passed"] = False
            results["issues"].append(
                f"Low performance score: {perf_result['performance_score']}/100"
            )

        # Check for critical performance issues
        critical_perf = [
            i for i in perf_result.get("n_plus_one_queries", []) if i.get("severity") == "high"
        ]
        if critical_perf:
            results["passed"] = False
            results["issues"].append(f"{len(critical_perf)} N+1 query issue(s)")

    except Exception as e:
        results["issues"].append(f"Performance analysis error: {e}")

    # Code smell detection
    try:
        smell_detector = CodeSmellDetector()
        smell_result = smell_detector.analyze_file(file_path)

        if smell_result["smell_score"] < 60:
            results["passed"] = False
            results["issues"].append(f"Low smell score: {smell_result['smell_score']}/100")

        # Check for god classes
        if smell_result["god_classes"]:
            results["issues"].append(f"{len(smell_result['god_classes'])} god class(es)")

    except Exception as e:
        results["issues"].append(f"Code smell analysis error: {e}")

    # Security scan
    try:
        security_scanner = SecurityScanner()
        security_result = security_scanner.analyze_file(file_path)

        # Any critical security issue fails the commit
        critical_security = []
        for category in ["sql_injection", "command_injection", "hardcoded_secrets", "eval_usage"]:
            critical_security.extend(security_result.get(category, []))

        if critical_security:
            results["passed"] = False
            results["issues"].append(
                f"CRITICAL: {len(critical_security)} security issue(s) detected"
            )

    except Exception as e:
        results["issues"].append(f"Security scan error: {e}")

    return results


def main():
    """Main pre-commit hook"""
    print("🤖 Running AI Code Review...")

    # Get staged files
    staged_files = get_staged_python_files()

    if not staged_files:
        print("✅ No Python files to review")
        return 0

    print(f"📝 Analyzing {len(staged_files)} file(s)...")

    # Analyze each file
    all_passed = True
    results = []

    for file_path in staged_files:
        if not Path(file_path).exists():
            continue

        print(f"  Checking: {file_path}")
        result = analyze_file(file_path)
        results.append(result)

        if not result["passed"]:
            all_passed = False

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Review Summary")
    print("=" * 60)

    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"\n{status}: {result['file']}")

        if result["issues"]:
            for issue in result["issues"]:
                print(f"  - {issue}")

    print("\n" + "=" * 60)

    if all_passed:
        print("✅ All checks passed! Proceeding with commit...")
        return 0
    else:
        print("❌ Code review found issues. Fix them before committing.")
        print("\nTo bypass this hook (not recommended):")
        print("  git commit --no-verify")
        return 1


if __name__ == "__main__":
    sys.exit(main())
