"""Below research handoff worker.

This worker consumes pending queue records, reformats research drafts with
Below-local Ollama, commits validated documents into Jimmy's research library,
triggers a reindex, and appends a completed record for every processed item.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from core.cluster.below.queue_schema import CompletedRecord, PendingRecord
from core.cluster.cluster_config import (
    get_below_ollama_url,
    get_jimmy_br3_root,
    get_jimmy_research_root,
    get_jimmy_semantic_url,
    get_jimmy_ssh_target,
)

logger = logging.getLogger(__name__)

REQUIRED_FRONTMATTER_KEYS = [
    "title",
    "domain",
    "techniques",
    "concepts",
    "subjects",
    "priority",
    "source_project",
    "created",
    "last_updated",
]
RETRY_DELAYS_SECONDS = (1, 2, 4)
REINDEX_TIMEOUT_SECONDS = 60
REINDEX_POLL_SECONDS = 5
RESEARCH_QUEUE_DIR = Path(".buildrunner") / "research-queue"
REPO_ROOT = Path(__file__).resolve().parents[3]
REFORMAT_PROMPT_PATH = Path(__file__).with_name("reformat_prompt.md")
METADATA_PROMPT_PATH = Path(__file__).with_name("metadata_prompt.md")
_SSH_CONNECT_TIMEOUT_SECONDS = 10


class WorkerError(RuntimeError):
    """Base error for worker failures."""


class OllamaError(WorkerError):
    """Raised when Ollama generation fails."""


class SchemaViolationError(WorkerError):
    """Raised when Jimmy-side validation fails."""


class CommitError(WorkerError):
    """Raised when a Jimmy git operation fails."""


SchemaViolation = SchemaViolationError


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_queue_dir(queue_dir: Path) -> int:
    """Create the queue scaffold when it does not exist.

    Returns the number of newly created files.
    """
    queue_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    for path in (
        queue_dir / ".gitkeep",
        queue_dir / "pending.jsonl",
        queue_dir / "completed.jsonl",
    ):
        if not path.exists():
            path.touch()
            created += 1
    return created


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _build_prompt(prompt_path: Path, record: PendingRecord) -> str:
    prompt = _read_prompt(prompt_path)
    return (
        f"{prompt}\n\n"
        f"Title: {record.title}\n"
        f"Created at: {record.created_at}\n"
        f"Intended path: {record.intended_path}\n"
        f"Sources: {json.dumps(record.sources, ensure_ascii=False)}\n\n"
        "Draft markdown:\n"
        f"{record.draft_markdown.strip()}\n"
    )


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(  # noqa: S310
        url,
        data=body,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            error_message = parsed.get("error") or parsed
        except json.JSONDecodeError:
            error_message = detail or f"HTTP {exc.code}"
        raise OllamaError(f"Ollama error: {error_message}") from exc
    except urllib.error.URLError as exc:
        raise OllamaError(f"Ollama connection failed: {exc.reason}") from exc


def _strip_wrapping_code_fence(markdown: str) -> str:
    stripped = markdown.lstrip()
    if not stripped.startswith("```"):
        return markdown
    first_newline = stripped.find("\n")
    if first_newline == -1:
        return markdown
    closing = stripped.rfind("```")
    if closing <= first_newline:
        return markdown
    return stripped[first_newline + 1 : closing].rstrip()


def _trim_preamble_to_frontmatter(markdown: str) -> str:
    markdown = markdown.lstrip("﻿").lstrip()
    if markdown.startswith("---\n") or markdown.startswith("---\r\n"):
        return markdown
    marker = "\n---\n"
    index = markdown.find(marker)
    if index == -1:
        marker = "\n---\r\n"
        index = markdown.find(marker)
    if index == -1:
        return markdown
    return markdown[index + 1 :]


def _load_frontmatter_from_markdown(markdown: str) -> dict[str, Any]:
    markdown = _strip_wrapping_code_fence(markdown)
    markdown = _trim_preamble_to_frontmatter(markdown)
    markdown = _normalize_frontmatter(markdown)
    if not markdown.startswith("---\n") and not markdown.startswith("---\r\n"):
        raise OllamaError("Ollama output missing YAML frontmatter")

    end_index = markdown.find("\n---", 4)
    if end_index == -1:
        raise OllamaError("Ollama output missing closing frontmatter fence")

    try:
        frontmatter = yaml.safe_load(markdown[4:end_index]) or {}
    except yaml.YAMLError as exc:
        raise OllamaError(f"Ollama output YAML parse failed: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise OllamaError("Ollama output frontmatter is not a mapping")
    return frontmatter


def _normalize_frontmatter(markdown: str) -> str:
    if not markdown.startswith("---\n") or "\n---" in markdown[4:]:
        return markdown

    lines = markdown.splitlines()
    if not lines or lines[0] != "---":
        return markdown

    for index, line in enumerate(lines[1:], start=1):
        if line.strip():
            continue
        frontmatter_text = "\n".join(lines[1:index]).strip()
        if not frontmatter_text:
            break
        parsed = yaml.safe_load(frontmatter_text) or {}
        if isinstance(parsed, dict):
            body = "\n".join(lines[index + 1 :]).strip()
            normalized = f"---\n{frontmatter_text}\n---"
            if body:
                normalized = f"{normalized}\n\n{body}"
            return normalized
        break

    return markdown


def _missing_frontmatter_keys(markdown: str) -> list[str]:
    frontmatter = _load_frontmatter_from_markdown(markdown)
    return [key for key in REQUIRED_FRONTMATTER_KEYS if key not in frontmatter]


def _parse_metadata_json(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama metadata response was not valid JSON") from exc

    required = {"topic", "tags", "domain", "difficulty"}
    missing = sorted(required.difference(payload))
    if missing:
        missing_str = ", ".join(missing)
        raise OllamaError(f"Ollama metadata response missing keys: {missing_str}")

    if not isinstance(payload.get("tags"), list):
        raise OllamaError("Ollama metadata response field 'tags' must be a list")

    difficulty = payload.get("difficulty")
    if difficulty not in {"beginner", "intermediate", "advanced"}:
        raise OllamaError("Ollama metadata response field 'difficulty' is invalid")

    return payload


def _ollama_generate(
    *,
    model: str,
    prompt: str,
    format_json: bool = False,
    num_predict: int = 1024,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": num_predict,
        },
    }
    if model == "llama3.3:70b":
        payload["options"]["num_ctx"] = int(os.environ.get("BR3_BELOW_LLAMA_NUM_CTX", "4096"))
        payload["options"]["num_gpu"] = 99
        payload["options"]["temperature"] = 0.0
    elif model.startswith("qwen2.5"):
        payload["options"]["num_ctx"] = int(os.environ.get("BR3_BELOW_QWEN25_NUM_CTX", "16384"))
        payload["options"]["temperature"] = 0.0
    elif model.startswith("qwen3"):
        payload["options"]["num_ctx"] = int(os.environ.get("BR3_BELOW_QWEN_NUM_CTX", "4096"))
        payload["options"]["temperature"] = 0.2
        payload["options"]["presence_penalty"] = 1.5
        payload["think"] = False
    if format_json:
        payload["format"] = "json"

    body = _http_json("POST", f"{get_below_ollama_url()}/api/generate", payload=payload)
    response_text = body.get("response")
    if not isinstance(response_text, str) or not response_text.strip():
        raise OllamaError("Ollama returned an empty response")
    return response_text.strip()


def generate_reformatted_markdown(record: PendingRecord) -> str:
    """Call Below-local Ollama to generate a schema-conformant document.

    Uses qwen2.5:14b by default — llama3.3:70b consistently failed to emit
    the required 9-key YAML frontmatter across 4 consecutive runs (2026-04-23).
    qwen2.5:14b follows strict output contracts reliably. Override via
    BR3_BELOW_REFORMAT_MODEL env var.
    """
    prompt = _build_prompt(REFORMAT_PROMPT_PATH, record)
    model = os.environ.get("BR3_BELOW_REFORMAT_MODEL", "qwen2.5:14b")
    raw = _ollama_generate(model=model, prompt=prompt, num_predict=8192)
    cleaned = _trim_preamble_to_frontmatter(_strip_wrapping_code_fence(raw))
    markdown = _normalize_frontmatter(cleaned)
    missing = _missing_frontmatter_keys(markdown)
    if missing:
        missing_str = ", ".join(missing)
        raise OllamaError(f"Ollama output missing frontmatter keys: {missing_str}")
    return markdown


def _synthesize_frontmatter_fallback(record: PendingRecord) -> str:
    """Build a schema-valid document from the record without Ollama.

    Used as a last-resort fallback when llama3.3:70b consistently fails to
    emit YAML frontmatter. Produces a minimal but valid document so the
    record can be committed rather than blocking the queue indefinitely.
    """
    today = datetime.now(UTC).date().isoformat()
    created = (record.created_at or "").split("T", 1)[0] or today
    title = record.title or "Untitled Research Document"
    title_yaml = title.replace('"', '\\"')
    frontmatter_lines = [
        "---",
        f'title: "{title_yaml}"',
        "domain: uncategorized",
        "techniques: []",
        "concepts: []",
        "subjects: []",
        "priority: medium",
        "source_project: BuildRunner3",
        f"created: {created}",
        f"last_updated: {today}",
        "---",
        "",
    ]
    body = (record.draft_markdown or "").lstrip()
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4 :].lstrip()
    return "\n".join(frontmatter_lines) + body


def generate_metadata(record: PendingRecord) -> dict[str, Any]:
    """Call Below-local Ollama to extract strict JSON metadata.

    Uses qwen2.5:14b by default — qwen3:8b intermittently emitted
    non-parseable JSON under ``format=json`` on 2026-04-23, forcing the
    empty-metadata fallback. qwen2.5:14b follows strict output contracts
    reliably (same rationale as the reformat step). Override via
    BR3_BELOW_METADATA_MODEL env var.
    """
    prompt = _build_prompt(METADATA_PROMPT_PATH, record)
    model = os.environ.get("BR3_BELOW_METADATA_MODEL", "qwen2.5:14b")
    metadata_text = _ollama_generate(
        model=model,
        prompt=prompt,
        format_json=True,
        num_predict=512,
    )
    return _parse_metadata_json(metadata_text)


def _run_command(
    command: list[str],
    *,
    input_text: str | None = None,
    cwd: Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        command,
        input=input_text,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
        check=False,
    )


def _normalize_git_failure(result: subprocess.CompletedProcess[str], action: str) -> str:
    detail = result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}"
    return f"git {action} failed: {detail}"


def _safe_target_path(root: Path, intended_path: str) -> Path:
    target = (root / intended_path).resolve()
    target.relative_to(root.resolve())
    return target


def _run_validator_locally(target_path: Path) -> None:
    validator_python = os.environ.get("BR3_JIMMY_VALIDATE_PYTHON", sys.executable)
    validator_script = Path(
        os.environ.get(
            "BR3_JIMMY_VALIDATE_SCRIPT",
            Path(get_jimmy_br3_root()) / "core/cluster/below/validate_document.py",
        )
    )
    result = _run_command(
        [validator_python, str(validator_script), str(target_path)],
        timeout=120,
    )
    if result.returncode != 0:
        raise SchemaViolation(result.stdout.strip() or result.stderr.strip() or "schema violation")


def _commit_local_repo(record: PendingRecord, reformatted_md: str, metadata: dict[str, Any]) -> str:
    del metadata
    research_root = Path(get_jimmy_research_root())
    repo_root = Path(os.environ.get("BR3_JIMMY_GIT_ROOT", str(research_root)))
    target_path = _safe_target_path(research_root, record.intended_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(reformatted_md, encoding="utf-8")
    _run_validator_locally(target_path)

    relative_path = str(target_path.relative_to(repo_root))
    commit_title = record.title.replace("\n", " ").strip()

    add_result = _run_command(["git", "-C", str(repo_root), "add", relative_path])
    if add_result.returncode != 0:
        raise CommitError(_normalize_git_failure(add_result, "add"))

    commit_result = _run_command(
        [
            "git",
            "-C",
            str(repo_root),
            "commit",
            "-m",
            f"research: add {commit_title} [auto]",
        ]
    )
    if commit_result.returncode != 0:
        raise CommitError(_normalize_git_failure(commit_result, "commit"))

    remotes_result = _run_command(["git", "-C", str(repo_root), "remote"])
    configured_remotes = (
        set(remotes_result.stdout.split()) if remotes_result.returncode == 0 else set()
    )
    if "muddy" in configured_remotes:
        push_result = _run_command(["git", "-C", str(repo_root), "push", "muddy", "HEAD:main"])
        if push_result.returncode != 0:
            raise CommitError(_normalize_git_failure(push_result, "push"))

    sha_result = _run_command(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    if sha_result.returncode != 0:
        raise CommitError(_normalize_git_failure(sha_result, "rev-parse"))
    return sha_result.stdout.strip()


_REMOTE_COMMIT_SCRIPT = r"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


payload = json.loads(sys.stdin.read())
research_root = Path(payload["research_root"]).resolve()
repo_root = Path(payload["repo_root"]).resolve()
target_path = (research_root / payload["intended_path"]).resolve()
target_path.relative_to(research_root)
target_path.parent.mkdir(parents=True, exist_ok=True)
target_path.write_text(payload["markdown"], encoding="utf-8")

validator = run([
    payload["validator_python"],
    payload["validator_script"],
    str(target_path),
])
if validator.returncode != 0:
    print(json.dumps({
        "ok": False,
        "type": "schema",
        "stdout": validator.stdout,
        "stderr": validator.stderr,
    }))
    raise SystemExit(1)

relative_path = str(target_path.relative_to(repo_root))
commit_title = payload["title"].replace("\n", " ").strip()
steps = [
    ("add", ["git", "-C", str(repo_root), "add", relative_path]),
    (
        "commit",
        [
            "git",
            "-C",
            str(repo_root),
            "commit",
            "-m",
            f"research: add {commit_title} [auto]",
        ],
    ),
]
remotes_result = run(["git", "-C", str(repo_root), "remote"])
configured_remotes = (
    set(remotes_result.stdout.split()) if remotes_result.returncode == 0 else set()
)
if "muddy" in configured_remotes:
    steps.append(("push", ["git", "-C", str(repo_root), "push", "muddy", "HEAD:main"]))
for name, command in steps:
    result = run(command)
    if result.returncode != 0:
        print(json.dumps({
            "ok": False,
            "type": name,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }))
        raise SystemExit(1)

sha = run(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
if sha.returncode != 0:
    print(json.dumps({
        "ok": False,
        "type": "rev-parse",
        "stdout": sha.stdout,
        "stderr": sha.stderr,
    }))
    raise SystemExit(1)

print(json.dumps({"ok": True, "sha": sha.stdout.strip()}))
""".strip()


def _commit_to_jimmy(record: PendingRecord, reformatted_md: str, metadata: dict[str, Any]) -> str:
    """Write, validate, commit, and push a research document on Jimmy."""
    if os.environ.get("BR3_RESEARCH_WORKER_LOCAL_JIMMY_ROOT"):
        return _commit_local_repo(record, reformatted_md, metadata)

    validator_python = os.environ.get(
        "BR3_JIMMY_VALIDATE_PYTHON",
        str(Path(get_jimmy_br3_root()) / ".venv/bin/python"),
    )
    validator_script = os.environ.get(
        "BR3_JIMMY_VALIDATE_SCRIPT",
        str(Path(get_jimmy_br3_root()) / "core/cluster/below/validate_document.py"),
    )
    payload = {
        "title": record.title,
        "intended_path": record.intended_path,
        "markdown": reformatted_md,
        "metadata": metadata,
        "research_root": get_jimmy_research_root(),
        "repo_root": os.environ.get("BR3_JIMMY_GIT_ROOT", get_jimmy_research_root()),
        "validator_python": validator_python,
        "validator_script": validator_script,
    }
    remote_script_path = os.environ.get(
        "BR3_JIMMY_REMOTE_HELPER",
        "/tmp/br3_research_commit.py",  # noqa: S108
    )
    script_result = _run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={_SSH_CONNECT_TIMEOUT_SECONDS}",
            get_jimmy_ssh_target(),
            f"cat > {remote_script_path}",
        ],
        input_text=_REMOTE_COMMIT_SCRIPT,
        timeout=60,
    )
    if script_result.returncode != 0:
        detail = script_result.stderr.strip() or script_result.stdout.strip()
        raise CommitError(detail or "failed to stage remote helper script")

    result = _run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={_SSH_CONNECT_TIMEOUT_SECONDS}",
            get_jimmy_ssh_target(),
            "python3",
            remote_script_path,
        ],
        input_text=json.dumps(payload),
        timeout=300,
    )
    _run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={_SSH_CONNECT_TIMEOUT_SECONDS}",
            get_jimmy_ssh_target(),
            "rm",
            "-f",
            remote_script_path,
        ],
        timeout=30,
    )
    stdout = result.stdout.strip()
    try:
        response = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        detail = stdout or result.stderr.strip() or f"exit={result.returncode}"
        raise CommitError(f"remote commit failed: {detail}") from exc

    if result.returncode != 0:
        detail = response.get("stdout") or response.get("stderr") or result.stderr.strip()
        if response.get("type") == "schema":
            raise SchemaViolation(str(detail).strip())
        raise CommitError(str(detail).strip() or "remote commit failed")

    sha = response.get("sha")
    if not isinstance(sha, str) or not sha:
        raise CommitError("remote commit did not return a commit sha")
    return sha


def _extract_chunk_count(stats: dict[str, Any]) -> int:
    raw_value = stats.get("chunk_count", stats.get("total_chunks", 0))
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return 0


def _get_research_stats() -> dict[str, Any]:
    return _http_json("GET", f"{get_jimmy_semantic_url()}/api/research/stats", timeout=15)


def _post_reindex() -> dict[str, Any]:
    return _http_json("POST", f"{get_jimmy_semantic_url()}/api/research/reindex", payload={}, timeout=15)


def _wait_for_reindex(
    pre_stats: dict[str, Any],
    *,
    commit_time_epoch: float,
    sleep_func: Any = time.sleep,
    timeout_seconds: int = REINDEX_TIMEOUT_SECONDS,
    poll_seconds: int = REINDEX_POLL_SECONDS,
) -> tuple[int, str | None]:
    _post_reindex()
    initial_chunk_count = _extract_chunk_count(pre_stats)
    deadline = time.monotonic() + timeout_seconds
    previous_indexing = bool(pre_stats.get("indexing", False))
    latest_chunk_count = initial_chunk_count

    while time.monotonic() < deadline:
        sleep_func(poll_seconds)
        stats = _get_research_stats()
        latest_chunk_count = _extract_chunk_count(stats)
        if latest_chunk_count != initial_chunk_count:
            return latest_chunk_count, None

        current_indexing = bool(stats.get("indexing", False))
        last_index = float(stats.get("last_index", 0) or 0)
        if previous_indexing and not current_indexing and last_index > commit_time_epoch:
            return latest_chunk_count, None
        previous_indexing = current_indexing

    return latest_chunk_count, "timeout waiting for chunk_count delta after 60s"


def _completed_from_invalid_line(raw_line: str, error: str) -> CompletedRecord:
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError:
        payload = {}

    pending = PendingRecord(
        id=str(payload.get("id") or uuid.uuid4()),
        title=str(payload.get("title") or "invalid-pending-record"),
        draft_markdown=str(payload.get("draft_markdown") or raw_line.rstrip("\n")),
        intended_path=str(payload.get("intended_path") or "docs/invalid/invalid-pending-record.md"),
        sources=list(payload.get("sources") or []),
        created_at=str(payload.get("created_at") or _utc_now_iso()),
    )
    return CompletedRecord(
        **asdict(pending),
        committed_sha="",
        chunk_count=0,
        status="error",
        error=error,
        completed_at=_utc_now_iso(),
        reindex_warning=None,
    )


class ResearchWorker:
    """Process the Below research queue until asked to stop."""

    def __init__(self, queue_dir: Path, poll_seconds: float = 10.0) -> None:
        self.queue_dir = queue_dir
        self.poll_seconds = poll_seconds
        self.stop_requested = False
        self.sleep = time.sleep
        ensure_queue_dir(self.queue_dir)

    @property
    def pending_path(self) -> Path:
        return self.queue_dir / "pending.jsonl"

    @property
    def completed_path(self) -> Path:
        return self.queue_dir / "completed.jsonl"

    def request_stop(self) -> None:
        self.stop_requested = True

    def generate_reformatted_markdown(self, record: PendingRecord) -> str:
        return generate_reformatted_markdown(record)

    def generate_metadata(self, record: PendingRecord) -> dict[str, Any]:
        return generate_metadata(record)

    def get_research_stats(self) -> dict[str, Any]:
        return _get_research_stats()

    def commit_to_jimmy(
        self,
        record: PendingRecord,
        reformatted_md: str,
        metadata: dict[str, Any],
    ) -> str:
        return _commit_to_jimmy(record, reformatted_md, metadata)

    def wait_for_reindex(
        self,
        pre_stats: dict[str, Any],
        *,
        commit_time_epoch: float,
    ) -> tuple[int, str | None]:
        return _wait_for_reindex(
            pre_stats,
            commit_time_epoch=commit_time_epoch,
            sleep_func=self.sleep,
        )

    def _retry_ollama(self, operation: str, func: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
            try:
                return func()
            except OllamaError as exc:
                last_error = exc
                if attempt >= len(RETRY_DELAYS_SECONDS):
                    break
                delay = RETRY_DELAYS_SECONDS[attempt]
                logger.warning("%s failed (attempt %s): %s", operation, attempt + 1, exc)
                self.sleep(delay)
        if last_error is None:
            raise OllamaError(f"{operation} failed")
        raise last_error

    def process_record(self, record: PendingRecord) -> CompletedRecord:
        pre_stats = self.get_research_stats()
        committed_sha = ""
        chunk_count = _extract_chunk_count(pre_stats)
        reindex_warning = None
        status = "ok"
        error = None

        try:
            try:
                reformatted_md = self._retry_ollama(
                    "reformat",
                    lambda: self.generate_reformatted_markdown(record),
                )
            except OllamaError as reformat_exc:
                logger.warning(
                    "reformat exhausted retries for %s; using deterministic fallback: %s",
                    record.id,
                    reformat_exc,
                )
                reformatted_md = _synthesize_frontmatter_fallback(record)
                reindex_warning = (
                    "reformat fallback used: "
                    f"{reformat_exc}. Document committed with deterministic frontmatter; "
                    "consider manual enrichment."
                )
            try:
                metadata = self._retry_ollama(
                    "metadata",
                    lambda: self.generate_metadata(record),
                )
            except OllamaError as metadata_exc:
                logger.warning(
                    "metadata exhausted retries for %s; proceeding with empty metadata: %s",
                    record.id,
                    metadata_exc,
                )
                metadata = {}
                existing = reindex_warning or ""
                reindex_warning = (existing + " " if existing else "") + (
                    f"metadata fallback: {metadata_exc}"
                )
            committed_sha = self.commit_to_jimmy(record, reformatted_md, metadata)
            chunk_count, reindex_followup = self.wait_for_reindex(
                pre_stats,
                commit_time_epoch=time.time(),
            )
            if reindex_followup:
                reindex_warning = (
                    f"{reindex_warning}; {reindex_followup}" if reindex_warning else reindex_followup
                )
        except Exception as exc:  # noqa: BLE001
            status = "error"
            error = str(exc)

        return CompletedRecord(
            **asdict(record),
            committed_sha=committed_sha,
            chunk_count=chunk_count,
            status=status,
            error=error,
            completed_at=_utc_now_iso(),
            reindex_warning=reindex_warning,
        )

    def _append_completed(self, completed: CompletedRecord) -> None:
        with self.completed_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{completed.to_jsonl()}\n")

    def _read_next_pending_line(self) -> tuple[int, str] | None:
        lines = self.pending_path.read_text(encoding="utf-8").splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.strip():
                return index, line
        return None

    def _remove_pending_line(self, line_index: int) -> None:
        lines = self.pending_path.read_text(encoding="utf-8").splitlines(keepends=True)
        if line_index >= len(lines):
            return
        del lines[line_index]
        self.pending_path.write_text("".join(lines), encoding="utf-8")

    def process_next_record(self) -> bool:
        next_line = self._read_next_pending_line()
        if next_line is None:
            return False

        line_index, raw_line = next_line
        try:
            record = PendingRecord.from_jsonl(raw_line)
            completed = self.process_record(record)
        except Exception as exc:  # noqa: BLE001
            completed = _completed_from_invalid_line(raw_line, str(exc))

        self._append_completed(completed)
        self._remove_pending_line(line_index)
        return True

    def run(self) -> int:
        logger.info("Starting Below research worker at %s", self.queue_dir)
        while True:
            processed = self.process_next_record()
            if self.stop_requested:
                logger.info("Stop requested; worker exiting cleanly")
                return 0
            if not processed:
                self.sleep(self.poll_seconds)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process the Below research queue")
    parser.add_argument(
        "--queue-dir",
        type=Path,
        default=RESEARCH_QUEUE_DIR,
        help="Queue directory containing pending.jsonl and completed.jsonl",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=10.0,
        help="Sleep interval between queue polls when idle",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("BR3_BELOW_WORKER_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = _parse_args(argv)
    worker = ResearchWorker(queue_dir=args.queue_dir, poll_seconds=args.poll_seconds)

    def _handle_signal(_signum: int, _frame: Any) -> None:
        worker.request_stop()

    signal.signal(signal.SIGTERM, _handle_signal)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _handle_signal)
    return worker.run()


if __name__ == "__main__":
    raise SystemExit(main())
