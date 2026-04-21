"""tests/cluster/test_multi_model_parity.py — Multi-model context parity tests (Phase 12).

Verifies that each model's context bundle cites at least one item from EACH of
the five source types declared in context-sources.yaml:
  (a) logs       — .buildrunner/*.log files
  (b) decisions  — decisions.public.log (filtered)
  (c) memory     — ~/.lockwood/memory.db session memory
  (d) intel      — ~/.lockwood/intel.db intel-scored items
  (e) research   — ~/Projects/research-library/ docs

Test strategy: with BR3_MULTI_MODEL_CONTEXT=on, assemble bundles for all 3 models
using synthetic fixture data (no real DBs required). Assert each bundle's sections
include all 5 source types with non-empty content.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Fixtures — synthetic source data injected into extractors
# ---------------------------------------------------------------------------

SYNTHETIC_LOG_CONTENT = "2026-04-20T12:00:00Z INFO browser.log: app loaded"
SYNTHETIC_DECISIONS_CONTENT = "[public] Phase 12: RLS enforced on all tables"
SYNTHETIC_MEMORY_CONTENT = "Prior session: decided to use LanceDB for vector store"
SYNTHETIC_INTEL_CONTENT = "Intel score=0.92: BAAI/bge-reranker-v2-m3 shows 15% lift"
SYNTHETIC_RESEARCH_CONTENT = "# Research: LanceDB architecture\n\nLanceDB is columnar-native..."


@pytest.fixture()
def mock_sources(tmp_path: Path) -> Generator[dict[str, Path], None, None]:
    """Create all five source types as temp files/dirs and patch extractors."""
    # ── Log files ─────────────────────────────────────────────────────────────
    br_dir = tmp_path / ".buildrunner"
    br_dir.mkdir()
    (br_dir / "browser.log").write_text(SYNTHETIC_LOG_CONTENT)
    (br_dir / "supabase.log").write_text("2026-04-20T12:01:00Z INFO supabase: query ok")
    (br_dir / "device.log").write_text("")
    (br_dir / "query.log").write_text("")

    # ── Decisions (public — already filtered) ─────────────────────────────────
    (br_dir / "decisions.public.log").write_text(SYNTHETIC_DECISIONS_CONTENT)

    # ── Memory DB ────────────────────────────────────────────────────────────
    mem_dir = tmp_path / ".lockwood"
    mem_dir.mkdir()
    mem_db = mem_dir / "memory.db"
    conn = sqlite3.connect(str(mem_db))
    conn.execute("CREATE TABLE memories (content TEXT, created_at TEXT)")
    conn.execute(
        "INSERT INTO memories VALUES (?, ?)",
        (SYNTHETIC_MEMORY_CONTENT, "2026-04-20T11:00:00Z"),
    )
    conn.commit()
    conn.close()

    # ── Intel DB ─────────────────────────────────────────────────────────────
    intel_db = mem_dir / "intel.db"
    conn2 = sqlite3.connect(str(intel_db))
    conn2.execute("CREATE TABLE intel (content TEXT, score REAL, created_at TEXT)")
    conn2.execute(
        "INSERT INTO intel VALUES (?, ?, ?)",
        (SYNTHETIC_INTEL_CONTENT, 0.92, "2026-04-20T10:00:00Z"),
    )
    conn2.commit()
    conn2.close()

    # ── Research library ──────────────────────────────────────────────────────
    research_dir = tmp_path / "research-library"
    research_dir.mkdir()
    (research_dir / "lancedb-architecture.md").write_text(SYNTHETIC_RESEARCH_CONTENT)

    # ── Patch module paths ────────────────────────────────────────────────────
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
        yield {
            "br_dir": br_dir,
            "mem_db": mem_db,
            "intel_db": intel_db,
            "research_dir": research_dir,
        }


def _get_sources_cited(bundle) -> set[str]:
    """Return the set of source_type names that have non-empty content."""
    return {
        sec.source_type
        for sec in bundle.sections
        if sec.content.strip() and sec.content.strip() != "[budget exhausted — content omitted]"
    }


# ---------------------------------------------------------------------------
# test_all_five_sources — each model cites all 5 source types
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model,budget", [
    ("claude", 32_000),
    ("codex", 48_000),
    ("ollama", 16_000),
])
def test_all_five_sources(mock_sources, model: str, budget: int) -> None:
    """Each model's bundle must cite at least one item from EACH of the 5 source types."""
    from core.cluster.context_bundle import ContextBundleAssembler

    # Patch count_tokens to return a safe integer (tokenizer may not be installed in CI)
    with mock.patch("core.cluster.context_bundle.count_tokens", return_value=100):
        with mock.patch.dict(os.environ, {"BR3_MULTI_MODEL_CONTEXT": "on"}):
            assembler = ContextBundleAssembler()
            bundle = assembler.assemble(model=model, token_budget=budget)

    sources_cited = _get_sources_cited(bundle)
    required_sources = {"logs", "decisions", "memory", "intel", "research"}

    print(f"\nModel={model}: sources_cited={sources_cited}")

    assert sources_cited >= required_sources, (
        f"Model '{model}' missing source types: {required_sources - sources_cited}. "
        f"Got: {sources_cited}"
    )


def test_all_three_models_pass(mock_sources) -> None:
    """Convenience: all 3 models pass the five-source parity check in one call."""
    from core.cluster.context_bundle import ContextBundleAssembler

    results: dict[str, set[str]] = {}
    required = {"logs", "decisions", "memory", "intel", "research"}

    with mock.patch("core.cluster.context_bundle.count_tokens", return_value=100):
        with mock.patch.dict(os.environ, {"BR3_MULTI_MODEL_CONTEXT": "on"}):
            assembler = ContextBundleAssembler()
            for model, budget in [("claude", 32_000), ("codex", 48_000), ("ollama", 16_000)]:
                bundle = assembler.assemble(model=model, token_budget=budget)
                results[model] = _get_sources_cited(bundle)

    for model, sources_cited in results.items():
        print(f"Model={model}: sources_cited={sources_cited}")
        assert sources_cited >= required, (
            f"Parity failure for model '{model}': missing {required - sources_cited}"
        )


def test_flag_off_returns_empty_bundle() -> None:
    """When BR3_MULTI_MODEL_CONTEXT is OFF, bundle is empty (zero behavior change)."""
    from core.cluster.context_bundle import ContextBundleAssembler

    with mock.patch.dict(os.environ, {"BR3_MULTI_MODEL_CONTEXT": "off"}):
        assembler = ContextBundleAssembler()
        bundle = assembler.assemble(model="codex", token_budget=48_000)

    assert bundle.sections == []
    assert bundle.token_total == 0
    assert bundle.budget["tokenizer"] == "disabled"


def test_router_per_model_budgets() -> None:
    """context_router.py enforces correct per-model token budgets."""
    from core.cluster.context_router import ContextRouter

    router = ContextRouter()

    assert router.get_config("claude").token_budget == 32_000
    assert router.get_config("codex").token_budget == 48_000
    assert router.get_config("ollama").token_budget == 16_000

    # Verify tokenizer names are NOT 'bytes'
    assert router.get_config("claude").tokenizer_display != "bytes"
    assert router.get_config("codex").tokenizer_display != "bytes"
    assert router.get_config("ollama").tokenizer_display != "bytes"

    # Verify all five source types are included for every model
    for model in ("claude", "codex", "ollama"):
        config = router.get_config(model)
        for src in ("logs", "decisions", "memory", "intel", "research"):
            assert src in config.sources, f"Model {model} missing source: {src}"


def test_router_unknown_model_raises() -> None:
    """context_router.py raises KeyError for unknown model names."""
    from core.cluster.context_router import ContextRouter
    router = ContextRouter()
    with pytest.raises(KeyError):
        router.get_config("gpt-3")


def test_prompt_block_format(mock_sources) -> None:
    """Bundle.to_prompt_block() produces a valid <cluster-context> block."""
    from core.cluster.context_bundle import ContextBundleAssembler

    with mock.patch("core.cluster.context_bundle.count_tokens", return_value=100):
        with mock.patch.dict(os.environ, {"BR3_MULTI_MODEL_CONTEXT": "on"}):
            assembler = ContextBundleAssembler()
            bundle = assembler.assemble(model="codex", token_budget=48_000)

    block = bundle.to_prompt_block()
    assert "<cluster-context>" in block
    assert "</cluster-context>" in block
