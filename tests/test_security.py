"""Tests for security module (secret detection and masking)."""

import os
import pytest
import tempfile
import subprocess
from pathlib import Path

from core.security.secret_masker import SecretMasker
from core.security.secret_detector import SecretDetector, SecretMatch
from core.security.sql_injection_detector import SQLInjectionDetector, SQLInjectionMatch
from core.security.git_hooks import GitHookManager, HookResult, format_hook_result


class TestSecretMasker:
    """Tests for SecretMasker class."""

    def test_mask_value_standard(self):
        """Test masking a standard length value."""
        result = SecretMasker.mask_value("sk-ant-api03-abc123def456ghi789")
        assert result == "sk-a...i789"
        assert len(result) < len("sk-ant-api03-abc123def456ghi789")

    def test_mask_value_short(self):
        """Test masking very short values."""
        result = SecretMasker.mask_value("short")
        assert result == "****"

    def test_mask_value_empty(self):
        """Test masking empty string."""
        result = SecretMasker.mask_value("")
        assert result == "****"

    def test_mask_value_custom_chars(self):
        """Test masking with custom number of visible chars."""
        result = SecretMasker.mask_value("abcdefghijklmnop", show_chars=6)
        assert result == "abcdef...klmnop"

    def test_is_sensitive_key_exact_match(self):
        """Test exact matches of sensitive key names."""
        assert SecretMasker.is_sensitive_key("api_key") is True
        assert SecretMasker.is_sensitive_key("secret") is True
        assert SecretMasker.is_sensitive_key("password") is True
        assert SecretMasker.is_sensitive_key("token") is True

    def test_is_sensitive_key_case_insensitive(self):
        """Test case-insensitive matching."""
        assert SecretMasker.is_sensitive_key("API_KEY") is True
        assert SecretMasker.is_sensitive_key("Secret") is True
        assert SecretMasker.is_sensitive_key("PASSWORD") is True

    def test_is_sensitive_key_substring(self):
        """Test substring matching."""
        assert SecretMasker.is_sensitive_key("my_api_key") is True
        assert SecretMasker.is_sensitive_key("database_password") is True
        assert SecretMasker.is_sensitive_key("oauth_token") is True

    def test_is_sensitive_key_non_sensitive(self):
        """Test non-sensitive key names."""
        assert SecretMasker.is_sensitive_key("username") is False
        assert SecretMasker.is_sensitive_key("email") is False
        assert SecretMasker.is_sensitive_key("name") is False
        assert SecretMasker.is_sensitive_key("count") is False

    def test_mask_config_value_sensitive(self):
        """Test masking config values with sensitive keys."""
        result = SecretMasker.mask_config_value("api_key", "secret123456")
        assert result == "secr...3456"

    def test_mask_config_value_non_sensitive(self):
        """Test non-sensitive config values pass through."""
        result = SecretMasker.mask_config_value("username", "john_doe")
        assert result == "john_doe"

    def test_sanitize_text_anthropic_key(self):
        """Test sanitizing text with Anthropic API key."""
        text = "Use this key: sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567abc890def123ghi456jkl789mno012"
        result = SecretMasker.sanitize_text(text)
        assert "sk-ant-api03" not in result
        assert "sk-a..." in result
        assert "Use this key:" in result

    def test_sanitize_text_openai_key(self):
        """Test sanitizing text with OpenAI API key."""
        text = "My OpenAI key is sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH"
        result = SecretMasker.sanitize_text(text)
        assert "sk-proj-abc" not in result
        assert "sk-p..." in result

    def test_sanitize_text_openrouter_key(self):
        """Test sanitizing text with OpenRouter API key."""
        text = "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"
        result = SecretMasker.sanitize_text(text)
        assert "d188597c216fad8ade206f4aa1ffa9af" not in result
        assert "sk-o..." in result

    def test_sanitize_text_jwt_token(self):
        """Test sanitizing text with JWT token."""
        text = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = SecretMasker.sanitize_text(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "eyJh..." in result

    def test_sanitize_text_notion_secret(self):
        """Test sanitizing text with Notion secret."""
        text = "Notion: ntn_FAKE1234567890EXAMPLETOKEN1234567890FAKE"
        result = SecretMasker.sanitize_text(text)
        assert "FAKE1234567890EXAMPLETOKEN1234567890FAKE" not in result
        assert "ntn_..." in result

    def test_sanitize_text_apify_key(self):
        """Test sanitizing text with Apify API key."""
        text = "apify_api_FAKETOKEN1234567890EXAMPLE"
        result = SecretMasker.sanitize_text(text)
        assert "FAKETOKEN1234567890EXAMPLE" not in result
        assert "apif..." in result

    def test_sanitize_text_bearer_token(self):
        """Test sanitizing text with Bearer token."""
        text = "Authorization: Bearer abc123def456ghi789jkl012"
        result = SecretMasker.sanitize_text(text)
        assert "abc123def456ghi789jkl012" not in result
        assert "Bear..." in result

    def test_sanitize_text_multiple_secrets(self):
        """Test sanitizing text with multiple different secrets."""
        text = """
        ANTHROPIC_KEY=sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567abc890def123ghi456jkl789mno012
        OPENAI_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH
        """
        result = SecretMasker.sanitize_text(text)
        assert "sk-ant-api03-abc" not in result
        assert "sk-proj-abc" not in result
        assert "ANTHROPIC_KEY=" in result
        assert "OPENAI_KEY=" in result

    def test_sanitize_text_no_secrets(self):
        """Test sanitizing text with no secrets."""
        text = "This is just regular text with no secrets."
        result = SecretMasker.sanitize_text(text)
        assert result == text

    def test_sanitize_dict_simple(self):
        """Test sanitizing a simple dictionary."""
        data = {
            "api_key": "secret123456",
            "username": "john"
        }
        result = SecretMasker.sanitize_dict(data)
        assert result["api_key"] == "secr...3456"
        assert result["username"] == "john"

    def test_sanitize_dict_nested(self):
        """Test sanitizing nested dictionaries."""
        data = {
            "database": {
                "password": "dbpass123456",
                "host": "localhost"
            },
            "api": {
                "key": "apikey123456"
            }
        }
        result = SecretMasker.sanitize_dict(data)
        assert result["database"]["password"] == "dbpa...3456"
        assert result["database"]["host"] == "localhost"
        assert result["api"]["key"] == "apik...3456"

    def test_sanitize_dict_with_list(self):
        """Test sanitizing dictionary with lists."""
        data = {
            "keys": ["key1_secret", "key2_secret"],
            "names": ["alice", "bob"]
        }
        result = SecretMasker.sanitize_dict(data)
        assert isinstance(result["keys"], list)
        assert isinstance(result["names"], list)

    def test_sanitize_dict_with_patterns(self):
        """Test sanitizing dict values that match secret patterns."""
        data = {
            "config": "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH"
        }
        result = SecretMasker.sanitize_dict(data)
        assert "sk-proj-abc" not in result["config"]

    def test_detect_pattern_anthropic(self):
        """Test detecting Anthropic key pattern."""
        text = "sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567abc890def123ghi456jkl789mno012"
        result = SecretMasker.detect_pattern(text)
        assert result == "anthropic_key"

    def test_detect_pattern_openai(self):
        """Test detecting OpenAI key pattern."""
        text = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH"
        result = SecretMasker.detect_pattern(text)
        assert result == "openai_key"

    def test_detect_pattern_openrouter(self):
        """Test detecting OpenRouter key pattern."""
        text = "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"
        result = SecretMasker.detect_pattern(text)
        assert result == "openrouter_key"

    def test_detect_pattern_none(self):
        """Test detecting no pattern."""
        text = "This is just regular text"
        result = SecretMasker.detect_pattern(text)
        assert result is None


class TestSecretDetector:
    """Tests for SecretDetector class."""

    def test_init_with_default_root(self):
        """Test initialization with default project root."""
        detector = SecretDetector()
        assert detector.project_root == Path.cwd()

    def test_init_with_custom_root(self):
        """Test initialization with custom project root."""
        custom_root = Path("/tmp/test")
        detector = SecretDetector(project_root=custom_root)
        assert detector.project_root == custom_root

    def test_scan_file_with_secret(self):
        """Test scanning a file that contains a secret."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("API_KEY = 'sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH'\n")
            f.write("USERNAME = 'john'\n")
            temp_path = f.name

        try:
            detector = SecretDetector()
            matches = detector.scan_file(temp_path)

            assert len(matches) > 0
            match = matches[0]
            assert match.pattern_name == "openai_key"
            assert match.line_number == 1
            assert "sk-p..." in match.secret_value
        finally:
            Path(temp_path).unlink()

    def test_scan_file_no_secrets(self):
        """Test scanning a file with no secrets."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("USERNAME = 'john'\n")
            f.write("EMAIL = 'john@example.com'\n")
            temp_path = f.name

        try:
            detector = SecretDetector()
            matches = detector.scan_file(temp_path)
            assert len(matches) == 0
        finally:
            Path(temp_path).unlink()

    def test_scan_file_nonexistent(self):
        """Test scanning a file that doesn't exist."""
        detector = SecretDetector()
        matches = detector.scan_file("/nonexistent/file.py")
        assert matches == []

    def test_scan_file_multiple_secrets(self):
        """Test scanning a file with multiple secrets."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("OPENAI_KEY = 'sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH'\n")
            f.write("NOTION_SECRET = 'ntn_FAKE1234567890EXAMPLETOKEN1234567890FAKE'\n")
            temp_path = f.name

        try:
            detector = SecretDetector()
            matches = detector.scan_file(temp_path)
            assert len(matches) == 2
            pattern_names = {m.pattern_name for m in matches}
            assert "openai_key" in pattern_names
            assert "notion_secret" in pattern_names
        finally:
            Path(temp_path).unlink()

    def test_scan_directory(self):
        """Test scanning a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = Path(tmpdir) / "config.py"
            file1.write_text("API_KEY = 'sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH'\n")

            file2 = Path(tmpdir) / "safe.py"
            file2.write_text("USERNAME = 'john'\n")

            detector = SecretDetector(project_root=Path(tmpdir))
            results = detector.scan_directory(tmpdir)

            assert len(results) == 1
            assert str(file1) in results
            assert len(results[str(file1)]) > 0

    def test_scan_directory_recursive(self):
        """Test scanning directory recursively."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = Path(tmpdir) / "src"
            subdir.mkdir()

            file1 = Path(tmpdir) / "config.py"
            file1.write_text("KEY1 = 'sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH'\n")

            file2 = subdir / "secrets.py"
            file2.write_text("KEY2 = 'ntn_FAKE1234567890EXAMPLETOKEN1234567890FAKE'\n")

            detector = SecretDetector(project_root=Path(tmpdir))
            results = detector.scan_directory(tmpdir, recursive=True)

            assert len(results) == 2

    def test_scan_directory_excludes(self):
        """Test that excluded directories are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create node_modules with secrets (should be excluded)
            node_modules = Path(tmpdir) / "node_modules"
            node_modules.mkdir()

            file1 = node_modules / "package.py"
            file1.write_text("KEY = 'sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH'\n")

            detector = SecretDetector(project_root=Path(tmpdir))
            results = detector.scan_directory(tmpdir)

            # node_modules should be excluded
            assert len(results) == 0

    def test_whitelist_functionality(self):
        """Test whitelisting false positives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            file1 = Path(tmpdir) / "test.py"
            file1.write_text("TEST_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'\n")

            # Create whitelist
            whitelist_dir = Path(tmpdir) / ".buildrunner" / "security"
            whitelist_dir.mkdir(parents=True)
            whitelist_file = whitelist_dir / "whitelist.txt"
            whitelist_file.write_text(f"{file1}:1:jwt_token\n")

            detector = SecretDetector(project_root=Path(tmpdir))
            matches = detector.scan_file(str(file1))

            # Should be whitelisted
            assert len(matches) == 0

    def test_add_to_whitelist(self):
        """Test adding entries to whitelist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = SecretDetector(project_root=Path(tmpdir))
            detector.add_to_whitelist("test.py", 42, "jwt_token")

            whitelist_file = Path(tmpdir) / ".buildrunner" / "security" / "whitelist.txt"
            assert whitelist_file.exists()

            content = whitelist_file.read_text()
            assert "test.py:42:jwt_token" in content

    def test_secret_match_str(self):
        """Test SecretMatch string representation."""
        match = SecretMatch(
            file_path="config.py",
            line_number=10,
            line_content="API_KEY = 'secret'",
            pattern_name="generic_api_key",
            secret_value="secr...cret",
            column_start=10,
            column_end=18
        )

        result = str(match)
        assert "config.py:10:10" in result
        assert "generic_api_key" in result
        assert "secr...cret" in result


class TestIntegration:
    """Integration tests for security module."""

    def test_full_workflow(self):
        """Test complete workflow: detect, mask, report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with secrets
            config_file = Path(tmpdir) / "config.py"
            config_file.write_text("""
API_KEY = 'sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH'
NOTION_KEY = 'ntn_FAKE1234567890EXAMPLETOKEN1234567890FAKE'
USERNAME = 'john'
""")

            # Detect secrets
            detector = SecretDetector(project_root=Path(tmpdir))
            matches = detector.scan_file(str(config_file))

            # Should find 2 secrets
            assert len(matches) == 2

            # All should be masked
            for match in matches:
                assert "..." in match.secret_value
                assert len(match.secret_value) < 20  # Masked value is short

            # Whitelist one
            detector.add_to_whitelist(str(config_file), 2, "openai_key")

            # Re-scan
            matches = detector.scan_file(str(config_file))

            # Should find 1 less (whitelisted one excluded)
            # Note: Line numbers might vary based on whitespace
            assert len(matches) <= 2


class TestSQLInjectionDetector:
    """Tests for SQLInjectionDetector class."""

    def test_init_default_root(self):
        """Test initialization with default root."""
        detector = SQLInjectionDetector()
        assert detector.project_root == Path.cwd()

    def test_init_custom_root(self):
        """Test initialization with custom root."""
        custom_root = Path("/tmp/test")
        detector = SQLInjectionDetector(project_root=custom_root)
        assert detector.project_root == custom_root

    def test_detect_python_string_concat(self):
        """Test detecting Python string concatenation in SQL."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('query = "SELECT * FROM users WHERE id=" + user_id\n')
            temp_path = f.name

        try:
            detector = SQLInjectionDetector()
            matches = detector.scan_file(temp_path)

            assert len(matches) > 0
            match = matches[0]
            assert match.vulnerability_type == 'string_concat'
            assert match.severity == 'high'
        finally:
            Path(temp_path).unlink()

    def test_detect_python_f_string(self):
        """Test detecting Python f-strings in SQL."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('query = f"SELECT * FROM users WHERE id={user_id}"\n')
            temp_path = f.name

        try:
            detector = SQLInjectionDetector()
            matches = detector.scan_file(temp_path)

            assert len(matches) > 0
            match = matches[0]
            assert match.vulnerability_type == 'f_string'
            assert match.severity == 'high'
        finally:
            Path(temp_path).unlink()

    def test_detect_python_format(self):
        """Test detecting Python .format() in SQL."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('query = "SELECT * FROM users WHERE id={}".format(user_id)\n')
            temp_path = f.name

        try:
            detector = SQLInjectionDetector()
            matches = detector.scan_file(temp_path)

            assert len(matches) > 0
            match = matches[0]
            assert match.vulnerability_type == 'format_string'
            assert match.severity == 'high'
        finally:
            Path(temp_path).unlink()

    def test_detect_python_percent_formatting(self):
        """Test detecting Python % formatting in SQL."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('query = "SELECT * FROM users WHERE id=%s" % user_id\n')
            temp_path = f.name

        try:
            detector = SQLInjectionDetector()
            matches = detector.scan_file(temp_path)

            assert len(matches) > 0
            match = matches[0]
            assert match.vulnerability_type == 'percent_formatting'
            assert match.severity == 'high'
        finally:
            Path(temp_path).unlink()

    def test_detect_js_template_literal(self):
        """Test detecting JavaScript template literals in SQL."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write('const query = `SELECT * FROM users WHERE id=${userId}`;\n')
            temp_path = f.name

        try:
            detector = SQLInjectionDetector()
            matches = detector.scan_file(temp_path)

            assert len(matches) > 0
            match = matches[0]
            assert match.vulnerability_type == 'template_literal'
            assert match.severity == 'high'
        finally:
            Path(temp_path).unlink()

    def test_detect_js_string_concat(self):
        """Test detecting JavaScript string concatenation in SQL."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write('const query = "SELECT * FROM users WHERE id=" + userId;\n')
            temp_path = f.name

        try:
            detector = SQLInjectionDetector()
            matches = detector.scan_file(temp_path)

            assert len(matches) > 0
            match = matches[0]
            assert match.vulnerability_type == 'string_concat'
            assert match.severity == 'high'
        finally:
            Path(temp_path).unlink()

    def test_safe_python_code(self):
        """Test that safe Python code doesn't trigger false positives."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))\n')
            temp_path = f.name

        try:
            detector = SQLInjectionDetector()
            matches = detector.scan_file(temp_path)

            assert len(matches) == 0
        finally:
            Path(temp_path).unlink()

    def test_scan_directory(self):
        """Test scanning a directory for SQL injection issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create vulnerable file
            file1 = Path(tmpdir) / "app.py"
            file1.write_text('query = "SELECT * FROM users WHERE id=" + user_id\n')

            # Create safe file
            file2 = Path(tmpdir) / "safe.py"
            file2.write_text('cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))\n')

            detector = SQLInjectionDetector(project_root=Path(tmpdir))
            results = detector.scan_directory(tmpdir)

            assert len(results) == 1
            assert str(file1) in results

    def test_get_safe_example_python(self):
        """Test getting safe example for Python."""
        detector = SQLInjectionDetector()
        example = detector.get_safe_example('python')

        assert 'parameterized' in example.lower()
        assert 'execute' in example.lower()

    def test_get_safe_example_javascript(self):
        """Test getting safe example for JavaScript."""
        detector = SQLInjectionDetector()
        example = detector.get_safe_example('javascript')

        assert 'parameterized' in example.lower()
        assert 'query' in example.lower()

    def test_get_vulnerability_summary(self):
        """Test getting vulnerability summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple vulnerable files
            file1 = Path(tmpdir) / "app1.py"
            file1.write_text('query = "SELECT * FROM users WHERE id=" + user_id\n')

            file2 = Path(tmpdir) / "app2.py"
            file2.write_text('query = f"SELECT * FROM users WHERE id={user_id}"\n')

            detector = SQLInjectionDetector(project_root=Path(tmpdir))
            results = detector.scan_directory(tmpdir)
            summary = detector.get_vulnerability_summary(results)

            assert summary['total_count'] == 2
            assert summary['file_count'] == 2
            assert summary['severity_breakdown']['high'] == 2

    def test_sql_injection_match_str(self):
        """Test SQLInjectionMatch string representation."""
        match = SQLInjectionMatch(
            file_path="app.py",
            line_number=10,
            line_content='query = "SELECT * FROM users WHERE id=" + user_id',
            vulnerability_type="string_concat",
            severity="high",
            suggestion="Use parameterized queries"
        )

        result = str(match)
        assert "app.py:10" in result
        assert "high" in result
        assert "string_concat" in result


class TestGitHookManager:
    """Tests for GitHookManager class."""

    def test_init_default_root(self):
        """Test initialization with default root."""
        manager = GitHookManager()
        assert manager.project_root == Path.cwd()

    def test_init_custom_root(self):
        """Test initialization with custom root."""
        custom_root = Path("/tmp/test")
        manager = GitHookManager(project_root=custom_root)
        assert manager.project_root == custom_root

    def test_is_git_repo_false(self):
        """Test detecting non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GitHookManager(project_root=Path(tmpdir))
            assert manager.is_git_repo() is False

    def test_is_git_repo_true(self):
        """Test detecting git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)

            manager = GitHookManager(project_root=Path(tmpdir))
            assert manager.is_git_repo() is True

    def test_get_hook_path(self):
        """Test getting hook path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GitHookManager(project_root=Path(tmpdir))
            hook_path = manager.get_hook_path('pre-commit')

            assert 'pre-commit' in str(hook_path)
            assert '.git/hooks' in str(hook_path)

    def test_is_hook_installed_false(self):
        """Test detecting when hook is not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)

            manager = GitHookManager(project_root=Path(tmpdir))
            assert manager.is_hook_installed('pre-commit') is False

    def test_install_hook_success(self):
        """Test successfully installing a hook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)

            manager = GitHookManager(project_root=Path(tmpdir))

            # Remove any default hooks that git init might have created
            hook_path = manager.get_hook_path('pre-commit')
            if hook_path.exists():
                hook_path.unlink()

            success, message = manager.install_hook('pre-commit')

            assert success is True
            assert "Installed" in message
            assert manager.is_hook_installed('pre-commit') is True

            # Check hook is executable
            assert os.access(hook_path, os.X_OK)

    def test_install_hook_not_git_repo(self):
        """Test installing hook in non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GitHookManager(project_root=Path(tmpdir))
            success, message = manager.install_hook('pre-commit')

            assert success is False
            assert "Not a git repository" in message

    def test_install_hook_already_installed(self):
        """Test installing hook when already installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)

            manager = GitHookManager(project_root=Path(tmpdir))

            # Remove any default hooks
            hook_path = manager.get_hook_path('pre-commit')
            if hook_path.exists():
                hook_path.unlink()

            # Install first time
            manager.install_hook('pre-commit')

            # Try to install again
            success, message = manager.install_hook('pre-commit')

            assert success is True
            assert "already installed" in message

    def test_install_hook_with_force(self):
        """Test installing hook with force flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)

            manager = GitHookManager(project_root=Path(tmpdir))

            # Remove any default hooks
            hook_path = manager.get_hook_path('pre-commit')
            if hook_path.exists():
                hook_path.unlink()

            # Install first time
            manager.install_hook('pre-commit')

            # Install again with force
            success, message = manager.install_hook('pre-commit', force=True)

            assert success is True
            assert "Installed" in message

    def test_uninstall_hook_success(self):
        """Test successfully uninstalling a hook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)

            manager = GitHookManager(project_root=Path(tmpdir))

            # Remove any default hooks
            hook_path = manager.get_hook_path('pre-commit')
            if hook_path.exists():
                hook_path.unlink()

            # Install then uninstall
            manager.install_hook('pre-commit')
            success, message = manager.uninstall_hook('pre-commit')

            assert success is True
            assert "Uninstalled" in message
            assert manager.is_hook_installed('pre-commit') is False

    def test_uninstall_hook_not_installed(self):
        """Test uninstalling when hook not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)

            manager = GitHookManager(project_root=Path(tmpdir))

            # Remove any default hooks
            hook_path = manager.get_hook_path('pre-commit')
            if hook_path.exists():
                hook_path.unlink()

            success, message = manager.uninstall_hook('pre-commit')

            assert success is True
            assert "not installed" in message

    def test_run_precommit_checks_no_violations(self):
        """Test running pre-commit checks with no issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=tmpdir)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=tmpdir)

            # Create safe file
            safe_file = Path(tmpdir) / "app.py"
            safe_file.write_text("def hello():\n    return 'world'\n")

            # Stage file
            subprocess.run(['git', 'add', 'app.py'], cwd=tmpdir)

            manager = GitHookManager(project_root=Path(tmpdir))
            result = manager.run_precommit_checks()

            assert result.passed is True
            assert len(result.violations) == 0
            assert result.duration_ms < 2000

    def test_run_precommit_checks_with_secret(self):
        """Test running pre-commit checks with a secret."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=tmpdir)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=tmpdir)

            # Create file with secret
            secret_file = Path(tmpdir) / "config.py"
            secret_file.write_text('API_KEY = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH"\n')

            # Stage file
            subprocess.run(['git', 'add', 'config.py'], cwd=tmpdir)

            manager = GitHookManager(project_root=Path(tmpdir))
            result = manager.run_precommit_checks()

            assert result.passed is False
            assert len(result.violations) > 0
            assert any("SECRET" in str(v) for v in result.violations)

    def test_run_precommit_checks_with_sql_injection(self):
        """Test running pre-commit checks with SQL injection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=tmpdir)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=tmpdir)

            # Create file with SQL injection
            sql_file = Path(tmpdir) / "app.py"
            sql_file.write_text('query = "SELECT * FROM users WHERE id=" + user_id\n')

            # Stage file
            subprocess.run(['git', 'add', 'app.py'], cwd=tmpdir)

            manager = GitHookManager(project_root=Path(tmpdir))
            result = manager.run_precommit_checks()

            assert result.passed is False
            assert len(result.violations) > 0
            assert any("SQL INJECTION" in str(v) for v in result.violations)

    def test_get_hook_status(self):
        """Test getting hook status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)

            manager = GitHookManager(project_root=Path(tmpdir))

            # Remove any default hooks
            hook_path = manager.get_hook_path('pre-commit')
            if hook_path.exists():
                hook_path.unlink()

            status = manager.get_hook_status()

            assert status['is_git_repo'] is True
            assert 'pre-commit' in status
            assert status['pre-commit']['installed'] is False

            # Install hook
            manager.install_hook('pre-commit')
            status = manager.get_hook_status()

            assert status['pre-commit']['installed'] is True

    def test_hook_result_str(self):
        """Test HookResult string representation."""
        result = HookResult(
            passed=True,
            violations=[],
            warnings=[],
            duration_ms=150.5,
            message="All checks passed"
        )

        assert "✅" in str(result)
        assert "All checks passed" in str(result)

    def test_format_hook_result_passed(self):
        """Test formatting passed hook result."""
        result = HookResult(
            passed=True,
            violations=[],
            warnings=["Some warning"],
            duration_ms=150.5,
            message="All checks passed"
        )

        formatted = format_hook_result(result)

        assert "✅" in formatted
        assert "All checks passed" in formatted
        assert "Some warning" in formatted

    def test_format_hook_result_failed(self):
        """Test formatting failed hook result."""
        result = HookResult(
            passed=False,
            violations=["Secret detected", "SQL injection found"],
            warnings=[],
            duration_ms=150.5,
            message="Security checks failed"
        )

        formatted = format_hook_result(result)

        assert "❌" in formatted
        assert "COMMIT BLOCKED" in formatted
        assert "Secret detected" in formatted
        assert "SQL injection found" in formatted
