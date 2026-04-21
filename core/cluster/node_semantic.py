"""
BR3 Cluster — Node 1: Lockwood (Memory)
Semantic search, symbol graph, impact analysis across all repos.

Run: uvicorn core.cluster.node_semantic:app --host 0.0.0.0 --port 8100
"""

import os
import time
import hashlib
import json
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel

from core.cluster.base_service import create_app

# --- Config ---
REPOS_DIR = os.environ.get("REPOS_DIR", os.path.expanduser("~/repos"))
CHROMA_DIR = os.environ.get("CHROMA_DIR", os.path.expanduser("~/.lockwood/chromadb"))
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-ai/CodeRankEmbed")
INDEX_INTERVAL = int(os.environ.get("INDEX_INTERVAL", "60"))  # seconds between re-index checks
DISABLE_INDEXER = os.environ.get("DISABLE_INDEXER", "true").lower() in ("true", "1", "yes")

# --- App ---
app = create_app(role="semantic-search", version="0.1.0")

# --- Include Intelligence Service routes (intel + deals share this port) ---
from core.cluster.node_intelligence import router as intel_router, intel_startup
app.include_router(intel_router)

# --- Include retrieve routes (Phase 10: auto-context, flag-gated) ---
from api.routes.retrieve import retrieve_router
app.include_router(retrieve_router)

@app.on_event("startup")
async def _intel_startup():
    await intel_startup()


# --- Lazy-loaded globals (heavy imports deferred) ---
_db = None
_table = None
_embed_model = None
_file_hashes: dict[str, str] = {}
_indexing = False
_last_index_time = 0.0
_index_stats = {"total_files": 0, "total_chunks": 0, "last_duration": 0.0}

LANCE_DIR = os.environ.get("LANCE_DIR", os.path.expanduser("~/.lockwood/lancedb"))
RESEARCH_DIR = os.environ.get("RESEARCH_DIR", os.path.expanduser("~/repos/research-library"))
RESEARCH_EMBED_MODEL = os.environ.get("RESEARCH_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RESEARCH_INDEX_INTERVAL = int(os.environ.get("RESEARCH_INDEX_INTERVAL", "300"))


def _get_db():
    """Get LanceDB connection. Disk-based — no HNSW in memory."""
    global _db, _table
    if _db is None:
        import lancedb
        os.makedirs(LANCE_DIR, exist_ok=True)
        _db = lancedb.connect(LANCE_DIR)
        if "codebase" in _db.table_names():
            _table = _db.open_table("codebase")
        else:
            _table = None
    return _db, _table


def _get_or_create_table(sample_dim: int):
    """Create the table on first insert."""
    global _table
    import pyarrow as pa
    db, _ = _get_db()
    if _table is None or "codebase" not in db.table_names():
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("text", pa.string()),
            pa.field("repo", pa.string()),
            pa.field("file", pa.string()),
            pa.field("start_line", pa.int32()),
            pa.field("end_line", pa.int32()),
            pa.field("language", pa.string()),
            pa.field("block_name", pa.string()),
            pa.field("block_type", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), sample_dim)),
        ])
        _table = db.create_table("codebase", schema=schema, mode="overwrite")
    return _table


_plan_table = None
_research_table = None
_research_embed_model = None
_research_file_hashes: dict[str, str] = {}
_research_indexing = False
_research_last_index_time = 0.0
_research_dir_mtime = 0.0
_research_stats = {"total_files": 0, "total_chunks": 0, "last_duration": 0.0}


def _get_or_create_plan_table(sample_dim: int):
    """Create or open the plan_outcomes LanceDB table for semantic plan search."""
    global _plan_table
    import pyarrow as pa
    db, _ = _get_db()
    if "plan_outcomes" in db.table_names():
        _plan_table = db.open_table("plan_outcomes")
        return _plan_table
    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("plan_text", pa.string()),
        pa.field("project", pa.string()),
        pa.field("build_name", pa.string()),
        pa.field("phase", pa.string()),
        pa.field("outcome", pa.string()),
        pa.field("accuracy_pct", pa.float32()),
        pa.field("drift_notes", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), sample_dim)),
    ])
    _plan_table = db.create_table("plan_outcomes", schema=schema, mode="overwrite")
    return _plan_table


def embed_plan(plan_id: int, project: str, build_name: str, phase: str,
               plan_text: str, outcome: str, accuracy_pct: float = None,
               drift_notes: str = None):
    """Embed a plan's text into LanceDB for semantic retrieval."""
    embedder = _get_embedder()
    embed_dim = embedder.get_sentence_embedding_dimension()
    table = _get_or_create_plan_table(embed_dim)
    embedding = embedder.encode([plan_text]).tolist()[0]
    table.add([{
        "id": f"plan:{plan_id}",
        "plan_text": plan_text[:5000],
        "project": project,
        "build_name": build_name,
        "phase": phase,
        "outcome": outcome,
        "accuracy_pct": float(accuracy_pct) if accuracy_pct is not None else 0.0,
        "drift_notes": drift_notes or "",
        "vector": embedding,
    }])


def search_similar_plans(query: str, project: str = None, limit: int = 3) -> list[dict]:
    """Vector search for semantically similar past plans. Returns top N with outcome + accuracy + drift."""
    embedder = _get_embedder()
    db, _ = _get_db()
    if "plan_outcomes" not in db.table_names():
        return []
    table = db.open_table("plan_outcomes")
    query_embedding = embedder.encode([query]).tolist()[0]

    try:
        search_query = table.search(query_embedding).metric("cosine").limit(limit * 2)
        if project:
            search_query = search_query.where(f"project = '{project}'")
        results = search_query.to_pandas()
    except Exception:
        return []

    hits = []
    for _, row in results.iterrows():
        distance = row.get("_distance", 1.0)
        hits.append({
            "plan_id": row.get("id", ""),
            "project": row.get("project", ""),
            "build_name": row.get("build_name", ""),
            "phase": row.get("phase", ""),
            "outcome": row.get("outcome", ""),
            "accuracy_pct": float(row.get("accuracy_pct", 0)),
            "drift_notes": row.get("drift_notes", ""),
            "plan_text": str(row.get("plan_text", ""))[:300],
            "score": round(max(0, 1 / (1 + distance)), 4),
        })
        if len(hits) >= limit:
            break

    return hits


def _get_embedder():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(EMBED_MODEL, trust_remote_code=True)
    return _embed_model


def _get_research_embedder():
    """Lazy-load text-optimized embedding model for research (separate from code embedder)."""
    global _research_embed_model
    if _research_embed_model is None:
        from sentence_transformers import SentenceTransformer
        _research_embed_model = SentenceTransformer(RESEARCH_EMBED_MODEL, trust_remote_code=True)
    return _research_embed_model


def _get_or_create_research_table(sample_dim: int):
    """Create or open the research_library LanceDB table."""
    global _research_table
    import pyarrow as pa
    db, _ = _get_db()
    if "research_library" in db.table_names():
        _research_table = db.open_table("research_library")
        return _research_table
    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("title", pa.string()),
        pa.field("section", pa.string()),
        pa.field("domain", pa.string()),
        pa.field("subjects", pa.string()),
        pa.field("priority", pa.string()),
        pa.field("techniques", pa.string()),
        pa.field("source_file", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), sample_dim)),
    ])
    _research_table = db.create_table("research_library", schema=schema, mode="overwrite")
    return _research_table


def run_research_index():
    """Index research library docs into LanceDB. Uses directory mtime to skip when unchanged."""
    global _research_file_hashes, _research_indexing, _research_last_index_time
    global _research_dir_mtime, _research_stats, _research_table

    if _research_indexing:
        print("Research index: already running, skipping")
        return
    _research_indexing = True
    start = time.time()
    print("Research index: starting...")

    try:
        from core.cluster.research_chunker import discover_research_docs, chunk_research_doc

        research_path = Path(RESEARCH_DIR)
        if not research_path.exists():
            print(f"Research dir not found: {RESEARCH_DIR}")
            return

        # Directory mtime check — skip entirely if unchanged
        docs_path = research_path / "docs"
        if docs_path.exists():
            current_mtime = _get_dir_mtime(docs_path)
            if current_mtime == _research_dir_mtime and _research_file_hashes:
                _research_last_index_time = time.time()  # update even on no-change check
                return  # nothing changed
            _research_dir_mtime = current_mtime

        files = discover_research_docs(RESEARCH_DIR)

        new_hashes = {}
        chunks_to_add = []

        for f in files:
            fh = file_hash(f)
            key = str(f)
            new_hashes[key] = fh
            if _research_file_hashes.get(key) == fh:
                continue
            chunks = chunk_research_doc(f)
            chunks_to_add.extend(chunks)

        if chunks_to_add:
            print(f"Research index: {len(chunks_to_add)} chunks from {len(files)} docs...")
            # Only load the embedding model when we actually have chunks to embed
            embedder = _get_research_embedder()
            embed_dim = embedder.get_sentence_embedding_dimension()

            if not _research_file_hashes:
                table = _get_or_create_research_table(embed_dim)
            else:
                db, _ = _get_db()
                if "research_library" in db.table_names():
                    table = db.open_table("research_library")
                else:
                    table = _get_or_create_research_table(embed_dim)

            batch_size = 16  # smaller batches to yield GIL for health checks
            rows = []
            for i in range(0, len(chunks_to_add), batch_size):
                batch = chunks_to_add[i:i + batch_size]
                texts = [c["text"] for c in batch]
                try:
                    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()
                    for j, c in enumerate(batch):
                        meta = c.get("metadata", {})
                        rows.append({
                            "id": c["id"],
                            "text": c["text"][:5000],
                            "title": meta.get("title", ""),
                            "section": meta.get("section", ""),
                            "domain": meta.get("domain", ""),
                            "subjects": meta.get("subjects", ""),
                            "priority": meta.get("priority", ""),
                            "techniques": meta.get("techniques", ""),
                            "source_file": meta.get("source_file", ""),
                            "vector": embeddings[j],
                        })
                except Exception as e:
                    print(f"  Research batch error at {i}: {e}")
                # Yield GIL between batches so uvicorn can serve health checks
                time.sleep(0.1)

            if rows:
                try:
                    if not _research_file_hashes:
                        table = _get_or_create_research_table(embed_dim)
                    table.add(rows)
                    _research_table = table
                    print(f"  Added {len(rows)} research chunks to LanceDB")
                except Exception as e:
                    print(f"  Research LanceDB insert error: {e}")

        _research_file_hashes = new_hashes
        _research_last_index_time = time.time()
        db, _ = _get_db()
        chunk_count = 0
        if "research_library" in db.table_names():
            chunk_count = db.open_table("research_library").count_rows()
        _research_stats = {
            "total_files": len(files),
            "total_chunks": chunk_count,
            "last_duration": round(time.time() - start, 1),
            "changed_files": len(chunks_to_add),
        }
    finally:
        _research_indexing = False


def _get_dir_mtime(dir_path: Path) -> float:
    """Get the max mtime across all files in a directory (recursive)."""
    max_mtime = 0.0
    try:
        for p in dir_path.rglob("*.md"):
            try:
                mt = p.stat().st_mtime
                if mt > max_mtime:
                    max_mtime = mt
            except OSError:
                continue
    except Exception:
        pass
    return max_mtime


def search_research(query: str, domain: str = None, limit: int = 5) -> list[dict]:
    """Semantic search over research library chunks."""
    embedder = _get_research_embedder()
    db, _ = _get_db()
    if "research_library" not in db.table_names():
        return []
    table = db.open_table("research_library")
    query_embedding = embedder.encode([query]).tolist()[0]

    try:
        search_query = table.search(query_embedding).metric("cosine").limit(limit * 2)
        if domain:
            search_query = search_query.where(f"domain LIKE '%{domain}%'")
        results = search_query.to_pandas()
    except Exception:
        return []

    hits = []
    seen_sections = set()
    for _, row in results.iterrows():
        section_key = f"{row.get('source_file', '')}:{row.get('section', '')}"
        if section_key in seen_sections:
            continue
        seen_sections.add(section_key)
        distance = row.get("_distance", 1.0)
        hits.append({
            "id": row.get("id", ""),
            "title": row.get("title", ""),
            "section": row.get("section", ""),
            "domain": row.get("domain", ""),
            "subjects": row.get("subjects", ""),
            "priority": row.get("priority", ""),
            "source_file": row.get("source_file", ""),
            "score": round(max(0, 1 / (1 + distance)), 4),
            "snippet": str(row.get("text", ""))[:400],
        })
        if len(hits) >= limit:
            break
    return hits


# --- File Discovery ---
SKIP_DIRS = {
    ".git", "node_modules", ".next", "dist", "build", ".buildrunner",
    "__pycache__", ".venv", "venv", ".playwright-mcp", ".cache",
    "coverage", ".nyc_output", ".turbo",
}
CODE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".py", ".md", ".yaml", ".yml",
    ".json", ".sql", ".css", ".html", ".sh", ".toml",
}


def discover_files(repos_dir: str) -> list[Path]:
    """Find all indexable files across all repos."""
    files = []
    for repo_dir in Path(repos_dir).iterdir():
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        for path in repo_dir.rglob("*"):
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            if path.is_file() and path.suffix in CODE_EXTENSIONS:
                # Skip files > 100KB
                try:
                    if path.stat().st_size <= 100_000:
                        files.append(path)
                except OSError:
                    continue
    return files


def file_hash(path: Path) -> str:
    """Quick hash to detect changes."""
    try:
        stat = path.stat()
        return hashlib.md5(f"{stat.st_mtime}:{stat.st_size}".encode()).hexdigest()
    except OSError:
        return ""


# --- AST-Aware Chunking ---
# Research: AST chunking has 65% better recall than fixed-size (RepoEval benchmark).
# Prepending metadata (file path, function name) is critical for embedding quality.

LANG_MAP = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".css": "css", ".html": "html", ".sh": "bash",
    ".sql": "sql", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
}

# AST node types that represent meaningful code blocks
BLOCK_TYPES = {
    "function_definition", "function_declaration", "arrow_function",
    "method_definition", "class_definition", "class_declaration",
    "interface_declaration", "type_alias_declaration", "enum_declaration",
    "export_statement", "import_statement", "lexical_declaration",
    "expression_statement", "if_statement", "for_statement",
    "decorated_definition",
}


def _get_parser(lang: str):
    """Get tree-sitter parser for a language."""
    try:
        from tree_sitter_languages import get_parser
        return get_parser(lang)
    except Exception:
        return None


def _extract_ast_blocks(content: bytes, lang: str, max_chunk: int = 2000) -> list[dict]:
    """Extract semantic blocks from AST. Returns list of {start_line, end_line, name, type}."""
    parser = _get_parser(lang)
    if not parser:
        return []

    try:
        tree = parser.parse(content)
    except Exception:
        return []

    blocks = []

    def walk(node, depth=0):
        if node.type in BLOCK_TYPES:
            text_len = node.end_byte - node.start_byte
            if text_len <= max_chunk:
                # Extract name if available
                name = ""
                for child in node.children:
                    if child.type in ("identifier", "property_identifier", "name"):
                        name = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                        break
                blocks.append({
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "name": name,
                    "type": node.type,
                })
            else:
                # Block too large — recurse into children
                for child in node.children:
                    walk(child, depth + 1)
        else:
            for child in node.children:
                walk(child, depth + 1)

    walk(tree.root_node)
    return blocks


def chunk_file(path: Path, chunk_size: int = 2000) -> list[dict]:
    """AST-aware chunking with metadata prepending. Falls back to line-based for non-code files."""
    try:
        content = path.read_text(errors="replace")
    except Exception:
        return []

    if not content.strip():
        return []

    repos_path = Path(REPOS_DIR).resolve()
    resolved = path.resolve()
    repo_name = resolved.parts[len(repos_path.parts)]
    rel_path = str(resolved.relative_to(repos_path / repo_name))
    lang = LANG_MAP.get(path.suffix)
    lines = content.split("\n")

    chunks = []
    chunk_counter = 0

    # Try AST chunking for supported languages
    ast_blocks = []
    if lang and lang not in ("json", "yaml", "css"):
        ast_blocks = _extract_ast_blocks(content.encode("utf-8"), lang, max_chunk=chunk_size)

    if ast_blocks:
        # AST-aware: chunk at semantic boundaries
        covered_lines = set()
        for block in ast_blocks:
            block_lines = lines[block["start_line"] - 1:block["end_line"]]
            block_text = "\n".join(block_lines)

            # Prepend metadata for embedding quality
            metadata_prefix = f"File: {repo_name}/{rel_path}\n"
            if block["name"]:
                metadata_prefix += f"{block['type'].replace('_', ' ').title()}: {block['name']}\n"
            metadata_prefix += "---\n"

            chunks.append({
                "id": f"{repo_name}/{rel_path}:c{chunk_counter}",
                "text": metadata_prefix + block_text,
                "metadata": {
                    "repo": repo_name,
                    "file": rel_path,
                    "start_line": block["start_line"],
                    "end_line": block["end_line"],
                    "language": lang,
                    "block_name": block.get("name", ""),
                    "block_type": block.get("type", ""),
                },
            })
            chunk_counter += 1
            covered_lines.update(range(block["start_line"], block["end_line"] + 1))

        # Catch uncovered lines (imports, top-level code, comments)
        uncovered = []
        for i, line in enumerate(lines, 1):
            if i not in covered_lines and line.strip():
                uncovered.append((i, line))

        if uncovered:
            uncovered_text = "\n".join(line for _, line in uncovered)
            if len(uncovered_text.strip()) > 30:
                metadata_prefix = f"File: {repo_name}/{rel_path}\nTop-level code and imports\n---\n"
                chunks.append({
                    "id": f"{repo_name}/{rel_path}:c{chunk_counter}",
                    "text": metadata_prefix + uncovered_text[:chunk_size],
                    "metadata": {
                        "repo": repo_name,
                        "file": rel_path,
                        "start_line": uncovered[0][0],
                        "end_line": uncovered[-1][0],
                        "language": lang,
                        "block_name": "",
                        "block_type": "top_level",
                    },
                })
                chunk_counter += 1
    else:
        # Fallback: line-based chunking with metadata for non-code files
        current_chunk = []
        current_len = 0
        chunk_start_line = 1

        for i, line in enumerate(lines, 1):
            current_chunk.append(line)
            current_len += len(line) + 1

            if current_len >= chunk_size:
                metadata_prefix = f"File: {repo_name}/{rel_path}\nLines {chunk_start_line}-{i}\n---\n"
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "id": f"{repo_name}/{rel_path}:c{chunk_counter}",
                    "text": metadata_prefix + chunk_text,
                    "metadata": {
                        "repo": repo_name,
                        "file": rel_path,
                        "start_line": chunk_start_line,
                        "end_line": i,
                        "language": path.suffix.lstrip("."),
                    },
                })
                chunk_counter += 1
                current_chunk = current_chunk[-3:]
                current_len = sum(len(l) + 1 for l in current_chunk)
                chunk_start_line = max(1, i - 2)

        if current_chunk and len("\n".join(current_chunk).strip()) > 30:
            metadata_prefix = f"File: {repo_name}/{rel_path}\nLines {chunk_start_line}-{len(lines)}\n---\n"
            chunks.append({
                "id": f"{repo_name}/{rel_path}:c{chunk_counter}",
                "text": metadata_prefix + "\n".join(current_chunk),
                "metadata": {
                    "repo": repo_name,
                    "file": rel_path,
                    "start_line": chunk_start_line,
                    "end_line": len(lines),
                    "language": path.suffix.lstrip("."),
                },
            })

    return chunks


# --- Indexing (LanceDB — disk-based, no memory pressure) ---
def run_index():
    """Index all files, skip unchanged ones. Uses LanceDB for disk-based vector storage."""
    global _file_hashes, _indexing, _last_index_time, _index_stats, _table
    if _indexing:
        return
    _indexing = True
    start = time.time()

    try:
        embedder = _get_embedder()
        embed_dim = embedder.get_sentence_embedding_dimension()
        files = discover_files(REPOS_DIR)

        new_hashes = {}
        chunks_to_add = []

        for f in files:
            fh = file_hash(f)
            key = str(f)
            new_hashes[key] = fh

            if _file_hashes.get(key) == fh:
                continue  # unchanged

            chunks = chunk_file(f)
            for chunk in chunks:
                chunks_to_add.append(chunk)

        # Deduplicate IDs
        seen_ids = set()
        unique_chunks = []
        for c in chunks_to_add:
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                unique_chunks.append(c)
        chunks_to_add = unique_chunks

        if chunks_to_add:
            print(f"Indexing {len(chunks_to_add)} chunks from {len(files)} files...")

            # On first run or full reindex, recreate the table
            if not _file_hashes:
                table = _get_or_create_table(embed_dim)
            else:
                _, table = _get_db()
                if table is None:
                    table = _get_or_create_table(embed_dim)

            # Process in small batches: embed and insert immediately to avoid OOM
            batch_size = 32
            total_inserted = 0
            for i in range(0, len(chunks_to_add), batch_size):
                batch = chunks_to_add[i:i + batch_size]
                texts = [c["text"] for c in batch]
                try:
                    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()
                    rows = []
                    for j, c in enumerate(batch):
                        meta = c.get("metadata", {})
                        rows.append({
                            "id": c["id"],
                            "text": c["text"][:5000],  # cap text to save disk
                            "repo": meta.get("repo", ""),
                            "file": meta.get("file", ""),
                            "start_line": meta.get("start_line", 0),
                            "end_line": meta.get("end_line", 0),
                            "language": meta.get("language", ""),
                            "block_name": meta.get("block_name", ""),
                            "block_type": meta.get("block_type", ""),
                            "vector": embeddings[j],
                        })
                    # Insert immediately after embedding
                    table.add(rows)
                    total_inserted += len(rows)
                    if (i // batch_size) % 50 == 0:
                        print(f"  Progress: {total_inserted}/{len(chunks_to_add)} chunks")
                except Exception as e:
                    print(f"  Batch error at {i}: {e}")

            _table = table
            print(f"  Indexed {total_inserted} chunks to LanceDB")

        _file_hashes = new_hashes
        _last_index_time = time.time()
        _, table = _get_db()
        chunk_count = table.count_rows() if table else 0
        _index_stats = {
            "total_files": len(files),
            "total_chunks": chunk_count,
            "last_duration": round(time.time() - start, 1),
            "changed_files": len(chunks_to_add),
        }
    finally:
        _indexing = False


# --- Background indexer ---
def _background_indexer():
    """Periodically re-index code and ingest memory data."""
    while True:
        try:
            run_index()
        except Exception as e:
            print(f"Index error: {e}")

        # Ingest memory data from repos
        try:
            _ingest_memory()
        except Exception as e:
            print(f"Memory ingest error: {e}")

        time.sleep(INDEX_INTERVAL)


def _ingest_memory():
    """Pull commits, test results, and log patterns from repos."""
    from core.cluster.memory_store import (
        ingest_commits, ingest_log_patterns
    )

    repos_path = Path(REPOS_DIR)
    for repo_dir in repos_path.iterdir():
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue

        # Ingest commits
        try:
            ingest_commits(repo_dir.name, str(repo_dir), count=50)
        except Exception:
            pass

        # Ingest log patterns from .buildrunner/ logs
        br_dir = repo_dir / ".buildrunner"
        if br_dir.exists():
            for log_name in ["browser.log", "supabase.log", "device.log", "query.log"]:
                log_path = br_dir / log_name
                if log_path.exists():
                    try:
                        ingest_log_patterns(log_name, str(log_path))
                    except Exception:
                        pass


def _init_research_stats():
    """Load stats from existing research_library table on startup.
    Does NOT populate file hashes — the first reindex will do a full scan
    to ensure new files added while Lockwood was down are always detected."""
    global _research_stats
    try:
        db, _ = _get_db()
        if "research_library" in db.table_names():
            table = db.open_table("research_library")
            count = table.count_rows()
            if count > 0:
                from core.cluster.research_chunker import discover_research_docs
                files = discover_research_docs(RESEARCH_DIR)
                _research_stats = {
                    "total_files": len(files),
                    "total_chunks": count,
                    "last_duration": 0.0,
                    "changed_files": 0,
                }
                # Don't populate _research_file_hashes — let first reindex scan all files
                # This ensures any files added while Lockwood was down get indexed
                print(f"Research index loaded: {count} chunks, {len(files)} docs on disk (full scan on first reindex)")
    except Exception as e:
        print(f"Research stats init: {e}")


def _background_research_indexer():
    """Periodically re-index research library (separate from code indexer, longer interval)."""
    _init_research_stats()
    # Delay first run so uvicorn can serve health checks during model load
    time.sleep(15)
    while True:
        try:
            run_research_index()
        except Exception as e:
            print(f"Research index error: {e}")
        time.sleep(RESEARCH_INDEX_INTERVAL)


@app.on_event("startup")
async def startup():
    if DISABLE_INDEXER:
        print("DISABLE_INDEXER=true — skipping embedding model and background indexer")
        # Still start research indexer — it uses its own model and is independent
        t2 = threading.Thread(target=_background_research_indexer, daemon=True)
        t2.start()
        print("Research indexer started (independent of code indexer)")
        return
    t = threading.Thread(target=_background_indexer, daemon=True)
    t.start()
    t2 = threading.Thread(target=_background_research_indexer, daemon=True)
    t2.start()


# --- API Models ---
class SearchRequest(BaseModel):
    query: str
    n_results: int = 10
    repo: Optional[str] = None


class ImpactRequest(BaseModel):
    file_path: str
    repo: Optional[str] = None


# --- API Endpoints ---
@app.post("/api/search")
async def search(req: SearchRequest):
    """Hybrid search: semantic (LanceDB vectors) + keyword (text filter). Research says hybrid beats either alone."""
    if DISABLE_INDEXER:
        return {"query": req.query, "results": [], "error": "Indexer disabled — semantic search unavailable"}
    _, table = _get_db()
    if table is None:
        return {"query": req.query, "results": [], "method": "no_index"}

    embedder = _get_embedder()
    query_embedding = embedder.encode([req.query]).tolist()[0]

    try:
        # Semantic search via LanceDB
        search_query = table.search(query_embedding).metric("cosine").limit(req.n_results * 2)
        if req.repo:
            search_query = search_query.where(f"repo = '{req.repo}'")
        results = search_query.to_pandas()
    except Exception as e:
        print(f"Search error: {e}")
        return {"query": req.query, "results": [], "error": str(e)}

    hits = []
    seen_files = set()
    for _, row in results.iterrows():
        file_key = f"{row.get('repo', '')}/{row.get('file', '')}"
        # Deduplicate by file — show best chunk per file
        if file_key in seen_files:
            continue
        seen_files.add(file_key)

        distance = row.get("_distance", 1.0)
        hits.append({
            "id": row.get("id", ""),
            "repo": row.get("repo", ""),
            "file": row.get("file", ""),
            "start_line": int(row.get("start_line", 0)),
            "end_line": int(row.get("end_line", 0)),
            "block_name": row.get("block_name", ""),
            "block_type": row.get("block_type", ""),
            "score": round(max(0, 1 / (1 + distance)), 4),
            "snippet": str(row.get("text", ""))[:300],
        })
        if len(hits) >= req.n_results:
            break

    return {"query": req.query, "results": hits, "method": "hybrid_lance"}


@app.post("/api/impact")
async def impact(req: ImpactRequest):
    """Find files that reference/import a given file. Combines semantic + keyword matching."""
    if DISABLE_INDEXER:
        return {"target": req.file_path, "impacted_files": [], "count": 0, "error": "Indexer disabled — semantic search unavailable"}
    _, table = _get_db()
    if table is None:
        return {"target": req.file_path, "impacted_files": [], "count": 0}

    embedder = _get_embedder()
    filename = Path(req.file_path).stem

    # Semantic search for import patterns
    query = f"import {filename} from require {filename}"
    query_embedding = embedder.encode([query]).tolist()[0]

    try:
        results = table.search(query_embedding).metric("cosine").limit(50).to_pandas()
    except Exception:
        results = None

    impacts = []
    seen_files = set()

    if results is not None:
        for _, row in results.iterrows():
            doc = str(row.get("text", ""))
            file_key = f"{row.get('repo', '')}/{row.get('file', '')}"

            if file_key in seen_files:
                continue

            # Keyword check: does the chunk actually reference the target file?
            if filename.lower() in doc.lower():
                seen_files.add(file_key)
                distance = row.get("_distance", 1.0)
                impacts.append({
                    "repo": row.get("repo", ""),
                    "file": row.get("file", ""),
                    "line": int(row.get("start_line", 0)),
                    "block_name": row.get("block_name", ""),
                    "score": round(max(0, 1 / (1 + distance)), 4),
                })

    # Also do a direct keyword search in LanceDB (hybrid)
    try:
        keyword_results = table.search().where(
            f"text LIKE '%{filename}%'"
        ).limit(30).to_pandas()

        for _, row in keyword_results.iterrows():
            file_key = f"{row.get('repo', '')}/{row.get('file', '')}"
            if file_key not in seen_files:
                seen_files.add(file_key)
                impacts.append({
                    "repo": row.get("repo", ""),
                    "file": row.get("file", ""),
                    "line": int(row.get("start_line", 0)),
                    "block_name": row.get("block_name", ""),
                    "score": 0.5,  # keyword match, no semantic score
                })
    except Exception:
        pass  # keyword search not supported on all LanceDB versions

    return {
        "target": req.file_path,
        "impacted_files": impacts,
        "count": len(impacts),
    }


@app.get("/api/stats")
async def stats():
    """Index statistics."""
    return {
        "indexing": _indexing,
        "last_index": _last_index_time,
        **_index_stats,
    }


@app.post("/api/reindex")
async def reindex():
    """Trigger immediate re-index."""
    if DISABLE_INDEXER:
        return {"status": "disabled", "error": "Indexer disabled — set DISABLE_INDEXER=false to enable"}
    if _indexing:
        return {"status": "already_indexing"}
    t = threading.Thread(target=run_index, daemon=True)
    t.start()
    return {"status": "started"}


# --- Memory API Endpoints ---

class BuildPhaseRecord(BaseModel):
    project: str
    build_name: str
    phase: str
    status: str
    duration_seconds: Optional[float] = None
    failure_reason: Optional[str] = None
    files_changed: Optional[list] = None


class NoteRecord(BaseModel):
    topic: str
    content: str
    project: Optional[str] = None
    source: str = "manual"


class CommitSearchRequest(BaseModel):
    query: str
    repo: Optional[str] = None
    limit: int = 20


@app.post("/api/memory/build")
async def record_build(req: BuildPhaseRecord):
    """Record a build phase outcome."""
    from core.cluster.memory_store import record_build_phase
    record_build_phase(
        req.project, req.build_name, req.phase, req.status,
        req.duration_seconds, req.failure_reason, req.files_changed
    )
    return {"status": "recorded"}


@app.get("/api/memory/builds")
async def get_builds(project: Optional[str] = None, limit: int = 50):
    """Get build history."""
    from core.cluster.memory_store import get_build_history
    return {"builds": get_build_history(project, limit)}


@app.get("/api/memory/predict/{project}/{phase_pattern}")
async def predict(project: str, phase_pattern: str):
    """Predict difficulty of a phase based on history."""
    from core.cluster.memory_store import predict_phase
    return predict_phase(project, phase_pattern)


@app.post("/api/memory/commits/search")
async def commit_search(req: CommitSearchRequest):
    """Search commit messages."""
    from core.cluster.memory_store import search_commits
    return {"commits": search_commits(req.query, req.repo, req.limit)}


@app.get("/api/memory/tests")
async def get_tests(project: Optional[str] = None, limit: int = 20):
    """Get recent test health data for sparklines and dashboard.

    Returns detailed per-run records from the test_health table (Phase 37 completion).
    Falls back to legacy test_results if test_health is empty.
    """
    from core.cluster.memory_store import get_test_health, get_latest_test_results
    results = get_test_health(project, limit)
    if not results:
        # Fallback to legacy table for backward compat
        results = get_latest_test_results(project)
    return {"results": results}


class TestHealthRecord(BaseModel):
    project: str
    sha: Optional[str] = None
    branch: Optional[str] = None
    pass_rate: float = 0.0
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list = []
    duration_ms: Optional[int] = None
    runner: str = "vitest"
    trigger: str = "watch"


@app.post("/api/memory/tests")
async def save_tests(req: TestHealthRecord):
    """Receive test health data from Walter or other test runners.

    Stores in test_health table with full SHA tracking, runner info, and trigger source.
    Also writes to legacy test_results for backward compat.
    """
    from core.cluster.memory_store import save_test_health
    return save_test_health(
        project=req.project, sha=req.sha, branch=req.branch,
        pass_rate=req.pass_rate, total=req.total, passed=req.passed,
        failed=req.failed, skipped=req.skipped, failures=req.failures,
        duration_ms=req.duration_ms, runner=req.runner, trigger=req.trigger
    )


@app.get("/api/memory/patterns")
async def get_patterns():
    """Get active log patterns."""
    from core.cluster.memory_store import get_active_patterns
    return {"patterns": get_active_patterns()}


@app.post("/api/memory/note")
async def save_architecture_note(req: NoteRecord):
    """Save an architecture note."""
    from core.cluster.memory_store import save_note
    save_note(req.topic, req.content, req.project, req.source)
    return {"status": "saved"}


@app.get("/api/memory/notes")
async def get_notes(query: str = "", project: Optional[str] = None):
    """Search architecture notes."""
    from core.cluster.memory_store import search_notes
    return {"notes": search_notes(query, project)}


@app.get("/api/brief/{project}")
async def get_brief(project: str):
    """Generate full context brief for a Claude session."""
    from core.cluster.memory_store import generate_brief
    return generate_brief(project)


@app.post("/api/memory/session")
async def save_session(project: str, branch: str = None, phase: str = None,
                       build_name: str = None, working_on: str = None):
    """Save current session state."""
    from core.cluster.memory_store import save_session_state
    save_session_state(project, branch, phase, build_name, working_on)
    return {"status": "saved"}


# --- Plan Memory API Endpoints ---

class PlanRecordRequest(BaseModel):
    project: str
    build_name: str
    phase: str
    plan_text: str
    outcome: str
    accuracy_pct: Optional[float] = None
    drift_notes: Optional[str] = None
    files_planned: Optional[list] = None
    files_actual: Optional[list] = None
    duration_seconds: Optional[float] = None


@app.post("/api/plans/record")
async def record_plan(req: PlanRecordRequest):
    """Record a plan outcome — stores in SQLite and embeds in LanceDB for semantic search."""
    from core.cluster.memory_store import record_plan_outcome, get_recent_plan_outcomes

    # Store in SQLite
    record_plan_outcome(
        req.project, req.build_name, req.phase, req.plan_text,
        req.outcome, req.accuracy_pct, req.drift_notes,
        req.files_planned, req.files_actual, req.duration_seconds
    )

    # Get the plan_id of the just-inserted record
    recent = get_recent_plan_outcomes(req.project, limit=1)
    plan_id = recent[0]["plan_id"] if recent else 0

    # Embed into LanceDB for semantic retrieval (skip if indexer disabled)
    if not DISABLE_INDEXER:
        try:
            embed_plan(
                plan_id, req.project, req.build_name, req.phase,
                req.plan_text, req.outcome, req.accuracy_pct, req.drift_notes
            )
        except Exception as e:
            return {"status": "recorded", "embedded": False, "error": str(e)}

    return {"status": "recorded", "plan_id": plan_id, "embedded": not DISABLE_INDEXER}


@app.get("/api/plans/similar")
async def similar_plans(query: str, project: Optional[str] = None, limit: int = 3):
    """Search for semantically similar past plans. Returns top N with outcome + accuracy."""
    if DISABLE_INDEXER:
        # Fallback: keyword search from SQLite
        from core.cluster.memory_store import get_recent_plan_outcomes
        all_plans = get_recent_plan_outcomes(project, limit=50) if project else []
        # Simple keyword filter
        query_lower = query.lower()
        matches = [
            p for p in all_plans
            if query_lower in (p.get("plan_text") or "").lower()
        ][:limit]
        return {"query": query, "results": matches, "method": "keyword_fallback"}

    results = search_similar_plans(query, project, limit)
    return {"query": query, "results": results, "method": "semantic"}


# --- Research Library API Endpoints ---

@app.get("/api/research/search")
async def research_search(query: str, limit: int = 5, domain: Optional[str] = None):
    """Semantic search over research library chunks. Returns top-k with source, section, score."""
    results = search_research(query, domain, limit)
    return {"query": query, "results": results, "count": len(results), "method": "semantic"}


@app.post("/api/research/vsearch")
async def research_vsearch(req: Request):
    """Vector search — accepts a pre-encoded query vector (embed on client, search on Lockwood).
    Use this when Lockwood can't load the embedding model (M2 8GB constraint).
    Body: {"vector": [float,...], "limit": int, "domain": str|null}"""
    data = await req.json()
    vector = data.get("vector", [])
    limit = data.get("limit", 5)
    domain = data.get("domain")
    if not vector:
        return {"error": "vector required", "results": []}

    db, _ = _get_db()
    if "research_library" not in db.table_names():
        return {"results": [], "count": 0}
    table = db.open_table("research_library")

    try:
        search_query = table.search(vector).metric("cosine").limit(limit * 2)
        if domain:
            search_query = search_query.where(f"domain LIKE '%{domain}%'")
        results = search_query.to_pandas()
    except Exception:
        return {"results": [], "count": 0}

    hits = []
    seen = set()
    for _, row in results.iterrows():
        key = f"{row.get('source_file', '')}:{row.get('section', '')}"
        if key in seen:
            continue
        seen.add(key)
        distance = row.get("_distance", 1.0)
        hits.append({
            "id": row.get("id", ""),
            "title": row.get("title", ""),
            "section": row.get("section", ""),
            "domain": row.get("domain", ""),
            "subjects": row.get("subjects", ""),
            "priority": row.get("priority", ""),
            "source_file": row.get("source_file", ""),
            "score": round(max(0, 1 / (1 + distance)), 4),
            "snippet": str(row.get("text", ""))[:400],
        })
        if len(hits) >= limit:
            break
    return {"results": hits, "count": len(hits), "method": "vsearch"}


@app.post("/api/research/reindex")
async def research_reindex():
    """Trigger immediate research library re-index. Clears mtime cache so new files are detected."""
    global _research_dir_mtime
    if _research_indexing:
        return {"status": "already_indexing"}
    # Clear mtime cache so the indexer doesn't skip based on stale directory mtime
    _research_dir_mtime = 0.0
    t = threading.Thread(target=run_research_index, daemon=True)
    t.start()
    return {"status": "started"}


@app.get("/api/research/stats")
async def research_stats():
    """Research index statistics."""
    return {
        "indexing": _research_indexing,
        "last_index": _research_last_index_time,
        "research_dir": RESEARCH_DIR,
        "embed_model": RESEARCH_EMBED_MODEL,
        **_research_stats,
    }


# --- Registry Sync (Phase 8) ---

@app.post("/api/registry/sync")
async def sync_registry(req: Request):
    """Receive cluster-builds registry from Muddy and store it."""
    from core.cluster.memory_store import save_registry
    data = await req.json()
    result = save_registry(data)
    return result


@app.get("/api/registry/sync")
async def get_registry():
    """Return the latest cluster-builds registry."""
    from core.cluster.memory_store import get_registry as _get_registry
    return _get_registry()
