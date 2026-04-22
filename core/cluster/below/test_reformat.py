from __future__ import annotations

import shutil
import subprocess

import pytest

from core.cluster.below.queue_schema import PendingRecord
from core.cluster.below.research_worker import (
    REQUIRED_FRONTMATTER_KEYS,
    generate_reformatted_markdown,
)
from core.cluster.cluster_config import get_below_ollama_url

CURL_BIN = shutil.which("curl") or "/usr/bin/curl"


def _ollama_reachable() -> bool:
    result = subprocess.run(  # noqa: S603
        [CURL_BIN, "-sS", "--max-time", "3", f"{get_below_ollama_url()}/api/tags"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _frontmatter_keys(markdown: str) -> set[str]:
    lines = markdown.splitlines()
    if not lines or lines[0] != "---":
        return set()
    keys: set[str] = set()
    for line in lines[1:]:
        if line == "---":
            break
        if ":" not in line:
            continue
        key = line.split(":", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


@pytest.mark.skipif(not _ollama_reachable(), reason="ollama unreachable")
def test_reformat_response_contains_required_frontmatter_keys() -> None:
    record = PendingRecord(
        id="b6479d61-20f1-4819-b1ec-0c2785e50001",
        title="Prompt caching heuristics for long-lived workers",
        draft_markdown=(
            "# Notes\n\n"
            "Investigate prompt cache breakpoints, queue-drain behavior, and safe reindexing.\n"
            "Mention BuildRunner3, Jimmy research library, and Below Ollama routing."
        ),
        intended_path="docs/techniques/prompt-caching-heuristics.md",
        sources=["notes://phase-6", "https://example.test/research/prompt-cache"],
        created_at="2026-04-22T00:00:00Z",
    )

    markdown = generate_reformatted_markdown(record)
    keys = _frontmatter_keys(markdown)

    assert markdown.startswith("---\n")
    assert set(REQUIRED_FRONTMATTER_KEYS).issubset(keys)
