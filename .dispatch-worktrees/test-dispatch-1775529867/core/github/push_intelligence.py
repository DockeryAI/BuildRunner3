"""
Push Intelligence - Smart push timing and readiness checks
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .git_client import GitClient


@dataclass
class PushReadiness:
    """Push readiness assessment"""

    is_ready: bool
    score: int  # 0-100
    blockers: List[str]
    warnings: List[str]
    passed_checks: List[str]


class PushIntelligence:
    """Determine when it's safe to push"""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)
        self.buildrunner_dir = self.repo_path / ".buildrunner"

    def assess_readiness(self, strict: bool = True) -> PushReadiness:
        """
        Assess if code is ready to push

        Args:
            strict: If True, enforce all checks. If False, only blockers.

        Returns:
            PushReadiness assessment
        """
        blockers = []
        warnings = []
        passed = []
        score = 100

        # Check 1: Uncommitted changes
        status = self.git.get_status()
        if not status.is_clean:
            if status.unstaged_files or status.untracked_files:
                blockers.append("Uncommitted changes detected")
                score -= 30
            else:
                passed.append("All changes committed")

        # Check 2: Tests passing
        try:
            from core.auto_debug import AutoDebugPipeline

            pipeline = AutoDebugPipeline(self.repo_path)
            report = pipeline.run(skip_deep=True)
            if not report.overall_success:
                blockers.append(f"Tests failing ({len(report.critical_failures)} failures)")
                score -= 40
            else:
                passed.append("All tests passing")
        except Exception:
            warnings.append("Could not run tests")
            score -= 10

        # Check 3: Security scan
        try:
            from core.security import SecretDetector, SQLInjectionDetector

            secret_detector = SecretDetector()
            sql_detector = SQLInjectionDetector()

            # Quick scan of staged files only
            secrets_found = False
            sql_risks_found = False

            for file in status.staged_files:
                file_path = self.repo_path / file
                if file_path.exists() and file_path.is_file():
                    try:
                        content = file_path.read_text()
                        if secret_detector.scan_text(content):
                            secrets_found = True
                        if sql_detector.scan_file(file_path):
                            sql_risks_found = True
                    except Exception:
                        pass

            if secrets_found:
                blockers.append("Exposed secrets detected")
                score -= 50
            elif sql_risks_found:
                warnings.append("SQL injection risks detected")
                score -= 10
            else:
                passed.append("Security scan clean")
        except Exception:
            warnings.append("Could not run security scan")

        # Check 4: Feature completeness
        features_file = self.buildrunner_dir / "features.json"
        if features_file.exists():
            import json

            with open(features_file) as f:
                data = json.load(f)
                incomplete = [
                    f for f in data.get("features", []) if f.get("status") == "in_progress"
                ]
                if incomplete and strict:
                    warnings.append(f"{len(incomplete)} features in progress")
                    score -= 5
                else:
                    passed.append("All features complete or continuing work acknowledged")

        # Check 5: Behind main
        is_behind, count = self.git.is_behind("origin/main")
        if is_behind:
            warnings.append(f"Branch is {count} commits behind origin/main")
            score -= 10
        else:
            passed.append("Branch is up to date with main")

        # Check 6: Merge conflicts
        current = self.git.current_branch()
        if current != "main":
            try:
                has_conflicts, files = self.git.has_conflicts_with("origin/main")
                if has_conflicts:
                    blockers.append(f"Merge conflicts detected in {len(files)} files")
                    score -= 30
                else:
                    passed.append("No merge conflicts")
            except Exception:
                warnings.append("Could not check for merge conflicts")

        is_ready = len(blockers) == 0
        return PushReadiness(
            is_ready=is_ready,
            score=max(0, score),
            blockers=blockers,
            warnings=warnings,
            passed_checks=passed,
        )

    def should_push(self) -> bool:
        """Simple yes/no: should we push?"""
        readiness = self.assess_readiness(strict=False)
        return readiness.is_ready

    def get_push_recommendation(self) -> str:
        """Get human-readable push recommendation"""
        readiness = self.assess_readiness(strict=True)

        if readiness.score >= 90:
            return "✅ Ready to push - all checks passed"
        elif readiness.score >= 70:
            return "⚠️  Can push but with warnings - review before pushing"
        elif readiness.score >= 50:
            return "🚧 Not recommended - fix warnings first"
        else:
            return "❌ Do not push - critical issues detected"
