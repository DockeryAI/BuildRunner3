"""JSONL schemas for the Below research handoff worker."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Literal, Self


@dataclass(slots=True)
class PendingRecord:
    id: str
    title: str
    draft_markdown: str
    intended_path: str
    sources: list[str]
    created_at: str

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_jsonl(cls, line: str) -> Self:
        payload = json.loads(line)
        return cls(**payload)


@dataclass(slots=True)
class CompletedRecord(PendingRecord):
    committed_sha: str
    chunk_count: int
    status: Literal["ok", "error"]
    error: str | None
    completed_at: str
    reindex_warning: str | None

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_jsonl(cls, line: str) -> Self:
        payload = json.loads(line)
        return cls(**payload)


def _run_self_test() -> int:
    pending = PendingRecord(
        id="5ec9367c-0d0b-4f38-938f-8078196d98ec",
        title="Synthetic pending title",
        draft_markdown="# Draft\n\nBody with unicode ✓",
        intended_path="docs/techniques/synthetic.md",
        sources=["https://example.test/a", "notes://synthetic"],
        created_at="2026-04-22T00:00:00Z",
    )
    completed = CompletedRecord(
        **asdict(pending),
        committed_sha="abc123def456",
        chunk_count=7,
        status="ok",
        error=None,
        completed_at="2026-04-22T00:05:00Z",
        reindex_warning=None,
    )

    if PendingRecord.from_jsonl(pending.to_jsonl()) != pending:
        sys.stdout.write("PendingRecord round-trip failed\n")
        return 1
    if CompletedRecord.from_jsonl(completed.to_jsonl()) != completed:
        sys.stdout.write("CompletedRecord round-trip failed\n")
        return 1

    sys.stdout.write("OK\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("--self-test is required")
    return _run_self_test()


if __name__ == "__main__":
    raise SystemExit(main())
