from __future__ import annotations

import re
from pathlib import Path

import perplexity

RESEARCH_MD = Path.home() / ".claude" / "commands" / "research.md"
STRIP_PLACEHOLDER_RE = re.compile(r"\{[A-Z_]+\}")
STRIP_TOKENS = ("<output_format>", "<thinking>", "WebSearch", "WebFetch")


def strip_non_claude_prompt(prompt: str) -> str:
    kept_lines: list[str] = []
    for line in prompt.splitlines():
        if any(token in line for token in STRIP_TOKENS):
            continue
        if STRIP_PLACEHOLDER_RE.search(line):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def test_research_md_documents_non_claude_strip_and_archaeology_filter() -> None:
    text = RESEARCH_MD.read_text()

    assert "On the non-Claude path only" in text
    assert "strip any line that contains literal `<output_format>`, `<thinking>`, `WebSearch`, or `WebFetch`" in text
    assert r"\{[A-Z_]+\}" in text
    assert "archaeology)" in text
    assert '--search-domain-filter "academic"' in text


def test_strip_non_claude_prompt_removes_provider_hostile_lines() -> None:
    prompt = """<role>
Keep this line.
<output_format>
Keep this too.
<thinking>
Run 5 WebSearch queries before deciding.
Use WebFetch on every promising result.
Investigate {TOPIC} carefully.
Final intact line."""

    stripped = strip_non_claude_prompt(prompt)

    assert stripped.splitlines() == [
        "<role>",
        "Keep this line.",
        "Keep this too.",
        "Final intact line.",
    ]
    for token in STRIP_TOKENS:
        assert token not in stripped
    assert "{TOPIC}" not in stripped


def test_parse_args_accepts_perplexity_search_filters(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "perplexity.py",
            "--prompt-file",
            str(tmp_path / "prompt.txt"),
            "--search-domain-filter",
            "academic",
            "--search-recency-filter",
            "month",
        ],
    )

    args = perplexity.parse_args()

    assert args.search_domain_filter == ["academic"]
    assert args.search_recency_filter == "month"


def test_build_request_body_emits_documented_filter_keys() -> None:
    body = perplexity.build_request_body(
        "Neolithic henges",
        max_tokens=512,
        system="You are a research assistant.",
        search_domain_filter=["academic"],
        search_recency_filter="month",
    )

    assert body["search_domain_filter"] == ["academic"]
    assert body["search_recency_filter"] == "month"
    assert body["messages"][1]["content"] == "Neolithic henges"
    assert body["max_tokens"] == 512


def test_build_request_body_omits_filter_keys_when_unset() -> None:
    body = perplexity.build_request_body(
        "Neolithic henges",
        max_tokens=256,
        system="You are a research assistant.",
    )

    assert "search_domain_filter" not in body
    assert "search_recency_filter" not in body
