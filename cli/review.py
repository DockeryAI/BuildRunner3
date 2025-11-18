#!/usr/bin/env python3
"""
AI Code Review CLI

Command-line interface for running code reviews manually.

Usage:
    python -m cli.review file <path>           # Review a single file
    python -m cli.review diff                  # Review staged changes
    python -m cli.review pattern <path>        # Run pattern analysis only
    python -m cli.review performance <path>    # Run performance analysis only
    python -m cli.review smells <path>         # Run code smell detection only
    python -m cli.review security <path>       # Run security scan only
    python -m cli.review install-hook          # Install pre-commit hook
"""
import sys
import os
import argparse
import subprocess
from pathlib import Path
from typing import Optional
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_code_review import CodeReviewer, CodeReviewError
from core.pattern_analyzer import PatternAnalyzer
from core.performance_analyzer import PerformanceAnalyzer
from core.code_smell_detector import CodeSmellDetector
from core.security_scanner import SecurityScanner


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def review_file(file_path: str, verbose: bool = False):
    """Review a single file comprehensively"""
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return 1

    print(f"🤖 Analyzing: {file_path}")

    overall_score = 0
    score_count = 0

    # Pattern Analysis
    print_section("Pattern Analysis")
    try:
        analyzer = PatternAnalyzer()
        result = analyzer.analyze_file(str(file_path))

        print(f"Separation Score: {result['separation_score']}/100")

        if result['patterns']:
            print(f"\nDetected Patterns ({len(result['patterns'])}):")
            for pattern in result['patterns']:
                print(f"  • {pattern['pattern_type']}: {pattern['description']}")
                print(f"    Confidence: {pattern['confidence']:.0%}")

        if result['violations']:
            print(f"\n⚠️  Layer Violations ({len(result['violations'])}):")
            for violation in result['violations']:
                print(f"  • [{violation['severity'].upper()}] {violation['description']}")

        overall_score += result['separation_score']
        score_count += 1

    except Exception as e:
        print(f"❌ Pattern analysis failed: {e}")

    # Performance Analysis
    print_section("Performance Analysis")
    try:
        analyzer = PerformanceAnalyzer()
        result = analyzer.analyze_file(str(file_path))

        print(f"Performance Score: {result['performance_score']}/100")

        if result['complexity_issues']:
            print(f"\n⚠️  Complexity Issues ({len(result['complexity_issues'])}):")
            for issue in result['complexity_issues']:
                print(f"  • [{issue['severity'].upper()}] {issue['description']}")
                if verbose:
                    print(f"    Location: {issue['location']}")

        if result['n_plus_one_queries']:
            print(f"\n⚠️  N+1 Query Issues ({len(result['n_plus_one_queries'])}):")
            for issue in result['n_plus_one_queries']:
                print(f"  • {issue['description']}")

        if result['memory_leaks']:
            print(f"\n⚠️  Memory Leak Indicators ({len(result['memory_leaks'])}):")
            for issue in result['memory_leaks']:
                print(f"  • {issue['description']}")

        overall_score += result['performance_score']
        score_count += 1

    except Exception as e:
        print(f"❌ Performance analysis failed: {e}")

    # Code Smell Detection
    print_section("Code Smell Detection")
    try:
        detector = CodeSmellDetector()
        result = detector.analyze_file(str(file_path))

        print(f"Smell Score: {result['smell_score']}/100")

        if result['long_methods']:
            print(f"\n⚠️  Long Methods ({len(result['long_methods'])}):")
            for smell in result['long_methods']:
                print(f"  • {smell['location']}: {smell['description']}")

        if result['long_parameter_lists']:
            print(f"\n⚠️  Long Parameter Lists ({len(result['long_parameter_lists'])}):")
            for smell in result['long_parameter_lists']:
                print(f"  • {smell['location']}: {smell['description']}")

        if result['god_classes']:
            print(f"\n⚠️  God Classes ({len(result['god_classes'])}):")
            for smell in result['god_classes']:
                print(f"  • {smell['location']}: {smell['description']}")

        if result['deep_nesting']:
            print(f"\n⚠️  Deep Nesting ({len(result['deep_nesting'])}):")
            for smell in result['deep_nesting']:
                print(f"  • {smell['location']}: {smell['description']}")

        overall_score += result['smell_score']
        score_count += 1

    except Exception as e:
        print(f"❌ Code smell detection failed: {e}")

    # Security Scan
    print_section("Security Scan")
    try:
        scanner = SecurityScanner()
        result = scanner.analyze_file(str(file_path))

        print(f"Security Score: {result['security_score']}/100")

        # Count critical issues
        critical_count = (
            len(result['sql_injection']) +
            len(result['command_injection']) +
            len(result['hardcoded_secrets']) +
            len(result['eval_usage'])
        )

        if critical_count > 0:
            print(f"\n🚨 CRITICAL SECURITY ISSUES: {critical_count}")

        if result['sql_injection']:
            print(f"\n⚠️  SQL Injection ({len(result['sql_injection'])}):")
            for issue in result['sql_injection']:
                print(f"  • [{issue['severity'].upper()}] {issue['description']}")

        if result['command_injection']:
            print(f"\n⚠️  Command Injection ({len(result['command_injection'])}):")
            for issue in result['command_injection']:
                print(f"  • [{issue['severity'].upper()}] {issue['description']}")

        if result['hardcoded_secrets']:
            print(f"\n⚠️  Hardcoded Secrets ({len(result['hardcoded_secrets'])}):")
            for issue in result['hardcoded_secrets']:
                print(f"  • {issue['location']}: {issue['description']}")

        if result['eval_usage']:
            print(f"\n⚠️  Dangerous Functions ({len(result['eval_usage'])}):")
            for issue in result['eval_usage']:
                print(f"  • {issue['description']}")

        overall_score += result['security_score']
        score_count += 1

    except Exception as e:
        print(f"❌ Security scan failed: {e}")

    # Overall Summary
    print_section("Overall Summary")

    if score_count > 0:
        avg_score = overall_score / score_count
        print(f"Average Score: {avg_score:.1f}/100")

        if avg_score >= 80:
            print("✅ Excellent code quality!")
        elif avg_score >= 60:
            print("⚠️  Good, but could be improved")
        else:
            print("❌ Needs improvement")

    return 0


async def review_diff():
    """Review staged changes using AI"""
    print_section("AI-Powered Diff Review")

    try:
        # Get staged diff
        result = subprocess.run(
            ['git', 'diff', '--cached'],
            capture_output=True,
            text=True,
            check=True
        )
        diff = result.stdout

        if not diff.strip():
            print("No staged changes to review")
            return 0

        # Review with AI
        reviewer = CodeReviewer()
        review_result = await reviewer.review_diff(diff)

        print("Summary:")
        print(review_result['summary'])

        if review_result['issues']:
            print(f"\n⚠️  Issues ({len(review_result['issues'])}):")
            for issue in review_result['issues']:
                print(f"  • {issue}")

        if review_result['suggestions']:
            print(f"\n💡 Suggestions ({len(review_result['suggestions'])}):")
            for suggestion in review_result['suggestions']:
                print(f"  • {suggestion}")

        print(f"\nScore: {review_result['score']}/100")

        return 0

    except CodeReviewError as e:
        print(f"❌ AI review failed: {e}")
        print("Make sure ANTHROPIC_API_KEY is set")
        return 1
    except subprocess.CalledProcessError:
        print("❌ Failed to get git diff")
        return 1


def install_hook():
    """Install pre-commit hook"""
    try:
        # Find git root
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            check=True
        )
        git_dir = Path(result.stdout.strip())

        # Copy hook
        hooks_dir = git_dir / 'hooks'
        hooks_dir.mkdir(exist_ok=True)

        hook_source = Path(__file__).parent.parent / 'hooks' / 'pre-commit'
        hook_dest = hooks_dir / 'pre-commit'

        # Copy and make executable
        hook_dest.write_text(hook_source.read_text())
        hook_dest.chmod(0o755)

        print(f"✅ Pre-commit hook installed: {hook_dest}")
        print("\nThe hook will run automatically on git commit")
        print("To bypass: git commit --no-verify")

        return 0

    except subprocess.CalledProcessError:
        print("❌ Not in a git repository")
        return 1
    except Exception as e:
        print(f"❌ Failed to install hook: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='AI Code Review CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # File review
    file_parser = subparsers.add_parser('file', help='Review a single file')
    file_parser.add_argument('path', help='Path to file')
    file_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    # Diff review
    diff_parser = subparsers.add_parser('diff', help='Review staged changes')

    # Pattern analysis
    pattern_parser = subparsers.add_parser('pattern', help='Run pattern analysis only')
    pattern_parser.add_argument('path', help='Path to file')

    # Performance analysis
    perf_parser = subparsers.add_parser('performance', help='Run performance analysis only')
    perf_parser.add_argument('path', help='Path to file')

    # Code smell detection
    smell_parser = subparsers.add_parser('smells', help='Run code smell detection only')
    smell_parser.add_argument('path', help='Path to file')

    # Security scan
    security_parser = subparsers.add_parser('security', help='Run security scan only')
    security_parser.add_argument('path', help='Path to file')

    # Install hook
    hook_parser = subparsers.add_parser('install-hook', help='Install pre-commit hook')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == 'file':
        return review_file(args.path, args.verbose)

    elif args.command == 'diff':
        return asyncio.run(review_diff())

    elif args.command == 'pattern':
        print_section("Pattern Analysis Only")
        analyzer = PatternAnalyzer()
        result = analyzer.analyze_file(args.path)
        print(f"Score: {result['separation_score']}/100")
        for rec in result['recommendations']:
            print(f"  • {rec}")
        return 0

    elif args.command == 'performance':
        print_section("Performance Analysis Only")
        analyzer = PerformanceAnalyzer()
        result = analyzer.analyze_file(args.path)
        print(f"Score: {result['performance_score']}/100")
        for rec in result['recommendations']:
            print(f"  • {rec}")
        return 0

    elif args.command == 'smells':
        print_section("Code Smell Detection Only")
        detector = CodeSmellDetector()
        result = detector.analyze_file(args.path)
        print(f"Score: {result['smell_score']}/100")
        for rec in result['recommendations']:
            print(f"  • {rec}")
        return 0

    elif args.command == 'security':
        print_section("Security Scan Only")
        scanner = SecurityScanner()
        result = scanner.analyze_file(args.path)
        print(f"Score: {result['security_score']}/100")
        for rec in result['recommendations']:
            print(f"  • {rec}")
        return 0

    elif args.command == 'install-hook':
        return install_hook()

    return 0


if __name__ == '__main__':
    sys.exit(main())
