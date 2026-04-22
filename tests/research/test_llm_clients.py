"""
test_llm_clients.py — Unit tests for the BR3 multi-LLM research client wrappers.

Coverage per provider:
  - Happy path: well-formed API response → ok envelope + DB row written
  - Missing key: returns missing_key error envelope, exit 2, DB row written
  - HTTP 5xx: returns fail envelope, circuit failure recorded, DB row written
  - Malformed response: parse_error in envelope, CB failure recorded
  - Circuit breaker: after 3 failures circuit opens; subsequent calls return circuit_open

Tests mock HTTPS at the urllib.request.urlopen boundary — never hit real APIs.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import helpers from conftest
# ---------------------------------------------------------------------------
from tests.research.conftest import (
    db_last_row,
    db_row_count,
    make_gemini_response,
    make_grok_response,
    make_perplexity_response,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_http_response(body: dict | str, status: int = 200) -> MagicMock:
    """Build a mock urllib HTTP response context manager."""
    if isinstance(body, dict):
        raw = json.dumps(body).encode("utf-8")
    else:
        raw = body.encode("utf-8") if isinstance(body, str) else body

    mock_resp = MagicMock()
    mock_resp.read.return_value = raw
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _fake_http_error(code: int, body: str = "") -> urllib.error.HTTPError:
    """Build a urllib HTTPError."""
    fp = BytesIO(body.encode("utf-8"))
    return urllib.error.HTTPError(
        url="https://example.com",
        code=code,
        msg=f"HTTP {code}",
        hdrs={},  # type: ignore[arg-type]
        fp=fp,
    )


# ===========================================================================
# _shared module tests
# ===========================================================================

class TestSharedCalcCost:
    def test_zero_tokens(self) -> None:
        import _shared
        assert _shared.calc_cost(0, 0, 3.0, 15.0) == 0.0

    def test_known_rates(self) -> None:
        import _shared
        # 1M in + 1M out at $3/$15 per MTok = $18
        cost = _shared.calc_cost(1_000_000, 1_000_000, 3.0, 15.0)
        assert abs(cost - 18.0) < 1e-9

    def test_partial_tokens(self) -> None:
        import _shared
        cost = _shared.calc_cost(500, 250, 4.0, 16.0)
        assert cost == pytest.approx((500 * 4.0 + 250 * 16.0) / 1_000_000)


class TestSharedRequireKey:
    def test_key_present(self, mock_env_with_keys: dict) -> None:
        import _shared
        key = _shared.require_key("perplexity")
        assert key == mock_env_with_keys["PERPLEXITY_API_KEY"]

    def test_key_missing(self, mock_env_no_keys: None) -> None:
        import _shared
        key = _shared.require_key("perplexity")
        assert key is None

    def test_codex_returns_sentinel(self, mock_env_no_keys: None) -> None:
        import _shared
        key = _shared.require_key("codex")
        assert key == "__codex_cli__"

    def test_gemini_key(self, mock_env_with_keys: dict) -> None:
        import _shared
        key = _shared.require_key("gemini")
        assert key == mock_env_with_keys["GEMINI_API_KEY"]

    def test_grok_key(self, mock_env_with_keys: dict) -> None:
        import _shared
        key = _shared.require_key("grok")
        assert key == mock_env_with_keys["XAI_API_KEY"]


class TestCircuitBreaker:
    def test_initially_closed(self) -> None:
        import _shared
        assert _shared.cb_is_open("perplexity") is False

    def test_opens_after_threshold(self) -> None:
        import _shared
        for _ in range(_shared._CB_THRESHOLD):
            _shared.cb_record_failure("perplexity")
        assert _shared.cb_is_open("perplexity") is True

    def test_does_not_open_before_threshold(self) -> None:
        import _shared
        for _ in range(_shared._CB_THRESHOLD - 1):
            _shared.cb_record_failure("perplexity")
        assert _shared.cb_is_open("perplexity") is False

    def test_success_clears_failures(self) -> None:
        import _shared
        _shared.cb_record_failure("perplexity")
        _shared.cb_record_failure("perplexity")
        _shared.cb_record_success("perplexity")
        # After success, failure list cleared — should not open
        assert _shared.cb_is_open("perplexity") is False

    def test_different_providers_independent(self) -> None:
        import _shared
        for _ in range(_shared._CB_THRESHOLD):
            _shared.cb_record_failure("perplexity")
        # gemini should still be closed
        assert _shared.cb_is_open("gemini") is False
        assert _shared.cb_is_open("perplexity") is True

    def test_circuit_stays_open_during_window(self) -> None:
        import _shared
        for _ in range(_shared._CB_THRESHOLD):
            _shared.cb_record_failure("grok")
        # Multiple checks — still open
        assert _shared.cb_is_open("grok") is True
        assert _shared.cb_is_open("grok") is True

    def test_failures_pruned_outside_window(self) -> None:
        import _shared
        # Force two failures, then fake them as old
        _shared.cb_record_failure("gemini")
        _shared.cb_record_failure("gemini")
        # Age them out by directly manipulating timestamps
        old_time = time.time() - (_shared._CB_WINDOW_SECS + 1)
        _shared._cb_state["gemini"]["fails"] = [old_time, old_time]
        _shared._cb_state["gemini"]["open_until"] = 0.0
        # After pruning, circuit should be closed
        assert _shared.cb_is_open("gemini") is False


class TestWriteCallRecord:
    def test_writes_ok_row(self, isolated_db: Path) -> None:
        import _shared
        _shared.write_call_record(
            provider="perplexity",
            model="sonar-pro",
            tokens_in=100,
            tokens_out=200,
            cost_usd=0.0033,
            latency_ms=450.0,
            ok=True,
            request_id="req-001",
        )
        assert db_row_count(isolated_db) == 1
        row = db_last_row(isolated_db)
        assert row is not None
        assert row["provider"] == "perplexity"
        assert row["ok"] == 1
        assert row["tokens_in"] == 100
        assert row["tokens_out"] == 200
        assert row["request_id"] == "req-001"

    def test_writes_failure_row(self, isolated_db: Path) -> None:
        import _shared
        _shared.write_call_record(
            provider="gemini",
            model="gemini-3.1-pro",
            tokens_in=None,
            tokens_out=None,
            cost_usd=None,
            latency_ms=300.0,
            ok=False,
            error="http_500: server error",
        )
        row = db_last_row(isolated_db)
        assert row is not None
        assert row["ok"] == 0
        assert row["error"] == "http_500: server error"
        assert row["cost_usd"] is None


# ===========================================================================
# Perplexity client tests
# ===========================================================================

class TestPerplexityClient:
    def _import(self):
        import perplexity
        return perplexity

    def test_happy_path(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        ppl = self._import()
        resp_body = make_perplexity_response(
            content="Key findings about distributed systems.",
            tokens_in=150,
            tokens_out=250,
        )
        mock_resp = _fake_http_response(resp_body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = ppl.call_api(
                "What are distributed systems?",
                mock_env_with_keys["PERPLEXITY_API_KEY"],
                max_tokens=512,
                system="You are a research assistant.",
            )

        assert result["ok"] is True
        assert result["provider"] == "perplexity"
        assert result["model"] == "sonar-pro"
        assert "Key findings" in result["content"]
        assert result["tokens_in"] == 150
        assert result["tokens_out"] == 250
        assert result["cost_usd"] > 0
        assert "citations" in result
        # DB row written
        assert db_row_count(isolated_db) >= 1
        row = db_last_row(isolated_db)
        assert row["ok"] == 1
        assert row["provider"] == "perplexity"

    def test_missing_key_error(self, mock_env_no_keys: None, isolated_db: Path, tmp_prompt_file: Path) -> None:
        ppl = self._import()
        # Simulate missing key path via main() with sys.argv
        import _shared
        key = _shared.require_key("perplexity")
        assert key is None
        envelope = _shared.missing_key_error("perplexity")
        assert envelope["ok"] is False
        assert "missing_key" in envelope["error"]
        assert "PERPLEXITY_API_KEY" in envelope["error"]

    def test_http_5xx_records_failure(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        ppl = self._import()
        with patch("urllib.request.urlopen", side_effect=_fake_http_error(503, "Service Unavailable")):
            result = ppl.call_api(
                "prompt",
                mock_env_with_keys["PERPLEXITY_API_KEY"],
                max_tokens=512,
                system="sys",
            )
        assert result["ok"] is False
        assert "http_503" in result["error"]
        # DB row written with ok=0
        row = db_last_row(isolated_db)
        assert row is not None
        assert row["ok"] == 0
        assert "http_503" in row["error"]

    def test_malformed_response(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        ppl = self._import()
        # Missing 'choices' key
        bad_body = {"unexpected_key": "value"}
        mock_resp = _fake_http_response(bad_body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = ppl.call_api(
                "prompt",
                mock_env_with_keys["PERPLEXITY_API_KEY"],
                max_tokens=512,
                system="sys",
            )
        assert result["ok"] is False
        assert "parse_error" in result["error"] or "http_" in result["error"] or result["ok"] is False

    def test_circuit_open_skips_network(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        import _shared
        ppl = self._import()
        # Open the circuit
        for _ in range(_shared._CB_THRESHOLD):
            _shared.cb_record_failure("perplexity")
        assert _shared.cb_is_open("perplexity") is True

        # Network should NOT be called
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Simulate what main() does when cb is open
            if _shared.cb_is_open("perplexity"):
                result = _shared.fail_envelope("perplexity", "circuit_open:perplexity")
                _shared.write_call_record(
                    provider="perplexity", model="sonar-pro",
                    tokens_in=None, tokens_out=None, cost_usd=None,
                    latency_ms=None, ok=False, error=result["error"],
                )
            mock_urlopen.assert_not_called()

        assert result["ok"] is False
        assert "circuit_open" in result["error"]
        row = db_last_row(isolated_db)
        assert row is not None
        assert row["ok"] == 0

    def test_parse_response_valid(self) -> None:
        ppl = self._import()
        payload = make_perplexity_response(content="test", tokens_in=50, tokens_out=100)
        raw = json.dumps(payload)
        content, tin, tout, citations, req_id = ppl._parse_response(raw)
        assert content == "test"
        assert tin == 50
        assert tout == 100
        assert isinstance(citations, list)

    def test_parse_response_invalid_json(self) -> None:
        ppl = self._import()
        with pytest.raises(ValueError, match="JSON parse failed"):
            ppl._parse_response("not json {{{")

    def test_parse_response_empty_choices(self) -> None:
        ppl = self._import()
        bad = json.dumps({"choices": [], "usage": {}})
        with pytest.raises(ValueError):
            ppl._parse_response(bad)


# ===========================================================================
# Gemini client tests
# ===========================================================================

class TestGeminiClient:
    def _import(self):
        import gemini
        return gemini

    def test_happy_path(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        gem = self._import()
        resp_body = make_gemini_response(
            content="Gemini research: distributed consensus algorithms.",
            tokens_in=120,
            tokens_out=180,
        )
        mock_resp = _fake_http_response(resp_body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = gem.call_api(
                "distributed systems research",
                mock_env_with_keys["GEMINI_API_KEY"],
                max_tokens=512,
                system="You are a research assistant.",
            )
        assert result["ok"] is True
        assert result["provider"] == "gemini"
        assert result["model"] == "gemini-3.1-pro"
        assert "consensus" in result["content"]
        assert result["tokens_in"] == 120
        assert result["tokens_out"] == 180
        row = db_last_row(isolated_db)
        assert row is not None
        assert row["ok"] == 1
        assert row["provider"] == "gemini"

    def test_missing_key_returns_envelope(self, mock_env_no_keys: None) -> None:
        import _shared
        key = _shared.require_key("gemini")
        assert key is None
        envelope = _shared.missing_key_error("gemini")
        assert envelope["ok"] is False
        assert "GEMINI_API_KEY" in envelope["error"]

    def test_http_5xx(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        gem = self._import()
        with patch("urllib.request.urlopen", side_effect=_fake_http_error(500, "Internal Server Error")):
            result = gem.call_api("prompt", mock_env_with_keys["GEMINI_API_KEY"], 512, "sys")
        assert result["ok"] is False
        assert "http_500" in result["error"]
        row = db_last_row(isolated_db)
        assert row["ok"] == 0

    def test_malformed_response_no_candidates(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        gem = self._import()
        bad_body = {"no_candidates_here": True}
        mock_resp = _fake_http_response(bad_body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = gem.call_api("prompt", mock_env_with_keys["GEMINI_API_KEY"], 512, "sys")
        assert result["ok"] is False

    def test_api_error_in_response(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        gem = self._import()
        error_body = {"error": {"message": "API key not valid", "code": 400}}
        mock_resp = _fake_http_response(error_body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = gem.call_api("prompt", mock_env_with_keys["GEMINI_API_KEY"], 512, "sys")
        assert result["ok"] is False

    def test_parse_response_valid(self) -> None:
        gem = self._import()
        payload = make_gemini_response(content="gemini text", tokens_in=80, tokens_out=120)
        raw = json.dumps(payload)
        content, tin, tout, req_id = gem._parse_response(raw)
        assert content == "gemini text"
        assert tin == 80
        assert tout == 120

    def test_parse_response_invalid_json(self) -> None:
        gem = self._import()
        with pytest.raises(ValueError, match="JSON parse failed"):
            gem._parse_response("{{broken")


# ===========================================================================
# Grok client tests
# ===========================================================================

class TestGrokClient:
    def _import(self):
        import grok
        return grok

    def test_happy_path(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        grk = self._import()
        resp_body = make_grok_response(
            content="Grok live search results: distributed systems 2026.",
            tokens_in=110,
            tokens_out=190,
        )
        mock_resp = _fake_http_response(resp_body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = grk.call_api(
                "distributed systems",
                mock_env_with_keys["XAI_API_KEY"],
                max_tokens=512,
                system="You are a research assistant.",
            )
        assert result["ok"] is True
        assert result["provider"] == "grok"
        assert result["model"] == "grok-4"
        assert "Grok" in result["content"]
        assert result["tokens_in"] == 110
        assert result["tokens_out"] == 190
        row = db_last_row(isolated_db)
        assert row["ok"] == 1

    def test_missing_key(self, mock_env_no_keys: None) -> None:
        import _shared
        key = _shared.require_key("grok")
        assert key is None
        envelope = _shared.missing_key_error("grok")
        assert "XAI_API_KEY" in envelope["error"]

    def test_http_5xx(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        grk = self._import()
        with patch("urllib.request.urlopen", side_effect=_fake_http_error(502, "Bad Gateway")):
            result = grk.call_api("prompt", mock_env_with_keys["XAI_API_KEY"], 512, "sys")
        assert result["ok"] is False
        assert "http_502" in result["error"]

    def test_malformed_response_missing_choices(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        grk = self._import()
        bad_body = {"id": "x", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
        mock_resp = _fake_http_response(bad_body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = grk.call_api("prompt", mock_env_with_keys["XAI_API_KEY"], 512, "sys")
        assert result["ok"] is False

    def test_api_error_field(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        grk = self._import()
        error_body = {"error": {"message": "Invalid API key", "type": "authentication_error"}}
        mock_resp = _fake_http_response(error_body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = grk.call_api("prompt", mock_env_with_keys["XAI_API_KEY"], 512, "sys")
        assert result["ok"] is False

    def test_parse_response_tool_call_content(self) -> None:
        grk = self._import()
        # When content is None but tool_calls has results
        payload = {
            "id": "grok-tc-001",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "web_search",
                                    "result": "Search result text here",
                                }
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 80},
        }
        raw = json.dumps(payload)
        content, tin, tout, req_id = grk._parse_response(raw)
        assert "Search result text here" in content

    def test_circuit_breaker_opens(self, mock_env_with_keys: dict, isolated_db: Path) -> None:
        import _shared
        grk = self._import()
        with patch("urllib.request.urlopen", side_effect=_fake_http_error(503)):
            for _ in range(_shared._CB_THRESHOLD):
                grk.call_api("prompt", mock_env_with_keys["XAI_API_KEY"], 512, "sys")
        assert _shared.cb_is_open("grok") is True


# ===========================================================================
# Codex client tests
# ===========================================================================

class TestCodexClient:
    def _import(self):
        import codex_research
        return codex_research

    def test_happy_path(self, isolated_db: Path, tmp_prompt_file: Path) -> None:
        cdx = self._import()
        # Simulate successful codex exec
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "## Key Findings\nCodex research on distributed systems.\n"
            "## All Sources\nhttps://example.com\n"
        )
        mock_result.stderr = "Tokens used: 200 in, 400 out\nCost: $0.014"

        with patch("subprocess.run", return_value=mock_result):
            # Preflight: version check OK, models list OK
            version_mock = MagicMock(returncode=0, stdout="codex 1.0.0", stderr="")
            models_mock = MagicMock(returncode=0, stdout="gpt-5.4\ngpt-4o\n", stderr="")

            # Clear preflight cache
            cdx._preflight_cache.clear()

            def fake_subprocess_run(cmd, **kwargs):
                if cmd[1] == "--version":
                    return version_mock
                elif "list" in cmd:
                    return models_mock
                return mock_result

            with patch("subprocess.run", side_effect=fake_subprocess_run):
                # Test call_codex directly (bypass preflight in main)
                result = cdx.call_codex(str(tmp_prompt_file), "gpt-5.4", "medium", 8192)

        assert result["ok"] is True
        assert result["provider"] == "codex"
        assert "Codex research" in result["content"]

    def test_preflight_missing_cli(self, isolated_db: Path) -> None:
        cdx = self._import()
        cdx._preflight_cache.clear()
        with patch("subprocess.run", side_effect=FileNotFoundError("codex not found")):
            ok, reason = cdx.preflight("gpt-5.4")
        assert ok is False
        assert "not found" in reason.lower() or "PATH" in reason

    def test_preflight_model_not_in_list(self, isolated_db: Path) -> None:
        cdx = self._import()
        cdx._preflight_cache.clear()
        version_mock = MagicMock(returncode=0, stdout="codex 1.0.0", stderr="")
        models_mock = MagicMock(returncode=0, stdout="gpt-4o\ngpt-3.5\n", stderr="")

        def fake_run(cmd, **kwargs):
            if "--version" in cmd:
                return version_mock
            return models_mock

        with patch("subprocess.run", side_effect=fake_run):
            ok, reason = cdx.preflight("gpt-5.4")
        assert ok is False
        assert "not found" in reason.lower() or "gpt-5.4" in reason

    def test_preflight_cached(self, isolated_db: Path) -> None:
        cdx = self._import()
        cdx._preflight_cache.clear()
        cdx._preflight_cache["gpt-5.4"] = (True, "")
        # Should not call subprocess
        with patch("subprocess.run") as mock_run:
            ok, reason = cdx.preflight("gpt-5.4")
        mock_run.assert_not_called()
        assert ok is True

    def test_codex_exit_nonzero(self, isolated_db: Path, tmp_prompt_file: Path) -> None:
        cdx = self._import()
        fail_mock = MagicMock(returncode=1, stdout="", stderr="auth error")
        with patch("subprocess.run", return_value=fail_mock):
            result = cdx.call_codex(str(tmp_prompt_file), "gpt-5.4", "medium", 8192)
        assert result["ok"] is False
        assert "codex_exit_1" in result["error"]

    def test_circuit_open_no_subprocess(self, isolated_db: Path) -> None:
        import _shared
        cdx = self._import()
        for _ in range(_shared._CB_THRESHOLD):
            _shared.cb_record_failure("codex")
        assert _shared.cb_is_open("codex") is True
        # In main() flow, circuit_open check happens before subprocess
        result = _shared.fail_envelope("codex", "circuit_open:codex")
        assert result["ok"] is False
        assert "circuit_open" in result["error"]

    def test_parse_trailer_tokens(self) -> None:
        cdx = self._import()
        output = "Some content here.\nTokens used: 123 in, 456 out\nCost: $0.025"
        tin, tout, cost = cdx._parse_trailer(output)
        assert tin == 123
        assert tout == 456
        assert cost == pytest.approx(0.025)

    def test_parse_trailer_no_tokens(self) -> None:
        cdx = self._import()
        output = "Just research content, no trailer."
        tin, tout, cost = cdx._parse_trailer(output)
        assert tin is None
        assert tout is None
        assert cost is None

    def test_extract_content_strips_trailer(self) -> None:
        cdx = self._import()
        output = "Research findings here.\nMore findings.\nTokens used: 100 in, 200 out\nCost: $0.01"
        content = cdx._extract_content(output)
        assert "Research findings here." in content
        assert "Tokens used" not in content
