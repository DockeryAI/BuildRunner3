from __future__ import annotations

from core.cluster.below import research_worker
from core.cluster.below.queue_schema import PendingRecord


class FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, object]:
        return self._payload


class StubWorker(research_worker.ResearchWorker):
    def get_research_stats(self) -> dict[str, object]:
        return {"total_chunks": 10}

    def generate_reformatted_markdown(self, record: PendingRecord) -> str:
        return record.draft_markdown

    def generate_metadata(self, record: PendingRecord) -> dict[str, object]:
        return {}

    def commit_to_jimmy(
        self,
        record: PendingRecord,
        reformatted_md: str,
        metadata: dict[str, object],
    ) -> str:
        return "abc123"


def make_record() -> PendingRecord:
    return PendingRecord(
        id="record-1",
        title="Correlation test",
        draft_markdown="# Draft\n",
        intended_path="docs/tests/correlation.md",
        sources=["https://example.com/source"],
        created_at="2026-04-25T00:00:00Z",
    )


def monotonic_counter(step: float = 1.0):
    state = {"value": 0.0}

    def fake_monotonic() -> float:
        value = state["value"]
        state["value"] += step
        return value

    return fake_monotonic


def test_wait_for_reindex_polls_started_job_until_done(monkeypatch) -> None:
    post_calls: list[tuple[str, dict[str, object] | None, int | float]] = []
    get_calls: list[tuple[str, int | float]] = []
    get_payloads = iter([
        {"state": "running", "rows_added": 0},
        {"state": "done", "rows_added": 3},
    ])

    def fake_post(url: str, json: dict[str, object] | None = None, timeout: int | float = 0):
        post_calls.append((url, json, timeout))
        return FakeResponse({"status": "started", "job_id": "job-started"})

    def fake_get(url: str, timeout: int | float = 0):
        get_calls.append((url, timeout))
        return FakeResponse(next(get_payloads))

    monkeypatch.setattr(research_worker.requests, "post", fake_post)
    monkeypatch.setattr(research_worker.requests, "get", fake_get)
    monkeypatch.setattr(research_worker.time, "monotonic", monotonic_counter())

    chunk_count, followup = research_worker._wait_for_reindex(  # noqa: SLF001
        {"total_chunks": 10},
        commit_time_epoch=0.0,
        sleep_func=lambda _: None,
    )

    assert chunk_count == 13
    assert followup is None
    assert post_calls == [
        (f"{research_worker.get_jimmy_semantic_url()}/api/research/reindex", {}, 15),
    ]
    assert get_calls == [
        (f"{research_worker.get_jimmy_semantic_url()}/api/research/reindex/job-started", 15),
        (f"{research_worker.get_jimmy_semantic_url()}/api/research/reindex/job-started", 15),
    ]


def test_wait_for_reindex_uses_inflight_job_id_when_already_indexing(monkeypatch) -> None:
    get_calls: list[str] = []

    def fake_post(url: str, json: dict[str, object] | None = None, timeout: int | float = 0):
        return FakeResponse({"status": "already_indexing", "job_id": "job-inflight"})

    def fake_get(url: str, timeout: int | float = 0):
        get_calls.append(url)
        return FakeResponse({"state": "done", "rows_added": 2})

    monkeypatch.setattr(research_worker.requests, "post", fake_post)
    monkeypatch.setattr(research_worker.requests, "get", fake_get)
    monkeypatch.setattr(research_worker.time, "monotonic", monotonic_counter())

    chunk_count, followup = research_worker._wait_for_reindex(  # noqa: SLF001
        {"total_chunks": 5},
        commit_time_epoch=0.0,
        sleep_func=lambda _: None,
    )

    assert chunk_count == 7
    assert followup is None
    assert get_calls == [
        f"{research_worker.get_jimmy_semantic_url()}/api/research/reindex/job-inflight",
    ]


def test_process_record_surfaces_reindex_failure(monkeypatch, tmp_path) -> None:
    worker = StubWorker(tmp_path)
    worker.sleep = lambda _: None

    def fake_post(url: str, json: dict[str, object] | None = None, timeout: int | float = 0):
        return FakeResponse({"status": "started", "job_id": "job-failed"})

    def fake_get(url: str, timeout: int | float = 0):
        return FakeResponse({"state": "failed", "rows_added": 0, "error": "boom"})

    monkeypatch.setattr(research_worker.requests, "post", fake_post)
    monkeypatch.setattr(research_worker.requests, "get", fake_get)
    monkeypatch.setattr(research_worker.time, "monotonic", monotonic_counter())

    completed = worker.process_record(make_record())

    assert completed.status == "error"
    assert completed.error == "reindex job job-failed failed: boom"
    assert completed.committed_sha == "abc123"


def test_process_record_timeout_does_not_flip_to_ok(monkeypatch, tmp_path) -> None:
    worker = StubWorker(tmp_path)
    worker.sleep = lambda _: None

    def fake_post(url: str, json: dict[str, object] | None = None, timeout: int | float = 0):
        return FakeResponse({"status": "started", "job_id": "job-timeout"})

    def fake_get(url: str, timeout: int | float = 0):
        return FakeResponse({"state": "running", "rows_added": 0})

    monkeypatch.setattr(research_worker.requests, "post", fake_post)
    monkeypatch.setattr(research_worker.requests, "get", fake_get)
    monkeypatch.setattr(research_worker.time, "monotonic", monotonic_counter())
    worker.wait_for_reindex = lambda pre_stats, *, commit_time_epoch: research_worker._wait_for_reindex(  # noqa: SLF001
        pre_stats,
        commit_time_epoch=commit_time_epoch,
        sleep_func=worker.sleep,
        timeout_seconds=2,
    )

    completed = worker.process_record(make_record())

    assert completed.status == "indexing_pending"
    assert completed.error == "timeout waiting for reindex job job-timeout after 2s"
    assert completed.committed_sha == "abc123"
