"""context_router.py — Single source of truth for per-model context sources and budgets.

Routes context bundle assembly to the right model-specific configuration.
Skills MUST NOT bypass this module when fetching model context.

Feature-gated: BR3_AUTO_CONTEXT=on. Default OFF until Phase 13.

Per-model token budgets (tokenizer-true via count-tokens.sh):
  claude  → 32K tokens  (cl100k_base)
  codex   → 48K tokens  (cl100k_base)
  ollama  → 16K tokens  (qwen2.5)

IMPORTANT: context_router.py is the ONLY path to model-specific bundles.
           Do not call ContextBundleAssembler directly with ad-hoc budgets.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Feature gate
_MULTI_MODEL_CONTEXT_ENV = "BR3_AUTO_CONTEXT"


def _multi_model_context_enabled() -> bool:
    return os.environ.get(_MULTI_MODEL_CONTEXT_ENV, "").strip().lower() == "on"


# ---------------------------------------------------------------------------
# Model routing config (single source of truth for budgets + sources)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelRoutingConfig:
    """Per-model routing configuration.

    Fields:
        model            — canonical model name
        token_budget     — hard output bundle limit (tokenizer-true)
        tokenizer_name   — name passed to count-tokens.sh --model
        tokenizer_display — human-readable name for the budget.tokenizer field
        sources          — ordered list of source type names to include
        description      — brief role description
    """

    model: str
    token_budget: int
    tokenizer_name: str
    tokenizer_display: str
    sources: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "token_budget": self.token_budget,
            "tokenizer_name": self.tokenizer_name,
            "tokenizer_display": self.tokenizer_display,
            "sources": list(self.sources),
            "description": self.description,
        }


# All five source types — every model sees all five for parity
_ALL_SOURCES = ("logs", "decisions", "memory", "intel", "research")

# ── Model routing table (authoritative) ──────────────────────────────────────
ROUTING_TABLE: dict[str, ModelRoutingConfig] = {
    "claude": ModelRoutingConfig(
        model="claude",
        token_budget=32_000,
        tokenizer_name="claude",
        tokenizer_display="cl100k_base",
        sources=_ALL_SOURCES,
        description="Claude Opus/Sonnet — 32K bundle within 200K context window",
    ),
    "codex": ModelRoutingConfig(
        model="codex",
        token_budget=48_000,
        tokenizer_name="codex",
        tokenizer_display="cl100k_base",
        sources=_ALL_SOURCES,
        description="Codex gpt-5.5 — 48K bundle within 400K Codex CLI / 1M API context window",
    ),
    "ollama": ModelRoutingConfig(
        model="ollama",
        token_budget=16_000,
        tokenizer_name="ollama",
        tokenizer_display="qwen2.5",
        sources=_ALL_SOURCES,
        description="Below (llama3.3:70b / qwen3:8b) — 16K bundle within 32K context",
    ),
}

# Alias for spec compatibility: spec refers to "below" in some places
ROUTING_TABLE["below"] = ModelRoutingConfig(
    model="ollama",
    token_budget=16_000,
    tokenizer_name="ollama",
    tokenizer_display="qwen2.5",
    sources=_ALL_SOURCES,
    description="Below alias → ollama routing config",
)


class ContextRouter:
    """Routes context bundle requests to per-model configurations.

    This is the SINGLE source of truth for which sources and budgets flow to
    which model. Do not bypass this class.

    Usage::

        router = ContextRouter()
        config = router.get_config("codex")
        bundle = router.route(model="codex", query="runtime fallback", phase="6")
    """

    def __init__(self) -> None:
        # Import here to avoid circular imports
        from core.cluster.context_bundle import ContextBundleAssembler
        self._assembler = ContextBundleAssembler()

    def get_config(self, model: str) -> ModelRoutingConfig:
        """Return routing config for the given model.

        Args:
            model: One of 'claude', 'codex', 'ollama' (or 'below' as alias).

        Raises:
            KeyError: unknown model name.
        """
        key = model.lower().strip()
        if key not in ROUTING_TABLE:
            raise KeyError(
                f"Unknown model '{model}'. Supported: {list(ROUTING_TABLE.keys())}"
            )
        return ROUTING_TABLE[key]

    def route(
        self,
        model: str,
        query: str = "",
        phase: str = "",
        skill: str = "",
    ):
        """Assemble a context bundle for model using the authoritative per-model config.

        If BR3_AUTO_CONTEXT is OFF, returns an empty ContextBundle.
        If the tokenizer is unavailable (count-tokens.sh exit 2), raises RuntimeError
        (fail-closed — never falls back to byte counting).

        Args:
            model:  Target model name.
            query:  Optional query string for reranker ordering.
            phase:  Optional phase hint.
            skill:  Optional skill hint.

        Returns:
            ContextBundle with sections for all five source types.

        Raises:
            RuntimeError: tokenizer unavailable.
            KeyError:     unknown model.
        """
        config = self.get_config(model)

        if not _multi_model_context_enabled():
            from core.cluster.context_bundle import ContextBundle
            return ContextBundle(
                model=config.model,
                sections=[],
                token_total=0,
                budget={
                    "limit": config.token_budget,
                    "used": 0,
                    "tokenizer": config.tokenizer_display,
                },
                assembled_at="",
            )

        return self._assembler.assemble(
            model=config.model,
            token_budget=config.token_budget,
            query=query,
            phase=phase,
            skill=skill,
        )

    def list_models(self) -> list[str]:
        """Return canonical model names (excluding aliases)."""
        return ["claude", "codex", "ollama"]

    def budgets(self) -> dict[str, int]:
        """Return {model: token_budget} for all canonical models."""
        return {m: ROUTING_TABLE[m].token_budget for m in self.list_models()}
