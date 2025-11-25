"""Secret detection for files and git repositories.

This module provides functionality to scan files, directories, and git
repositories for accidentally committed secrets like API keys and tokens.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set
import fnmatch

from .secret_masker import SecretMasker


@dataclass
class SecretMatch:
    """Represents a detected secret in a file.

    Attributes:
        file_path: Path to file containing the secret
        line_number: Line number where secret was found
        line_content: Content of the line (secret will be masked)
        pattern_name: Name of the pattern that matched (e.g., 'anthropic_key')
        secret_value: The actual secret value (masked)
        column_start: Starting column of the match
        column_end: Ending column of the match
    """
    file_path: str
    line_number: int
    line_content: str
    pattern_name: str
    secret_value: str
    column_start: int
    column_end: int

    def __str__(self) -> str:
        """Return human-readable representation."""
        return (
            f"{self.file_path}:{self.line_number}:{self.column_start} "
            f"[{self.pattern_name}] {self.secret_value}"
        )


class SecretDetector:
    """Detect secrets in files and git repositories.

    This class provides methods to scan for accidentally committed secrets
    in source code, configuration files, and git history.

    Example:
        >>> detector = SecretDetector()
        >>> matches = detector.scan_file("config.py")
        >>> if matches:
        ...     print(f"Found {len(matches)} secrets!")
    """

    # Default patterns to exclude from scanning
    DEFAULT_EXCLUDE_PATTERNS = {
        '.git',
        'node_modules',
        'venv',
        '__pycache__',
        '.pytest_cache',
        'dist',
        'build',
        '*.pyc',
        '*.pyo',
        '*.so',
        '*.dylib',
        '.DS_Store',
    }

    # File extensions that are likely to contain secrets
    SCAN_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx',
        '.yml', '.yaml', '.json', '.toml',
        '.env', '.env.local', '.env.production',
        '.sh', '.bash', '.zsh',
        '.rb', '.go', '.java', '.cpp', '.c',
        '.php', '.cs', '.swift', '.kt',
        '.txt', '.md', '.rst',
        '.conf', '.config', '.cfg',
    }

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the secret detector.

        Args:
            project_root: Root directory of the project (default: current dir)
        """
        self.project_root = project_root or Path.cwd()
        self.whitelist: Set[str] = set()
        self.ignore_patterns: List[str] = []
        self._load_whitelist()
        self._load_securityignore()

    def _load_whitelist(self) -> None:
        """Load whitelist of known false positives."""
        whitelist_file = self.project_root / '.buildrunner' / 'security' / 'whitelist.txt'
        if whitelist_file.exists():
            try:
                content = whitelist_file.read_text()
                # Format: file:line:pattern or just file:line
                self.whitelist = {
                    line.strip()
                    for line in content.splitlines()
                    if line.strip() and not line.startswith('#')
                }
            except Exception:
                pass  # Ignore errors loading whitelist

    def _load_securityignore(self) -> None:
        """Load .securityignore patterns (gitignore-style)."""
        securityignore_file = self.project_root / '.securityignore'
        if securityignore_file.exists():
            try:
                content = securityignore_file.read_text()
                self.ignore_patterns = [
                    line.strip()
                    for line in content.splitlines()
                    if line.strip() and not line.startswith('#')
                ]
            except Exception:
                pass  # Ignore errors loading .securityignore

    def _matches_ignore_pattern(self, file_path: Path) -> bool:
        """Check if file matches any .securityignore pattern."""
        # Convert to string relative to project root
        try:
            rel_path = file_path.relative_to(self.project_root)
            rel_path_str = str(rel_path)
        except ValueError:
            rel_path_str = str(file_path)

        for pattern in self.ignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith('/'):
                dir_pattern = pattern.rstrip('/')
                if any(part == dir_pattern for part in file_path.parts):
                    return True

            # Handle glob patterns
            if fnmatch.fnmatch(rel_path_str, pattern):
                return True

            # Handle ** patterns (match any directory depth)
            if '**' in pattern:
                glob_pattern = pattern.replace('**', '*')
                if fnmatch.fnmatch(rel_path_str, glob_pattern):
                    return True

        return False

    def _is_whitelisted(self, file_path: str, line_number: int, pattern_name: str) -> bool:
        """Check if a match is whitelisted."""
        checks = [
            f"{file_path}:{line_number}:{pattern_name}",
            f"{file_path}:{line_number}",
            file_path,
        ]
        return any(check in self.whitelist for check in checks)

    def _should_scan_file(self, file_path: Path) -> bool:
        """Check if file should be scanned based on extension and exclusions."""
        # Check .securityignore patterns first
        if self._matches_ignore_pattern(file_path):
            return False

        # Check if file is in excluded directory
        parts = file_path.parts
        for part in parts:
            if part in self.DEFAULT_EXCLUDE_PATTERNS:
                return False

        # Check if extension is scannable
        if file_path.suffix and file_path.suffix not in self.SCAN_EXTENSIONS:
            return False

        # Don't scan binary files
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(512)  # Try reading first 512 bytes
            return True
        except (UnicodeDecodeError, PermissionError):
            return False

    def scan_file(self, file_path: str) -> List[SecretMatch]:
        """Scan a single file for secrets.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of SecretMatch objects for detected secrets

        Example:
            >>> detector = SecretDetector()
            >>> matches = detector.scan_file("config.py")
            >>> for match in matches:
            ...     print(match)
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return []

        if not self._should_scan_file(path):
            return []

        matches = []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    # Check each pattern
                    for pattern_name, pattern in SecretMasker.SENSITIVE_PATTERNS.items():
                        # Skip generic pattern - too many false positives
                        if pattern_name == 'generic_api_key':
                            continue

                        for match in re.finditer(pattern, line):
                            secret_value = match.group(0)

                            # Check whitelist
                            if self._is_whitelisted(str(path), line_num, pattern_name):
                                continue

                            # Create match object
                            matches.append(SecretMatch(
                                file_path=str(path),
                                line_number=line_num,
                                line_content=line.rstrip(),
                                pattern_name=pattern_name,
                                secret_value=SecretMasker.mask_value(secret_value),
                                column_start=match.start(),
                                column_end=match.end(),
                            ))

        except Exception as e:
            # Ignore errors reading individual files
            pass

        return matches

    def scan_directory(
        self,
        directory: Optional[str] = None,
        exclude: Optional[List[str]] = None,
        recursive: bool = True
    ) -> Dict[str, List[SecretMatch]]:
        """Recursively scan a directory for secrets.

        Args:
            directory: Directory to scan (default: project root)
            exclude: Additional patterns to exclude
            recursive: Whether to scan subdirectories

        Returns:
            Dictionary mapping file paths to lists of SecretMatch objects

        Example:
            >>> detector = SecretDetector()
            >>> results = detector.scan_directory("src/")
            >>> for file, matches in results.items():
            ...     print(f"{file}: {len(matches)} secrets")
        """
        scan_dir = Path(directory) if directory else self.project_root
        if not scan_dir.exists() or not scan_dir.is_dir():
            return {}

        # Combine default and custom exclusions
        exclude_patterns = self.DEFAULT_EXCLUDE_PATTERNS.copy()
        if exclude:
            exclude_patterns.update(exclude)

        results = {}

        # Scan files
        pattern = '**/*' if recursive else '*'
        for file_path in scan_dir.glob(pattern):
            if not file_path.is_file():
                continue

            # Check exclusions
            if any(excl in file_path.parts for excl in exclude_patterns):
                continue

            matches = self.scan_file(str(file_path))
            if matches:
                results[str(file_path)] = matches

        return results

    def scan_git_staged(self) -> Dict[str, List[SecretMatch]]:
        """Scan git staged files for secrets.

        This is used by the pre-commit hook to prevent committing secrets.

        Returns:
            Dictionary mapping file paths to lists of SecretMatch objects

        Example:
            >>> detector = SecretDetector()
            >>> staged = detector.scan_git_staged()
            >>> if staged:
            ...     print("Secrets in staged files!")
        """
        try:
            # Get list of staged files
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )

            staged_files = result.stdout.strip().split('\n')
            staged_files = [f for f in staged_files if f]

            # Scan each staged file
            results = {}
            for file_path in staged_files:
                full_path = self.project_root / file_path
                if full_path.exists():
                    matches = self.scan_file(str(full_path))
                    if matches:
                        results[file_path] = matches

            return results

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Not in a git repo or git not available
            return {}

    def scan_git_history(
        self,
        file_path: Optional[str] = None,
        max_commits: int = 100
    ) -> Dict[str, List[SecretMatch]]:
        """Scan git history for secrets in committed files.

        Args:
            file_path: Specific file to check (None = all files)
            max_commits: Maximum number of commits to check

        Returns:
            Dictionary mapping "commit:file" to lists of SecretMatch objects

        Example:
            >>> detector = SecretDetector()
            >>> history = detector.scan_git_history(max_commits=50)
            >>> if history:
            ...     print("Secrets found in git history!")
        """
        try:
            # Build git log command
            cmd = ['git', 'log', f'-{max_commits}', '--all', '--oneline']
            if file_path:
                cmd.extend(['--', file_path])

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )

            commits = [
                line.split()[0]
                for line in result.stdout.strip().split('\n')
                if line
            ]

            results = {}

            # Check each commit for secrets
            for commit in commits:
                # Get files changed in this commit
                files_result = subprocess.run(
                    ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commit],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=True
                )

                files = files_result.stdout.strip().split('\n')

                for file in files:
                    if not file:
                        continue

                    # Get file content at this commit
                    try:
                        content_result = subprocess.run(
                            ['git', 'show', f'{commit}:{file}'],
                            cwd=self.project_root,
                            capture_output=True,
                            text=True,
                            check=True
                        )

                        # Scan content
                        for line_num, line in enumerate(content_result.stdout.split('\n'), start=1):
                            for pattern_name, pattern in SecretMasker.SENSITIVE_PATTERNS.items():
                                if pattern_name == 'generic_api_key':
                                    continue

                                for match in re.finditer(pattern, line):
                                    key = f"{commit}:{file}"
                                    if key not in results:
                                        results[key] = []

                                    results[key].append(SecretMatch(
                                        file_path=f"{commit}:{file}",
                                        line_number=line_num,
                                        line_content=line.rstrip(),
                                        pattern_name=pattern_name,
                                        secret_value=SecretMasker.mask_value(match.group(0)),
                                        column_start=match.start(),
                                        column_end=match.end(),
                                    ))

                    except subprocess.CalledProcessError:
                        # File doesn't exist at this commit or binary
                        continue

            return results

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Not in a git repo or git not available
            return {}

    def add_to_whitelist(self, file_path: str, line_number: int, pattern_name: Optional[str] = None) -> None:
        """Add a false positive to the whitelist.

        Args:
            file_path: Path to file
            line_number: Line number of false positive
            pattern_name: Optional pattern name to whitelist

        Example:
            >>> detector = SecretDetector()
            >>> detector.add_to_whitelist("test.py", 42, "jwt_token")
        """
        whitelist_file = self.project_root / '.buildrunner' / 'security' / 'whitelist.txt'
        whitelist_file.parent.mkdir(parents=True, exist_ok=True)

        entry = f"{file_path}:{line_number}"
        if pattern_name:
            entry += f":{pattern_name}"

        # Add to memory
        self.whitelist.add(entry)

        # Append to file
        with open(whitelist_file, 'a') as f:
            f.write(f"{entry}\n")
