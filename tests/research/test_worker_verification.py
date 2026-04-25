from __future__ import annotations

from core.cluster.below import research_worker
from core.cluster.below.queue_schema import CompletedRecord, PendingRecord

SUCCESS_MARKDOWN = """---
title: Verified Research Title
domain: infrastructure
techniques: [verification]
concepts: [retrieval]
subjects: [research worker]
priority: medium
source_project: BuildRunner3
created: 2026-04-25
last_updated: 2026-04-25
---

# Verified Research Heading

This paragraph is long enough to be used as the retrieval verification fallback body.
"""


def make_record() -> PendingRecord:
    return PendingRecord(
        id="verify-1",
        title="Verification test",
        draft_markdown="# Draft\n\nVerification body.",
        intended_path="docs/testing/verified.md",
        sources=["tests://verification"],
        created_at="2026-04-25T00:00:00Z",
    )


def matching_payload(path: str, score: float) -> dict[str, object]:
    return {
        "results": [
            {
                "source": "research",
                "source_url": f"/srv/jimmy/research-library/{path}",
                "score": score,
                "text": "Matched chunk",
            }
        ]
    }


class VerificationWorker(research_worker.ResearchWorker):
    def __init__(
        self,
        queue_dir,
        *,
        retrieve_payloads: list[dict[str, object]] | None = None,
        reformat_exception: Exception | None = None,
        metadata_exception: Exception | None = None,
        reindex_result: tuple[int, str | None] = (12, None),
    ) -> None:
        super().__init__(queue_dir, poll_seconds=0)
        self.retrieve_payloads = list(retrieve_payloads or [])
        self.retrieve_calls: list[dict[str, object]] = []
        self.reformat_exception = reformat_exception
        self.metadata_exception = metadata_exception
        self.reindex_result = reindex_result
        self.sleep = lambda _seconds: None

    def get_research_stats(self) -> dict[str, object]:
        return {"total_chunks": 9}

    def generate_reformatted_markdown(self, record: PendingRecord) -> str:
        del record
        if self.reformat_exception is not None:
            raise self.reformat_exception
        return SUCCESS_MARKDOWN

    def generate_metadata(self, record: PendingRecord) -> dict[str, object]:
        del record
        if self.metadata_exception is not None:
            raise self.metadata_exception
        return {
            "topic": "Verification",
            "tags": ["verification"],
            "domain": "infrastructure",
            "difficulty": "intermediate",
        }

    def commit_to_jimmy(
        self,
        record: PendingRecord,
        reformatted_md: str,
        metadata: dict[str, object],
    ) -> str:
        del record, reformatted_md, metadata
        return "abc123"

    def wait_for_reindex(
        self,
        pre_stats: dict[str, object],
        *,
        commit_time_epoch: float,
    ) -> tuple[int, str | None]:
        del pre_stats, commit_time_epoch
        return self.reindex_result

    def retrieve_research(
        self,
        query: str,
        *,
        top_k: int = 10,
        sources: list[str] | None = None,
    ) -> dict[str, object]:
        self.retrieve_calls.append(
            {
                "query": query,
                "top_k": top_k,
                "sources": sources,
            }
        )
        if self.retrieve_payloads:
            return self.retrieve_payloads.pop(0)
        return {"results": []}


def read_completed(queue_dir) -> list[CompletedRecord]:
    lines = (queue_dir / "completed.jsonl").read_text(encoding="utf-8").splitlines()
    return [CompletedRecord.from_jsonl(line) for line in lines if line.strip()]


def test_verify_retrieval_returns_true_for_matching_hit_at_threshold(tmp_path) -> None:
    record = make_record()
    worker = VerificationWorker(
        tmp_path,
        retrieve_payloads=[matching_payload(record.intended_path, 0.5)],
    )

    assert worker.verify_retrieval(record, SUCCESS_MARKDOWN) is True
    assert worker.retrieve_calls == [
        {
            "query": "Verified Research Title",
            "top_k": 10,
            "sources": ["research"],
        }
    ]


def test_verify_retrieval_returns_false_when_score_below_threshold(tmp_path) -> None:
    record = make_record()
    worker = VerificationWorker(
        tmp_path,
        retrieve_payloads=[matching_payload(record.intended_path, 0.49)],
    )

    assert worker.verify_retrieval(record, SUCCESS_MARKDOWN) is False


def test_verify_retrieval_returns_false_when_path_missing(tmp_path) -> None:
    worker = VerificationWorker(
        tmp_path,
        retrieve_payloads=[matching_payload("docs/testing/other.md", 0.9)],
    )

    assert worker.verify_retrieval(make_record(), SUCCESS_MARKDOWN) is False


def test_process_record_sets_indexing_pending_on_verification_failure(tmp_path) -> None:
    worker = VerificationWorker(
        tmp_path,
        retrieve_payloads=[matching_payload("docs/testing/other.md", 0.9)],
    )

    completed = worker.process_record(make_record())

    assert completed.status == "indexing_pending"
    assert "not found" in (completed.error or "")
    assert completed.committed_sha == "abc123"


def test_process_record_sets_indexing_pending_on_reformat_fallback(tmp_path) -> None:
    record = make_record()
    worker = VerificationWorker(
        tmp_path,
        retrieve_payloads=[matching_payload(record.intended_path, 0.9)],
        reformat_exception=research_worker.OllamaError("frontmatter contract failed"),
    )

    completed = worker.process_record(record)

    assert completed.status == "indexing_pending"
    assert "reformat fallback used" in (completed.error or "")


def test_process_record_sets_indexing_pending_on_metadata_fallback(tmp_path) -> None:
    record = make_record()
    worker = VerificationWorker(
        tmp_path,
        retrieve_payloads=[matching_payload(record.intended_path, 0.9)],
        metadata_exception=research_worker.OllamaError("metadata JSON invalid"),
    )

    completed = worker.process_record(record)

    assert completed.status == "indexing_pending"
    assert "metadata fallback" in (completed.error or "")


def test_process_next_record_reenqueues_once_then_flips_to_error(tmp_path) -> None:
    record = make_record()
    worker = VerificationWorker(
        tmp_path,
        retrieve_payloads=[
            matching_payload("docs/testing/other.md", 0.9),
            matching_payload("docs/testing/other.md", 0.9),
        ],
    )
    research_worker.enqueue_pending(tmp_path, record)

    assert worker.process_next_record() is True
    first_completed = read_completed(tmp_path)
    assert first_completed[-1].status == "indexing_pending"
    assert len(list(worker.pending_dir.glob("*.json"))) == 1

    assert worker.process_next_record() is True
    second_completed = read_completed(tmp_path)
    assert second_completed[-1].status == "error"
    assert "retrieval verification failed" in (second_completed[-1].error or "")
    assert list(worker.pending_dir.glob("*.json")) == []


def test_query_source_priority_prefers_title_then_h1_then_paragraph() -> None:
    assert research_worker.build_retrieval_verify_query(SUCCESS_MARKDOWN) == (
        "Verified Research Title",
        "title",
    )

    h1_markdown = """# Heading Wins

Paragraph body.
"""
    assert research_worker.build_retrieval_verify_query(h1_markdown) == ("Heading Wins", "h1")

    paragraph_markdown = (
        "\n\nFirst paragraph should be selected because there is no heading.\n\n"
        "Second paragraph is ignored."
    )
    query, source = research_worker.build_retrieval_verify_query(paragraph_markdown)
    assert source == "paragraph"
    assert query == "First paragraph should be selected because there is no heading."
