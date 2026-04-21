"""
tests/cluster/test_cache_breakpoints_flag.py

Phase 4: BR3_CACHE_BREAKPOINTS flag enforcement tests.

Verifies:
  - flag off  → 0 breakpoints (no cache_control on any block)
  - flag on   → ≤3 breakpoints (exactly the 3-breakpoint contract from cluster-max Phase 8)
  - flag read occurs once at module import (cached in _CACHE_BREAKPOINTS_ENABLED)
  - get_breakpoint_count() returns 0 (off) or 3 (on)
  - cached_block_indices() returns [] (off) or [0, 1] (on)
  - has_cache_control() correctly identifies marked blocks
"""

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load the REAL cache_policy module, bypassing any MagicMock that an earlier
# test file may have injected into sys.modules["core.runtime.cache_policy"].
# We do this by temporarily removing the mock, loading the real module via
# importlib.util, and restoring it in sys.modules under its canonical key.
_CACHE_POLICY_KEY = "core.runtime.cache_policy"

def _ensure_real_cache_policy():
    """Return the real cache_policy module, evicting any mock from sys.modules."""
    existing = sys.modules.get(_CACHE_POLICY_KEY)
    # If a MagicMock is registered, evict it so the real loader can run.
    if existing is not None and not hasattr(existing, "__file__"):
        del sys.modules[_CACHE_POLICY_KEY]
    # Load (or re-use) the real module.
    spec = importlib.util.find_spec(_CACHE_POLICY_KEY)
    if spec is None:
        raise ImportError(f"Cannot find {_CACHE_POLICY_KEY}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_CACHE_POLICY_KEY] = mod
    spec.loader.exec_module(mod)
    return mod

_cache_policy_module = _ensure_real_cache_policy()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_cache_policy(flag_value: str):
    """Re-exec cache_policy with a specific BR3_CACHE_BREAKPOINTS value.

    Uses spec.loader.exec_module() directly so that:
    - The env var is set before the module body runs (flag read at import time).
    - We never call importlib.reload() on a MagicMock that another test file
      may have registered under sys.modules["core.runtime.cache_policy"].
    """
    os.environ["BR3_CACHE_BREAKPOINTS"] = flag_value
    spec = importlib.util.find_spec(_CACHE_POLICY_KEY)
    spec.loader.exec_module(_cache_policy_module)
    return _cache_policy_module


def _count_breakpoints(blocks: list[dict[str, Any]]) -> int:
    """Count how many blocks have cache_control markers."""
    return sum(1 for b in blocks if "cache_control" in b)


# ---------------------------------------------------------------------------
# Tests: flag off → 0 breakpoints
# ---------------------------------------------------------------------------

class TestCacheBreakpointsFlagOff:
    """When BR3_CACHE_BREAKPOINTS=off, zero cache_control markers are emitted."""

    def test_flag_off_zero_breakpoints(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        blocks = cp.build_cached_prompt(
            system_text="system prompt",
            skill_context="skill context",
            task_payload="task payload",
        )

        assert _count_breakpoints(blocks) == 0, (
            f"Expected 0 breakpoints when flag off, got {_count_breakpoints(blocks)}"
        )

    def test_flag_off_three_blocks_returned(self, monkeypatch):
        """build_cached_prompt still returns 3 blocks even when flag is off."""
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        blocks = cp.build_cached_prompt("sys", "ctx", "payload")

        assert len(blocks) == 3

    def test_flag_off_all_blocks_are_text_type(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        blocks = cp.build_cached_prompt("sys", "ctx", "payload")

        for block in blocks:
            assert block["type"] == "text"

    def test_flag_off_no_block_has_cache_control(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        blocks = cp.build_cached_prompt("sys", "ctx", "payload")

        for i, block in enumerate(blocks):
            assert "cache_control" not in block, (
                f"Block {i} has unexpected cache_control when flag is off"
            )

    def test_flag_off_get_breakpoint_count_returns_0(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        assert cp.get_breakpoint_count() == 0

    def test_flag_off_cached_block_indices_empty(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        assert cp.cached_block_indices() == []

    def test_flag_off_content_preserved(self, monkeypatch):
        """Text content is preserved in all blocks even with no cache markers."""
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        system = "system prompt text"
        context = "skill context text"
        payload = "task payload text"

        blocks = cp.build_cached_prompt(system, context, payload)

        assert blocks[0]["text"] == system
        assert blocks[1]["text"] == context
        assert blocks[2]["text"] == payload


# ---------------------------------------------------------------------------
# Tests: flag on → ≤3 breakpoints (exactly the Phase 8 contract)
# ---------------------------------------------------------------------------

class TestCacheBreakpointsFlagOn:
    """When BR3_CACHE_BREAKPOINTS=on, exactly the 3-breakpoint Phase 8 contract."""

    def test_flag_on_exactly_2_cached_blocks(self, monkeypatch):
        """Blocks 0 and 1 (system + skill_context) carry cache_control; block 2 does not."""
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        blocks = cp.build_cached_prompt("sys", "ctx", "payload")

        assert _count_breakpoints(blocks) == 2, (
            "Expected 2 blocks with cache_control (breakpoints 1+2), "
            f"got {_count_breakpoints(blocks)}"
        )

    def test_flag_on_breakpoint_count_is_3(self, monkeypatch):
        """get_breakpoint_count() reports 3 (the contract number, not cached-block count)."""
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        assert cp.get_breakpoint_count() == 3

    def test_flag_on_cached_block_indices_are_0_and_1(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        assert cp.cached_block_indices() == [0, 1]

    def test_flag_on_block_0_has_ephemeral_cache_control(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        blocks = cp.build_cached_prompt("sys", "ctx", "payload")

        assert blocks[0].get("cache_control") == {"type": "ephemeral"}

    def test_flag_on_block_1_has_ephemeral_cache_control(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        blocks = cp.build_cached_prompt("sys", "ctx", "payload")

        assert blocks[1].get("cache_control") == {"type": "ephemeral"}

    def test_flag_on_block_2_has_no_cache_control(self, monkeypatch):
        """Task payload (breakpoint 3) must never carry cache_control."""
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        blocks = cp.build_cached_prompt("sys", "ctx", "payload")

        assert "cache_control" not in blocks[2]

    def test_flag_on_breakpoints_at_most_3(self, monkeypatch):
        """Honour the ≤3 contract: never more than 3 breakpoints."""
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        blocks = cp.build_cached_prompt("sys", "ctx", "payload")

        assert _count_breakpoints(blocks) <= 3

    def test_flag_on_content_preserved(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        system = "system prompt"
        context = "skill ctx"
        payload = "task payload"

        blocks = cp.build_cached_prompt(system, context, payload)

        assert blocks[0]["text"] == system
        assert blocks[1]["text"] == context
        assert blocks[2]["text"] == payload


# ---------------------------------------------------------------------------
# Tests: has_cache_control helper
# ---------------------------------------------------------------------------

class TestHasCacheControl:
    def test_block_with_cache_control_returns_true(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        block = {"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}
        assert cp.has_cache_control(block) is True

    def test_block_without_cache_control_returns_false(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        block = {"type": "text", "text": "x"}
        assert cp.has_cache_control(block) is False


# ---------------------------------------------------------------------------
# Tests: flag caching (read once at import)
# ---------------------------------------------------------------------------

class TestFlagCaching:
    """BR3_CACHE_BREAKPOINTS is read once at module import, not per call."""

    def test_flag_cached_as_bool_off(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        assert isinstance(cp._CACHE_BREAKPOINTS_ENABLED, bool)
        assert cp._CACHE_BREAKPOINTS_ENABLED is False

    def test_flag_cached_as_bool_on(self, monkeypatch):
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        cp = _reload_cache_policy("on")

        assert isinstance(cp._CACHE_BREAKPOINTS_ENABLED, bool)
        assert cp._CACHE_BREAKPOINTS_ENABLED is True

    def test_env_change_after_import_not_observed(self, monkeypatch):
        """Changing the env var after module load does NOT change the cached value."""
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        original = cp._CACHE_BREAKPOINTS_ENABLED
        assert original is False

        # Change env var — module-level cache should be unchanged
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "on")
        assert cp._CACHE_BREAKPOINTS_ENABLED is False  # still the cached value

    def test_flag_off_blocks_unchanged_on_repeated_calls(self, monkeypatch):
        """Repeated calls with flag off always return 0 breakpoints."""
        monkeypatch.setenv("BR3_CACHE_BREAKPOINTS", "off")
        cp = _reload_cache_policy("off")

        for _ in range(3):
            blocks = cp.build_cached_prompt("sys", "ctx", "payload")
            assert _count_breakpoints(blocks) == 0
