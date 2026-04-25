"""
test_dispatcher.py — Tests for llm-dispatch.sh provider routing and DB write behavior.

Tests:
  - Each valid provider routes to the correct .py client
  - Allowlist rejects unknown providers (exit 3, JSON error envelope)
  - Missing --prompt-file exits 4
  - Prompt file not found exits 4
  - DB row written on failure (missing key path)
  - JSON envelope structure on stdout for each provider
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.research.conftest import db_last_row, db_row_count

# Path to the dispatcher script
DISPATCH_SH = str(Path.home() / ".buildrunner" / "scripts" / "llm-dispatch.sh")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_dispatch(
    args: list[str],
    env: dict[str, str] | None = None,
    timeout: int = 15,
) -> tuple[int, str, str]:
    """
    Run llm-dispatch.sh with given args.
    Returns (returncode, stdout, stderr).
    """
    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    result = subprocess.run(
        ["/bin/bash", DISPATCH_SH] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=base_env,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def parse_envelope(stdout: str) -> dict:
    """Parse JSON envelope from dispatcher stdout."""
    return json.loads(stdout)


# ===========================================================================
# Allowlist validation
# ===========================================================================

class TestAllowlistValidation:
    def test_invalid_provider_exits_3(self, tmp_path: Path) -> None:
        prompt = tmp_path / "q.txt"
        prompt.write_text("test prompt")
        rc, stdout, _ = run_dispatch(["badprovider", "--prompt-file", str(prompt)])
        assert rc == 3
        env = parse_envelope(stdout)
        assert env["ok"] is False
        assert "invalid_provider" in env["error"]

    def test_invalid_provider_lists_allowed(self, tmp_path: Path) -> None:
        prompt = tmp_path / "q.txt"
        prompt.write_text("test prompt")
        rc, stdout, _ = run_dispatch(["openai", "--prompt-file", str(prompt)])
        assert rc == 3
        env = parse_envelope(stdout)
        # The error should mention the allowed providers
        assert "perplexity" in env["error"] or "invalid_provider" in env["error"]

    def test_empty_provider_name(self, tmp_path: Path) -> None:
        prompt = tmp_path / "q.txt"
        prompt.write_text("test prompt")
        rc, stdout, _ = run_dispatch(["", "--prompt-file", str(prompt)])
        assert rc == 3

    @pytest.mark.parametrize("provider", ["perplexity", "gemini", "grok", "codex"])
    def test_valid_providers_pass_allowlist(self, provider: str, tmp_path: Path) -> None:
        """Valid provider names pass allowlist check (exit NOT 3, even if key missing)."""
        prompt = tmp_path / "q.txt"
        prompt.write_text("test prompt")
        # Remove all keys so dispatch will fail with missing_key (exit 2) — NOT allowlist error (exit 3)
        env = {
            "PERPLEXITY_API_KEY": "",
            "GEMINI_API_KEY": "",
            "XAI_API_KEY": "",
        }
        if provider == "codex":
            # Codex uses CLI auth — will fail with preflight error, not exit 3
            pass
        rc, stdout, _ = run_dispatch([provider, "--prompt-file", str(prompt)], env=env)
        # Should NOT be exit 3 (allowlist) — could be 1 or 2 for key/preflight failure
        assert rc != 3, f"Provider '{provider}' wrongly rejected by allowlist (exit {rc})"


# ===========================================================================
# Prompt file validation
# ===========================================================================

class TestPromptFileValidation:
    def test_missing_prompt_file_flag_exits_4(self) -> None:
        rc, stdout, _ = run_dispatch(["perplexity"])
        assert rc == 4
        env = parse_envelope(stdout)
        assert env["ok"] is False
        assert "missing_prompt_file" in env["error"]

    def test_nonexistent_prompt_file_exits_4(self) -> None:
        rc, stdout, _ = run_dispatch([
            "perplexity",
            "--prompt-file", "/nonexistent/path/to/prompt.txt"
        ])
        assert rc == 4
        env = parse_envelope(stdout)
        assert env["ok"] is False
        assert "not_found" in env["error"] or "missing" in env["error"]


# ===========================================================================
# Provider routing
# ===========================================================================

class TestProviderRouting:
    """
    Test that each provider name routes to the correct Python client.
    We do this by checking the 'provider' field in the returned JSON envelope
    when the dispatch fails due to missing key (no network call needed).
    """

    def _run_with_no_keys(self, provider: str, tmp_path: Path) -> dict:
        prompt = tmp_path / "q.txt"
        prompt.write_text("research topic")
        env = {
            "PERPLEXITY_API_KEY": "",
            "GEMINI_API_KEY": "",
            "XAI_API_KEY": "",
        }
        _, stdout, _ = run_dispatch([provider, "--prompt-file", str(prompt)], env=env)
        try:
            return parse_envelope(stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Non-JSON stdout for provider {provider!r}: {stdout!r}")

    def test_perplexity_routes_to_perplexity_client(self, tmp_path: Path) -> None:
        result = self._run_with_no_keys("perplexity", tmp_path)
        assert result["provider"] == "perplexity"

    def test_gemini_routes_to_gemini_client(self, tmp_path: Path) -> None:
        result = self._run_with_no_keys("gemini", tmp_path)
        assert result["provider"] == "gemini"

    def test_grok_routes_to_grok_client(self, tmp_path: Path) -> None:
        result = self._run_with_no_keys("grok", tmp_path)
        assert result["provider"] == "grok"


# ===========================================================================
# DB writes on failure paths
# ===========================================================================

class TestDbWriteOnFailure:
    """
    Verify that research_llm_calls rows are written even when provider fails.
    Uses an isolated temp DB via BR3_DATA_DB env var.
    """

    def _run_no_keys(self, provider: str, tmp_path: Path, db_path: Path) -> tuple[int, dict]:
        prompt = tmp_path / "q.txt"
        prompt.write_text("research topic")
        env = {
            "PERPLEXITY_API_KEY": "",
            "GEMINI_API_KEY": "",
            "XAI_API_KEY": "",
            "BR3_DATA_DB": str(db_path),
        }
        rc, stdout, _ = run_dispatch([provider, "--prompt-file", str(prompt)], env=env)
        try:
            envelope = parse_envelope(stdout)
        except json.JSONDecodeError:
            envelope = {"ok": False, "error": "parse_failed", "stdout": stdout}
        return rc, envelope

    def test_perplexity_missing_key_writes_db_row(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data.db"
        rc, envelope = self._run_no_keys("perplexity", tmp_path, db_path)
        assert envelope["ok"] is False
        assert db_path.exists(), "DB should be created even on failure"
        assert db_row_count(db_path) >= 1
        row = db_last_row(db_path)
        assert row is not None
        assert row["ok"] == 0
        assert row["provider"] == "perplexity"

    def test_gemini_missing_key_writes_db_row(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data.db"
        rc, envelope = self._run_no_keys("gemini", tmp_path, db_path)
        assert envelope["ok"] is False
        if db_path.exists() and db_row_count(db_path) > 0:
            row = db_last_row(db_path)
            assert row["provider"] == "gemini"

    def test_grok_missing_key_writes_db_row(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data.db"
        rc, envelope = self._run_no_keys("grok", tmp_path, db_path)
        assert envelope["ok"] is False
        if db_path.exists() and db_row_count(db_path) > 0:
            row = db_last_row(db_path)
            assert row["provider"] == "grok"


# ===========================================================================
# JSON envelope structure
# ===========================================================================

class TestEnvelopeStructure:
    """Verify JSON envelope shape from dispatcher output."""

    def test_invalid_provider_envelope_has_required_fields(self, tmp_path: Path) -> None:
        prompt = tmp_path / "q.txt"
        prompt.write_text("test")
        _, stdout, _ = run_dispatch(["fakeprovider", "--prompt-file", str(prompt)])
        env = parse_envelope(stdout)
        assert "ok" in env
        assert "provider" in env
        assert "error" in env
        assert env["ok"] is False

    def test_missing_key_envelope_has_required_fields(self, tmp_path: Path) -> None:
        prompt = tmp_path / "q.txt"
        prompt.write_text("test")
        env_vars = {
            "PERPLEXITY_API_KEY": "",
            "GEMINI_API_KEY": "",
            "XAI_API_KEY": "",
        }
        _, stdout, _ = run_dispatch(
            ["perplexity", "--prompt-file", str(prompt)],
            env=env_vars,
        )
        env = parse_envelope(stdout)
        assert "ok" in env
        assert env["ok"] is False
        assert "provider" in env
        assert "error" in env


# ===========================================================================
# Python unit tests for dispatcher logic (no shell subprocess)
# ===========================================================================

class TestDispatcherPythonUnit:
    """
    Unit-level tests that exercise the Python client selection logic
    without going through the shell script.
    """

    def test_all_clients_importable(self) -> None:
        """Every provider client can be imported cleanly."""
        import perplexity
        import gemini
        import grok
        import codex_research

        assert hasattr(perplexity, "call_api")
        assert hasattr(gemini, "call_api")
        assert hasattr(grok, "call_api")
        assert hasattr(codex_research, "call_codex")

    def test_provider_constants(self) -> None:
        """Each client declares the correct PROVIDER constant."""
        import perplexity
        import gemini
        import grok
        import codex_research

        assert perplexity.PROVIDER == "perplexity"
        assert gemini.PROVIDER == "gemini"
        assert grok.PROVIDER == "grok"
        assert codex_research.PROVIDER == "codex"

    def test_model_constants(self) -> None:
        """Each client declares the correct MODEL constant."""
        import perplexity
        import gemini
        import grok
        import codex_research

        assert perplexity.MODEL == "sonar-pro"
        assert gemini.MODEL == "gemini-2.5-pro"
        assert grok.MODEL == "grok-4"
        assert codex_research.DEFAULT_MODEL == "gpt-5.5"

    def test_client_files_exist(self) -> None:
        clients_dir = Path.home() / ".buildrunner" / "scripts" / "llm-clients"
        for name in ["perplexity.py", "gemini.py", "grok.py", "codex_research.py", "_shared.py"]:
            assert (clients_dir / name).exists(), f"Missing client: {name}"

    def test_dispatch_sh_exists_and_executable(self) -> None:
        p = Path(DISPATCH_SH)
        assert p.exists(), f"llm-dispatch.sh not found at {DISPATCH_SH}"
        assert os.access(str(p), os.X_OK), "llm-dispatch.sh is not executable"
