"""
BR Version Detector - Identify BuildRunner version in existing projects

Detects:
- BR 1.0 (if any legacy indicators exist)
- BR 2.0 (.runner/ directory)
- BR 3.0 (.buildrunner/ directory)
- No BR (fresh project)
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class BRVersion(str, Enum):
    """BuildRunner version enum"""

    NONE = "none"
    BR1 = "1.0"
    BR2 = "2.0"
    BR3 = "3.0"


@dataclass
class VersionDetectionResult:
    """Result of version detection"""

    version: BRVersion
    confidence: float  # 0.0-1.0
    indicators: list[str]
    legacy_files: list[Path]
    buildrunner_dir: Optional[Path] = None


class BRVersionDetector:
    """
    Detects BuildRunner version in existing project

    Detection logic:
    1. Check for .buildrunner/ → BR 3.0
    2. Check for .runner/ → BR 2.0
    3. Check for legacy indicators → BR 1.0 (if needed)
    4. Otherwise → No BR
    """

    def __init__(self, project_path: Path):
        """
        Initialize detector

        Args:
            project_path: Path to project root
        """
        self.project_path = Path(project_path).resolve()

    def detect(self) -> VersionDetectionResult:
        """
        Detect BR version in project

        Returns:
            VersionDetectionResult with detected version
        """
        # Check BR 3.0 first
        buildrunner_dir = self.project_path / ".buildrunner"
        if buildrunner_dir.exists() and buildrunner_dir.is_dir():
            return self._detect_br3(buildrunner_dir)

        # Check BR 2.0
        runner_dir = self.project_path / ".runner"
        if runner_dir.exists() and runner_dir.is_dir():
            return self._detect_br2(runner_dir)

        # Check BR 1.0 (if we ever need to support it)
        # For now, skip BR1 detection

        # No BR detected
        return VersionDetectionResult(
            version=BRVersion.NONE,
            confidence=1.0,
            indicators=["No .buildrunner/ or .runner/ directory found"],
            legacy_files=[],
        )

    def _detect_br3(self, buildrunner_dir: Path) -> VersionDetectionResult:
        """
        Detect BR 3.0 project

        Args:
            buildrunner_dir: Path to .buildrunner directory

        Returns:
            Detection result for BR 3.0
        """
        indicators = [".buildrunner/ directory exists"]
        legacy_files = []
        confidence = 0.8  # Start with medium confidence

        # Check for BR 3.0 indicators
        spec_file = buildrunner_dir / "PROJECT_SPEC.md"
        if spec_file.exists():
            indicators.append("PROJECT_SPEC.md exists")
            confidence = 1.0

        features_file = buildrunner_dir / "features.json"
        if features_file.exists():
            indicators.append("features.json exists")
            legacy_files.append(features_file)
            confidence = max(confidence, 0.9)

        governance_dir = buildrunner_dir / "governance"
        if governance_dir.exists():
            indicators.append("governance/ directory exists")
            confidence = 1.0

        return VersionDetectionResult(
            version=BRVersion.BR3,
            confidence=confidence,
            indicators=indicators,
            legacy_files=legacy_files,
            buildrunner_dir=buildrunner_dir,
        )

    def _detect_br2(self, runner_dir: Path) -> VersionDetectionResult:
        """
        Detect BR 2.0 project

        Args:
            runner_dir: Path to .runner directory

        Returns:
            Detection result for BR 2.0
        """
        indicators = [".runner/ directory exists"]
        legacy_files = []
        confidence = 0.8

        # Check for BR 2.0 indicators
        hrpo_file = runner_dir / "hrpo.json"
        if hrpo_file.exists():
            indicators.append("hrpo.json exists")
            legacy_files.append(hrpo_file)
            confidence = 1.0

        governance_file = runner_dir / "governance.json"
        if governance_file.exists():
            indicators.append("governance.json exists")
            legacy_files.append(governance_file)
            confidence = max(confidence, 0.9)

        features_file = runner_dir / "features.json"
        if features_file.exists():
            indicators.append("features.json exists")
            legacy_files.append(features_file)

        return VersionDetectionResult(
            version=BRVersion.BR2,
            confidence=confidence,
            indicators=indicators,
            legacy_files=legacy_files,
            buildrunner_dir=runner_dir,
        )

    def needs_migration(self) -> bool:
        """
        Check if project needs migration to BR 3.0

        Returns:
            True if migration needed
        """
        result = self.detect()
        return result.version in [BRVersion.BR1, BRVersion.BR2]

    def has_buildrunner(self) -> bool:
        """
        Check if project has any version of BuildRunner

        Returns:
            True if BR detected
        """
        result = self.detect()
        return result.version != BRVersion.NONE
