"""Round-trip tests for PendingRecord adversarial_review field."""

from __future__ import annotations

import json

from core.cluster.below.queue_schema import (
    AdversarialReview,
    CompletedRecord,
    PendingRecord,
)


def _base_pending(**overrides) -> PendingRecord:
    defaults = dict(
        id="00000000-0000-0000-0000-000000000001",
        title="t",
        draft_markdown="# t",
        intended_path="docs/techniques/t.md",
        sources=["https://example.test/x"],
        created_at="2026-04-22T00:00:00Z",
    )
    defaults.update(overrides)
    return PendingRecord(**defaults)


def test_pending_record_without_review_roundtrip():
    record = _base_pending()
    line = record.to_jsonl()
    assert "adversarial_review" not in json.loads(line)
    assert PendingRecord.from_jsonl(line) == record


def test_pending_record_with_review_roundtrip():
    review = AdversarialReview(
        reviewers=["codex", "gemini"],
        critique_summary="3 weakest claims, 2 hallucination risks",
        revisions_applied=["downgraded 2 confidence tags", "inserted 1 review note"],
        notes_inserted=1,
        degraded=False,
        degraded_reason=None,
    )
    record = _base_pending(adversarial_review=review)
    round_tripped = PendingRecord.from_jsonl(record.to_jsonl())
    assert round_tripped == record
    assert round_tripped.adversarial_review == review


def test_pending_record_degraded_review_roundtrip():
    review = AdversarialReview(
        reviewers=[],
        critique_summary="no review — fallback exhausted",
        revisions_applied=[],
        notes_inserted=0,
        degraded=True,
        degraded_reason="all_reviewers_failed",
    )
    record = _base_pending(adversarial_review=review)
    round_tripped = PendingRecord.from_jsonl(record.to_jsonl())
    assert round_tripped == record
    assert round_tripped.adversarial_review.degraded is True
    assert round_tripped.adversarial_review.degraded_reason == "all_reviewers_failed"


def test_pending_record_legacy_jsonl_without_field_still_parses():
    legacy_line = json.dumps(
        {
            "id": "legacy",
            "title": "legacy",
            "draft_markdown": "# legacy",
            "intended_path": "docs/techniques/legacy.md",
            "sources": [],
            "created_at": "2026-04-22T00:00:00Z",
        },
        sort_keys=True,
    )
    parsed = PendingRecord.from_jsonl(legacy_line)
    assert parsed.adversarial_review is None


def test_completed_record_still_roundtrips():
    completed = CompletedRecord(
        id="c",
        title="c",
        draft_markdown="# c",
        intended_path="docs/techniques/c.md",
        sources=[],
        created_at="2026-04-22T00:00:00Z",
        committed_sha="abc",
        chunk_count=1,
        status="ok",
        error=None,
        completed_at="2026-04-22T00:05:00Z",
        reindex_warning=None,
    )
    assert CompletedRecord.from_jsonl(completed.to_jsonl()) == completed
