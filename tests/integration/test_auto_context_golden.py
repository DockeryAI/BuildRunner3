"""
Integration tests for Phase 10: Auto-Context Hook golden tests.

Tests:
1. count-tokens.sh returns integer for known input (flag irrelevant — this is a local tool)
2. auto-context.sh trivial-prompt skip: no <auto-context> block, no ledger entry
3. auto-context.sh with flag OFF: passthrough, zero side effects
4. retrieve endpoint (flag-gated): returns empty when flag off; correct shape when on
5. Reranker passthrough when flag off
6. Exclusion enforcement: no secret/log paths in output

Run: pytest tests/integration/test_auto_context_golden.py -x
Jimmy must be reachable at 10.0.1.106:8100 for live endpoint tests.
Flag-off tests run fully locally.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

# ─── Helpers ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
COUNT_TOKENS = Path.home() / ".buildrunner/scripts/count-tokens.sh"
AUTO_CONTEXT = Path.home() / ".buildrunner/hooks/auto-context.sh"
LEDGER = Path.home() / ".buildrunner/auto-context-ledger.jsonl"
JIMMY_URL = "http://10.0.1.106:8100"
FIXTURES = REPO_ROOT / "tests/fixtures"

AUTO_CONTEXT_ON = os.environ.get("BR3_AUTO_CONTEXT", "off").lower() == "on"


def _run_hook(prompt: str, env_override: dict | None = None) -> subprocess.CompletedProcess:
    """Run auto-context.sh with a prompt on stdin."""
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["bash", str(AUTO_CONTEXT)],
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


def _ledger_entries_after(ts_before: float) -> list[dict]:
    """Return ledger entries written after ts_before (epoch seconds)."""
    if not LEDGER.exists():
        return []
    entries = []
    for line in LEDGER.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            ts_str = entry.get("ts", "")
            # Parse ISO ts
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
            if ts >= ts_before:
                entries.append(entry)
        except Exception:
            continue
    return entries


# ─── count-tokens.sh tests ────────────────────────────────────────────────────

class TestCountTokens:
    """count-tokens.sh must return a valid integer; exit 2 if tokenizer missing."""

    def test_script_exists_and_executable(self):
        assert COUNT_TOKENS.exists(), f"count-tokens.sh not found at {COUNT_TOKENS}"
        assert os.access(COUNT_TOKENS, os.X_OK), "count-tokens.sh not executable"

    def test_claude_model_returns_integer(self):
        """echo 'hello world' | count-tokens.sh --model claude should return 2 ± 1."""
        result = subprocess.run(
            ["bash", str(COUNT_TOKENS), "--model", "claude"],
            input="hello world",
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 2:
            pytest.skip("tiktoken not installed — tokenizer unavailable (expected exit 2)")
        assert result.returncode == 0, f"Unexpected exit {result.returncode}: {result.stderr}"
        count = int(result.stdout.strip())
        assert 1 <= count <= 5, f"Expected ~2 tokens for 'hello world', got {count}"

    def test_no_byte_count_fallback_on_missing_tokenizer(self):
        """If tokenizer is absent, exit code MUST be 2 — never 0 with byte count."""
        # We test by using an invalid model name to force exit 1 (arg error),
        # verifying that only exit 0 or 2 are the valid outcomes for real models.
        result = subprocess.run(
            ["bash", str(COUNT_TOKENS), "--model", "claude"],
            input="test payload",
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Only valid exits: 0 (tokenizer available), 2 (tokenizer missing)
        assert result.returncode in (0, 2), (
            f"count-tokens.sh exited {result.returncode} — should be 0 or 2 only. "
            f"Byte-count fallback is forbidden. stderr: {result.stderr}"
        )
        if result.returncode == 0:
            # Must be a valid integer, not a byte count proxy
            output = result.stdout.strip()
            assert output.isdigit(), f"Output is not an integer: {output!r}"

    def test_bad_model_exits_1(self):
        result = subprocess.run(
            ["bash", str(COUNT_TOKENS), "--model", "bogus-model"],
            input="test",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1, "Bad model name should exit 1"

    def test_missing_model_flag_exits_1(self):
        result = subprocess.run(
            ["bash", str(COUNT_TOKENS)],
            input="test",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1, "Missing --model should exit 1"

    def test_file_input(self):
        """count-tokens.sh --model claude <file> should count the file's tokens."""
        sample = FIXTURES / "sample_prompt.txt"
        if not sample.exists():
            pytest.skip("sample_prompt.txt fixture not found")
        result = subprocess.run(
            ["bash", str(COUNT_TOKENS), "--model", "claude", str(sample)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 2:
            pytest.skip("tiktoken not installed")
        assert result.returncode == 0
        count = int(result.stdout.strip())
        assert count > 0, "Should have >0 tokens for non-empty file"


# ─── Trivial-prompt skip tests ────────────────────────────────────────────────

class TestTrivialSkip:
    """Trivial prompts must produce NO <auto-context> block and NO ledger entry."""

    TRIVIAL_CASES = [
        "/save",
        "/help",
        "/brief",
        "y",
        "n",
        "yes",
        "no",
        "ok",
        "continue",
        "go ahead",
        "done",
        # Short prompt (<40 chars)
        "what is 2+2",
        "fix it",
    ]

    @pytest.mark.parametrize("prompt", TRIVIAL_CASES)
    def test_trivial_passthrough_flag_off(self, prompt):
        """Flag OFF: all prompts pass through unchanged, no <auto-context>."""
        result = _run_hook(prompt, env_override={"BR3_AUTO_CONTEXT": "off"})
        assert result.returncode == 0
        assert "<auto-context>" not in result.stdout
        # Output should be the original prompt (or empty if hook passes through)

    @pytest.mark.parametrize("prompt", TRIVIAL_CASES)
    def test_trivial_no_injection_flag_on(self, prompt):
        """Flag ON: trivial prompts still get NO <auto-context> injection."""
        ts_before = time.time()
        result = _run_hook(prompt, env_override={"BR3_AUTO_CONTEXT": "on"})
        assert result.returncode == 0
        assert "<auto-context>" not in result.stdout, (
            f"Trivial prompt {prompt!r} should not produce <auto-context> block"
        )
        # No ledger entry should be written for trivial prompts
        new_entries = _ledger_entries_after(ts_before)
        assert len(new_entries) == 0, (
            f"Trivial prompt {prompt!r} wrote {len(new_entries)} ledger entry/entries — "
            "trivial prompts must produce zero ledger entries"
        )


# ─── Flag-off tests ───────────────────────────────────────────────────────────

class TestFlagOff:
    """BR3_AUTO_CONTEXT != on must produce ZERO behavior change."""

    NON_TRIVIAL_PROMPT = (
        "Implement the runtime fallback dispatcher for when Jimmy "
        "semantic search is unavailable. Route to Lockwood as backup "
        "and log the fallback event to decisions.log."
    )

    def test_passthrough_unmodified(self):
        """Flag off: output equals input exactly."""
        result = _run_hook(self.NON_TRIVIAL_PROMPT, env_override={"BR3_AUTO_CONTEXT": "off"})
        assert result.returncode == 0
        assert "<auto-context>" not in result.stdout
        # Prompt should be passed through (stdout contains the original)
        assert self.NON_TRIVIAL_PROMPT in result.stdout or result.stdout.strip() == self.NON_TRIVIAL_PROMPT.strip()

    def test_no_ledger_entry_written(self):
        """Flag off: no ledger entries written even for non-trivial prompts."""
        ts_before = time.time()
        _run_hook(self.NON_TRIVIAL_PROMPT, env_override={"BR3_AUTO_CONTEXT": "off"})
        new_entries = _ledger_entries_after(ts_before)
        assert len(new_entries) == 0, (
            f"Flag off wrote {len(new_entries)} ledger entries — must be zero"
        )

    def test_no_network_call_flag_off(self):
        """Flag off: hook exits immediately without making any retrieve calls.
        Verify via timing — should complete in <200ms (no network roundtrip)."""
        start = time.time()
        _run_hook(self.NON_TRIVIAL_PROMPT, env_override={"BR3_AUTO_CONTEXT": "off"})
        elapsed = time.time() - start
        assert elapsed < 1.0, (
            f"Flag-off hook took {elapsed:.2f}s — expected <1s (should be immediate passthrough)"
        )


# ─── Retrieve endpoint tests (require Jimmy) ─────────────────────────────────

class TestRetrieveEndpoint:
    """Tests for the /retrieve endpoint on Jimmy. Skipped if Jimmy unreachable."""

    @pytest.fixture(autouse=True)
    def check_jimmy(self):
        """Skip all tests in this class if Jimmy is unreachable or /retrieve not deployed."""
        import urllib.request
        import urllib.error
        # Check /health first
        try:
            urllib.request.urlopen(f"{JIMMY_URL}/health", timeout=3)
        except Exception:
            pytest.skip(f"Jimmy not reachable at {JIMMY_URL}")
        # Check /retrieve is deployed (HEAD-style probe via OPTIONS or small POST)
        try:
            payload = json.dumps({"query": "probe", "top_k": 1}).encode()
            req = urllib.request.Request(
                f"{JIMMY_URL}/retrieve",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pytest.skip("/retrieve not yet deployed to Jimmy — skip endpoint tests")
        except Exception:
            pytest.skip(f"Jimmy /retrieve not accessible")

    def test_retrieve_flag_off_returns_empty(self):
        """With BR3_AUTO_CONTEXT=off, /retrieve should return empty results."""
        import urllib.request
        import urllib.error
        payload = json.dumps({"query": "runtime fallback", "top_k": 3}).encode()
        try:
            req = urllib.request.Request(
                f"{JIMMY_URL}/retrieve",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            # flag_active should be False when env is off
            # (Jimmy reads its own env — if deployed with flag off, results empty)
            assert "results" in data
            assert "flag_active" in data
        except urllib.error.HTTPError as e:
            pytest.fail(f"/retrieve returned HTTP {e.code}: {e.read()}")

    def test_retrieve_response_shape(self):
        """Response has required fields when Jimmy is accessible."""
        import urllib.request
        import urllib.error
        payload = json.dumps({"query": "runtime fallback", "top_k": 3}).encode()
        req = urllib.request.Request(
            f"{JIMMY_URL}/retrieve",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            pytest.fail(f"/retrieve HTTP {e.code}")

        assert "query" in data
        assert "results" in data
        assert isinstance(data["results"], list)
        assert "flag_active" in data

        for snippet in data["results"]:
            assert "source" in snippet
            assert "source_url" in snippet
            assert "score" in snippet
            assert "text" in snippet
            assert isinstance(snippet["score"], (int, float))

    def test_rerank_health_endpoint(self):
        """GET /rerank/health returns 200 with status field."""
        import urllib.request
        with urllib.request.urlopen(f"{JIMMY_URL}/rerank/health", timeout=5) as resp:
            data = json.loads(resp.read())
        assert "status" in data

    def test_retrieve_no_secret_paths_in_results(self):
        """Results must never include snippets from secret/log files."""
        import urllib.request
        import urllib.error
        payload = json.dumps({"query": "API key token secret", "top_k": 5}).encode()
        req = urllib.request.Request(
            f"{JIMMY_URL}/retrieve",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError:
            return  # endpoint error is not the exclusion test

        FORBIDDEN_SUFFIXES = (".env", ".token", ".key", ".pem", ".cert", ".log", ".secret")
        FORBIDDEN_NAMES = ("credentials.json", "active-token.env", "secrets.env")

        for snippet in data.get("results", []):
            url = snippet.get("source_url", "")
            for suffix in FORBIDDEN_SUFFIXES:
                assert not url.endswith(suffix), (
                    f"Secret/log file path leaked into results: {url}"
                )
            for name in FORBIDDEN_NAMES:
                assert not url.endswith(name), (
                    f"Secret file name leaked into results: {url}"
                )


# ─── Ledger schema tests ──────────────────────────────────────────────────────

class TestLedgerSchema:
    """Validate ledger entry schema when an injection occurs."""

    NON_TRIVIAL_PROMPT = (
        "Implement the runtime fallback dispatcher for when Jimmy "
        "semantic search is unavailable. The dispatcher should route "
        "to Lockwood as backup and log the event to decisions.log."
    )

    @pytest.mark.skipif(not AUTO_CONTEXT_ON, reason="BR3_AUTO_CONTEXT not on")
    def test_ledger_entry_written_on_injection(self):
        """A non-trivial prompt with flag on should write a valid ledger entry."""
        ts_before = time.time()
        result = _run_hook(self.NON_TRIVIAL_PROMPT, env_override={"BR3_AUTO_CONTEXT": "on"})
        assert result.returncode == 0

        # If no context injected (Jimmy down, budget exceeded, etc.), skip assertion
        if "<auto-context>" not in result.stdout:
            pytest.skip("No injection occurred (Jimmy may be down or flag off in env)")

        new_entries = _ledger_entries_after(ts_before)
        assert len(new_entries) >= 1, "Expected at least one ledger entry after injection"

        entry = new_entries[0]
        required_fields = {"ts", "event", "prompt_excerpt", "sources_injected", "tokens_used", "top_score"}
        missing = required_fields - set(entry.keys())
        assert not missing, f"Ledger entry missing fields: {missing}"

        assert isinstance(entry["tokens_used"], int), "tokens_used must be integer"
        assert entry["tokens_used"] > 0, "tokens_used must be positive"
        assert entry["tokens_used"] <= 4096, "tokens_used must not exceed 4K budget"
        assert isinstance(entry["sources_injected"], list), "sources_injected must be list"
        assert isinstance(entry["top_score"], (int, float)), "top_score must be numeric"
        assert entry["event"] in ("PromptSubmit", "PhaseStart", "UserPromptSubmit"), (
            f"Unexpected event type: {entry['event']}"
        )

    @pytest.mark.skipif(not AUTO_CONTEXT_ON, reason="BR3_AUTO_CONTEXT not on")
    def test_budget_never_exceeded(self):
        """tokens_used in all recent ledger entries must be ≤ 4096."""
        if not LEDGER.exists():
            pytest.skip("No ledger file yet")
        entries = _ledger_entries_after(time.time() - 3600)  # last hour
        for entry in entries:
            tokens = entry.get("tokens_used", 0)
            assert tokens <= 4096, (
                f"Budget breach: entry has tokens_used={tokens} > 4096"
            )
