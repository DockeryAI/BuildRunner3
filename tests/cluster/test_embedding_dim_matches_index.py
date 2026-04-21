"""tests/cluster/test_embedding_dim_matches_index.py — Phase 6 dim guard.

Verifies the canonical embedder matches the LanceDB index schema:
  - config exports `all-MiniLM-L6-v2` and dim 384
  - the embedder actually emits 384-wide vectors
  - `assert_index_dim_matches` raises on mismatch and passes on match
  - if `$LANCE_DIR` points to a live index with `research_library`, the
    stored vector column width matches config (reindex required otherwise)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_canonical_embedder_is_minilm_384() -> None:
    from core.cluster import lancedb_config

    assert lancedb_config.get_embedding_model() == "sentence-transformers/all-MiniLM-L6-v2"
    assert lancedb_config.get_embedding_dim() == 384


def test_assert_index_dim_matches_behavior() -> None:
    from core.cluster import lancedb_config

    lancedb_config.assert_index_dim_matches(384)  # no raise
    with pytest.raises(RuntimeError, match="Embedding-dim mismatch"):
        lancedb_config.assert_index_dim_matches(768)


def test_embedder_output_width_matches_config() -> None:
    """Load the sentence-transformer and confirm encode() returns 384-wide vectors."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        pytest.skip("sentence-transformers not installed in this environment")

    from core.cluster.lancedb_config import get_embedding_model, get_embedding_dim

    model = SentenceTransformer(get_embedding_model())
    vec = model.encode(["canonical embedder smoke test"])[0]
    assert len(vec) == get_embedding_dim(), (
        f"Embedder output width {len(vec)} != config dim {get_embedding_dim()}. "
        "Model and config are out of sync."
    )


def test_lancedb_research_library_vector_width() -> None:
    """If a LanceDB URI is reachable and research_library exists, vector width must match config."""
    try:
        import lancedb
    except ImportError:
        pytest.skip("lancedb not installed in this environment")

    from core.cluster.lancedb_config import get_lancedb_uri, get_embedding_dim

    uri = get_lancedb_uri()
    if not Path(uri).is_dir():
        pytest.skip(f"LanceDB URI not present on disk: {uri}")

    db = lancedb.connect(uri)
    if "research_library" not in db.table_names():
        pytest.skip("research_library table not yet built — run reindex-research.sh")

    tbl = db.open_table("research_library")
    # Pull one row; lance schema exposes vector as fixed-size list.
    sample = tbl.to_pandas().head(1)
    if sample.empty:
        pytest.skip("research_library table is empty")
    width = len(sample.iloc[0]["vector"])
    assert width == get_embedding_dim(), (
        f"Stored vector width {width} != config dim {get_embedding_dim()}. "
        "Re-run ~/.buildrunner/scripts/reindex-research.sh to rebuild."
    )
