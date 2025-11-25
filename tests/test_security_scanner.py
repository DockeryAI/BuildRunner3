"""
Tests for Security Scanner
"""

import pytest
import ast
from pathlib import Path
from core.security_scanner import SecurityScanner, SecurityIssue


class TestSecurityScanner:
    """Test SecurityScanner class"""

    @pytest.fixture
    def scanner(self, tmp_path):
        """Create SecurityScanner instance"""
        return SecurityScanner(project_root=tmp_path)

    def test_init(self, tmp_path):
        """Test initialization"""
        scanner = SecurityScanner(project_root=tmp_path)
        assert scanner.project_root == tmp_path

    def test_detect_sql_injection_string_formatting(self, scanner):
        """Test detection of SQL injection with string formatting"""
        code = """
def get_user(username):
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
"""
        tree = ast.parse(code)

        issues = scanner.detect_sql_injection(tree, code)

        assert len(issues) == 1
        assert issues[0].issue_type == "sql_injection"
        assert issues[0].severity == "critical"
        assert issues[0].cwe_id == "CWE-89"

    def test_detect_sql_injection_safe_query(self, scanner):
        """Test that parameterized queries are not flagged"""
        code = """
def get_user(username):
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
"""
        tree = ast.parse(code)

        issues = scanner.detect_sql_injection(tree, code)

        # Parameterized query should not be flagged
        assert len(issues) == 0

    def test_detect_command_injection_shell_true(self, scanner):
        """Test detection of command injection with shell=True"""
        code = """
import subprocess
def run_command(user_input):
    subprocess.call(user_input, shell=True)
"""
        tree = ast.parse(code)

        issues = scanner.detect_command_injection(tree, code)

        assert len(issues) == 1
        assert issues[0].issue_type == "command_injection"
        assert issues[0].severity == "critical"
        assert "shell=True" in issues[0].description

    def test_detect_command_injection_string_formatting(self, scanner):
        """Test detection of command injection with string formatting"""
        code = """
import subprocess
def run_command(filename):
    subprocess.call(f"ls -l {filename}")
"""
        tree = ast.parse(code)

        issues = scanner.detect_command_injection(tree, code)

        assert len(issues) == 1
        assert issues[0].issue_type == "command_injection"
        assert issues[0].severity == "high"

    def test_detect_command_injection_safe(self, scanner):
        """Test that safe command execution is not flagged"""
        code = """
import subprocess
def run_command():
    subprocess.call(['ls', '-l'])
"""
        tree = ast.parse(code)

        issues = scanner.detect_command_injection(tree, code)

        # List arguments without shell=True should be safe
        assert len(issues) == 0

    def test_detect_hardcoded_password(self, scanner):
        """Test detection of hardcoded password"""
        code = """
password = "SuperSecret123!"
db_password = "admin"
"""

        issues = scanner.detect_hardcoded_secrets(code)

        assert len(issues) == 2
        assert all(i.issue_type == "hardcoded_secret" for i in issues)
        assert all(i.severity == "critical" for i in issues)

    def test_detect_hardcoded_api_key(self, scanner):
        """Test detection of hardcoded API key"""
        code = """
api_key = "sk-abc123xyz"
API_KEY = "secret-key-here"
"""

        issues = scanner.detect_hardcoded_secrets(code)

        assert len(issues) == 2
        assert all("api" in i.description.lower() for i in issues)

    def test_hardcoded_secrets_skip_placeholders(self, scanner):
        """Test that placeholder values are not flagged"""
        code = """
password = "your-password"
api_key = ""
secret = "xxx"
"""

        issues = scanner.detect_hardcoded_secrets(code)

        # Placeholders should not be flagged
        assert len(issues) == 0

    def test_detect_eval_usage(self, scanner):
        """Test detection of eval usage"""
        code = """
def process(user_input):
    result = eval(user_input)
    return result
"""
        tree = ast.parse(code)

        issues = scanner.detect_eval_usage(tree)

        assert len(issues) == 1
        assert issues[0].issue_type == "dangerous_function"
        assert issues[0].severity == "critical"
        assert "eval" in issues[0].description

    def test_detect_exec_usage(self, scanner):
        """Test detection of exec usage"""
        code = """
def process(code_string):
    exec(code_string)
"""
        tree = ast.parse(code)

        issues = scanner.detect_eval_usage(tree)

        assert len(issues) == 1
        assert "exec" in issues[0].description

    def test_detect_compile_usage(self, scanner):
        """Test detection of compile usage"""
        code = """
def process(code_string):
    compiled = compile(code_string, '<string>', 'exec')
"""
        tree = ast.parse(code)

        issues = scanner.detect_eval_usage(tree)

        assert len(issues) == 1
        assert "compile" in issues[0].description

    def test_detect_insecure_random(self, scanner):
        """Test detection of insecure random usage"""
        code = """
import random
def generate_token():
    return random.randint(0, 1000000)
"""
        tree = ast.parse(code)

        issues = scanner.detect_insecure_random(tree)

        assert len(issues) == 1
        assert issues[0].issue_type == "insecure_random"
        assert issues[0].severity == "medium"
        assert "secrets" in issues[0].recommendation

    def test_detect_path_traversal(self, scanner):
        """Test detection of path traversal vulnerability"""
        code = """
def read_file(filename):
    with open(f"/data/{filename}") as f:
        return f.read()
"""
        tree = ast.parse(code)

        issues = scanner.detect_path_traversal(tree, code)

        assert len(issues) == 1
        assert issues[0].issue_type == "path_traversal"
        assert issues[0].severity == "high"
        assert issues[0].cwe_id == "CWE-22"

    def test_path_traversal_safe_path(self, scanner):
        """Test that static paths are not flagged"""
        code = """
def read_file():
    with open("/etc/config.txt") as f:
        return f.read()
"""
        tree = ast.parse(code)

        issues = scanner.detect_path_traversal(tree, code)

        # Static path should not be flagged
        assert len(issues) == 0

    def test_detect_weak_crypto_md5(self, scanner):
        """Test detection of weak MD5 usage"""
        code = """
import hashlib
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
"""
        tree = ast.parse(code)

        issues = scanner.detect_weak_crypto(tree, code)

        assert len(issues) == 1
        assert issues[0].issue_type == "weak_crypto"
        assert issues[0].severity == "medium"
        assert "md5" in issues[0].description.lower()

    def test_detect_weak_crypto_sha1(self, scanner):
        """Test detection of weak SHA1 usage"""
        code = """
import hashlib
def hash_data(data):
    return hashlib.sha1(data.encode()).hexdigest()
"""
        tree = ast.parse(code)

        issues = scanner.detect_weak_crypto(tree, code)

        assert len(issues) == 1
        assert "sha1" in issues[0].description.lower()

    def test_strong_crypto_not_flagged(self, scanner):
        """Test that strong crypto algorithms are not flagged"""
        code = """
import hashlib
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
"""
        tree = ast.parse(code)

        issues = scanner.detect_weak_crypto(tree, code)

        # SHA-256 should not be flagged
        assert len(issues) == 0

    def test_calculate_security_score_perfect(self, scanner):
        """Test security score with no issues"""
        score = scanner.calculate_security_score([], [], [], [], [], [], [])
        assert score == 100

    def test_calculate_security_score_critical_issues(self, scanner):
        """Test security score with critical issues"""
        sql_injection = [
            SecurityIssue("sql_injection", "test", "critical", "Test", "Test", "CWE-89")
        ]
        hardcoded_secrets = [
            SecurityIssue("hardcoded_secret", "test", "critical", "Test", "Test", "CWE-798")
        ]

        score = scanner.calculate_security_score(
            sql_injection, [], hardcoded_secrets, [], [], [], []
        )

        # Score should be: 100 - 30 (sql) - 25 (secrets) = 45
        assert score == 45

    def test_calculate_security_score_all_issues(self, scanner):
        """Test security score with all types of issues"""
        sql = [SecurityIssue("sql_injection", "test", "critical", "Test", "Test")]
        cmd = [SecurityIssue("command_injection", "test", "critical", "Test", "Test")]
        secrets = [SecurityIssue("hardcoded_secret", "test", "critical", "Test", "Test")]
        eval_use = [SecurityIssue("dangerous_function", "test", "critical", "Test", "Test")]
        path = [SecurityIssue("path_traversal", "test", "high", "Test", "Test")]
        random_use = [SecurityIssue("insecure_random", "test", "medium", "Test", "Test")]
        crypto = [SecurityIssue("weak_crypto", "test", "medium", "Test", "Test")]

        score = scanner.calculate_security_score(
            sql, cmd, secrets, eval_use, random_use, path, crypto
        )

        # Score should be 0 (100 - 30 - 30 - 25 - 25 - 15 - 10 - 10 = -45, capped at 0)
        assert score == 0

    def test_generate_recommendations_with_critical_issues(self, scanner):
        """Test recommendation generation with critical issues"""
        sql = [SecurityIssue("sql_injection", "test", "critical", "Test", "Test")]
        secrets = [SecurityIssue("hardcoded_secret", "test", "critical", "Test", "Test")]

        recommendations = scanner.generate_recommendations(sql, [], secrets, [], [], [], [])

        assert len(recommendations) >= 2
        assert any("CRITICAL" in r and "SQL injection" in r for r in recommendations)
        assert any("CRITICAL" in r and "secret" in r for r in recommendations)

    def test_generate_recommendations_no_issues(self, scanner):
        """Test recommendations with no issues"""
        recommendations = scanner.generate_recommendations([], [], [], [], [], [], [])

        assert len(recommendations) == 1
        assert "No critical security issues" in recommendations[0]

    def test_analyze_file_success(self, scanner, tmp_path):
        """Test full file analysis"""
        test_file = tmp_path / "test_security.py"
        test_file.write_text(
            """
import hashlib
password = "test123"

def hash_data(data):
    return hashlib.md5(data.encode()).hexdigest()
"""
        )

        result = scanner.analyze_file(str(test_file))

        assert "sql_injection" in result
        assert "command_injection" in result
        assert "hardcoded_secrets" in result
        assert "eval_usage" in result
        assert "insecure_random" in result
        assert "path_traversal" in result
        assert "weak_crypto" in result
        assert "security_score" in result
        assert "recommendations" in result
        assert 0 <= result["security_score"] <= 100

        # Should detect hardcoded password and weak crypto
        assert len(result["hardcoded_secrets"]) > 0
        assert len(result["weak_crypto"]) > 0

    def test_analyze_file_not_found(self, scanner):
        """Test analysis of non-existent file"""
        with pytest.raises(FileNotFoundError):
            scanner.analyze_file("/nonexistent/file.py")

    def test_analyze_file_syntax_error(self, scanner, tmp_path):
        """Test analysis of file with syntax errors"""
        test_file = tmp_path / "bad.py"
        test_file.write_text("def invalid syntax here")

        result = scanner.analyze_file(str(test_file))

        # Should return error result
        assert result["security_score"] == 0
        assert "Syntax error" in result["recommendations"][0]

    def test_is_sql_call(self, scanner):
        """Test SQL call detection"""
        code = "cursor.execute('SELECT * FROM users')"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert scanner._is_sql_call(call_node) is True

    def test_is_command_call(self, scanner):
        """Test command call detection"""
        code = "subprocess.call(['ls'])"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert scanner._is_command_call(call_node) is True

    def test_has_shell_true(self, scanner):
        """Test shell=True detection"""
        code = "subprocess.call(cmd, shell=True)"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert scanner._has_shell_true(call_node) is True

    def test_has_shell_false(self, scanner):
        """Test shell=False detection"""
        code = "subprocess.call(cmd, shell=False)"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert scanner._has_shell_true(call_node) is False

    def test_uses_string_formatting_fstring(self, scanner):
        """Test f-string formatting detection"""
        code = "execute(f'SELECT * FROM {table}')"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert scanner._uses_string_formatting(call_node) is True

    def test_uses_string_formatting_format(self, scanner):
        """Test .format() detection"""
        code = "execute('SELECT * FROM {}'.format(table))"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert scanner._uses_string_formatting(call_node) is True

    def test_is_dynamic_string(self, scanner):
        """Test dynamic string detection"""
        # f-string
        code = "f'test {var}'"
        tree = ast.parse(code)
        node = tree.body[0].value

        assert scanner._is_dynamic_string(node) is True

    def test_multiple_vulnerabilities(self, scanner, tmp_path):
        """Test file with multiple security vulnerabilities"""
        test_file = tmp_path / "vulnerable.py"
        test_file.write_text(
            """
import subprocess
import hashlib

password = "admin123"
api_key = "secret-key"

def run_command(user_input):
    subprocess.call(user_input, shell=True)

def hash_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()

def execute_code(code):
    eval(code)
"""
        )

        result = scanner.analyze_file(str(test_file))

        # Should detect multiple types of vulnerabilities
        assert len(result["hardcoded_secrets"]) >= 2
        assert len(result["command_injection"]) >= 1
        assert len(result["weak_crypto"]) >= 1
        assert len(result["eval_usage"]) >= 1
        assert result["security_score"] < 50  # Low score due to multiple issues
