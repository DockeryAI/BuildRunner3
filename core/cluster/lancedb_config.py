"""core/cluster/lancedb_config.py — Single source of truth for LanceDB URI.

Any module that touches LanceDB (retrieve.py, node_semantic.py, research_chunker,
reindex scripts) MUST import `get_lancedb_uri()` from here. No hardcoded paths.

Environment:
    LANCE_DIR — overrides the URI. Set to `/srv/jimmy/lancedb` on Jimmy
    (canonical production host per Phase 1 Muddy→Jimmy decision). Unset
    falls back to `~/.lockwood/lancedb` for backward compatibility during
    the Phase 4 migration window. After the 7-day Lockwood retention
    period, the Lockwood copy is removed and every consumer must set
    LANCE_DIR explicitly.

Embedding:
    EMBEDDING_MODEL — canonical sentence-transformers model. Default:
    `sentence-transformers/all-MiniLM-L6-v2` (384-dim). Phase 6 confirmed.
    EMBEDDING_DIM — vector column width. MUST match the embedder output
    and the index schema. Startup asserts fire if they diverge.
"""

from __future__ import annotations

import os
from pathlib import Path

# Fallback during transition; explicit LANCE_DIR env overrides on all hosts.
_LOCKWOOD_FALLBACK = str(Path.home() / ".lockwood" / "lancedb")
_JIMMY_CANONICAL = "/srv/jimmy/lancedb"

EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "384"))


def _resolve_cached_sentence_transformer(model_name: str) -> str:
    """Prefer a local HuggingFace snapshot path when it exists.

    This keeps Jimmy offline: `SentenceTransformer(<snapshot-dir>)` loads from
    disk directly instead of attempting network metadata calls for the model id.
    Non-default model ids fall through untouched.
    """
    if Path(model_name).is_absolute():
        return model_name
    if model_name != "sentence-transformers/all-MiniLM-L6-v2":
        return model_name

    hub_root = Path.home() / ".cache" / "huggingface" / "hub"
    model_root = hub_root / "models--sentence-transformers--all-MiniLM-L6-v2"
    ref_path = model_root / "refs" / "main"
    if ref_path.is_file():
        snapshot = (model_root / "snapshots" / ref_path.read_text().strip())
        if snapshot.is_dir():
            return str(snapshot)
    snapshots_dir = model_root / "snapshots"
    if snapshots_dir.is_dir():
        for candidate in sorted(snapshots_dir.iterdir()):
            if candidate.is_dir():
                return str(candidate)
    return model_name


def get_lancedb_uri() -> str:
    """Return the canonical LanceDB URI for this host.

    Resolution order:
      1. `$LANCE_DIR` if set (explicit override wins).
      2. `/srv/jimmy/lancedb` if that path exists (we are on Jimmy).
      3. `~/.lockwood/lancedb` (transitional fallback).
    """
    override = os.environ.get("LANCE_DIR")
    if override:
        return override
    if Path(_JIMMY_CANONICAL).is_dir():
        return _JIMMY_CANONICAL
    return _LOCKWOOD_FALLBACK


def get_embedding_model() -> str:
    return _resolve_cached_sentence_transformer(EMBEDDING_MODEL)


def get_embedding_dim() -> int:
    return EMBEDDING_DIM


def assert_index_dim_matches(actual_dim: int) -> None:
    """Raise at startup if an opened index's vector width disagrees with config."""
    if actual_dim != EMBEDDING_DIM:
        raise RuntimeError(
            f"Embedding-dim mismatch: config={EMBEDDING_DIM} index={actual_dim}. "
            "Re-run ~/.buildrunner/scripts/reindex-research.sh to rebuild."
        )
