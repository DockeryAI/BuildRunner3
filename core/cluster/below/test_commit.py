from __future__ import annotations

import shutil
import subprocess
import uuid

import pytest

from core.cluster.below.queue_schema import PendingRecord
from core.cluster.below.research_worker import _commit_to_jimmy
from core.cluster.cluster_config import get_jimmy_research_root, get_jimmy_ssh_target

SSH_BIN = shutil.which("ssh") or "/usr/bin/ssh"


def _ssh_reachable() -> bool:
    result = subprocess.run(  # noqa: S603
        [
            SSH_BIN,
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=3",
            get_jimmy_ssh_target(),
            "true",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.skipif(not _ssh_reachable(), reason="jimmy unreachable")
def test_commit_to_jimmy_writes_valid_document_and_creates_commit() -> None:
    test_id = uuid.uuid4().hex
    title = f"Phase 6 automated test {test_id}"
    intended_path = f"docs/automated-tests/p6-{test_id}.md"
    record = PendingRecord(
        id=str(uuid.uuid4()),
        title=title,
        draft_markdown="# placeholder\n",
        intended_path=intended_path,
        sources=["tests://phase-6"],
        created_at="2026-04-22T00:00:00Z",
    )
    markdown = f"""---
title: {title}
domain: infrastructure
techniques:
  - queue-processing
concepts:
  - validation
subjects:
  - research-library
priority: medium
source_project: BuildRunner3
created: 2026-04-22T00:00:00Z
last_updated: 2026-04-22T00:00:00Z
---

# {title}

Synthetic integration test document.
"""
    committed_sha = ""
    metadata = {
        "topic": "Phase 6 automated test",
        "tags": ["automation", "research"],
        "domain": "infrastructure",
        "difficulty": "intermediate",
    }

    try:
        committed_sha = _commit_to_jimmy(record, markdown, metadata)

        exists_result = subprocess.run(  # noqa: S603
            [
                SSH_BIN,
                "-o",
                "BatchMode=yes",
                get_jimmy_ssh_target(),
                "test",
                "-f",
                f"{get_jimmy_research_root()}/{intended_path}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert exists_result.returncode == 0

        log_result = subprocess.run(  # noqa: S603
            [
                SSH_BIN,
                "-o",
                "BatchMode=yes",
                get_jimmy_ssh_target(),
                f"git -C {get_jimmy_research_root()} log -1 --format=%H\\ %s",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert log_result.returncode == 0
        assert committed_sha in log_result.stdout
        assert f"research: add {title} [auto]" in log_result.stdout
    finally:
        cleanup_script = (
            f"if [ -n '{committed_sha}' ]; then "
            f"git -C {get_jimmy_research_root()} reset --hard HEAD~1 && "
            f"git -C {get_jimmy_research_root()} push muddy HEAD:main --force-with-lease; "
            "else "
            f"rm -f {get_jimmy_research_root()}/{intended_path}; "
            "fi"
        )
        subprocess.run(  # noqa: S603
            [SSH_BIN, "-o", "BatchMode=yes", get_jimmy_ssh_target(), cleanup_script],
            capture_output=True,
            text=True,
            check=False,
        )
