from __future__ import annotations

from typing import TYPE_CHECKING

from core.cluster.below.queue_schema import CompletedRecord, PendingRecord
from core.cluster.below.research_worker import CommitError, OllamaError, ResearchWorker

if TYPE_CHECKING:
    from pathlib import Path


def _write_pending(queue_dir, record: PendingRecord) -> None:
    with (queue_dir / "pending.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(f"{record.to_jsonl()}\n")


def _read_completed(queue_dir) -> CompletedRecord:
    lines = (queue_dir / "completed.jsonl").read_text(encoding="utf-8").splitlines()
    return CompletedRecord.from_jsonl(lines[-1])


def _record() -> PendingRecord:
    return PendingRecord(
        id="2f6ca5ef-e95f-438e-b87a-7f0b63210001",
        title="Failure modes",
        draft_markdown="# Draft\n\nFailure handling test.",
        intended_path="docs/failure-modes.md",
        sources=["tests://failure-modes"],
        created_at="2026-04-22T00:00:00Z",
    )


def test_ollama_unreachable_records_error_after_retries(tmp_path: Path) -> None:
    worker = ResearchWorker(tmp_path, poll_seconds=0)
    delays: list[int] = []
    attempts = {"count": 0}
    worker.sleep = delays.append

    def fail_reformat(record: PendingRecord) -> str:
        del record
        attempts["count"] += 1
        raise OllamaError("Ollama connection failed: connection refused")

    worker.generate_reformatted_markdown = fail_reformat
    _write_pending(tmp_path, _record())

    assert worker.process_next_record() is True
    completed = _read_completed(tmp_path)

    assert attempts["count"] == 4
    assert delays == [1, 2, 4]
    assert completed.status == "error"
    assert "Ollama" in (completed.error or "")


def test_ollama_oom_records_error_after_retries(tmp_path: Path) -> None:
    worker = ResearchWorker(tmp_path, poll_seconds=0)
    delays: list[int] = []
    attempts = {"count": 0}
    worker.sleep = delays.append

    def fail_reformat(record: PendingRecord) -> str:
        del record
        attempts["count"] += 1
        raise OllamaError("Ollama error: out of memory")

    worker.generate_reformatted_markdown = fail_reformat
    _write_pending(tmp_path, _record())

    assert worker.process_next_record() is True
    completed = _read_completed(tmp_path)

    assert attempts["count"] == 4
    assert delays == [1, 2, 4]
    assert completed.status == "error"
    assert "out of memory" in (completed.error or "")


def test_git_push_rejected_records_error_without_retry(tmp_path: Path) -> None:
    worker = ResearchWorker(tmp_path, poll_seconds=0)
    commit_calls = {"count": 0}
    worker.sleep = lambda _seconds: None
    worker.generate_reformatted_markdown = lambda _record: (
        "---\n"
        "title: Failure modes\n"
        "domain: infrastructure\n"
        "techniques: [queue-processing]\n"
        "concepts: [git]\n"
        "subjects: [jimmy]\n"
        "priority: medium\n"
        "source_project: BuildRunner3\n"
        "created: 2026-04-22T00:00:00Z\n"
        "last_updated: 2026-04-22T00:00:00Z\n"
        "---\n"
    )
    worker.generate_metadata = lambda _record: {
        "topic": "Git push",
        "tags": ["git"],
        "domain": "infrastructure",
        "difficulty": "intermediate",
    }
    worker.get_research_stats = lambda: {"chunk_count": 9, "indexing": False, "last_index": 1}

    def reject_push(record: PendingRecord, reformatted_md: str, metadata: dict[str, str]) -> str:
        del record, reformatted_md, metadata
        commit_calls["count"] += 1
        raise CommitError("git push failed: rejected non-fast-forward")

    worker.commit_to_jimmy = reject_push
    _write_pending(tmp_path, _record())

    assert worker.process_next_record() is True
    completed = _read_completed(tmp_path)

    assert commit_calls["count"] == 1
    assert completed.status == "error"
    assert "rejected non-fast-forward" in (completed.error or "")


def test_reindex_timeout_records_warning_but_keeps_ok_status(tmp_path: Path) -> None:
    worker = ResearchWorker(tmp_path, poll_seconds=0)
    worker.sleep = lambda _seconds: None
    worker.generate_reformatted_markdown = lambda _record: (
        "---\n"
        "title: Failure modes\n"
        "domain: infrastructure\n"
        "techniques: [queue-processing]\n"
        "concepts: [reindex]\n"
        "subjects: [jimmy]\n"
        "priority: medium\n"
        "source_project: BuildRunner3\n"
        "created: 2026-04-22T00:00:00Z\n"
        "last_updated: 2026-04-22T00:00:00Z\n"
        "---\n"
    )
    worker.generate_metadata = lambda _record: {
        "topic": "Reindex timeout",
        "tags": ["reindex"],
        "domain": "infrastructure",
        "difficulty": "intermediate",
    }
    worker.get_research_stats = lambda: {"chunk_count": 9, "indexing": False, "last_index": 1}
    worker.commit_to_jimmy = lambda _record, _markdown, _metadata: "deadbeef"
    worker.wait_for_reindex = lambda _stats, *, commit_time_epoch: (  # noqa: ARG005
        9,
        "timeout waiting for chunk_count delta after 60s",
    )
    _write_pending(tmp_path, _record())

    assert worker.process_next_record() is True
    completed = _read_completed(tmp_path)

    assert completed.status == "ok"
    assert completed.reindex_warning == "timeout waiting for chunk_count delta after 60s"
