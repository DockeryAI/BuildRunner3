"""
TypeScript Error Checker
Early detection of TypeScript errors using tsc
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ErrorSeverity(Enum):
    """Severity of TypeScript error"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class TypeScriptError:
    """Represents a TypeScript compilation error"""

    file: str
    line: int
    column: int
    message: str
    code: str
    severity: ErrorSeverity


@dataclass
class TypeScriptCheckResult:
    """Result of TypeScript check"""

    success: bool
    errors: List[TypeScriptError]
    warnings: List[TypeScriptError]
    duration_ms: float
    files_checked: int
    type_coverage_percent: Optional[float] = None


class TypeScriptChecker:
    """Checks TypeScript code for errors"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.tsc_path = self._find_tsc()

    def _find_tsc(self) -> Optional[Path]:
        """Find TypeScript compiler"""
        # Check local node_modules first
        local_tsc = self.project_root / "node_modules" / ".bin" / "tsc"
        if local_tsc.exists():
            return local_tsc

        # Check global tsc
        try:
            result = subprocess.run(["which", "tsc"], capture_output=True, text=True)
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception:
            pass

        return None

    def check(
        self, files: Optional[List[Path]] = None, incremental: bool = True, strict: bool = False
    ) -> TypeScriptCheckResult:
        """
        Run TypeScript compiler check

        Args:
            files: Specific files to check (None = all)
            incremental: Use incremental compilation
            strict: Enable strict mode
        """
        if not self.tsc_path:
            return TypeScriptCheckResult(
                success=False, errors=[], warnings=[], duration_ms=0, files_checked=0
            )

        import time

        start = time.time()

        # Build tsc command
        cmd = [str(self.tsc_path), "--noEmit"]

        if incremental:
            cmd.append("--incremental")

        if strict:
            cmd.append("--strict")

        # Add specific files if provided
        if files:
            cmd.extend([str(f) for f in files])

        # Run tsc
        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)

            duration_ms = (time.time() - start) * 1000

            # Parse output
            errors, warnings = self._parse_tsc_output(result.stdout + result.stderr)

            files_checked = len(files) if files else self._count_ts_files()

            return TypeScriptCheckResult(
                success=result.returncode == 0,
                errors=errors,
                warnings=warnings,
                duration_ms=duration_ms,
                files_checked=files_checked,
            )

        except Exception as e:
            return TypeScriptCheckResult(
                success=False,
                errors=[
                    TypeScriptError(
                        file="",
                        line=0,
                        column=0,
                        message=f"Failed to run TypeScript check: {str(e)}",
                        code="INTERNAL",
                        severity=ErrorSeverity.ERROR,
                    )
                ],
                warnings=[],
                duration_ms=(time.time() - start) * 1000,
                files_checked=0,
            )

    def check_imports(self, files: List[Path]) -> List[TypeScriptError]:
        """Check if all imports in files resolve correctly"""
        errors = []

        for file in files:
            if not file.exists():
                continue

            try:
                content = file.read_text()
                imports = self._extract_imports(content)

                for import_path in imports:
                    if not self._resolve_import(file, import_path):
                        errors.append(
                            TypeScriptError(
                                file=str(file),
                                line=0,
                                column=0,
                                message=f"Cannot resolve import: {import_path}",
                                code="TS2307",
                                severity=ErrorSeverity.ERROR,
                            )
                        )
            except Exception:
                continue

        return errors

    def calculate_type_coverage(self) -> float:
        """Calculate percentage of code with proper type annotations"""
        # This is a simplified version
        # Could integrate with type-coverage tool for accurate results
        ts_files = list(self.project_root.rglob("*.ts")) + list(self.project_root.rglob("*.tsx"))

        if not ts_files:
            return 0.0

        any_count = 0
        total_lines = 0

        for file in ts_files:
            # Skip node_modules
            if "node_modules" in str(file):
                continue

            try:
                content = file.read_text()
                lines = content.split("\n")
                total_lines += len(lines)
                any_count += content.count(": any")
                any_count += content.count("<any>")
            except Exception:
                continue

        if total_lines == 0:
            return 0.0

        # Simple heuristic: fewer 'any' = better coverage
        return max(0.0, min(100.0, 100.0 - (any_count / total_lines * 1000)))

    def _parse_tsc_output(self, output: str) -> tuple[List[TypeScriptError], List[TypeScriptError]]:
        """Parse TypeScript compiler output"""
        errors = []
        warnings = []

        for line in output.split("\n"):
            if not line.strip():
                continue

            # Parse format: path/to/file.ts(line,col): error TS1234: message
            if "): error TS" in line or "): warning TS" in line:
                try:
                    # Extract file path and position
                    file_part, rest = line.split("): ", 1)
                    file_path, position = file_part.rsplit("(", 1)
                    line_num, col_num = map(int, position.split(","))

                    # Extract severity, code, and message
                    if "error TS" in rest:
                        severity_part, message = rest.split(": ", 1)
                        severity = ErrorSeverity.ERROR
                    else:
                        severity_part, message = rest.split(": ", 1)
                        severity = ErrorSeverity.WARNING

                    code = severity_part.split()[-1]  # Extract TS code

                    error = TypeScriptError(
                        file=file_path.strip(),
                        line=line_num,
                        column=col_num,
                        message=message.strip(),
                        code=code,
                        severity=severity,
                    )

                    if severity == ErrorSeverity.ERROR:
                        errors.append(error)
                    else:
                        warnings.append(error)

                except Exception:
                    # If parsing fails, treat as generic error
                    continue

        return errors, warnings

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import paths from TypeScript content"""
        import re

        imports = []

        # Match import statements
        import_pattern = r'import\s+.*?\s+from\s+["\']([^"\']+)["\']'
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))

        # Match require statements
        require_pattern = r'require\(["\']([^"\']+)["\']\)'
        for match in re.finditer(require_pattern, content):
            imports.append(match.group(1))

        return imports

    def _resolve_import(self, source_file: Path, import_path: str) -> bool:
        """Check if import path can be resolved"""
        # Relative imports
        if import_path.startswith("."):
            base_dir = source_file.parent
            target = (base_dir / import_path).resolve()

            # Try various extensions
            for ext in ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx"]:
                if (target.parent / (target.name + ext)).exists():
                    return True

            return False

        # Absolute/module imports
        # Check node_modules
        node_modules = self.project_root / "node_modules" / import_path
        if node_modules.exists():
            return True

        # Check if it's a built-in Node module
        builtin_modules = {
            "fs",
            "path",
            "http",
            "https",
            "crypto",
            "os",
            "util",
            "stream",
            "events",
            "buffer",
            "url",
            "querystring",
        }
        if import_path in builtin_modules:
            return True

        return False

    def _count_ts_files(self) -> int:
        """Count total TypeScript files in project"""
        ts_files = list(self.project_root.rglob("*.ts")) + list(self.project_root.rglob("*.tsx"))

        # Filter out node_modules
        ts_files = [f for f in ts_files if "node_modules" not in str(f)]

        return len(ts_files)
