"""tests/cluster/test_context_bundle.py — Context bundle primitives (Phase 12).

Unit-level coverage for the bundle assembler:
  1. Flag OFF → empty bundle
  2. filter_private_lines drops [private] lines and preserves [privately] / [private-note]
  3. count_tokens raises RuntimeError on exit 2 (fail-closed tokenizer)
  4. assemble propagates tokenizer error (no byte fallback)
  5. All five source types present in a populated bundle
  6. to_prompt_block renders the expected <cluster-context> envelope
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# filter_private_lines — boundary semantics
# ---------------------------------------------------------------------------

def test_filter_private_lines_drops_tagged_lines() -> None:
    from core.cluster.context_bundle import filter_private_lines

    raw = (
        "public line 1\n"
        "[private] secret sauce\n"
        "public line 2\n"
        "tail [private] trailing\n"
        "public line 3\n"
    )
    out = filter_private_lines(raw)
    assert "secret sauce" not in out
    assert "trailing" not in out
    assert "public line 1" in out
    assert "public line 2" in out
    assert "public line 3" in out


def test_filter_private_lines_preserves_word_boundary_negatives() -> None:
    """[privately] and [private-note] must NOT be filtered."""
    from core.cluster.context_bundle import filter_private_lines

    raw = (
        "[privately] keep me\n"
        "[private-note] keep me too\n"
        "[private] drop me\n"
    )
    out = filter_private_lines(raw)
    assert "[privately]" in out
    assert "[private-note]" in out
    assert "drop me" not in out


# ---------------------------------------------------------------------------
# count_tokens — exit-2 fail-closed
# ---------------------------------------------------------------------------

def test_count_tokens_raises_on_exit_2(tmp_path: Path) -> None:
    from core.cluster import context_bundle

    fake_script = tmp_path / "count-tokens.sh"
    fake_script.write_text("#!/bin/sh\nexit 2\n")
    fake_result = mock.Mock(returncode=2, stdout="", stderr="tokenizer missing")
    with mock.patch.object(context_bundle, "_COUNT_TOKENS_SH", fake_script), \
         mock.patch("core.cluster.context_bundle.subprocess.run", return_value=fake_result):
        with pytest.raises(RuntimeError, match="tokenizer unavailable"):
            context_bundle.count_tokens("some text", "claude")


def test_count_tokens_rejects_unknown_model(tmp_path: Path) -> None:
    from core.cluster import context_bundle

    fake_script = tmp_path / "count-tokens.sh"
    fake_script.write_text("#!/bin/sh\nexit 0\n")
    with mock.patch.object(context_bundle, "_COUNT_TOKENS_SH", fake_script):
        with pytest.raises(ValueError, match="Unknown model"):
            context_bundle.count_tokens("x", "gpt-9")


def test_count_tokens_missing_script_raises(tmp_path: Path) -> None:
    from core.cluster import context_bundle

    missing = tmp_path / "does-not-exist.sh"
    with mock.patch.object(context_bundle, "_COUNT_TOKENS_SH", missing):
        with pytest.raises(RuntimeError, match="count-tokens.sh not found"):
            context_bundle.count_tokens("x", "claude")


# ---------------------------------------------------------------------------
# assemble — flag OFF short-circuit + tokenizer-error propagation
# ---------------------------------------------------------------------------

def test_assemble_flag_off_returns_empty_bundle() -> None:
    from core.cluster.context_bundle import ContextBundleAssembler

    with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "off"}):
        bundle = ContextBundleAssembler().assemble(model="claude", token_budget=32_000)

    assert bundle.sections == []
    assert bundle.token_total == 0
    assert bundle.budget["tokenizer"] == "disabled"


def test_assemble_propagates_tokenizer_failure(tmp_path: Path) -> None:
    """If count_tokens raises RuntimeError, assemble must re-raise (no byte fallback)."""
    from core.cluster.context_bundle import ContextBundleAssembler

    br_dir = tmp_path / ".buildrunner"
    br_dir.mkdir()
    (br_dir / "browser.log").write_text("line a\nline b\n")

    with mock.patch.multiple(
        "core.cluster.context_bundle",
        _BROWSER_LOG=br_dir / "browser.log",
        _SUPABASE_LOG=br_dir / "supabase.log",
        _DEVICE_LOG=br_dir / "device.log",
        _QUERY_LOG=br_dir / "query.log",
        _DECISIONS_LOG=br_dir / "decisions.log",
        _DECISIONS_PUBLIC_LOG=br_dir / "decisions.public.log",
    ), mock.patch(
        "core.cluster.context_bundle.count_tokens",
        side_effect=RuntimeError("tokenizer unavailable"),
    ), mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
        with pytest.raises(RuntimeError, match="tokenizer unavailable"):
            ContextBundleAssembler().assemble(model="claude", token_budget=32_000)


# ---------------------------------------------------------------------------
# Five-source presence + prompt-block envelope
# ---------------------------------------------------------------------------

@pytest.fixture()
def populated_sources(tmp_path: Path) -> Generator[dict, None, None]:
    br_dir = tmp_path / ".buildrunner"
    br_dir.mkdir()
    (br_dir / "browser.log").write_text("browser entry")
    (br_dir / "supabase.log").write_text("supabase entry")
    (br_dir / "device.log").write_text("")
    (br_dir / "query.log").write_text("")
    (br_dir / "decisions.public.log").write_text("[public] decision entry")

    mem_dir = tmp_path / ".lockwood"
    mem_dir.mkdir()
    mem_db = mem_dir / "memory.db"
    conn = sqlite3.connect(str(mem_db))
    conn.execute("CREATE TABLE memories (content TEXT, created_at TEXT)")
    conn.execute("INSERT INTO memories VALUES (?, ?)", ("memory entry", "2026-04-20T00:00:00Z"))
    conn.commit()
    conn.close()

    intel_db = mem_dir / "intel.db"
    conn = sqlite3.connect(str(intel_db))
    conn.execute("CREATE TABLE intel (content TEXT, score REAL, created_at TEXT)")
    conn.execute(
        "INSERT INTO intel VALUES (?, ?, ?)",
        ("intel entry", 0.95, "2026-04-20T00:00:00Z"),
    )
    conn.commit()
    conn.close()

    research_dir = tmp_path / "research-library"
    research_dir.mkdir()
    (research_dir / "note.md").write_text("# research entry\nbody")

    with mock.patch.multiple(
        "core.cluster.context_bundle",
        _BROWSER_LOG=br_dir / "browser.log",
        _SUPABASE_LOG=br_dir / "supabase.log",
        _DEVICE_LOG=br_dir / "device.log",
        _QUERY_LOG=br_dir / "query.log",
        _DECISIONS_LOG=br_dir / "decisions.log",
        _DECISIONS_PUBLIC_LOG=br_dir / "decisions.public.log",
        _MEMORY_DB=mem_db,
        _INTEL_DB=intel_db,
        _JIMMY_MEMORY_DB=mem_db,
        _JIMMY_INTEL_DB=intel_db,
        _RESEARCH_LIBRARY=research_dir,
        _JIMMY_RESEARCH=research_dir,
    ):
        yield {"tmp_path": tmp_path}


def test_bundle_contains_all_five_source_types(populated_sources) -> None:
    from core.cluster.context_bundle import ContextBundleAssembler

    with mock.patch("core.cluster.context_bundle.count_tokens", return_value=50), \
         mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
        bundle = ContextBundleAssembler().assemble(model="claude", token_budget=32_000)

    source_types = {s.source_type for s in bundle.sections}
    assert source_types == {"logs", "decisions", "memory", "intel", "research"}


def test_to_prompt_block_wraps_sections(populated_sources) -> None:
    from core.cluster.context_bundle import ContextBundleAssembler

    with mock.patch("core.cluster.context_bundle.count_tokens", return_value=50), \
         mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
        bundle = ContextBundleAssembler().assemble(model="claude", token_budget=32_000)

    block = bundle.to_prompt_block()
    assert block.startswith("<cluster-context>")
    assert block.rstrip().endswith("</cluster-context>")
    assert "## LOGS" in block
    assert "## DECISIONS" in block
