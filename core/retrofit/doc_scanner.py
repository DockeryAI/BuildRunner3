"""Documentation Scanner - finds and reads project documentation files"""

import logging
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DocumentationFile:
    """Represents a documentation file"""

    path: Path
    type: str  # 'readme', 'changelog', 'contributing', 'docs', 'other'
    content: str
    size_bytes: int


class DocumentationScanner:
    """Scans project for documentation files"""

    # Common documentation files
    DOC_PATTERNS = {
        "readme": ["README.md", "README.txt", "README", "readme.md"],
        "changelog": ["CHANGELOG.md", "CHANGELOG.txt", "CHANGELOG", "HISTORY.md"],
        "contributing": ["CONTRIBUTING.md", "CONTRIBUTE.md"],
        "license": ["LICENSE.md", "LICENSE.txt", "LICENSE"],
        "docs": ["docs/**/*.md", "doc/**/*.md", "documentation/**/*.md"],
    }

    # Maximum file size to read (1MB)
    MAX_FILE_SIZE = 1024 * 1024

    def __init__(self, project_root: Path):
        """
        Initialize documentation scanner

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)

    def scan(self) -> List[DocumentationFile]:
        """
        Scan project for documentation files

        Returns:
            List of documentation files found
        """
        logger.info(f"Scanning for documentation in {self.project_root}")
        docs = []

        # Scan for each documentation type
        for doc_type, patterns in self.DOC_PATTERNS.items():
            for pattern in patterns:
                docs.extend(self._find_files(pattern, doc_type))

        logger.info(f"Found {len(docs)} documentation files")
        return docs

    def _find_files(self, pattern: str, doc_type: str) -> List[DocumentationFile]:
        """Find files matching pattern"""
        docs = []

        try:
            if "**" in pattern:
                # Glob pattern
                for file_path in self.project_root.glob(pattern):
                    if file_path.is_file():
                        doc = self._read_file(file_path, doc_type)
                        if doc:
                            docs.append(doc)
            else:
                # Direct file
                file_path = self.project_root / pattern
                if file_path.exists() and file_path.is_file():
                    doc = self._read_file(file_path, doc_type)
                    if doc:
                        docs.append(doc)
        except Exception as e:
            logger.warning(f"Error scanning pattern {pattern}: {e}")

        return docs

    def _read_file(self, file_path: Path, doc_type: str) -> DocumentationFile | None:
        """Read documentation file"""
        try:
            # Check file size
            size = file_path.stat().st_size
            if size > self.MAX_FILE_SIZE:
                logger.warning(f"Skipping large file: {file_path} ({size} bytes)")
                return None

            # Read content
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Try with different encoding
                content = file_path.read_text(encoding="latin-1")

            return DocumentationFile(
                path=file_path, type=doc_type, content=content, size_bytes=size
            )

        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
            return None

    def get_summary(self, docs: List[DocumentationFile]) -> Dict[str, any]:
        """Get summary of documentation files"""
        summary = {
            "total_files": len(docs),
            "total_size_bytes": sum(doc.size_bytes for doc in docs),
            "by_type": {},
        }

        for doc in docs:
            if doc.type not in summary["by_type"]:
                summary["by_type"][doc.type] = []
            summary["by_type"][doc.type].append(str(doc.path.relative_to(self.project_root)))

        return summary
