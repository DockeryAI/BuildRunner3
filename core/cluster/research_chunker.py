"""
BR3 Cluster — Research Library Chunker
Markdown-aware chunking for the research library. Splits on H2/H3 headers,
preserves YAML frontmatter as metadata context for each chunk.

Used by node_semantic.py to index ~/repos/research-library/docs/ into LanceDB.
"""

import yaml
from pathlib import Path
from typing import Optional


def parse_frontmatter(content: str) -> tuple[dict, str, int]:
    """Extract YAML frontmatter and return (metadata, body, body_start_line)."""
    if not content.startswith("---"):
        return {}, content, 1
    end = content.find("---", 3)
    if end == -1:
        return {}, content, 1
    try:
        meta = yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        meta = {}
    body_start = end + 3
    while body_start < len(content) and content[body_start] == "\n":
        body_start += 1
    body = content[body_start:]
    body_start_line = content[:body_start].count("\n") + 1
    return meta, body, body_start_line


def _count_nonempty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _build_sections(body: str, body_start_line: int) -> list[dict]:
    """Return H2-partitioned sections with source line numbers."""
    lines = body.splitlines()
    if not lines:
        return []

    sections: list[dict] = []
    intro_start = 0
    current_header: Optional[str] = None
    current_start: Optional[int] = None

    for idx, line in enumerate(lines):
        if line.startswith("## "):
            if current_header is None and idx > intro_start:
                intro_lines = lines[intro_start:idx]
                if any(part.strip() for part in intro_lines):
                    sections.append({
                        "header": "Introduction",
                        "content": "\n".join(intro_lines).strip(),
                        "start_line": body_start_line + intro_start,
                        "end_line": body_start_line + idx - 1,
                    })
            elif current_header is not None and current_start is not None:
                section_lines = lines[current_start:idx]
                sections.append({
                    "header": current_header,
                    "content": "\n".join(section_lines[1:]).strip(),
                    "start_line": body_start_line + current_start,
                    "end_line": body_start_line + idx - 1,
                })
            current_header = line[3:].strip()
            current_start = idx

    if current_header is None:
        if any(part.strip() for part in lines):
            sections.append({
                "header": "Introduction",
                "content": "\n".join(lines).strip(),
                "start_line": body_start_line,
                "end_line": body_start_line + len(lines) - 1,
            })
    elif current_start is not None:
        section_lines = lines[current_start:]
        sections.append({
            "header": current_header,
            "content": "\n".join(section_lines[1:]).strip(),
            "start_line": body_start_line + current_start,
            "end_line": body_start_line + len(lines) - 1,
        })

    return sections


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

    meta, body, body_start_line = parse_frontmatter(content)
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

    sections = _build_sections(body, body_start_line)

    chunks = []
    chunk_counter = 0

    for section in sections:
        section_header = section["header"]
        section_content = section["content"]
        section_start_line = section["start_line"]
        section_end_line = section["end_line"]
        full_section = f"## {section_header}\n\n{section_content}" if section_header != "Introduction" else section_content

        if len(full_section) <= max_chunk_chars:
            # Section fits in one chunk
            if _count_nonempty_lines(full_section) < 2 or len(full_section.strip()) < 100:
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
                start_line=section_start_line,
                end_line=section_end_line,
            ))
            chunk_counter += 1
        else:
            # Section too large, split on H3
            section_lines = section_content.splitlines()
            h3_indices = [idx for idx, line in enumerate(section_lines) if line.startswith("### ")]

            # Content before first H3 in this section
            pre_h3_end = h3_indices[0] - 1 if h3_indices else len(section_lines) - 1
            pre_h3_text = "\n".join(section_lines[: pre_h3_end + 1]).strip()
            if pre_h3_text and len(pre_h3_text) >= 100:
                chunk_text = meta_prefix + f"Section: {section_header}\n\n" + pre_h3_text
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
                    start_line=section_start_line,
                    end_line=section_start_line + pre_h3_end,
                ))
                chunk_counter += 1

            # H3 sub-sections
            for idx, start_idx in enumerate(h3_indices):
                next_idx = h3_indices[idx + 1] if idx + 1 < len(h3_indices) else len(section_lines)
                sub_lines = section_lines[start_idx:next_idx]
                sub_header = sub_lines[0][4:].strip() if sub_lines else ""
                sub_content = "\n".join(sub_lines[1:]).strip()

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
                    start_line=section_start_line + start_idx,
                    end_line=section_start_line + next_idx - 1,
                ))
                chunk_counter += 1

    return chunks


def _make_chunk(chunk_id: str, text: str, title: str, section: str,
                domain: str, subjects: str, priority: str,
                techniques: str, source_file: str,
                start_line: int, end_line: int) -> dict:
    return {
        "id": chunk_id,
        "text": text,
        "start_line": start_line,
        "end_line": end_line,
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
