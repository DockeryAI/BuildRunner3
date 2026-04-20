"""BR3-owned checkpoint store for runtime task envelopes."""

from __future__ import annotations

import json
from pathlib import Path

from core.runtime.result_schema import CheckpointRecord


class OrchestrationCheckpointStore:
    """Persist BR3 checkpoints without depending on model-internal session resume."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, record: CheckpointRecord) -> Path:
        path = self.root / f"{record.task_id}-{record.checkpoint_id}.json"
        path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return path

    def load(self, task_id: str, checkpoint_id: str) -> CheckpointRecord:
        path = self.root / f"{task_id}-{checkpoint_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CheckpointRecord(**payload)
