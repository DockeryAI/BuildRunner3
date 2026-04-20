import importlib.util
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / "core/cluster/cross_model_review.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cross_model_review", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_semver_and_supported_range():
    module = load_module()

    assert module.parse_semver("codex-cli 0.48.0") == (0, 48, 0)
    assert module.is_supported_codex_version((0, 48, 0)) is True
    assert module.is_supported_codex_version((0, 47, 9)) is False
    assert module.is_supported_codex_version((0, 49, 0)) is False


def test_parse_codex_event_stream_extracts_final_message_and_usage():
    module = load_module()
    stdout = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "abc"}),
            json.dumps({"type": "turn.started"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"id": "item_0", "type": "agent_message", "text": "[]"},
                }
            ),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {"input_tokens": 123, "output_tokens": 9},
                }
            ),
        ]
    )

    events = module.parse_codex_event_stream(stdout)
    message, usage = module.extract_codex_message_and_usage(events)

    assert [event["type"] for event in events] == [
        "thread.started",
        "turn.started",
        "item.completed",
        "turn.completed",
    ]
    assert message == "[]"
    assert usage == {"input_tokens": 123, "output_tokens": 9}


def test_check_codex_auth_missing_token(monkeypatch, tmp_path):
    module = load_module()
    monkeypatch.setattr(module, "HOME", tmp_path)

    auth_dir = tmp_path / ".codex"
    auth_dir.mkdir()
    (auth_dir / "auth.json").write_text('{"tokens": {}}', encoding="utf-8")

    assert module.check_codex_auth() == (False, "Codex tokens missing. Run: codex")


def test_extract_changed_files_skips_path_traversal():
    from core.runtime.context_compiler import extract_changed_files

    changed_files = extract_changed_files(
        "\n".join(
            [
                "+++ b/api/app.py",
                "+++ b/../../etc/passwd",
                "+++ b//absolute/path.txt",
            ]
        )
    )

    assert changed_files == ["api/app.py"]


def test_review_via_codex_timeout_logs_runtime_metadata(monkeypatch, tmp_path):
    module = load_module()
    monkeypatch.setattr(module, "RUNTIME_CAPABILITY_LOG", tmp_path / "runtime-capability.log")
    monkeypatch.setattr(
        module,
        "ensure_codex_compatible",
        lambda: {"raw": "codex-cli 0.48.0", "parsed": (0, 48, 0)},
    )
    monkeypatch.setattr(module, "check_codex_auth", lambda project_root=None, command="codex": (True, None))

    def fake_run(cmd, capture_output, text, timeout, cwd):
        assert cwd.startswith("/tmp/") or "br3-codex-live-review-" in cwd
        assert "--ask-for-approval" in cmd
        assert "--skip-git-repo-check" in cmd
        raise subprocess.TimeoutExpired(cmd="codex", timeout=5)

    with patch.object(module.subprocess, "run", side_effect=fake_run):
        with pytest.raises(RuntimeError, match="Codex timed out after 5s"):
            module.review_via_codex(
                "reply with only []",
                {"backends": {"codex": {"timeout_seconds": 5}}},
                "/tmp/project",
                "deadbeef",
            )

    log_path = tmp_path / "runtime-capability.log"
    assert log_path.exists()
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["backend"] == "codex"
    assert entry["commit_sha"] == "deadbeef"
    assert entry["status"] == "error"
    assert entry["error_class"] == "RuntimeError"
    assert entry["isolated"] is True
