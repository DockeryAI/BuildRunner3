"""Data models for BR3 Retrofit system"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum


class ArtifactType(str, Enum):
    """Type of code artifact"""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    ROUTE = "route"  # API endpoint
    COMPONENT = "component"  # UI component
    MODEL = "model"  # Database model
    TEST = "test"
    MODULE = "module"


@dataclass
class CodeArtifact:
    """Represents a single code artifact (function, class, route, etc.)"""

    type: ArtifactType
    name: str
    file_path: Path
    line_number: int
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)  # Functions/methods called
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def description(self) -> str:
        """Get description from docstring or name"""
        if self.docstring:
            # Get first line of docstring
            return self.docstring.split("\n")[0].strip()
        return f"{self.type.value}: {self.name}"


@dataclass
class ExtractedFeature:
    """A feature extracted from codebase analysis"""

    id: str
    name: str
    description: str
    artifacts: List[CodeArtifact] = field(default_factory=list)
    confidence: float = 0.0  # 0.0-1.0
    priority: str = "medium"  # low, medium, high
    requirements: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    technical_details: Dict[str, Any] = field(default_factory=dict)

    @property
    def file_count(self) -> int:
        """Number of unique files in this feature"""
        return len(set(a.file_path for a in self.artifacts))

    @property
    def artifact_count(self) -> int:
        """Total number of artifacts"""
        return len(self.artifacts)


@dataclass
class ScanResult:
    """Result of scanning a codebase"""

    project_root: Path
    project_name: str
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    artifacts: List[CodeArtifact] = field(default_factory=list)
    features: List[ExtractedFeature] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    scan_duration_seconds: float = 0.0

    @property
    def summary(self) -> str:
        """Get summary string"""
        return (
            f"Scanned {self.total_files} files ({self.total_lines} lines) "
            f"in {self.scan_duration_seconds:.1f}s. "
            f"Found {len(self.artifacts)} artifacts, "
            f"extracted {len(self.features)} features."
        )
