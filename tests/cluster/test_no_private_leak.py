"""tests/cluster/test_no_private_leak.py — MANDATORY canary test for [private] leak prevention.

Seeds decisions.log with a synthetic [private] canary line, runs the filter, assembles bundles,
and asserts the canary token appears NOWHERE in output.

This is the two-layer filter verification:
  Layer 1: filter_private_lines() (the same logic used by filter-private-decisions.sh)
  Layer 2: context_bundle.py extraction re-filters as defense-in-depth

IMPORTANT: This test MUST pass before Phase 12 is marked complete.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest


CANARY_TOKEN = "secret-canary-token-XYZ"
PRIVATE_LINE = f"[private] {CANARY_TOKEN}"
PUBLIC_LINE_1 = "[public] Phase 12: context parity shipped"
PUBLIC_LINE_2 = "2026-04-20T12:00:00Z PHASE-12 COMPLETE <model> key-decision"


# ---------------------------------------------------------------------------
# test_filter_private_lines — Python filter function
# ---------------------------------------------------------------------------

def test_filter_private_lines_removes_canary() -> None:
    """filter_private_lines() must drop the [private] canary line."""
    from core.cluster.context_bundle import filter_private_lines

    decisions_content = "\n".join([PUBLIC_LINE_1, PRIVATE_LINE, PUBLIC_LINE_2])
    result = filter_private_lines(decisions_content)

    assert CANARY_TOKEN not in result, (
        f"PRIVATE LEAK: canary token '{CANARY_TOKEN}' found in filter_private_lines output"
    )
    assert "[private]" not in result, (
        "PRIVATE LEAK: '[private]' tag found in filter_private_lines output"
    )
    # Public lines preserved
    assert PUBLIC_LINE_1 in result
    assert PUBLIC_LINE_2 in result


def test_filter_private_lines_line_count() -> None:
    """Two public lines + one private line → two lines in output."""
    from core.cluster.context_bundle import filter_private_lines

    text = "\n".join([PUBLIC_LINE_1, PRIVATE_LINE, PUBLIC_LINE_2])
    result = filter_private_lines(text)
    output_lines = [ln for ln in result.splitlines() if ln.strip()]
    assert len(output_lines) == 2, (
        f"Expected 2 lines after filtering, got {len(output_lines)}: {output_lines}"
    )


def test_filter_does_not_drop_privately() -> None:
    """Word-boundary filter must NOT drop the word 'privately' (no false positives)."""
    from core.cluster.context_bundle import filter_private_lines

    line = "This was done privately for good reason."
    result = filter_private_lines(line)
    assert "privately" in result, "False positive: 'privately' should NOT be stripped"


def test_filter_idempotent() -> None:
    """Running filter twice produces the same output (idempotent)."""
    from core.cluster.context_bundle import filter_private_lines

    text = "\n".join([PUBLIC_LINE_1, PRIVATE_LINE, PUBLIC_LINE_2])
    once = filter_private_lines(text)
    twice = filter_private_lines(once)
    assert once == twice


# ---------------------------------------------------------------------------
# test_filter_script — shell script filter-private-decisions.sh
# ---------------------------------------------------------------------------

FILTER_SCRIPT = Path.home() / ".buildrunner" / "scripts" / "filter-private-decisions.sh"


@pytest.mark.skipif(
    not FILTER_SCRIPT.exists(),
    reason="filter-private-decisions.sh not installed",
)
def test_shell_filter_removes_canary() -> None:
    """filter-private-decisions.sh must drop lines with [private] token."""
    text = "\n".join([PUBLIC_LINE_1, PRIVATE_LINE, PUBLIC_LINE_2])

    result = subprocess.run(
        [str(FILTER_SCRIPT)],
        input=text,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, f"filter script failed: {result.stderr}"
    assert CANARY_TOKEN not in result.stdout, (
        f"PRIVATE LEAK: canary found in shell filter output: {result.stdout!r}"
    )
    assert "[private]" not in result.stdout


@pytest.mark.skipif(
    not FILTER_SCRIPT.exists(),
    reason="filter-private-decisions.sh not installed",
)
def test_shell_filter_line_count() -> None:
    """Shell filter: 3 input lines (1 private) → 2 output lines."""
    text = "\n".join([PUBLIC_LINE_1, PRIVATE_LINE, PUBLIC_LINE_2])

    result = subprocess.run(
        [str(FILTER_SCRIPT)],
        input=text,
        capture_output=True,
        text=True,
        timeout=10,
    )

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}: {lines}"


# ---------------------------------------------------------------------------
# test_bundle_no_private_leak — full bundle assembly
# ---------------------------------------------------------------------------

@pytest.fixture()
def canary_sources(tmp_path: Path) -> Generator[dict, None, None]:
    """Create source fixtures that include the [private] canary line."""
    br_dir = tmp_path / ".buildrunner"
    br_dir.mkdir()

    # decisions.log WITH [private] canary (raw — should be filtered)
    decisions_raw = "\n".join([PUBLIC_LINE_1, PRIVATE_LINE, PUBLIC_LINE_2])
    (br_dir / "decisions.log").write_text(decisions_raw)

    # decisions.public.log WITHOUT canary (simulates what sync would produce)
    from core.cluster.context_bundle import filter_private_lines
    (br_dir / "decisions.public.log").write_text(filter_private_lines(decisions_raw))

    # Minimal log files
    (br_dir / "browser.log").write_text("INFO browser: loaded")
    (br_dir / "supabase.log").write_text("")
    (br_dir / "device.log").write_text("")
    (br_dir / "query.log").write_text("")

    # Memory DB (no canary)
    mem_dir = tmp_path / ".lockwood"
    mem_dir.mkdir()
    mem_db = mem_dir / "memory.db"
    conn = sqlite3.connect(str(mem_db))
    conn.execute("CREATE TABLE memories (content TEXT, created_at TEXT)")
    conn.execute("INSERT INTO memories VALUES (?, ?)", ("Safe memory entry", "2026-04-20T11:00:00Z"))
    conn.commit()
    conn.close()

    # Intel DB (no canary)
    intel_db = mem_dir / "intel.db"
    conn2 = sqlite3.connect(str(intel_db))
    conn2.execute("CREATE TABLE intel (content TEXT, score REAL, created_at TEXT)")
    conn2.execute("INSERT INTO intel VALUES (?, ?, ?)", ("Safe intel entry", 0.9, "2026-04-20T10:00:00Z"))
    conn2.commit()
    conn2.close()

    # Research dir (no canary)
    research_dir = tmp_path / "research-library"
    research_dir.mkdir()
    (research_dir / "safe-doc.md").write_text("# Safe research doc\n\nNo sensitive data here.")

    with mock.patch.multiple(
        "core.cluster.context_bundle",
        _BROWSER_LOG=br_dir / "browser.log",
        _SUPABASE_LOG=br_dir / "supabase.log",
        _DEVICE_LOG=br_dir / "device.log",
        _QUERY_LOG=br_dir / "query.log",
        _DECISIONS_LOG=br_dir / "decisions.log",
        _DECISIONS_PUBLIC_LOG=br_dir / "decisions.public.log",
        _MEMORY_DB=mem_dir / "memory.db",
        _INTEL_DB=intel_db,
        _JIMMY_MEMORY_DB=mem_dir / "memory.db",
        _JIMMY_INTEL_DB=intel_db,
        _RESEARCH_LIBRARY=research_dir,
        _JIMMY_RESEARCH=research_dir,
    ):
        yield {"br_dir": br_dir, "decisions_raw": decisions_raw}


def test_bundle_no_private_leak(canary_sources) -> None:
    """Assemble bundles for all models; canary must NOT appear in any bundle output."""
    from core.cluster.context_bundle import ContextBundleAssembler

    with mock.patch("core.cluster.context_bundle.count_tokens", return_value=100):
        with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
            assembler = ContextBundleAssembler()

            for model, budget in [("claude", 32_000), ("codex", 48_000), ("ollama", 16_000)]:
                bundle = assembler.assemble(model=model, token_budget=budget)
                prompt_block = bundle.to_prompt_block()

                # Canary must NOT appear anywhere in the bundle
                assert CANARY_TOKEN not in prompt_block, (
                    f"PRIVATE LEAK in model={model} bundle: "
                    f"canary '{CANARY_TOKEN}' found in prompt block"
                )
                assert "[private]" not in prompt_block, (
                    f"PRIVATE LEAK in model={model} bundle: '[private]' tag found"
                )

                # Also check raw section content
                for sec in bundle.sections:
                    assert CANARY_TOKEN not in sec.content, (
                        f"PRIVATE LEAK in model={model} section={sec.source_type}: "
                        f"canary '{CANARY_TOKEN}' found"
                    )


def test_raw_decisions_log_is_filtered(canary_sources) -> None:
    """Even if decisions.public.log is absent, the raw log extractor must filter [private]."""
    from core.cluster.context_bundle import _extract_decisions

    # Temporarily remove the public log to force fallback to raw log
    public_log = canary_sources["br_dir"] / "decisions.public.log"
    public_log.unlink(missing_ok=True)

    # Re-patch with no public log
    with mock.patch("core.cluster.context_bundle._DECISIONS_PUBLIC_LOG", public_log):
        section = _extract_decisions()

    assert CANARY_TOKEN not in section.content, (
        f"PRIVATE LEAK: canary found in decisions section even from raw log path"
    )
    assert "[private]" not in section.content


# ---------------------------------------------------------------------------
# test_shared_private_filter — core.cluster.private_filter is the single source
# ---------------------------------------------------------------------------

def test_shared_private_filter_module_is_source_of_truth() -> None:
    """context_bundle.filter_private_lines must be the same symbol as core.cluster.private_filter."""
    from core.cluster import context_bundle, private_filter

    assert context_bundle.filter_private_lines is private_filter.filter_private_lines, (
        "filter_private_lines must re-export from core.cluster.private_filter "
        "so every egress path shares one implementation."
    )


# ---------------------------------------------------------------------------
# test_research_canary — research docs must not leak [private] into bundles
# ---------------------------------------------------------------------------

RESEARCH_CANARY = "research-canary-sensitive-ABC"
RESEARCH_PRIVATE_LINE = f"[private] {RESEARCH_CANARY}"


def test_research_canary_never_reaches_bundle(tmp_path: Path) -> None:
    """Research library doc containing [private] must be stripped before bundle append."""
    from core.cluster import context_bundle
    from core.cluster.context_bundle import ContextBundleAssembler

    research_dir = tmp_path / "research-library"
    research_dir.mkdir()
    (research_dir / "tainted.md").write_text(
        f"# Tainted doc\n\n{RESEARCH_PRIVATE_LINE}\n\n[public] safe body line.\n"
    )
    br_dir = tmp_path / ".buildrunner"
    br_dir.mkdir()
    (br_dir / "decisions.log").write_text(PUBLIC_LINE_1 + "\n")
    (br_dir / "decisions.public.log").write_text(PUBLIC_LINE_1 + "\n")
    (br_dir / "browser.log").write_text("")
    (br_dir / "supabase.log").write_text("")
    (br_dir / "device.log").write_text("")
    (br_dir / "query.log").write_text("")

    mem_dir = tmp_path / ".lockwood"
    mem_dir.mkdir()
    missing_db = mem_dir / "nonexistent.db"

    with mock.patch.multiple(
        "core.cluster.context_bundle",
        _RESEARCH_LIBRARY=research_dir,
        _JIMMY_RESEARCH=research_dir,
        _BROWSER_LOG=br_dir / "browser.log",
        _SUPABASE_LOG=br_dir / "supabase.log",
        _DEVICE_LOG=br_dir / "device.log",
        _QUERY_LOG=br_dir / "query.log",
        _DECISIONS_LOG=br_dir / "decisions.log",
        _DECISIONS_PUBLIC_LOG=br_dir / "decisions.public.log",
        _MEMORY_DB=missing_db,
        _INTEL_DB=missing_db,
        _JIMMY_MEMORY_DB=missing_db,
        _JIMMY_INTEL_DB=missing_db,
    ):
        with mock.patch.object(context_bundle, "count_tokens", return_value=100):
            with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
                assembler = ContextBundleAssembler()
                bundle = assembler.assemble(model="claude", token_budget=32_000)
                prompt = bundle.to_prompt_block()

    assert RESEARCH_CANARY not in prompt, (
        f"PRIVATE LEAK: research canary '{RESEARCH_CANARY}' appeared in bundle prompt"
    )
    assert "[private]" not in prompt


def test_retrieve_route_scrubs_private_lines(monkeypatch, tmp_path: Path) -> None:
    """POST /retrieve must scrub [private] lines from every source row."""
    from api.routes import retrieve as retrieve_mod

    # Seed a decisions.log containing the research canary on a [private] line.
    decisions_log = tmp_path / "decisions.log"
    decisions_log.write_text(
        "\n".join([
            PUBLIC_LINE_1,
            f"[private] {RESEARCH_CANARY}",
            PUBLIC_LINE_2,
        ])
    )
    monkeypatch.setattr(retrieve_mod, "DECISIONS_LOG", str(decisions_log))

    hits = retrieve_mod._search_decisions("canary", limit=10)
    for h in hits:
        assert RESEARCH_CANARY not in h["text"], (
            f"PRIVATE LEAK in /retrieve decisions row: {h['text']!r}"
        )
        assert "[private]" not in h["text"]


def test_private_filter_pattern_anchoring() -> None:
    """Verify [private] filter uses word-boundary anchoring (not substring match)."""
    from core.cluster.context_bundle import filter_private_lines

    test_cases = [
        # Should be DROPPED
        ("[private] secret data", True),
        ("prefix [private] secret", True),
        ("info [private]", True),

        # Should be KEPT (not matching \b\[private\]\b)
        ("[privately] discussed", False),
        ("not_private", False),
        ("[public] [private-note] something", False),  # [private-note] is not [private]
    ]

    for line, should_be_dropped in test_cases:
        result = filter_private_lines(line)
        if should_be_dropped:
            assert "[private]" not in result, (
                f"Expected line to be dropped but '[private]' survived in: {result!r}"
            )
        else:
            # Non-private lines should survive
            assert line.strip() in result.strip(), (
                f"False positive: '{line}' was incorrectly dropped. Output: {result!r}"
            )
