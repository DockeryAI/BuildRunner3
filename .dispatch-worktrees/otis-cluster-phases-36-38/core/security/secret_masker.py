"""Secret masking utilities for BuildRunner.

This module provides functionality to detect and mask sensitive values
in terminal output, logs, and telemetry to prevent accidental exposure.
"""

import re
from typing import Optional


class SecretMasker:
    """Mask sensitive values in terminal output and logs.

    This class provides methods to detect and mask secrets like API keys,
    tokens, and passwords to prevent accidental exposure in CLI output,
    logs, and telemetry data.

    Example:
        >>> masker = SecretMasker()
        >>> masker.mask_value("sk-ant-api03-abc123def456")
        'sk-a...456'

        >>> masker.mask_config_value("api_key", "secret-value")
        'secr...alue'

        >>> masker.sanitize_text("My key is sk-ant-api03-abc123")
        'My key is sk-a...123'
    """

    # Regex patterns for common API key formats
    # Patterns are designed to be strict enough to avoid false positives
    # but flexible enough to catch real-world keys
    SENSITIVE_PATTERNS = {
        "anthropic_key": r"sk-ant-[a-zA-Z0-9_-]{20,}",  # Relaxed from 85+ to 20+
        "openai_key": r"sk-proj-[a-zA-Z0-9]{20,}",  # Relaxed from 40+ to 20+
        "openai_legacy_key": r"sk-[a-zA-Z0-9]{32,}",  # More flexible range
        "openrouter_key": r"sk-or-v1-[a-f0-9]{64}",
        "jwt_token": r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
        "notion_secret": r"ntn_[a-zA-Z0-9]{20,}",  # Relaxed from 40+ to 20+
        "notion_token": r"secret_[a-zA-Z0-9]{20,}",  # Relaxed from 40+ to 20+
        "apify_key": r"apify_api_[a-zA-Z0-9]{20,}",  # Relaxed from 30+ to 20+
        "bearer_token": r"Bearer\s+[a-zA-Z0-9_.\-]{20,}",
        "basic_auth": r"Basic\s+[a-zA-Z0-9+/=]{20,}",
        "aws_key": r"AKIA[0-9A-Z]{16}",
        "github_token": r"gh[pousr]_[A-Za-z0-9_]{36,255}",
        "slack_token": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,}",
        "generic_api_key": r"[a-zA-Z0-9_-]{32,}",  # Last resort, lower priority
    }

    # Keywords that indicate sensitive values
    SENSITIVE_KEYS = {
        "api_key",
        "apikey",
        "api-key",
        "secret",
        "secret_key",
        "secret-key",
        "token",
        "auth_token",
        "auth-token",
        "access_token",
        "password",
        "passwd",
        "pwd",
        "key",
        "private_key",
        "private-key",
        "auth",
        "authorization",
        "credential",
        "credentials",
        "jwt",
        "bearer",
        "session",
        "session_id",
        "session-id",
    }

    @staticmethod
    def mask_value(value: str, show_chars: int = 4) -> str:
        """Mask a sensitive value, showing only first and last characters.

        Args:
            value: The sensitive value to mask
            show_chars: Number of characters to show at start/end (default: 4)

        Returns:
            Masked value like "sk-a...123" or "****" for very short values

        Example:
            >>> SecretMasker.mask_value("sk-ant-api03-abc123def456")
            'sk-a...f456'
            >>> SecretMasker.mask_value("short")
            '****'
        """
        if not value:
            return "****"

        # For very short values, just mask completely
        if len(value) < 8:
            return "****"

        # Show first N and last N characters
        return f"{value[:show_chars]}...{value[-show_chars:]}"

    @staticmethod
    def is_sensitive_key(key: str) -> bool:
        """Check if a key name indicates a sensitive value.

        Args:
            key: The key name to check (e.g., "api_key", "password")

        Returns:
            True if key name suggests sensitive data

        Example:
            >>> SecretMasker.is_sensitive_key("api_key")
            True
            >>> SecretMasker.is_sensitive_key("username")
            False
        """
        key_lower = key.lower()

        # Exact match
        if key_lower in SecretMasker.SENSITIVE_KEYS:
            return True

        # Substring match (e.g., "my_api_key" contains "api_key")
        for sensitive_key in SecretMasker.SENSITIVE_KEYS:
            if sensitive_key in key_lower:
                return True

        return False

    @staticmethod
    def mask_config_value(key: str, value: str, show_chars: int = 4) -> str:
        """Mask a configuration value if the key suggests it's sensitive.

        Args:
            key: Configuration key name
            value: Configuration value
            show_chars: Number of characters to show (default: 4)

        Returns:
            Masked value if key is sensitive, original value otherwise

        Example:
            >>> SecretMasker.mask_config_value("api_key", "secret123")
            'secr...123'
            >>> SecretMasker.mask_config_value("username", "john")
            'john'
        """
        if SecretMasker.is_sensitive_key(key):
            return SecretMasker.mask_value(value, show_chars)
        return value

    @staticmethod
    def sanitize_text(text: str, show_chars: int = 4) -> str:
        """Replace all detected secrets in text with masked versions.

        This scans the entire text for patterns matching known secret formats
        and replaces them with masked values.

        Args:
            text: Text that may contain secrets
            show_chars: Number of characters to show in masked values

        Returns:
            Text with all detected secrets masked

        Example:
            >>> SecretMasker.sanitize_text("Use key sk-ant-api03-abc123")
            'Use key sk-a...123'
        """
        if not text:
            return text

        sanitized = text

        # Apply each pattern in order (most specific first)
        for pattern_name, pattern in SecretMasker.SENSITIVE_PATTERNS.items():
            # Skip generic pattern on first pass
            if pattern_name == "generic_api_key":
                continue

            def mask_match(match):
                return SecretMasker.mask_value(match.group(0), show_chars)

            sanitized = re.sub(pattern, mask_match, sanitized)

        return sanitized

    @staticmethod
    def sanitize_dict(data: dict, show_chars: int = 4) -> dict:
        """Recursively sanitize a dictionary, masking sensitive values.

        Args:
            data: Dictionary that may contain sensitive values
            show_chars: Number of characters to show in masked values

        Returns:
            New dictionary with sensitive values masked

        Example:
            >>> SecretMasker.sanitize_dict({"api_key": "secret", "name": "app"})
            {'api_key': 'secr...ret', 'name': 'app'}
        """
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = SecretMasker.sanitize_dict(value, show_chars)
            elif isinstance(value, list):
                # Sanitize lists
                sanitized[key] = [
                    (
                        SecretMasker.sanitize_dict(item, show_chars)
                        if isinstance(item, dict)
                        else (
                            SecretMasker.sanitize_text(str(item), show_chars)
                            if isinstance(item, str)
                            else item
                        )
                    )
                    for item in value
                ]
            elif isinstance(value, str):
                # Mask if key is sensitive OR if value matches pattern
                if SecretMasker.is_sensitive_key(key):
                    sanitized[key] = SecretMasker.mask_value(value, show_chars)
                else:
                    sanitized[key] = SecretMasker.sanitize_text(value, show_chars)
            else:
                # Non-string values pass through
                sanitized[key] = value

        return sanitized

    @staticmethod
    def detect_pattern(text: str) -> Optional[str]:
        """Detect which secret pattern matches the text, if any.

        Args:
            text: Text to check for secret patterns

        Returns:
            Pattern name if matched, None otherwise

        Example:
            >>> SecretMasker.detect_pattern("sk-ant-api03-abc123")
            'anthropic_key'
        """
        for pattern_name, pattern in SecretMasker.SENSITIVE_PATTERNS.items():
            if pattern_name == "generic_api_key":
                continue  # Skip generic pattern for detection

            if re.search(pattern, text):
                return pattern_name

        return None
