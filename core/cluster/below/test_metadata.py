from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from core.cluster.below.queue_schema import PendingRecord
from core.cluster.below.research_worker import generate_metadata
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


@pytest.mark.skipif(not _ollama_reachable(), reason="ollama unreachable")
def test_metadata_response_is_valid_json_with_required_keys() -> None:
    record = PendingRecord(
        id="1e06c6c9-e507-4b98-a071-c6b9876dc001",
        title="Research queue failure handling",
        draft_markdown=(
            "The worker retries Ollama failures with exponential backoff and never drops a queue "
            "record silently. It commits validated markdown into Jimmy's research library."
        ),
        intended_path="docs/architecture/research-queue-failures.md",
        sources=["notes://phase-6"],
        created_at="2026-04-22T00:00:00Z",
    )

    metadata = generate_metadata(record)
    serialized = json.dumps(metadata)
    parsed = json.loads(serialized)

    assert set(parsed) == {"topic", "tags", "domain", "difficulty"}
    assert isinstance(parsed["tags"], list)
