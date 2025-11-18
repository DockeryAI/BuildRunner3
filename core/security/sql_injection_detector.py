"""SQL injection detection for BuildRunner.

This module provides functionality to detect potential SQL injection
vulnerabilities in source code by finding string concatenation in SQL queries.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class SQLInjectionMatch:
    """Represents a potential SQL injection vulnerability.

    Attributes:
        file_path: Path to file containing the vulnerability
        line_number: Line number where issue was found
        line_content: Content of the line
        vulnerability_type: Type of vulnerability (string_concat, formatted_string, etc.)
        severity: Severity level (high, medium, low)
        suggestion: How to fix the issue
    """
    file_path: str
    line_number: int
    line_content: str
    vulnerability_type: str
    severity: str
    suggestion: str

    def __str__(self) -> str:
        """Return human-readable representation."""
        return (
            f"{self.file_path}:{self.line_number} [{self.severity}] "
            f"{self.vulnerability_type} - {self.suggestion}"
        )


class SQLInjectionDetector:
    """Detect potential SQL injection vulnerabilities in source code.

    This class scans for common SQL injection patterns like string concatenation
    in queries, formatted strings with user input, and other unsafe practices.

    Example:
        >>> detector = SQLInjectionDetector()
        >>> matches = detector.scan_file("app.py")
        >>> if matches:
        ...     print(f"Found {len(matches)} potential vulnerabilities!")
    """

    # SQL keywords that indicate a query
    SQL_KEYWORDS = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
        'ALTER', 'TRUNCATE', 'EXEC', 'EXECUTE', 'UNION', 'MERGE'
    }

    # Patterns that indicate string concatenation in SQL (Python)
    PYTHON_PATTERNS = [
        # String concatenation: "SELECT * FROM users WHERE id=" + user_id
        (r'["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)[^"\']*["\']'
         r'\s*\+\s*\w+',
         'string_concat',
         'high',
         'Use parameterized queries instead of string concatenation'),

        # f-string with SQL: f"SELECT * FROM users WHERE id={user_id}"
        (r'f["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)[^"\']*\{[^}]+\}',
         'f_string',
         'high',
         'Use parameterized queries instead of f-strings'),

        # .format() with SQL: "SELECT * FROM users WHERE id={}".format(user_id)
        (r'["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)[^"\']*\{[^}]*\}["\']'
         r'\s*\.format\(',
         'format_string',
         'high',
         'Use parameterized queries instead of .format()'),

        # % formatting: "SELECT * FROM users WHERE id=%s" % user_id
        (r'["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)[^"\']*%[sd]["\']'
         r'\s*%\s*',
         'percent_formatting',
         'high',
         'Use parameterized queries instead of % formatting'),
    ]

    # Patterns for JavaScript/TypeScript
    JS_PATTERNS = [
        # Template literals: `SELECT * FROM users WHERE id=${userId}`
        (r'`(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)[^`]*\$\{[^}]+\}',
         'template_literal',
         'high',
         'Use parameterized queries instead of template literals'),

        # String concatenation: "SELECT * FROM users WHERE id=" + userId
        (r'["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)[^"\']*["\']'
         r'\s*\+\s*\w+',
         'string_concat',
         'high',
         'Use parameterized queries instead of string concatenation'),
    ]

    # File extensions to scan for each language
    LANGUAGE_PATTERNS = {
        'python': (['.py'], PYTHON_PATTERNS),
        'javascript': (['.js', '.jsx', '.ts', '.tsx'], JS_PATTERNS),
    }

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the SQL injection detector.

        Args:
            project_root: Root directory of the project (default: current dir)
        """
        self.project_root = project_root or Path.cwd()

    def _get_language_patterns(self, file_path: Path) -> Optional[List]:
        """Get the appropriate patterns for a file based on extension."""
        extension = file_path.suffix
        for lang_name, (extensions, patterns) in self.LANGUAGE_PATTERNS.items():
            if extension in extensions:
                return patterns
        return None

    def scan_file(self, file_path: str) -> List[SQLInjectionMatch]:
        """Scan a single file for SQL injection vulnerabilities.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of SQLInjectionMatch objects for detected vulnerabilities

        Example:
            >>> detector = SQLInjectionDetector()
            >>> matches = detector.scan_file("app.py")
            >>> for match in matches:
            ...     print(match)
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return []

        patterns = self._get_language_patterns(path)
        if not patterns:
            return []

        matches = []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    # Check each pattern
                    for pattern, vuln_type, severity, suggestion in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            matches.append(SQLInjectionMatch(
                                file_path=str(path),
                                line_number=line_num,
                                line_content=line.rstrip(),
                                vulnerability_type=vuln_type,
                                severity=severity,
                                suggestion=suggestion,
                            ))
                            break  # Only report one issue per line

        except Exception:
            # Ignore errors reading files
            pass

        return matches

    def scan_directory(
        self,
        directory: Optional[str] = None,
        recursive: bool = True
    ) -> Dict[str, List[SQLInjectionMatch]]:
        """Recursively scan a directory for SQL injection vulnerabilities.

        Args:
            directory: Directory to scan (default: project root)
            recursive: Whether to scan subdirectories

        Returns:
            Dictionary mapping file paths to lists of SQLInjectionMatch objects

        Example:
            >>> detector = SQLInjectionDetector()
            >>> results = detector.scan_directory("src/")
            >>> for file, matches in results.items():
            ...     print(f"{file}: {len(matches)} issues")
        """
        scan_dir = Path(directory) if directory else self.project_root
        if not scan_dir.exists() or not scan_dir.is_dir():
            return {}

        results = {}

        # Collect all scannable extensions
        scannable_extensions = set()
        for extensions, _ in self.LANGUAGE_PATTERNS.values():
            scannable_extensions.update(extensions)

        # Scan files
        pattern = '**/*' if recursive else '*'
        for file_path in scan_dir.glob(pattern):
            if not file_path.is_file():
                continue

            if file_path.suffix not in scannable_extensions:
                continue

            matches = self.scan_file(str(file_path))
            if matches:
                results[str(file_path)] = matches

        return results

    def get_safe_example(self, language: str = 'python') -> str:
        """Get an example of safe parameterized query for the language.

        Args:
            language: Programming language (python, javascript)

        Returns:
            Example code showing safe query practices

        Example:
            >>> detector = SQLInjectionDetector()
            >>> print(detector.get_safe_example('python'))
        """
        if language == 'python':
            return """# Safe: Using parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE id = ?",
    (user_id,)
)

# Or with named parameters:
cursor.execute(
    "SELECT * FROM users WHERE id = :user_id",
    {"user_id": user_id}
)

# With SQLAlchemy:
session.query(User).filter(User.id == user_id).first()

# With Django ORM:
User.objects.filter(id=user_id).first()
"""
        elif language == 'javascript':
            return """// Safe: Using parameterized queries
const query = 'SELECT * FROM users WHERE id = $1';
const values = [userId];
await client.query(query, values);

// With Sequelize:
await User.findOne({ where: { id: userId } });

// With Prisma:
await prisma.user.findUnique({ where: { id: userId } });
"""
        else:
            return "# No example available for this language"

    def get_vulnerability_summary(
        self,
        results: Dict[str, List[SQLInjectionMatch]]
    ) -> Dict[str, any]:
        """Generate a summary of detected vulnerabilities.

        Args:
            results: Results from scan_directory()

        Returns:
            Summary dict with counts and severity breakdown

        Example:
            >>> detector = SQLInjectionDetector()
            >>> results = detector.scan_directory("src/")
            >>> summary = detector.get_vulnerability_summary(results)
            >>> print(f"Total issues: {summary['total_count']}")
        """
        total_count = sum(len(matches) for matches in results.values())

        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        type_counts = {}

        for matches in results.values():
            for match in matches:
                severity_counts[match.severity] = severity_counts.get(match.severity, 0) + 1
                type_counts[match.vulnerability_type] = type_counts.get(match.vulnerability_type, 0) + 1

        return {
            'total_count': total_count,
            'file_count': len(results),
            'severity_breakdown': severity_counts,
            'type_breakdown': type_counts,
            'files_affected': list(results.keys()),
        }
