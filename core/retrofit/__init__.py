"""BR3 Retrofit System - Attach to existing projects"""

from .codebase_scanner import CodebaseScanner
from .feature_extractor import FeatureExtractor
from .prd_synthesizer import PRDSynthesizer
from .models import CodeArtifact, ExtractedFeature, ScanResult
from .version_detector import BRVersionDetector, BRVersion, VersionDetectionResult

__all__ = [
    "CodebaseScanner",
    "FeatureExtractor",
    "PRDSynthesizer",
    "CodeArtifact",
    "ExtractedFeature",
    "ScanResult",
    "BRVersionDetector",
    "BRVersion",
    "VersionDetectionResult",
]
