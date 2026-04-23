"""
semantic_cache.py — Semantic answer cache backed by sqlite-vec.

Stores Claude/LLM responses keyed by (model, method_name, prompt_embedding,
normalized_prompt_hash) so the same prompt family can be served from cache
without paying for a redundant API call.

DB location: $HOME/.buildrunner/state/answer_cache.db  (NOT in repo)
Table:        answer_cache (created on first use)

Cache key design:
    - model:               prevents cross-model response bleed
    - method_name:         separates review, summarize, classify, etc.
    - prompt_embedding:    768-d vector for semantic similarity lookup
    - prompt_hash:         MD5 of normalized prompt — exact-match guard to
                           prevent near-miss false positives at high similarity

Warm-up mode:
    During the first N days (default 7), hits are logged but NOT served —
    the cache accumulates signal before trusting its own hits.

Admin CLI (run as module):
    python3 -m core.cluster.below.semantic_cache inspect
    python3 -m core.cluster.below.semantic_cache clear
    python3 -m core.cluster.below.semantic_cache stats

Usage:
    from core.cluster.below.semantic_cache import SemanticCache

    cache = SemanticCache()
    hit = cache.lookup("claude-opus-4-7", "summarize", prompt_text)
    if hit is None:
        answer = call_claude(prompt_text)
        cache.store("claude-opus-4-7", "summarize", prompt_text, answer)
    else:
        answer = hit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = Path.home() / ".buildrunner" / "state" / "answer_cache.db"
DEFAULT_SIMILARITY_THRESHOLD: float = 0.95
DEFAULT_TTL_DAYS: int = 30
DEFAULT_WARMUP_DAYS: int = 7

EMBED_DIM: int = 768


# ---------------------------------------------------------------------------
# SemanticCache
# ---------------------------------------------------------------------------


class SemanticCache:
    """
    Semantic answer cache using sqlite-vec for approximate nearest-neighbour lookup.

    Args:
        db_path:    Path to the SQLite database file (created if absent).
        threshold:  Cosine similarity threshold for a cache hit (default 0.95).
        ttl_days:   Entry TTL in days; older entries are evicted on lookup.
        warmup_days: Number of days to log-only before serving hits.
    """

    def __init__(
        self,
        db_path: Path = _DEFAULT_DB_PATH,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        ttl_days: int = DEFAULT_TTL_DAYS,
        warmup_days: int = DEFAULT_WARMUP_DAYS,
    ) -> None:
        self.db_path = db_path
        self.threshold = threshold
        self.ttl_days = ttl_days
        self.warmup_days = warmup_days
        self._conn = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup(
        self,
        model: str,
        method: str,
        prompt: str,
        *,
        skip_cache: bool = False,
    ) -> Optional[str]:
        """
        Look up a cached answer for (model, method, prompt).

        Returns:
            Cached answer string if a hit is found above threshold AND the
            warm-up period has passed. Otherwise None.

        Args:
            model:       LLM model name (e.g. "claude-opus-4-7").
            method:      Method tag (e.g. "summarize", "classify", "review").
            prompt:      The full prompt text.
            skip_cache:  If True, always returns None (exclusion list enforcement).
        """
        if skip_cache:
            return None

        try:
            self._ensure_init()
            vec = self._embed(prompt)
            prompt_hash = _hash_prompt(prompt)
            return self._query(model, method, vec, prompt_hash)
        except Exception as exc:  # noqa: BLE001
            logger.debug("semantic_cache.lookup failed: %s", exc)
            return None

    def store(
        self,
        model: str,
        method: str,
        prompt: str,
        answer: str,
        *,
        skip_cache: bool = False,
    ) -> None:
        """
        Store a (model, method, prompt, answer) entry in the cache.

        Args:
            model:      LLM model name.
            method:     Method tag.
            prompt:     The prompt text.
            answer:     The LLM response to cache.
            skip_cache: If True, does nothing (exclusion list enforcement).
        """
        if skip_cache:
            return

        try:
            self._ensure_init()
            vec = self._embed(prompt)
            prompt_hash = _hash_prompt(prompt)
            self._insert(model, method, vec, prompt_hash, answer)
        except Exception as exc:  # noqa: BLE001
            logger.debug("semantic_cache.store failed: %s", exc)

    # ------------------------------------------------------------------
    # Admin CLI helpers (also callable from code)
    # ------------------------------------------------------------------

    def inspect(self, limit: int = 20) -> list[dict]:
        """Return the most recent cache entries."""
        try:
            self._ensure_init()
            cur = self._conn.execute(
                "SELECT model, method, prompt_hash, stored_at, answer "
                "FROM answer_cache ORDER BY stored_at DESC LIMIT ?",
                (limit,),
            )
            rows = []
            for row in cur.fetchall():
                rows.append({
                    "model": row[0],
                    "method": row[1],
                    "prompt_hash": row[2],
                    "stored_at": row[3],
                    "answer_preview": row[4][:80] if row[4] else "",
                })
            return rows
        except Exception as exc:
            logger.debug("inspect failed: %s", exc)
            return []

    def clear(self) -> int:
        """Delete all entries. Returns count deleted."""
        try:
            self._ensure_init()
            cur = self._conn.execute("DELETE FROM answer_cache")
            self._conn.commit()
            return cur.rowcount
        except Exception as exc:
            logger.debug("clear failed: %s", exc)
            return 0

    def stats(self) -> dict:
        """Return cache statistics."""
        try:
            self._ensure_init()
            total = self._conn.execute("SELECT COUNT(*) FROM answer_cache").fetchone()[0]
            by_model = self._conn.execute(
                "SELECT model, COUNT(*) FROM answer_cache GROUP BY model"
            ).fetchall()
            by_method = self._conn.execute(
                "SELECT method, COUNT(*) FROM answer_cache GROUP BY method"
            ).fetchall()
            oldest = self._conn.execute(
                "SELECT MIN(stored_at) FROM answer_cache"
            ).fetchone()[0]
            return {
                "total_entries": total,
                "by_model": dict(by_model),
                "by_method": dict(by_method),
                "oldest_entry": oldest,
                "db_path": str(self.db_path),
                "threshold": self.threshold,
                "ttl_days": self.ttl_days,
                "warmup_days": self.warmup_days,
            }
        except Exception as exc:
            logger.debug("stats failed: %s", exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        # WAL + busy_timeout to handle concurrent cache writers without locking errors
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._create_table()
        self._initialized = True

    def _create_table(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS answer_cache (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                model       TEXT    NOT NULL,
                method      TEXT    NOT NULL,
                prompt_hash TEXT    NOT NULL,
                embedding   BLOB    NOT NULL,
                answer      TEXT    NOT NULL,
                stored_at   REAL    NOT NULL,
                UNIQUE(model, method, prompt_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_answer_cache_model_method
                ON answer_cache (model, method);
        """)
        self._conn.commit()

    def _embed(self, prompt: str) -> list[float]:
        """Embed prompt via Below. Raises BelowOfflineError on failure."""
        from core.cluster.below.embed import embed_batch
        vecs = embed_batch([prompt])
        return vecs[0]

    def _query(
        self,
        model: str,
        method: str,
        vec: list[float],
        prompt_hash: str,
    ) -> Optional[str]:
        """Find the nearest cached entry for (model, method) and return answer if above threshold."""
        import struct

        # Evict expired entries first
        self._evict_expired()

        # Retrieve all entries for (model, method)
        cur = self._conn.execute(
            "SELECT prompt_hash, embedding, answer, stored_at FROM answer_cache "
            "WHERE model = ? AND method = ?",
            (model, method),
        )
        rows = cur.fetchall()
        if not rows:
            return None

        best_score = -1.0
        best_answer: Optional[str] = None
        best_stored_at: Optional[float] = None


        for row in rows:
            stored_hash = row[0]
            blob = row[1]
            answer = row[2]
            stored_at = row[3]

            # Deserialize embedding
            n = len(blob) // 4
            stored_vec = list(struct.unpack(f"{n}f", blob))
            if len(stored_vec) != EMBED_DIM:
                continue

            # Cosine similarity
            score = _cosine_similarity(vec, stored_vec)

            # Exact-match bonus: if hashes match, treat as perfect hit
            if stored_hash == prompt_hash:
                score = 1.0

            if score > best_score:
                best_score = score
                best_answer = answer
                best_stored_at = stored_at

        if best_score < self.threshold:
            return None

        # Warm-up guard: log but don't serve during warm-up period
        if best_stored_at is not None:
            entry_age_days = (time.time() - best_stored_at) / 86400
            cache_age_days = (time.time() - self._cache_created_at()) / 86400
            if cache_age_days < self.warmup_days:
                logger.info(
                    "semantic_cache: warm-up mode — hit at %.3f (model=%s method=%s) — NOT served",
                    best_score, model, method,
                )
                return None

        logger.debug(
            "semantic_cache: HIT score=%.3f model=%s method=%s",
            best_score, model, method,
        )
        return best_answer

    def _insert(
        self,
        model: str,
        method: str,
        vec: list[float],
        prompt_hash: str,
        answer: str,
    ) -> None:
        import struct
        blob = struct.pack(f"{len(vec)}f", *vec)
        now = time.time()
        self._conn.execute(
            "INSERT OR REPLACE INTO answer_cache "
            "(model, method, prompt_hash, embedding, answer, stored_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (model, method, prompt_hash, blob, answer, now),
        )
        self._conn.commit()

    def _evict_expired(self) -> None:
        cutoff = time.time() - self.ttl_days * 86400
        self._conn.execute(
            "DELETE FROM answer_cache WHERE stored_at < ?", (cutoff,)
        )
        self._conn.commit()

    def _cache_created_at(self) -> float:
        """Return timestamp of oldest entry (proxy for cache creation time)."""
        row = self._conn.execute("SELECT MIN(stored_at) FROM answer_cache").fetchone()
        if row and row[0]:
            return float(row[0])
        return time.time()  # empty cache → treat as new


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _hash_prompt(prompt: str) -> str:
    """Normalize and hash the prompt for exact-match guard."""
    normalized = " ".join(prompt.split()).lower()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Admin CLI
# ---------------------------------------------------------------------------


def _main() -> None:
    parser = argparse.ArgumentParser(
        prog="below-cache",
        description="Semantic answer cache admin CLI",
    )
    parser.add_argument(
        "command",
        choices=["inspect", "clear", "stats"],
        help="Action to perform",
    )
    parser.add_argument(
        "--db",
        default=str(_DEFAULT_DB_PATH),
        help=f"Cache DB path (default: {_DEFAULT_DB_PATH})",
    )
    args = parser.parse_args()

    cache = SemanticCache(db_path=Path(args.db))

    if args.command == "inspect":
        rows = cache.inspect()
        if not rows:
            print("Cache is empty.")
        else:
            for row in rows:
                print(json.dumps(row))

    elif args.command == "clear":
        n = cache.clear()
        print(f"Cleared {n} entries from {args.db}")

    elif args.command == "stats":
        s = cache.stats()
        print(json.dumps(s, indent=2))


if __name__ == "__main__":
    _main()
