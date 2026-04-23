"""context_injector.py — Registry-side context injection wrapper (Phase 12).

Wraps RuntimeRegistry.execute(task) calls to prepend a per-model context bundle
when BR3_AUTO_CONTEXT=on.

Feature-gated: default OFF until Phase 13.
IMPORTANT: context_router.py is the ONLY path to model-specific bundles.
           This module calls ContextRouter — never assembles bundles directly.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.runtime.types import RuntimeTask

logger = logging.getLogger(__name__)

_MULTI_MODEL_CONTEXT_ENV = "BR3_AUTO_CONTEXT"


def _multi_model_context_enabled() -> bool:
    """Return True when BR3_AUTO_CONTEXT=on (case-insensitive). Default OFF."""
    return os.environ.get(_MULTI_MODEL_CONTEXT_ENV, "").strip().lower() == "on"


# Map RuntimeRegistry runtime names → context router model keys
_RUNTIME_TO_MODEL: dict[str, str] = {
    "claude": "claude",
    "codex": "codex",
    "ollama": "ollama",
}


class ContextInjector:
    """Injects per-model context bundles into RuntimeTask prompts.

    Used by RuntimeRegistry.execute() when BR3_AUTO_CONTEXT=on.
    When the flag is OFF, inject() is a no-op — zero behavior change.

    Usage::

        injector = ContextInjector()
        task = injector.inject(task, runtime_name="codex", phase="12")
    """

    def __init__(self) -> None:
        self._router = None  # Lazy-init to avoid circular imports at module load

    def _get_router(self):
        if self._router is None:
            from core.cluster.context_router import ContextRouter
            self._router = ContextRouter()
        return self._router

    def inject(
        self,
        task: "RuntimeTask",
        runtime_name: str = "claude",
        phase: str = "",
        skill: str = "",
    ) -> "RuntimeTask":
        """Prepend a <cluster-context> block to task.prompt if flag is ON.

        If the context router fails (Jimmy unreachable, tokenizer unavailable),
        logs a warning and returns the original task unmodified (graceful degrade).

        Args:
            task:         The RuntimeTask to inject context into.
            runtime_name: Runtime name from RuntimeRegistry (claude | codex | ollama).
            phase:        Optional phase hint for context relevance.
            skill:        Optional skill name for context relevance.

        Returns:
            RuntimeTask — either with context prepended (flag ON + router success)
            or the original task (flag OFF or router failure).
        """
        if not _multi_model_context_enabled():
            return task

        model = _RUNTIME_TO_MODEL.get(runtime_name, "claude")
        router = self._get_router()

        try:
            bundle = router.route(
                model=model,
                query=_extract_query(task),
                phase=phase,
                skill=skill,
            )
        except RuntimeError as exc:
            # tokenizer unavailable — graceful degrade, log warning, proceed without bundle
            logger.warning(
                "ContextInjector: tokenizer unavailable for model=%s, skipping injection: %s",
                model,
                exc,
            )
            return task
        except Exception as exc:  # noqa: BLE001
            # Jimmy unreachable or other failure — graceful degrade
            logger.warning(
                "ContextInjector: context routing failed for model=%s, skipping injection: %s",
                model,
                exc,
            )
            return task

        if not bundle.sections or bundle.token_total == 0:
            return task

        prompt_block = bundle.to_prompt_block()
        # Prepend context block to existing prompt
        original_prompt = getattr(task, "prompt", "") or ""
        task_with_context = _copy_task_with_prompt(
            task, prompt_block + "\n\n" + original_prompt
        )

        logger.debug(
            "ContextInjector: injected %d tokens into %s task",
            bundle.token_total,
            runtime_name,
        )
        return task_with_context


def _extract_query(task: "RuntimeTask") -> str:
    """Extract a query string from a RuntimeTask for context routing."""
    prompt = getattr(task, "prompt", "") or ""
    # Use first 200 chars of prompt as query hint
    return prompt[:200].replace("\n", " ").strip()


def _copy_task_with_prompt(task: "RuntimeTask", new_prompt: str) -> "RuntimeTask":
    """Return a shallow copy of task with prompt replaced.

    Handles both dataclass and plain-object RuntimeTask shapes.
    """
    import dataclasses
    if dataclasses.is_dataclass(task):
        return dataclasses.replace(task, prompt=new_prompt)  # type: ignore[arg-type]
    # Fallback: mutate a copy
    import copy
    new_task = copy.copy(task)
    new_task.prompt = new_prompt
    return new_task
