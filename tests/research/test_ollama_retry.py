from __future__ import annotations

import json
import socket

import pytest
import requests

from core.cluster.below import research_worker
from core.cluster.below.queue_schema import PendingRecord

SUCCESS_MARKDOWN = """---
title: Retry Test Title
domain: infrastructure
techniques: [fallback]
concepts: [ollama]
subjects: [research worker]
priority: medium
source_project: BuildRunner3
created: 2026-04-25
last_updated: 2026-04-25
---

# Retry Test Title

Body content for retry tests.
"""


def make_record() -> PendingRecord:
    return PendingRecord(
        id="retry-1",
        title="Retry test",
        draft_markdown="# Draft\n\nRetry body.",
        intended_path="docs/testing/retry.md",
        sources=["tests://retry"],
        created_at="2026-04-25T00:00:00Z",
    )


def matching_payload(path: str, score: float = 0.9) -> dict[str, object]:
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


def configure_attempt_log(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    attempt_log = tmp_path / ".buildrunner" / "research-queue" / "ollama-attempts.jsonl"
    monkeypatch.setattr(research_worker, "OLLAMA_ATTEMPTS_LOG_PATH", attempt_log)
    monkeypatch.setattr(research_worker, "_utc_now_iso", lambda: "2026-04-25T00:00:00Z")
    monkeypatch.setattr(
        research_worker,
        "get_below_ollama_url",
        lambda: "http://127.0.0.1:11434",
    )


def read_attempts(tmp_path) -> list[dict[str, object]]:
    attempt_log = tmp_path / ".buildrunner" / "research-queue" / "ollama-attempts.jsonl"
    return [
        json.loads(line)
        for line in attempt_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def make_worker(tmp_path) -> research_worker.ResearchWorker:
    worker = research_worker.ResearchWorker(tmp_path, poll_seconds=0)
    worker.sleep = lambda _seconds: None
    return worker


def test_retry_ollama_wraps_socket_timeout_after_retries_exhaust(monkeypatch, tmp_path) -> None:
    configure_attempt_log(monkeypatch, tmp_path)
    worker = make_worker(tmp_path)
    socket_timeout = socket.__dict__["timeout"]

    def always_timeout() -> str:
        raise socket_timeout("timed out")

    with pytest.raises(research_worker.OllamaError, match=r"^ollama_socket_timeout:") as excinfo:
        worker._retry_ollama("reformat", always_timeout)  # noqa: SLF001

    assert "timed out" in str(excinfo.value)
    attempts = read_attempts(tmp_path)
    assert len(attempts) == len(research_worker.RETRY_DELAYS_SECONDS) + 1
    assert all(attempt["operation"] == "reformat" for attempt in attempts)
    assert all(attempt["outcome"] == "error" for attempt in attempts)


def test_retry_ollama_wraps_timeout_error_after_retries_exhaust(monkeypatch, tmp_path) -> None:
    configure_attempt_log(monkeypatch, tmp_path)
    worker = make_worker(tmp_path)

    def always_timeout() -> str:
        raise TimeoutError("deadline exceeded")

    with pytest.raises(research_worker.OllamaError, match=r"^ollama_socket_timeout:") as excinfo:
        worker._retry_ollama("metadata", always_timeout)  # noqa: SLF001

    assert "deadline exceeded" in str(excinfo.value)
    attempts = read_attempts(tmp_path)
    assert len(attempts) == len(research_worker.RETRY_DELAYS_SECONDS) + 1
    assert all(attempt["operation"] == "metadata" for attempt in attempts)
    assert all(attempt["outcome"] == "error" for attempt in attempts)


def test_retry_ollama_wraps_requests_connection_error_after_retries_exhaust(
    monkeypatch,
    tmp_path,
) -> None:
    configure_attempt_log(monkeypatch, tmp_path)
    worker = make_worker(tmp_path)

    def always_connection_error() -> str:
        raise requests.exceptions.ConnectionError("connection dropped")

    with pytest.raises(research_worker.OllamaError, match=r"^ollama_socket_timeout:") as excinfo:
        worker._retry_ollama("reformat", always_connection_error)  # noqa: SLF001

    assert "connection dropped" in str(excinfo.value)
    attempts = read_attempts(tmp_path)
    assert len(attempts) == len(research_worker.RETRY_DELAYS_SECONDS) + 1
    assert all(attempt["operation"] == "reformat" for attempt in attempts)
    assert all(attempt["outcome"] == "error" for attempt in attempts)


def test_retry_ollama_writes_attempt_jsonl_for_reformat_and_metadata(monkeypatch, tmp_path) -> None:
    configure_attempt_log(monkeypatch, tmp_path)
    worker = make_worker(tmp_path)
    metadata_attempts = {"count": 0}

    assert worker._retry_ollama("reformat", lambda: SUCCESS_MARKDOWN) == SUCCESS_MARKDOWN  # noqa: SLF001

    def flaky_metadata() -> dict[str, object]:
        metadata_attempts["count"] += 1
        if metadata_attempts["count"] == 1:
            raise research_worker.OllamaError("metadata JSON invalid")
        return {
            "topic": "Retry",
            "tags": ["retry"],
            "domain": "infrastructure",
            "difficulty": "intermediate",
        }

    metadata = worker._retry_ollama("metadata", flaky_metadata)  # noqa: SLF001

    assert metadata["topic"] == "Retry"

    attempts = read_attempts(tmp_path)
    assert (tmp_path / ".buildrunner" / "research-queue" / "ollama-attempts.jsonl").exists()
    assert [attempt["operation"] for attempt in attempts] == ["reformat", "metadata", "metadata"]
    assert attempts[0]["outcome"] == "ok"
    assert attempts[1]["outcome"] == "error"
    assert attempts[2]["outcome"] == "ok"
    assert attempts[1]["error_class"] == "OllamaError"
    assert attempts[0]["host"] == "127.0.0.1:11434"
    for attempt in attempts:
        assert set(attempt) == {
            "ts",
            "operation",
            "elapsed_ms",
            "error_class",
            "retry_index",
            "host",
            "outcome",
        }
        assert attempt["ts"] == "2026-04-25T00:00:00Z"
        assert isinstance(attempt["elapsed_ms"], int)
        assert isinstance(attempt["retry_index"], int)


class FallbackWorker(research_worker.ResearchWorker):
    def __init__(self, queue_dir) -> None:
        super().__init__(queue_dir, poll_seconds=0)
        self.sleep = lambda _seconds: None

    def get_research_stats(self) -> dict[str, object]:
        return {"total_chunks": 4}

    def generate_reformatted_markdown(self, record: PendingRecord) -> str:
        del record
        raise socket.__dict__["timeout"]("body exceeded client timeout")

    def generate_metadata(self, record: PendingRecord) -> dict[str, object]:
        del record
        return {
            "topic": "Retry",
            "tags": ["retry"],
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
        return 6, None

    def retrieve_research(
        self,
        query: str,
        *,
        top_k: int = 10,
        sources: list[str] | None = None,
    ) -> dict[str, object]:
        del query, top_k, sources
        return matching_payload(make_record().intended_path)


def test_process_record_socket_timeout_uses_deterministic_frontmatter_fallback(
    monkeypatch,
    tmp_path,
) -> None:
    configure_attempt_log(monkeypatch, tmp_path)
    worker = FallbackWorker(tmp_path)

    completed = worker.process_record(make_record())

    assert completed.status == "indexing_pending"
    assert "reformat fallback used" in (completed.error or "")
    assert completed.committed_sha == "abc123"

    attempts = read_attempts(tmp_path)
    assert attempts
    assert attempts[0]["operation"] == "reformat"
