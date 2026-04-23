"""
BR3 Cluster — Otis TypeCheck Worker
Phase 6: tsc --noEmit --watch per BR3 project, publishes error counts
via the Phase 1 workloads[] schema.

Phase 1 schema (workloads[] entry):
    {
        "name": "tsc",
        "pid": int | None,
        "cpu_pct": float,
        "started_at": str,   # ISO-8601
        "project": str,      # repo path
        "error_count": int,
    }

Dashboard label: "tsc-watch · N projects · M errors"
busy_state: "idle" | "active" | "saturated"
"""

import os
import re
import time
import signal
import threading
import subprocess
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

logger = logging.getLogger("otis.typecheck")

# ── Constants ──────────────────────────────────────────────────────────────────

PROJECTS_FILE = os.environ.get(
    "OTIS_PROJECTS_FILE",
    os.path.expanduser("~/.buildrunner/otis-projects.txt"),
)
HEARTBEAT_PATH = os.environ.get(
    "OTIS_HEARTBEAT",
    os.path.expanduser(
        "~/Projects/BuildRunner3/.buildrunner/locks/phase-6/heartbeat"
    ),
)
HEARTBEAT_INTERVAL = int(os.environ.get("OTIS_HEARTBEAT_INTERVAL", "30"))

# Regex: TypeScript watch output lines
# "Found 3 error(s). Watching for file changes."
# "Found 0 errors. Watching for file changes."
_TSC_ERROR_RE = re.compile(r"Found\s+(\d+)\s+error", re.IGNORECASE)
_TSC_WATCHING_RE = re.compile(r"Watching for file changes", re.IGNORECASE)

# Threshold for busy_state classification
_SATURATED_PROJECTS = 5   # >= this many erroring projects → saturated


# ── Dataclass for per-project state ──────────────────────────────────────────

@dataclass
class _ProjectState:
    project: str          # repo path (absolute)
    proc: Optional[subprocess.Popen] = None
    pid: Optional[int] = None
    error_count: int = 0
    started_at: Optional[str] = None
    last_output_at: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def to_workload(self) -> dict:
        cpu = 0.0
        if _HAS_PSUTIL and self.pid is not None:
            try:
                cpu = psutil.Process(self.pid).cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                cpu = 0.0
        return {
            "name": "tsc",
            "pid": self.pid,
            "cpu_pct": cpu,
            "started_at": self.started_at or "",
            "project": self.project,
            "error_count": self.error_count,
        }


# ── TypecheckWorker — one per project ────────────────────────────────────────

class TypecheckWorker:
    """Manages a single `tsc --noEmit --watch` subprocess for one project."""

    def __init__(self, project_path: str):
        self._path = project_path
        self._state = _ProjectState(project=project_path)
        self._reader: Optional[threading.Thread] = None
        self._active = False

    # ── Public ──────────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Launch tsc --watch. Returns True if started successfully."""
        if self._active and self._state.proc and self._state.proc.poll() is None:
            return True  # already running

        tsconfig = Path(self._path) / "tsconfig.json"
        if not tsconfig.exists():
            logger.warning("No tsconfig.json in %s — skipping", self._path)
            return False

        tsc_bin = self._find_tsc()
        if not tsc_bin:
            logger.warning("No tsc binary found for %s — skipping", self._path)
            return False

        cmd = [tsc_bin, "--noEmit", "--watch", "--pretty", "false"]
        env = {**os.environ, "FORCE_COLOR": "0"}

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=self._path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                start_new_session=True,
            )
        except (OSError, FileNotFoundError) as exc:
            logger.error("Failed to start tsc for %s: %s", self._path, exc)
            return False

        with self._state._lock:
            self._state.proc = proc
            self._state.pid = proc.pid
            self._state.started_at = datetime.now(timezone.utc).isoformat()
            self._state.error_count = 0
        self._active = True

        # Background reader
        self._reader = threading.Thread(
            target=self._read_output,
            args=(proc,),
            daemon=True,
            name=f"tsc-reader-{Path(self._path).name}",
        )
        self._reader.start()
        logger.info("Started tsc watch pid=%s for %s", proc.pid, self._path)
        return True

    def stop(self, timeout: float = 3.0):
        """SIGTERM → SIGKILL after timeout. Frees compilation cache."""
        self._active = False
        with self._state._lock:
            proc = self._state.proc
            pid = self._state.pid

        if proc is None or proc.poll() is not None:
            return

        logger.info("Stopping tsc pid=%s for %s", pid, self._path)
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

        deadline = time.time() + timeout
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            time.sleep(0.1)

        if proc.poll() is None:
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

        with self._state._lock:
            self._state.proc = None
            self._state.pid = None
            self._state.started_at = None

        # tsc stores .tsbuildinfo — remove it to free compilation cache
        self._clear_build_cache()
        logger.info("Stopped tsc for %s", self._path)

    def workload(self) -> dict:
        with self._state._lock:
            return self._state.to_workload()

    def is_alive(self) -> bool:
        with self._state._lock:
            return self._state.proc is not None and self._state.proc.poll() is None

    # ── Internal ──────────────────────────────────────────────────────────

    def _read_output(self, proc: subprocess.Popen):
        """Read tsc stdout, parse error counts."""
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                m = _TSC_ERROR_RE.search(line)
                if m:
                    count = int(m.group(1))
                    with self._state._lock:
                        self._state.error_count = count
                        self._state.last_output_at = time.time()
                    if count > 0:
                        logger.debug("tsc %s: %d error(s)", Path(self._path).name, count)
                    else:
                        logger.debug("tsc %s: clean", Path(self._path).name)
        except (ValueError, OSError):
            pass

    def _find_tsc(self) -> Optional[str]:
        """Locate tsc: project node_modules first, then global."""
        candidates = [
            Path(self._path) / "node_modules" / ".bin" / "tsc",
            Path(self._path) / "node_modules" / "typescript" / "bin" / "tsc",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        # Global
        try:
            result = subprocess.run(
                ["which", "tsc"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
        return None

    def _clear_build_cache(self):
        """Remove .tsbuildinfo files to free compilation cache after stop."""
        try:
            for p in Path(self._path).rglob("*.tsbuildinfo"):
                if "node_modules" in p.parts:
                    continue
                p.unlink(missing_ok=True)
        except OSError:
            pass


# ── TypecheckManager — coordinates all workers ───────────────────────────────

class TypecheckManager:
    """Manages a pool of TypecheckWorkers, one per registered project.

    Projects are loaded from OTIS_PROJECTS_FILE (one path per line).
    Exposes workloads() → list[dict] in Phase 1 schema format.
    Pause/resume via HTTP (handled by otis_service.py routes).
    """

    def __init__(self, projects_file: str = PROJECTS_FILE):
        self._projects_file = projects_file
        self._workers: dict[str, TypecheckWorker] = {}  # project_path → worker
        self._lock = threading.Lock()
        self._paused = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._running = False

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self):
        """Load projects and start all workers."""
        self._running = True
        projects = self._load_projects()
        logger.info("TypecheckManager starting with %d projects", len(projects))

        with self._lock:
            for path in projects:
                w = TypecheckWorker(path)
                w.start()
                self._workers[path] = w

        # Heartbeat thread
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True, name="tsc-heartbeat"
        )
        self._heartbeat_thread.start()

        # Watchdog: restart crashed workers
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="tsc-watchdog"
        )
        self._watchdog_thread.start()

        self._touch_heartbeat()

    def stop(self):
        """Stop all workers."""
        self._running = False
        with self._lock:
            for w in self._workers.values():
                w.stop()
            self._workers.clear()

    def pause(self):
        """SIGTERM all running workers. On resume they cold-start (~8s each)."""
        with self._lock:
            if self._paused:
                return
            logger.info("Pausing all tsc workers (dispatch arrived)")
            for w in self._workers.values():
                w.stop()
            self._paused = True

    def resume(self):
        """Cold-start all workers after dispatch exits."""
        with self._lock:
            if not self._paused:
                return
            logger.info("Resuming all tsc workers (dispatch exited)")
            projects = self._load_projects()
            self._workers.clear()
            for path in projects:
                w = TypecheckWorker(path)
                w.start()
                self._workers[path] = w
            self._paused = False
        self._touch_heartbeat()

    # ── Schema output ──────────────────────────────────────────────────────

    def workloads(self) -> list[dict]:
        """Return workloads[] in Phase 1 schema format."""
        try:
            with self._lock:
                if not _HAS_PSUTIL:
                    return []
                return [w.workload() for w in self._workers.values()]
        except Exception:
            return []

    def status(self) -> dict:
        """Full status dict for /status endpoint."""
        wl = self.workloads()
        total_errors = sum(w["error_count"] for w in wl)
        active_count = sum(1 for w in wl if w["pid"] is not None)
        erroring = sum(1 for w in wl if w["error_count"] > 0)

        if self._paused:
            busy_state = "idle"
        elif erroring >= _SATURATED_PROJECTS:
            busy_state = "saturated"
        elif active_count > 0:
            busy_state = "active"
        else:
            busy_state = "idle"

        return {
            "label": f"tsc-watch · {active_count} projects · {total_errors} errors",
            "busy_state": busy_state,
            "paused": self._paused,
            "project_count": len(self._workers),
            "active_count": active_count,
            "total_errors": total_errors,
            "workloads": wl,
        }

    # ── Internal ──────────────────────────────────────────────────────────

    def _load_projects(self) -> list[str]:
        """Load project paths from file. Skips blank lines and comments."""
        path = Path(self._projects_file)
        if not path.exists():
            logger.warning("Projects file not found: %s", self._projects_file)
            return []
        lines = path.read_text().splitlines()
        projects = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            expanded = os.path.expanduser(line)
            if Path(expanded).exists():
                projects.append(expanded)
            else:
                logger.warning("Project path not found, skipping: %s", expanded)
        return projects

    def _heartbeat_loop(self):
        """Touch heartbeat file every HEARTBEAT_INTERVAL seconds."""
        while self._running:
            self._touch_heartbeat()
            time.sleep(HEARTBEAT_INTERVAL)

    def _touch_heartbeat(self):
        try:
            hb = Path(HEARTBEAT_PATH)
            hb.parent.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            hb.write_text(ts + "\n")
        except OSError as e:
            logger.debug("Heartbeat write failed: %s", e)

    def _watchdog_loop(self):
        """Restart crashed workers every 60s unless paused."""
        while self._running:
            time.sleep(60)
            if self._paused:
                continue
            with self._lock:
                for path, w in self._workers.items():
                    if not w.is_alive() and not self._paused:
                        logger.warning("tsc worker for %s died — restarting", path)
                        w.start()


# ── Module-level singleton ─────────────────────────────────────────────────────

_manager: Optional[TypecheckManager] = None


def get_manager() -> TypecheckManager:
    """Return (or create) the module-level TypecheckManager."""
    global _manager
    if _manager is None:
        _manager = TypecheckManager()
    return _manager
