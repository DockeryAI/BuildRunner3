"""tests/cluster/test_context_router.py — ContextRouter behavior (Phase 12).

Verifies the per-model routing contract:
  1. Budgets: claude=32K, codex=48K, ollama=16K
  2. 'below' alias resolves to ollama budget
  3. Unknown model raises KeyError
  4. Flag OFF → empty bundle with config budget preserved
  5. Flag ON delegates to assembler with model-specific budget
  6. All five source types are declared for every model
"""

from __future__ import annotations

import os
from unittest import mock

import pytest


def test_per_model_budgets() -> None:
    from core.cluster.context_router import ContextRouter

    budgets = ContextRouter().budgets()
    assert budgets == {"claude": 32_000, "codex": 48_000, "ollama": 16_000}


def test_below_alias_resolves_to_ollama_budget() -> None:
    from core.cluster.context_router import ContextRouter

    router = ContextRouter()
    below_cfg = router.get_config("below")
    ollama_cfg = router.get_config("ollama")
    assert below_cfg.token_budget == ollama_cfg.token_budget == 16_000
    assert below_cfg.tokenizer_display == ollama_cfg.tokenizer_display == "qwen2.5"


def test_unknown_model_raises_keyerror() -> None:
    from core.cluster.context_router import ContextRouter

    with pytest.raises(KeyError, match="Unknown model"):
        ContextRouter().get_config("gpt-9")


def test_route_flag_off_returns_empty_bundle_with_budget() -> None:
    from core.cluster.context_router import ContextRouter

    with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "off"}):
        bundle = ContextRouter().route(model="codex")

    assert bundle.sections == []
    assert bundle.token_total == 0
    assert bundle.budget["limit"] == 48_000
    assert bundle.budget["tokenizer"] == "cl100k_base"


def test_route_flag_on_delegates_to_assembler_with_budget() -> None:
    from core.cluster.context_router import ContextRouter

    router = ContextRouter()
    fake_assembler = mock.Mock()
    fake_assembler.assemble.return_value = mock.Mock()
    router._assembler = fake_assembler

    with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
        router.route(model="ollama", query="q", phase="12", skill="review")

    fake_assembler.assemble.assert_called_once_with(
        model="ollama",
        token_budget=16_000,
        query="q",
        phase="12",
        skill="review",
    )


def test_all_sources_included_for_every_canonical_model() -> None:
    from core.cluster.context_router import ContextRouter

    router = ContextRouter()
    expected = ("logs", "decisions", "memory", "intel", "research")
    for model in router.list_models():
        cfg = router.get_config(model)
        assert cfg.sources == expected, f"{model} missing source: {cfg.sources}"


def test_list_models_excludes_aliases() -> None:
    from core.cluster.context_router import ContextRouter

    assert ContextRouter().list_models() == ["claude", "codex", "ollama"]
