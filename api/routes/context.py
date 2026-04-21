"""api/routes/context.py — GET /context/{model} endpoint (Phase 12).

Serves per-model context bundles on Jimmy (port 4500, behind gateway).
Accepts query + phase + skill params; returns sized bundle with budget field.

Feature-gated: BR3_MULTI_MODEL_CONTEXT=on. Returns 503 if flag is OFF.

Endpoint: GET /context/{model}?query=<q>&phase=<p>&skill=<s>
  model: claude | codex | ollama (also accepts 'below' as alias for ollama)

Response shape:
  {
    "bundle": { ...ContextBundle.to_dict() },
    "budget": { "limit": int, "used": int, "tokenizer": str }
  }

IMPORTANT: Read-only surface. No mutation of any source through this route.
IMPORTANT: context_router.py is the single source of truth for bundles.
IMPORTANT (Phase 1): This module exposes ONLY an APIRouter named 'router'.
  No module-level FastAPI app here. Standalone bootstrap lives in:
  api/services/context_api_standalone.py
  Mounting into node_semantic.py: core/cluster/node_semantic.py
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/context", tags=["context"])

_MULTI_MODEL_CONTEXT_ENV = "BR3_MULTI_MODEL_CONTEXT"

_SUPPORTED_MODELS = {"claude", "codex", "ollama", "below"}


def _multi_model_context_enabled() -> bool:
    return os.environ.get(_MULTI_MODEL_CONTEXT_ENV, "").strip().lower() == "on"


@router.get("/{model}")
async def get_context(
    model: str,
    query: str = Query(default="", description="Query string for context relevance"),
    phase: str = Query(default="", description="Phase hint (e.g. '12')"),
    skill: str = Query(default="", description="Skill name hint"),
) -> JSONResponse:
    """Return a per-model context bundle.

    If BR3_MULTI_MODEL_CONTEXT is OFF, returns 503.
    If model is unknown, returns 400.
    If tokenizer is unavailable (count-tokens.sh exit 2), returns 503.
    If Jimmy sources are unreachable, gracefully returns partial bundle.

    Response includes a `budget` field with {limit, used, tokenizer} —
    the `tokenizer` value is the model-specific tokenizer name (NOT 'bytes').
    """
    model_key = model.lower().strip()

    if model_key not in _SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model}'. Supported: {sorted(_SUPPORTED_MODELS)}",
        )

    if not _multi_model_context_enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "BR3_MULTI_MODEL_CONTEXT is OFF. "
                "Enable with BR3_MULTI_MODEL_CONTEXT=on (Phase 13 cutover)."
            ),
        )

    try:
        from core.cluster.context_router import ContextRouter
        router_inst = ContextRouter()

        bundle = router_inst.route(
            model=model_key,
            query=query,
            phase=phase,
            skill=skill,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        # tokenizer unavailable — fail-closed
        logger.error("context endpoint: tokenizer unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Tokenizer unavailable — bundle refused: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("context endpoint: unexpected error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Context assembly failed: {exc}",
        ) from exc

    bundle_dict = bundle.to_dict()

    return JSONResponse(
        content={
            "bundle": bundle_dict,
            "budget": bundle_dict.get("budget", {}),
        }
    )
