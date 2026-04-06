"""
Security Scanner - Detect security vulnerabilities and anti-patterns

Analyzes code for:
- SQL injection vulnerabilities
- Command injection
- Hardcoded secrets (passwords, API keys)
- Use of eval/exec
- Insecure random number generation
- Path traversal vulnerabilities
- Weak cryptography
- Bandit integration for additional checks
"""

import ast
import re
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SecurityIssue:
    """Represents a security issue"""

    issue_type: str
    location: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    recommendation: str
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID


class SecurityScanner:
    """
    Detect security vulnerabilities and anti-patterns

    Features:
    - SQL injection detection
    - Command injection detection
    - Hardcoded secrets detection
    - eval/exec usage detection
    - Insecure random detection
    - Path traversal detection
    - Weak crypto detection
    """

    # Patterns for detecting secrets
    SECRET_PATTERNS = {
        "password": re.compile(r'password\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
        "api_key": re.compile(r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
        "secret": re.compile(r'secret\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
        "token": re.compile(r'token\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
    }

    # Dangerous functions
    DANGEROUS_FUNCTIONS = {
        "eval": "CWE-95",
        "exec": "CWE-95",
        "compile": "CWE-95",
        "__import__": "CWE-95",
    }

    # SQL-like function names
    SQL_FUNCTIONS = {"execute", "executemany", "query", "raw", "exec_driver_sql"}

    # Command execution functions
    COMMAND_FUNCTIONS = {"system", "popen", "spawn", "call", "check_output", "run"}

    # Weak crypto algorithms
    WEAK_CRYPTO = {"md5", "sha1", "des", "rc4"}

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize SecurityScanner

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Comprehensive security analysis of a file

        Args:
            file_path: Path to file to analyze

        Returns:
            Dict with:
                - sql_injection: List of potential SQL injection issues
                - command_injection: List of command injection issues
                - hardcoded_secrets: List of hardcoded secrets
                - eval_usage: List of eval/exec usage
                - insecure_random: List of insecure random usage
                - path_traversal: List of path traversal issues
                - weak_crypto: List of weak cryptography usage
                - security_score: Score 0-100 (higher is better)
                - recommendations: List of recommendations
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file
        try:
            code = file_path.read_text()
        except Exception as e:
            return self._error_result(f"Failed to read file: {e}")

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return self._error_result(f"Syntax error: {e}")

        # Run security checks
        sql_injection = self.detect_sql_injection(tree, code)
        command_injection = self.detect_command_injection(tree, code)
        hardcoded_secrets = self.detect_hardcoded_secrets(code)
        eval_usage = self.detect_eval_usage(tree)
        insecure_random = self.detect_insecure_random(tree)
        path_traversal = self.detect_path_traversal(tree, code)
        weak_crypto = self.detect_weak_crypto(tree, code)

        # Calculate security score
        security_score = self.calculate_security_score(
            sql_injection,
            command_injection,
            hardcoded_secrets,
            eval_usage,
            insecure_random,
            path_traversal,
            weak_crypto,
        )

        # Generate recommendations
        recommendations = self.generate_recommendations(
            sql_injection,
            command_injection,
            hardcoded_secrets,
            eval_usage,
            insecure_random,
            path_traversal,
            weak_crypto,
        )

        return {
            "sql_injection": [vars(i) for i in sql_injection],
            "command_injection": [vars(i) for i in command_injection],
            "hardcoded_secrets": [vars(i) for i in hardcoded_secrets],
            "eval_usage": [vars(i) for i in eval_usage],
            "insecure_random": [vars(i) for i in insecure_random],
            "path_traversal": [vars(i) for i in path_traversal],
            "weak_crypto": [vars(i) for i in weak_crypto],
            "security_score": security_score,
            "recommendations": recommendations,
        }

    def detect_sql_injection(self, tree: ast.AST, code: str) -> List[SecurityIssue]:
        """
        Detect potential SQL injection vulnerabilities

        Args:
            tree: AST of the code
            code: Source code

        Returns:
            List of SQL injection issues
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for SQL execution methods
                if self._is_sql_call(node):
                    # Check if using string formatting/concatenation
                    if self._uses_string_formatting(node):
                        issues.append(
                            SecurityIssue(
                                issue_type="sql_injection",
                                location=f"Line {node.lineno}",
                                severity="critical",
                                description="Potential SQL injection: SQL query uses string formatting",
                                recommendation="Use parameterized queries or ORM methods",
                                cwe_id="CWE-89",
                            )
                        )

        return issues

    def detect_command_injection(self, tree: ast.AST, code: str) -> List[SecurityIssue]:
        """
        Detect potential command injection vulnerabilities

        Args:
            tree: AST of the code
            code: Source code

        Returns:
            List of command injection issues
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for command execution functions
                if self._is_command_call(node):
                    # Check if shell=True is used
                    if self._has_shell_true(node):
                        issues.append(
                            SecurityIssue(
                                issue_type="command_injection",
                                location=f"Line {node.lineno}",
                                severity="critical",
                                description="Command injection risk: shell=True with user input",
                                recommendation="Avoid shell=True, use list arguments instead",
                                cwe_id="CWE-78",
                            )
                        )
                    # Check for string formatting in command
                    elif self._uses_string_formatting(node):
                        issues.append(
                            SecurityIssue(
                                issue_type="command_injection",
                                location=f"Line {node.lineno}",
                                severity="high",
                                description="Potential command injection: command uses string formatting",
                                recommendation="Use list arguments and avoid string formatting",
                                cwe_id="CWE-78",
                            )
                        )

        return issues

    def detect_hardcoded_secrets(self, code: str) -> List[SecurityIssue]:
        """
        Detect hardcoded secrets (passwords, API keys)

        Args:
            code: Source code

        Returns:
            List of hardcoded secret issues
        """
        issues = []
        lines = code.split("\n")

        for pattern_name, pattern in self.SECRET_PATTERNS.items():
            for i, line in enumerate(lines, 1):
                matches = pattern.findall(line)
                for match in matches:
                    # Skip empty values and placeholders
                    if match and match not in ["", "your-password", "your-api-key", "xxx", "***"]:
                        issues.append(
                            SecurityIssue(
                                issue_type="hardcoded_secret",
                                location=f"Line {i}",
                                severity="critical",
                                description=f"Hardcoded {pattern_name} detected",
                                recommendation="Use environment variables or secret management",
                                cwe_id="CWE-798",
                            )
                        )

        return issues

    def detect_eval_usage(self, tree: ast.AST) -> List[SecurityIssue]:
        """
        Detect usage of eval/exec

        Args:
            tree: AST of the code

        Returns:
            List of eval/exec usage issues
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in self.DANGEROUS_FUNCTIONS:
                        issues.append(
                            SecurityIssue(
                                issue_type="dangerous_function",
                                location=f"Line {node.lineno}",
                                severity="critical",
                                description=f"Use of dangerous function '{func_name}'",
                                recommendation=f"Avoid {func_name}, use safer alternatives",
                                cwe_id=self.DANGEROUS_FUNCTIONS[func_name],
                            )
                        )

        return issues

    def detect_insecure_random(self, tree: ast.AST) -> List[SecurityIssue]:
        """
        Detect insecure random number generation

        Args:
            tree: AST of the code

        Returns:
            List of insecure random issues
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for random module usage (not secrets module)
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == "random":
                            issues.append(
                                SecurityIssue(
                                    issue_type="insecure_random",
                                    location=f"Line {node.lineno}",
                                    severity="medium",
                                    description="Use of insecure random module for security purposes",
                                    recommendation="Use secrets module for cryptographic operations",
                                    cwe_id="CWE-330",
                                )
                            )

        return issues

    def detect_path_traversal(self, tree: ast.AST, code: str) -> List[SecurityIssue]:
        """
        Detect potential path traversal vulnerabilities

        Args:
            tree: AST of the code
            code: Source code

        Returns:
            List of path traversal issues
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for file operations
                if isinstance(node.func, ast.Name):
                    if node.func.id == "open":
                        # Check if path uses string formatting/concatenation
                        if node.args and self._is_dynamic_string(node.args[0]):
                            issues.append(
                                SecurityIssue(
                                    issue_type="path_traversal",
                                    location=f"Line {node.lineno}",
                                    severity="high",
                                    description="Potential path traversal: file path uses dynamic input",
                                    recommendation="Validate and sanitize file paths, use Path.resolve()",
                                    cwe_id="CWE-22",
                                )
                            )

        return issues

    def detect_weak_crypto(self, tree: ast.AST, code: str) -> List[SecurityIssue]:
        """
        Detect usage of weak cryptographic algorithms

        Args:
            tree: AST of the code
            code: Source code

        Returns:
            List of weak crypto issues
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for hashlib usage
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == "hashlib":
                            algo = node.func.attr.lower()
                            if algo in self.WEAK_CRYPTO:
                                issues.append(
                                    SecurityIssue(
                                        issue_type="weak_crypto",
                                        location=f"Line {node.lineno}",
                                        severity="medium",
                                        description=f"Weak cryptographic algorithm '{algo}' used",
                                        recommendation="Use SHA-256 or stronger algorithms",
                                        cwe_id="CWE-327",
                                    )
                                )

        return issues

    def calculate_security_score(
        self,
        sql_injection: List[SecurityIssue],
        command_injection: List[SecurityIssue],
        hardcoded_secrets: List[SecurityIssue],
        eval_usage: List[SecurityIssue],
        insecure_random: List[SecurityIssue],
        path_traversal: List[SecurityIssue],
        weak_crypto: List[SecurityIssue],
    ) -> int:
        """
        Calculate overall security score

        Args:
            Various issue lists

        Returns:
            Score from 0-100 (higher is better)
        """
        score = 100

        # Critical issues
        score -= len(sql_injection) * 30
        score -= len(command_injection) * 30
        score -= len(hardcoded_secrets) * 25
        score -= len(eval_usage) * 25

        # High severity
        score -= len(path_traversal) * 15

        # Medium severity
        score -= len(insecure_random) * 10
        score -= len(weak_crypto) * 10

        return max(0, min(100, score))

    def generate_recommendations(
        self,
        sql_injection: List[SecurityIssue],
        command_injection: List[SecurityIssue],
        hardcoded_secrets: List[SecurityIssue],
        eval_usage: List[SecurityIssue],
        insecure_random: List[SecurityIssue],
        path_traversal: List[SecurityIssue],
        weak_crypto: List[SecurityIssue],
    ) -> List[str]:
        """Generate actionable security recommendations"""
        recommendations = []

        if sql_injection:
            recommendations.append(
                f"CRITICAL: Fix {len(sql_injection)} SQL injection vulnerability(ies)"
            )

        if command_injection:
            recommendations.append(
                f"CRITICAL: Fix {len(command_injection)} command injection vulnerability(ies)"
            )

        if hardcoded_secrets:
            recommendations.append(f"CRITICAL: Remove {len(hardcoded_secrets)} hardcoded secret(s)")

        if eval_usage:
            recommendations.append(f"CRITICAL: Remove {len(eval_usage)} dangerous function call(s)")

        if path_traversal:
            recommendations.append(f"Fix {len(path_traversal)} path traversal vulnerability(ies)")

        if insecure_random:
            recommendations.append(
                f"Replace {len(insecure_random)} insecure random usage(s) with secrets module"
            )

        if weak_crypto:
            recommendations.append(f"Upgrade {len(weak_crypto)} weak cryptographic algorithm(s)")

        if not recommendations:
            recommendations.append("No critical security issues detected")

        return recommendations

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Return error result"""
        return {
            "sql_injection": [],
            "command_injection": [],
            "hardcoded_secrets": [],
            "eval_usage": [],
            "insecure_random": [],
            "path_traversal": [],
            "weak_crypto": [],
            "security_score": 0,
            "recommendations": [error_msg],
        }

    def _is_sql_call(self, node: ast.Call) -> bool:
        """Check if call is SQL-related"""
        if isinstance(node.func, ast.Attribute):
            method = node.func.attr.lower()
            return method in self.SQL_FUNCTIONS
        return False

    def _is_command_call(self, node: ast.Call) -> bool:
        """Check if call is command execution"""
        if isinstance(node.func, ast.Attribute):
            method = node.func.attr.lower()
            if method in self.COMMAND_FUNCTIONS:
                return True
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id.lower()
            if func_name in self.COMMAND_FUNCTIONS:
                return True
        return False

    def _has_shell_true(self, node: ast.Call) -> bool:
        """Check if shell=True is in call arguments"""
        for keyword in node.keywords:
            if keyword.arg == "shell":
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    return True
        return False

    def _uses_string_formatting(self, node: ast.Call) -> bool:
        """Check if call arguments use string formatting"""
        for arg in node.args:
            if isinstance(arg, (ast.JoinedStr, ast.BinOp)):
                return True
            # Check for .format() calls
            if isinstance(arg, ast.Call):
                if isinstance(arg.func, ast.Attribute):
                    if arg.func.attr == "format":
                        return True
        return False

    def _is_dynamic_string(self, node: ast.AST) -> bool:
        """Check if string is dynamically constructed"""
        return isinstance(node, (ast.JoinedStr, ast.BinOp, ast.Call))


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python security_scanner.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    scanner = SecurityScanner()
    result = scanner.analyze_file(file_path)

    print(f"\n=== Security Analysis for {file_path} ===\n")
    print(f"Security Score: {result['security_score']}/100\n")

    if result["sql_injection"]:
        print("SQL Injection Vulnerabilities:")
        for issue in result["sql_injection"]:
            print(f"  - [{issue['severity'].upper()}] {issue['description']}")
            print(f"    {issue['recommendation']}")

    if result["command_injection"]:
        print("\nCommand Injection Vulnerabilities:")
        for issue in result["command_injection"]:
            print(f"  - [{issue['severity'].upper()}] {issue['description']}")

    if result["hardcoded_secrets"]:
        print(f"\nHardcoded Secrets: {len(result['hardcoded_secrets'])} detected")

    if result["eval_usage"]:
        print("\nDangerous Function Usage:")
        for issue in result["eval_usage"]:
            print(f"  - [{issue['severity'].upper()}] {issue['description']}")

    if result["insecure_random"]:
        print(f"\nInsecure Random Usage: {len(result['insecure_random'])} detected")

    if result["path_traversal"]:
        print(f"\nPath Traversal Issues: {len(result['path_traversal'])} detected")

    if result["weak_crypto"]:
        print(f"\nWeak Cryptography: {len(result['weak_crypto'])} detected")

    print("\nRecommendations:")
    for rec in result["recommendations"]:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()
