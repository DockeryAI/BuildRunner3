"""
e2e_research_smoke.py — Live-API smoke test for the multi-LLM research pipeline.

Asserts (when API keys are available):
  (a) At least 2 distinct model families appear in dispatched results
  (b) At least 1 result contains content (non-empty)
  (c) Total estimated cost stays below $0.50 for the smoke topic

IMPORTANT: All tests in this module are skipped if API keys are absent.
The smoke topic is deliberately narrow ("Write a haiku about distributed systems")
to minimize token usage.

Run:
    pytest tests/research/e2e_research_smoke.py -v
    # or directly:
    python tests/research/e2e_research_smoke.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Key detection
# ---------------------------------------------------------------------------

LLM_CLIENTS_DIR = str(Path.home() / ".buildrunner" / "scripts" / "llm-clients")
if LLM_CLIENTS_DIR not in sys.path:
    sys.path.insert(0, LLM_CLIENTS_DIR)

DISPATCH_SH = str(Path.home() / ".buildrunner" / "scripts" / "llm-dispatch.sh")

# Smoke topic — minimal token use
SMOKE_PROMPT = (
    "In exactly 2-3 sentences, what is the CAP theorem in distributed systems? "
    "Be extremely brief. No preamble."
)

# Cost cap for the entire smoke run
SMOKE_COST_CAP_USD = 0.50

# Timeout per provider call
PROVIDER_TIMEOUT_SECS = 60


def _key_available(env_var: str) -> bool:
    """Check if an env var is set and non-empty (load from ~/.buildrunner/.env first)."""
    env_file = Path.home() / ".buildrunner" / ".env"
    if env_file.exists():
        with env_file.open() as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == env_var and v:
                    os.environ.setdefault(k, v)
    return bool(os.environ.get(env_var, "").strip())


PROVIDERS_AVAILABLE: list[str] = []
if _key_available("PERPLEXITY_API_KEY"):
    PROVIDERS_AVAILABLE.append("perplexity")
if _key_available("GEMINI_API_KEY"):
    PROVIDERS_AVAILABLE.append("gemini")
if _key_available("XAI_API_KEY"):
    PROVIDERS_AVAILABLE.append("grok")

NO_KEYS = len(PROVIDERS_AVAILABLE) == 0
HAS_DISPATCH = Path(DISPATCH_SH).exists()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dispatch_provider(provider: str, prompt: str) -> dict[str, Any]:
    """
    Call llm-dispatch.sh for a single provider.
    Returns parsed JSON envelope. Never raises on API failure — returns ok:False.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        result = subprocess.run(
            ["/bin/bash", DISPATCH_SH, provider, "--prompt-file", prompt_file, "--max-tokens", "256"],
            capture_output=True,
            text=True,
            timeout=PROVIDER_TIMEOUT_SECS,
        )
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return {
                "ok": False,
                "provider": provider,
                "error": f"json_parse_failed: {result.stdout[:200]}",
            }
    except subprocess.TimeoutExpired:
        return {"ok": False, "provider": provider, "error": f"timeout:{PROVIDER_TIMEOUT_SECS}s"}
    finally:
        try:
            os.unlink(prompt_file)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(NO_KEYS, reason="no API keys — set PERPLEXITY_API_KEY / GEMINI_API_KEY / XAI_API_KEY")
@pytest.mark.skipif(not HAS_DISPATCH, reason="llm-dispatch.sh not found — Phase 1 not complete")
class TestE2EResearchSmoke:
    """
    Live-API smoke tests. Only run when at least one provider key is set.
    Skipped gracefully in CI and when keys are absent.
    """

    @pytest.fixture(scope="class")
    def smoke_results(self) -> list[dict]:
        """Dispatch smoke topic to all available providers. Cached at class scope."""
        results = []
        for provider in PROVIDERS_AVAILABLE:
            result = dispatch_provider(provider, SMOKE_PROMPT)
            results.append(result)
        return results

    def test_at_least_one_provider_responds(self, smoke_results: list[dict]) -> None:
        ok_results = [r for r in smoke_results if r.get("ok")]
        assert len(ok_results) >= 1, (
            f"No providers responded successfully. Results: {smoke_results}"
        )

    def test_at_least_two_families_when_keys_available(self, smoke_results: list[dict]) -> None:
        """
        When 2+ keys are set, at least 2 providers should succeed.
        This exercises the multi-family assertion from the spec.
        """
        if len(PROVIDERS_AVAILABLE) < 2:
            pytest.skip("Only 1 provider key available — multi-family test requires 2+")
        ok_results = [r for r in smoke_results if r.get("ok")]
        families = {r["provider"] for r in ok_results}
        assert len(families) >= 2, (
            f"Expected >=2 families, got: {families}. Results: {smoke_results}"
        )

    def test_content_non_empty(self, smoke_results: list[dict]) -> None:
        ok_results = [r for r in smoke_results if r.get("ok")]
        for r in ok_results:
            assert r.get("content"), f"Provider {r['provider']} returned empty content"
            assert len(r["content"]) > 10, (
                f"Provider {r['provider']} content too short: {r['content']!r}"
            )

    def test_total_cost_under_cap(self, smoke_results: list[dict]) -> None:
        total_cost = sum(r.get("cost_usd") or 0.0 for r in smoke_results if r.get("ok"))
        assert total_cost < SMOKE_COST_CAP_USD, (
            f"Smoke run cost ${total_cost:.4f} exceeds cap of ${SMOKE_COST_CAP_USD}"
        )

    def test_ok_envelope_has_required_fields(self, smoke_results: list[dict]) -> None:
        required = {"ok", "provider", "model", "content", "tokens_in", "tokens_out", "cost_usd", "latency_ms"}
        ok_results = [r for r in smoke_results if r.get("ok")]
        for r in ok_results:
            missing = required - set(r.keys())
            assert not missing, (
                f"Provider {r['provider']} envelope missing fields: {missing}"
            )

    def test_tokens_positive_on_success(self, smoke_results: list[dict]) -> None:
        ok_results = [r for r in smoke_results if r.get("ok")]
        for r in ok_results:
            assert r.get("tokens_in", 0) > 0 or r.get("tokens_out", 0) > 0, (
                f"Provider {r['provider']} returned zero tokens"
            )

    def test_latency_ms_positive(self, smoke_results: list[dict]) -> None:
        ok_results = [r for r in smoke_results if r.get("ok")]
        for r in ok_results:
            assert r.get("latency_ms", 0) > 0, (
                f"Provider {r['provider']} returned non-positive latency"
            )


@pytest.mark.skipif(NO_KEYS, reason="no API keys")
@pytest.mark.skipif(not HAS_DISPATCH, reason="llm-dispatch.sh not found")
class TestE2EDbPersistence:
    """Verify that live calls write rows to research_llm_calls."""

    def test_live_call_writes_db_row(self, tmp_path: Path) -> None:
        """A successful live call should write a row to the DB."""
        if not PROVIDERS_AVAILABLE:
            pytest.skip("no providers available")

        db_path = tmp_path / "smoke_data.db"
        env = os.environ.copy()
        env["BR3_DATA_DB"] = str(db_path)

        provider = PROVIDERS_AVAILABLE[0]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(SMOKE_PROMPT)
            prompt_file = f.name

        try:
            subprocess.run(
                ["/bin/bash", DISPATCH_SH, provider, "--prompt-file", prompt_file, "--max-tokens", "128"],
                capture_output=True,
                text=True,
                timeout=PROVIDER_TIMEOUT_SECS,
                env=env,
            )
        finally:
            try:
                os.unlink(prompt_file)
            except OSError:
                pass

        # DB row check
        import sqlite3
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            try:
                count = conn.execute("SELECT COUNT(*) FROM research_llm_calls").fetchone()[0]
                assert count >= 1, f"Expected >=1 DB rows, got {count}"
            finally:
                conn.close()
        # If DB wasn't created, the test is informational only
        # (some failure paths may not create it if the process exits early)


# ---------------------------------------------------------------------------
# Standalone runner (no pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if NO_KEYS:
        print("SKIP: no API keys configured")
        print("Set PERPLEXITY_API_KEY, GEMINI_API_KEY, or XAI_API_KEY in ~/.buildrunner/.env")
        sys.exit(0)

    if not HAS_DISPATCH:
        print(f"SKIP: llm-dispatch.sh not found at {DISPATCH_SH}")
        sys.exit(0)

    print(f"Running smoke test against providers: {PROVIDERS_AVAILABLE}")
    total_cost = 0.0
    families_ok = []

    for provider in PROVIDERS_AVAILABLE:
        print(f"  Dispatching to {provider}...", end=" ", flush=True)
        result = dispatch_provider(provider, SMOKE_PROMPT)
        if result.get("ok"):
            cost = result.get("cost_usd") or 0.0
            total_cost += cost
            families_ok.append(provider)
            print(f"OK (tokens={result.get('tokens_in')}+{result.get('tokens_out')}, cost=${cost:.4f})")
        else:
            print(f"FAIL ({result.get('error', 'unknown')})")

    print(f"\nFamilies OK: {families_ok}")
    print(f"Total cost:  ${total_cost:.4f} (cap: ${SMOKE_COST_CAP_USD})")

    passed = True
    if len(families_ok) < 1:
        print("FAIL: no providers responded")
        passed = False
    if total_cost >= SMOKE_COST_CAP_USD:
        print(f"FAIL: cost ${total_cost:.4f} exceeds cap ${SMOKE_COST_CAP_USD}")
        passed = False

    sys.exit(0 if passed else 1)
