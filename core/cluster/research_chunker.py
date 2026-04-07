"""
BR3 Cluster — Research Library Chunker
Markdown-aware chunking for the research library. Splits on H2/H3 headers,
preserves YAML frontmatter as metadata context for each chunk.

Used by node_semantic.py to index ~/repos/research-library/docs/ into LanceDB.
"""

import re
import yaml
from pathlib import Path
from typing import Optional


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (metadata, body)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    try:
        meta = yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        meta = {}
    body = content[end + 3:].lstrip("\n")
    return meta, body


def chunk_research_doc(path: Path, max_chunk_chars: int = 2000) -> list[dict]:
    """
    Split a research markdown doc into semantic chunks.

    Strategy:
    - Split on H2 (##) headers as primary boundaries
    - If a section > max_chunk_chars, split on H3 (###) sub-headers
    - Each chunk inherits doc title + frontmatter fields
    - Chunks < 100 chars are merged with the next section
    - Frontmatter metadata prepended to chunk text before embedding
    """
    try:
        content = path.read_text(errors="replace")
    except Exception:
        return []

    if not content.strip():
        return []

    meta, body = parse_frontmatter(content)
    title = meta.get("title", path.stem.replace("-", " ").title())
    domain = meta.get("domain", "")
    if isinstance(domain, list):
        domain = ", ".join(domain)
    subjects = meta.get("subjects", [])
    if isinstance(subjects, list):
        subjects = ", ".join(subjects[:20])
    elif not isinstance(subjects, str):
        subjects = str(subjects) if subjects else ""
    priority = meta.get("priority", "")
    techniques = meta.get("techniques", [])
    if isinstance(techniques, list):
        techniques = ", ".join(techniques[:10])
    elif not isinstance(techniques, str):
        techniques = str(techniques) if techniques else ""

    # Build metadata prefix for embedding context
    meta_prefix = f"Research: {title}\n"
    if domain:
        meta_prefix += f"Domain: {domain}\n"
    if subjects:
        meta_prefix += f"Subjects: {subjects}\n"
    meta_prefix += "---\n"

    rel_path = str(path)
    # Try to make relative to research-library
    try:
        parts = path.parts
        idx = parts.index("research-library")
        rel_path = "/".join(parts[idx:])
    except (ValueError, IndexError):
        pass

    # Split body into H2 sections
    h2_pattern = re.compile(r'^## ', re.MULTILINE)
    h2_splits = h2_pattern.split(body)
    h2_headers = h2_pattern.findall(body)

    sections = []
    # First section (before any H2) - often TL;DR or intro
    if h2_splits[0].strip():
        sections.append(("Introduction", h2_splits[0].strip()))

    # Remaining H2 sections
    for i, section_body in enumerate(h2_splits[1:]):
        lines = section_body.split("\n", 1)
        header = lines[0].strip()
        content_text = lines[1].strip() if len(lines) > 1 else ""
        sections.append((header, content_text))

    chunks = []
    chunk_counter = 0

    for section_header, section_content in sections:
        full_section = f"## {section_header}\n\n{section_content}" if section_header != "Introduction" else section_content

        if len(full_section) <= max_chunk_chars:
            # Section fits in one chunk
            if len(full_section.strip()) < 100:
                continue  # too small, skip
            chunk_text = meta_prefix + f"Section: {section_header}\n\n" + section_content
            chunks.append(_make_chunk(
                chunk_id=f"{rel_path}:c{chunk_counter}",
                text=chunk_text,
                title=title,
                section=section_header,
                domain=domain,
                subjects=subjects,
                priority=priority,
                techniques=techniques,
                source_file=rel_path,
            ))
            chunk_counter += 1
        else:
            # Section too large, split on H3
            h3_pattern = re.compile(r'^### ', re.MULTILINE)
            h3_splits = h3_pattern.split(section_content)

            # Content before first H3 in this section
            if h3_splits[0].strip() and len(h3_splits[0].strip()) >= 100:
                chunk_text = meta_prefix + f"Section: {section_header}\n\n" + h3_splits[0].strip()
                chunks.append(_make_chunk(
                    chunk_id=f"{rel_path}:c{chunk_counter}",
                    text=chunk_text[:max_chunk_chars + len(meta_prefix)],
                    title=title,
                    section=section_header,
                    domain=domain,
                    subjects=subjects,
                    priority=priority,
                    techniques=techniques,
                    source_file=rel_path,
                ))
                chunk_counter += 1

            # H3 sub-sections
            for sub_body in h3_splits[1:]:
                sub_lines = sub_body.split("\n", 1)
                sub_header = sub_lines[0].strip()
                sub_content = sub_lines[1].strip() if len(sub_lines) > 1 else ""

                if len(sub_content) < 100:
                    continue

                full_sub = f"{section_header} > {sub_header}"
                chunk_text = meta_prefix + f"Section: {full_sub}\n\n" + sub_content
                chunks.append(_make_chunk(
                    chunk_id=f"{rel_path}:c{chunk_counter}",
                    text=chunk_text[:max_chunk_chars + len(meta_prefix)],
                    title=title,
                    section=full_sub,
                    domain=domain,
                    subjects=subjects,
                    priority=priority,
                    techniques=techniques,
                    source_file=rel_path,
                ))
                chunk_counter += 1

    return chunks


def _make_chunk(chunk_id: str, text: str, title: str, section: str,
                domain: str, subjects: str, priority: str,
                techniques: str, source_file: str) -> dict:
    return {
        "id": chunk_id,
        "text": text,
        "metadata": {
            "title": title,
            "section": section,
            "domain": domain,
            "subjects": subjects,
            "priority": priority,
            "techniques": techniques,
            "source_file": source_file,
        },
    }


def discover_research_docs(research_dir: str) -> list[Path]:
    """Find all .md files in the research library docs/ directory."""
    docs_path = Path(research_dir) / "docs"
    if not docs_path.exists():
        # Try without /docs suffix
        docs_path = Path(research_dir)
    files = []
    for path in docs_path.rglob("*.md"):
        # Skip index files and schema
        if path.name in ("index.md", "schema.md", "GEO-INDEX.md", "MEMORY.md"):
            continue
        try:
            if path.stat().st_size <= 200_000:  # skip files > 200KB
                files.append(path)
        except OSError:
            continue
    return files
