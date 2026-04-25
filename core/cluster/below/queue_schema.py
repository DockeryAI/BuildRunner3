"""JSONL schemas for the Below research handoff worker."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Literal, Self


@dataclass(slots=True)
class AdversarialReview:
    reviewers: list[str]
    critique_summary: str
    revisions_applied: list[str]
    notes_inserted: int
    degraded: bool
    degraded_reason: str | None


@dataclass(slots=True)
class PendingRecord:
    id: str
    title: str
    draft_markdown: str
    intended_path: str
    sources: list[str]
    created_at: str
    adversarial_review: AdversarialReview | None = field(default=None, kw_only=True)

    def to_jsonl(self) -> str:
        payload = asdict(self)
        if payload.get("adversarial_review") is None:
            payload.pop("adversarial_review", None)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_jsonl(cls, line: str) -> Self:
        payload = json.loads(line)
        review = payload.pop("adversarial_review", None)
        if review is not None:
            review = AdversarialReview(**review)
        return cls(**payload, adversarial_review=review)


@dataclass(slots=True)
class CompletedRecord(PendingRecord):
    committed_sha: str
    chunk_count: int
    status: Literal["ok", "error", "indexing_pending"]
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
    if "adversarial_review" in pending.to_jsonl():
        sys.stdout.write("PendingRecord serialized adversarial_review when None\n")
        return 1
    if CompletedRecord.from_jsonl(completed.to_jsonl()) != completed:
        sys.stdout.write("CompletedRecord round-trip failed\n")
        return 1

    pending_reviewed = PendingRecord(
        id=pending.id,
        title=pending.title,
        draft_markdown=pending.draft_markdown,
        intended_path=pending.intended_path,
        sources=pending.sources,
        created_at=pending.created_at,
        adversarial_review=AdversarialReview(
            reviewers=["codex", "gemini"],
            critique_summary="3 weakest claims, 1 hallucination risk",
            revisions_applied=["downgraded 2 confidence tags"],
            notes_inserted=1,
            degraded=False,
            degraded_reason=None,
        ),
    )
    round_tripped = PendingRecord.from_jsonl(pending_reviewed.to_jsonl())
    if round_tripped != pending_reviewed:
        sys.stdout.write("PendingRecord with adversarial_review round-trip failed\n")
        return 1

    degraded = PendingRecord(
        id=pending.id,
        title=pending.title,
        draft_markdown=pending.draft_markdown,
        intended_path=pending.intended_path,
        sources=pending.sources,
        created_at=pending.created_at,
        adversarial_review=AdversarialReview(
            reviewers=[],
            critique_summary="no critique — fallback exhausted",
            revisions_applied=[],
            notes_inserted=0,
            degraded=True,
            degraded_reason="all_reviewers_failed",
        ),
    )
    if PendingRecord.from_jsonl(degraded.to_jsonl()) != degraded:
        sys.stdout.write("PendingRecord degraded round-trip failed\n")
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
