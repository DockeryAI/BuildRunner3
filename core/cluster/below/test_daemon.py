from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core.cluster.below.queue_schema import CompletedRecord, PendingRecord


class _MockHandler(BaseHTTPRequestHandler):
    chunk_count = 11
    indexing = False
    last_index = 1.0

    def do_GET(self) -> None:
        if self.path == "/api/research/stats":
            payload = {
                "indexing": self.__class__.indexing,
                "last_index": self.__class__.last_index,
                "chunk_count": self.__class__.chunk_count,
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if self.path == "/api/generate":
            model = payload.get("model")
            if model == "llama3.3:70b":
                response_text = """---
title: Mocked daemon doc
domain: infrastructure
techniques:
  - queue-processing
concepts:
  - daemonization
subjects:
  - below-worker
priority: medium
source_project: BuildRunner3
created: 2026-04-22T00:00:00Z
last_updated: 2026-04-22T00:00:00Z
---

# Mocked daemon doc

Processed by the daemon test.
"""
            else:
                response_text = json.dumps(
                    {
                        "topic": "Daemon test",
                        "tags": ["worker", "queue"],
                        "domain": "infrastructure",
                        "difficulty": "beginner",
                    }
                )
            body = json.dumps({"response": response_text}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/research/reindex":
            self.__class__.indexing = True

            def finish_reindex() -> None:
                time.sleep(0.2)
                self.__class__.chunk_count += 3
                self.__class__.last_index = time.time()
                self.__class__.indexing = False

            threading.Thread(target=finish_reindex, daemon=True).start()
            body = b'{"status":"started"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, message_format: str, *args: object) -> None:
        del message_format, args


def _start_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def _init_git_repo(path: Path, remote_path: Path) -> None:
    git_bin = shutil.which("git") or "/usr/bin/git"

    def run_git(*args: str, cwd: Path | None = None, capture_output: bool = False) -> None:
        subprocess.run(  # noqa: S603
            [git_bin, *args],
            cwd=cwd,
            check=True,
            capture_output=capture_output,
        )

    path.mkdir(parents=True, exist_ok=True)
    remote_path.mkdir(parents=True, exist_ok=True)
    run_git("init", "--bare", str(remote_path), capture_output=True)
    run_git("init", cwd=path, capture_output=True)
    run_git("config", "user.email", "test@example.com", cwd=path)
    run_git("config", "user.name", "BR3 Test", cwd=path)
    run_git("remote", "add", "muddy", str(remote_path), cwd=path)
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    run_git("add", "README.md", cwd=path)
    run_git("commit", "-m", "seed", cwd=path, capture_output=True)
    run_git("branch", "-M", "main", cwd=path)
    run_git("push", "muddy", "HEAD:main", cwd=path, capture_output=True)


def test_worker_daemon_processes_queue_and_exits_cleanly(tmp_path: Path) -> None:
    queue_dir = Path("/tmp") / f"test-queue-{os.getpid()}"  # noqa: S108
    queue_dir.mkdir(parents=True, exist_ok=True)
    (queue_dir / "pending.jsonl").write_text("", encoding="utf-8")
    (queue_dir / "completed.jsonl").write_text("", encoding="utf-8")
    (queue_dir / ".gitkeep").write_text("", encoding="utf-8")

    research_root = tmp_path / "jimmy-research-library"
    muddy_remote = tmp_path / "muddy-remote.git"
    _init_git_repo(research_root, muddy_remote)
    server, base_url = _start_server()

    env = os.environ.copy()
    env["BR3_BELOW_OLLAMA_URL"] = base_url
    env["BR3_JIMMY_SEMANTIC_URL"] = base_url
    env["BR3_RESEARCH_WORKER_LOCAL_JIMMY_ROOT"] = str(research_root)
    env["BR3_JIMMY_RESEARCH_ROOT"] = str(research_root)
    env["BR3_JIMMY_GIT_ROOT"] = str(research_root)
    env["BR3_JIMMY_REPO_ROOT"] = str(Path.cwd())
    env["BR3_JIMMY_VALIDATE_PYTHON"] = sys.executable
    env["PYTHONPATH"] = str(Path.cwd())

    process = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "core.cluster.below.research_worker",
            "--queue-dir",
            str(queue_dir),
            "--poll-seconds",
            "1",
        ],
        cwd=Path.cwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        record = PendingRecord(
            id="afbb5de5-db4d-4d2d-8203-998d66de0001",
            title="Daemon queue test",
            draft_markdown="# Draft\n\nQueue worker daemon test.",
            intended_path="docs/automated-tests/daemon-test.md",
            sources=["tests://daemon"],
            created_at="2026-04-22T00:00:00Z",
        )
        with (queue_dir / "pending.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(f"{record.to_jsonl()}\n")

        deadline = time.time() + 30
        completed_record = None
        while time.time() < deadline:
            lines = (queue_dir / "completed.jsonl").read_text(encoding="utf-8").splitlines()
            if lines:
                completed_record = CompletedRecord.from_jsonl(lines[-1])
                break
            time.sleep(0.2)

        assert completed_record is not None
        assert completed_record.status == "ok"
        assert completed_record.committed_sha
        assert completed_record.chunk_count > 0
        assert completed_record.reindex_warning is None

        process.send_signal(signal.SIGTERM)
        return_code = process.wait(timeout=10)
        assert return_code == 0
    finally:
        if process.poll() is None:
            process.kill()
        server.shutdown()
        server.server_close()
