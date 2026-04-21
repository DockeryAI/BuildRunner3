"""
BR3 Cluster — /retrieve endpoint
POST /retrieve — two-stage retrieval: vector search → cross-encoder rerank.

Sources:
  - research:          research library (LanceDB research_library table)
  - lockwood-code:     code codebase index (LanceDB codebase table)
  - lockwood-memory:   architecture notes + session state (SQLite memory_store)
  - decisions:         .buildrunner/decisions.log entries

Feature-gated: BR3_AUTO_CONTEXT=on. Flag off → returns empty results, zero side-effects.

Deploy: registered in node_semantic.py via app.include_router(retrieve_router)
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Feature gate
AUTO_CONTEXT_ENABLED = os.environ.get("BR3_AUTO_CONTEXT", "off").lower() == "on"

# Paths (Jimmy layout)
DECISIONS_LOG = os.environ.get(
    "DECISIONS_LOG",
    os.path.expanduser("~/.buildrunner/decisions.log"),
)
LANCE_DIR = os.environ.get("LANCE_DIR", os.path.expanduser("~/.lockwood/lancedb"))

retrieve_router = APIRouter()


# --- Request / Response models ---

class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5
    sources: Optional[list[str]] = None  # defaults to all 4 sources


class Snippet(BaseModel):
    source: str          # e.g. "research", "lockwood-code", "lockwood-memory", "decisions"
    source_url: str      # file path or identifier
    start_line: int = 0
    end_line: int = 0
    score: float
    text: str


class RetrieveResponse(BaseModel):
    query: str
    results: list[Snippet]
    total_candidates: int
    stage1_count: int
    stage2_count: int
    flag_active: bool


# --- Source implementations ---

def _search_research(query: str, limit: int = 20) -> list[dict]:
    """Stage 1: vector search over research_library LanceDB table."""
    try:
        import lancedb
        from sentence_transformers import SentenceTransformer
        db = lancedb.connect(LANCE_DIR)
        if "research_library" not in db.table_names():
            return []
        table = db.open_table("research_library")
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        vec = model.encode([query]).tolist()[0]
        results = table.search(vec).metric("cosine").limit(limit).to_pandas()
        hits = []
        for _, row in results.iterrows():
            dist = float(row.get("_distance", 1.0))
            hits.append({
                "source": "research",
                "source_url": row.get("source_file", ""),
                "start_line": 0,
                "end_line": 0,
                "score": round(max(0.0, 1.0 / (1.0 + dist)), 4),
                "text": str(row.get("text", ""))[:800],
            })
        return hits
    except Exception as e:
        logger.warning(f"research search error: {e}")
        return []


def _search_lockwood_code(query: str, limit: int = 20) -> list[dict]:
    """Stage 1: vector search over codebase LanceDB table."""
    try:
        import lancedb
        from sentence_transformers import SentenceTransformer
        db = lancedb.connect(LANCE_DIR)
        if "codebase" not in db.table_names():
            return []
        table = db.open_table("codebase")
        # Use nomic-embed or fallback to MiniLM
        embed_model = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        model = SentenceTransformer(embed_model, trust_remote_code=True)
        vec = model.encode([query]).tolist()[0]
        results = table.search(vec).metric("cosine").limit(limit).to_pandas()
        hits = []
        for _, row in results.iterrows():
            dist = float(row.get("_distance", 1.0))
            repo = row.get("repo", "")
            file_ = row.get("file", "")
            hits.append({
                "source": "lockwood-code",
                "source_url": f"{repo}/{file_}" if repo else file_,
                "start_line": int(row.get("start_line", 0)),
                "end_line": int(row.get("end_line", 0)),
                "score": round(max(0.0, 1.0 / (1.0 + dist)), 4),
                "text": str(row.get("text", ""))[:800],
            })
        return hits
    except Exception as e:
        logger.warning(f"lockwood-code search error: {e}")
        return []


def _search_lockwood_memory(query: str, limit: int = 10) -> list[dict]:
    """Stage 1: keyword + semantic search over architecture notes in SQLite."""
    try:
        from core.cluster.memory_store import search_notes
        notes = search_notes(query, project=None)
        hits = []
        q_lower = query.lower()
        for note in notes[:limit]:
            content = note.get("content", "")
            # Simple relevance: count query token matches
            tokens = re.findall(r'\w+', q_lower)
            match_count = sum(1 for t in tokens if t in content.lower())
            score = min(1.0, match_count / max(len(tokens), 1) * 0.8 + 0.1)
            hits.append({
                "source": "lockwood-memory",
                "source_url": f"memory:notes:{note.get('topic', '')}",
                "start_line": 0,
                "end_line": 0,
                "score": round(score, 4),
                "text": f"Topic: {note.get('topic', '')}\n{content[:600]}",
            })
        return hits
    except Exception as e:
        logger.warning(f"lockwood-memory search error: {e}")
        return []


def _search_decisions(query: str, limit: int = 10) -> list[dict]:
    """Stage 1: keyword search over decisions.log entries."""
    try:
        log_path = Path(DECISIONS_LOG)
        if not log_path.exists():
            return []
        # Never read *.log secrets — decisions.log is a structured plaintext log, not secret
        lines = log_path.read_text(errors="replace").splitlines()
        q_lower = query.lower()
        tokens = re.findall(r'\w+', q_lower)
        hits = []
        for i, line in enumerate(reversed(lines)):
            if not line.strip():
                continue
            line_lower = line.lower()
            match_count = sum(1 for t in tokens if t in line_lower)
            if match_count == 0:
                continue
            score = min(1.0, match_count / max(len(tokens), 1) * 0.9)
            hits.append({
                "source": "decisions",
                "source_url": f"decisions.log:L{len(lines) - i}",
                "start_line": len(lines) - i,
                "end_line": len(lines) - i,
                "score": round(score, 4),
                "text": line[:600],
            })
            if len(hits) >= limit:
                break
        return hits
    except Exception as e:
        logger.warning(f"decisions search error: {e}")
        return []


# --- Two-stage retrieval ---

VALID_SOURCES = {"research", "lockwood-code", "lockwood-memory", "decisions"}


def _stage1_search(query: str, sources: list[str], candidates_per_source: int = 20) -> list[dict]:
    """Gather Stage 1 candidates from all requested sources."""
    candidates = []
    for src in sources:
        if src == "research":
            candidates.extend(_search_research(query, limit=candidates_per_source))
        elif src == "lockwood-code":
            candidates.extend(_search_lockwood_code(query, limit=candidates_per_source))
        elif src == "lockwood-memory":
            candidates.extend(_search_lockwood_memory(query, limit=candidates_per_source))
        elif src == "decisions":
            candidates.extend(_search_decisions(query, limit=candidates_per_source))
    return candidates


def _stage2_rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """Stage 2: cross-encoder rerank. Falls back gracefully if reranker unavailable."""
    try:
        from core.cluster.reranker import rerank, ScoredResult
        scored_input = [
            ScoredResult(
                text=c["text"],
                score=c["score"],
                source=c["source"],
                source_url=c["source_url"],
                start_line=c.get("start_line", 0),
                end_line=c.get("end_line", 0),
            )
            for c in candidates
        ]
        reranked = rerank(query, scored_input, top_k=top_k)
        return [
            {
                "source": r.source,
                "source_url": r.source_url,
                "start_line": r.start_line,
                "end_line": r.end_line,
                "score": r.score,
                "text": r.text,
            }
            for r in reranked
        ]
    except Exception as e:
        logger.warning(f"Stage 2 rerank failed, using Stage 1 order: {e}")
        # Graceful fallback to Stage 1 scores
        return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]


# --- Route ---

@retrieve_router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(req: RetrieveRequest):
    """
    Two-stage retrieval endpoint.

    Stage 1: vector + keyword search across requested sources.
    Stage 2: cross-encoder rerank via bge-reranker-v2-m3.

    Returns top-K snippets with source URLs and line ranges.
    Flag off (BR3_AUTO_CONTEXT != on) → returns empty results.
    """
    if not AUTO_CONTEXT_ENABLED:
        return RetrieveResponse(
            query=req.query,
            results=[],
            total_candidates=0,
            stage1_count=0,
            stage2_count=0,
            flag_active=False,
        )

    # Validate sources
    requested_sources = req.sources or list(VALID_SOURCES)
    sources = [s for s in requested_sources if s in VALID_SOURCES]
    if not sources:
        sources = list(VALID_SOURCES)

    # Stage 1
    candidates = _stage1_search(req.query, sources, candidates_per_source=20)
    stage1_count = len(candidates)

    # Stage 2
    top_results = _stage2_rerank(req.query, candidates, top_k=req.top_k)

    snippets = [
        Snippet(
            source=r["source"],
            source_url=r["source_url"],
            start_line=r.get("start_line", 0),
            end_line=r.get("end_line", 0),
            score=r["score"],
            text=r["text"],
        )
        for r in top_results
    ]

    return RetrieveResponse(
        query=req.query,
        results=snippets,
        total_candidates=stage1_count,
        stage1_count=stage1_count,
        stage2_count=len(snippets),
        flag_active=True,
    )


@retrieve_router.get("/rerank/health")
async def rerank_health():
    """Health check for the reranker subsystem."""
    from core.cluster.reranker import reranker_health
    return reranker_health()
