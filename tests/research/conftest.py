"""
conftest.py — shared fixtures for tests/research/.

Provides:
- tmp_prompt_file: a temporary file containing a research prompt
- isolated_db: per-test SQLite path via BR3_DATA_DB env override
- mock_env_with_keys: sets fake API keys in os.environ for the test
- mock_env_no_keys: ensures API keys are absent from os.environ
- reset_circuit_breaker: resets _shared._cb_state between tests
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Make llm-clients importable
LLM_CLIENTS_DIR = str(Path.home() / ".buildrunner" / "scripts" / "llm-clients")
if LLM_CLIENTS_DIR not in sys.path:
    sys.path.insert(0, LLM_CLIENTS_DIR)


# ---------------------------------------------------------------------------
# Prompt file fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_prompt_file(tmp_path: Path) -> Path:
    """Write a short research prompt to a temp file and return its path."""
    f = tmp_path / "prompt.txt"
    f.write_text("What are the key principles of distributed systems?")
    return f


# ---------------------------------------------------------------------------
# Isolated DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Set BR3_DATA_DB to a fresh temp path so tests never pollute the real DB.
    Returns the Path to the new db file.
    """
    db_path = tmp_path / "test_data.db"
    monkeypatch.setenv("BR3_DATA_DB", str(db_path))

    # Reset the module-level DB connection cache in _shared so it picks up the new path
    try:
        import _shared
        _shared._db_conn = None
        _shared._db_path_used = None
        _shared._env_loaded = False
        _shared._env_cache = {}
    except ImportError:
        pass

    yield db_path

    # Cleanup: reset again after test
    try:
        import _shared
        if _shared._db_conn is not None:
            try:
                _shared._db_conn.close()
            except Exception:
                pass
        _shared._db_conn = None
        _shared._db_path_used = None
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# API key fixtures
# ---------------------------------------------------------------------------

FAKE_KEYS = {
    "PERPLEXITY_API_KEY": "pplx-test-key-0000000000000000000000000000000000000000",
    "GEMINI_API_KEY": "AIzaFakeGeminiTestKey0000000000000000",
    "XAI_API_KEY": "xai-test-key-0000000000000000000000000000000000000000000000",
}


@pytest.fixture
def mock_env_with_keys(monkeypatch: pytest.MonkeyPatch, isolated_db: Path) -> dict[str, str]:
    """
    Set fake API keys in os.environ for the duration of the test.
    Also resets the _shared env-load cache so it sees the new values.
    """
    for k, v in FAKE_KEYS.items():
        monkeypatch.setenv(k, v)

    try:
        import _shared
        _shared._env_loaded = False
        _shared._env_cache = {}
    except ImportError:
        pass

    return FAKE_KEYS


@pytest.fixture
def mock_env_no_keys(monkeypatch: pytest.MonkeyPatch, isolated_db: Path) -> None:
    """
    Remove all provider API keys from os.environ for the duration of the test.
    """
    for k in FAKE_KEYS:
        monkeypatch.delenv(k, raising=False)

    try:
        import _shared
        _shared._env_loaded = False
        _shared._env_cache = {}
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Circuit breaker reset fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_circuit_breaker(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """
    Reset the in-memory circuit breaker state before each test and prevent
    _cb_sync_from_db from loading stale state from the real data.db.

    The no-op patch on _cb_sync_from_db ensures that tests which don't use
    isolated_db still have a clean circuit state (not polluted by prior runs).
    """
    try:
        import _shared
        _shared._cb_state.clear()
        # Prevent real DB reads from re-populating the CB state during tests
        monkeypatch.setattr(_shared, "_cb_sync_from_db", lambda provider: None)
    except ImportError:
        pass
    yield
    try:
        import _shared
        _shared._cb_state.clear()
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_perplexity_response(
    content: str = "Research findings here.",
    tokens_in: int = 100,
    tokens_out: int = 200,
    citations: list[str] | None = None,
    request_id: str = "pplx-req-001",
) -> dict:
    """Build a valid Perplexity API response payload."""
    return {
        "id": request_id,
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                }
            }
        ],
        "usage": {
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
        },
        "citations": citations or ["https://example.com/source1"],
    }


def make_gemini_response(
    content: str = "Gemini research findings.",
    tokens_in: int = 120,
    tokens_out: int = 180,
    response_id: str = "gemini-resp-001",
) -> dict:
    """Build a valid Gemini API response payload."""
    return {
        "responseId": response_id,
        "candidates": [
            {
                "content": {
                    "parts": [{"text": content}],
                    "role": "model",
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": tokens_in,
            "candidatesTokenCount": tokens_out,
        },
    }


def make_grok_response(
    content: str = "Grok research findings.",
    tokens_in: int = 110,
    tokens_out: int = 190,
    request_id: str = "grok-req-001",
) -> dict:
    """Build a valid xAI Grok API response payload (OpenAI-compatible)."""
    return {
        "id": request_id,
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                }
            }
        ],
        "usage": {
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
        },
    }


def db_row_count(db_path: Path, table: str = "research_llm_calls") -> int:
    """Return row count from the given table in the test DB."""
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def db_last_row(db_path: Path, table: str = "research_llm_calls") -> dict | None:
    """Return the most recent row from the given table as a dict."""
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            f"SELECT * FROM {table} ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
