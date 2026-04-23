"""
BR3 Cluster — Process detector

Shared detector for ground-truth workload reporting on every node.
Platform branches for macOS (Apple nodes) and Windows (Below). Returns a
`{name, pid, cpu_pct, started_at, project, extra}` entry per tracked process
plus a `busy_state` enum computed from CPU, load, and workload count.

Consumed by `core/cluster/base_service.py` `/health` and
`core/cluster/node_tests.py` `/api/health` so that SSH-initiated work
(e.g. `npx vitest` run by hand) is visible in the dashboard and router.

psutil is required. Call `warmup()` once at service startup — psutil's
`cpu_percent(interval=None)` returns 0.0 on the first call on every
platform; without the warmup `busy_state` misfires to `idle` immediately
after a restart.
"""

from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass
from typing import Any

try:
    import psutil
except ImportError as exc:  # pragma: no cover — bootstrap path
    raise RuntimeError(
        "psutil is required for process_detector. "
        "Install with `pip install 'psutil>=5.9.8'`."
    ) from exc


# --------------------------------------------------------------------------- #
# Tracked workload matchers
# --------------------------------------------------------------------------- #

# Each matcher declares:
#   name      — canonical label emitted to /health
#   patterns  — substrings matched (case-insensitive) against the process
#               name AND against the joined command line. ANY match is a hit.
#   ignore    — substrings that disqualify an otherwise-matching process
#               (e.g. `vitest --version` or editor helpers)
@dataclass(frozen=True)
class WorkloadMatcher:
    name: str
    patterns: tuple[str, ...]
    ignore: tuple[str, ...] = ()


MATCHERS: tuple[WorkloadMatcher, ...] = (
    WorkloadMatcher(name="vitest", patterns=("vitest",), ignore=("--version", "vitest-mcp")),
    WorkloadMatcher(name="playwright", patterns=("playwright",), ignore=("--version", "playwright-report", "playwright-core")),
    WorkloadMatcher(name="tsc", patterns=("tsc",), ignore=("tsconfig-", "tsc-watch-wrapper")),
    WorkloadMatcher(name="ollama", patterns=("ollama",), ignore=()),
    WorkloadMatcher(name="claude", patterns=("claude",), ignore=("claude-logs", "claude-check")),
)

# Standard project roots — used to resolve the `project` label from a
# process's cwd. Extend via `BR3_PROJECT_ROOTS` env var (colon-separated).
_DEFAULT_PROJECT_ROOTS: tuple[str, ...] = (
    os.path.expanduser("~/Projects"),
    os.path.expanduser("~/repos"),
    "/srv",
    "/tmp",  # Phase 4 rsyncs shard work into /tmp/br-test-<id>/
)


def _project_roots() -> list[str]:
    extra = os.environ.get("BR3_PROJECT_ROOTS", "")
    roots = list(_DEFAULT_PROJECT_ROOTS)
    if extra:
        roots.extend(p for p in extra.split(":") if p)
    return roots


# --------------------------------------------------------------------------- #
# busy_state thresholds
# --------------------------------------------------------------------------- #

# Overridable via env for operator tuning; defaults match the BUILD spec.
_THRESH_ACTIVE_CPU = float(os.environ.get("BR3_BUSY_ACTIVE_CPU", "30"))
_THRESH_SATURATED_CPU = float(os.environ.get("BR3_BUSY_SATURATED_CPU", "75"))


# --------------------------------------------------------------------------- #
# Warmup
# --------------------------------------------------------------------------- #

_WARMED_UP = False


def warmup() -> None:
    """Prime psutil.cpu_percent so the next call returns a real reading.

    psutil docs: the first invocation of cpu_percent(interval=None) always
    returns 0.0 because it has no prior sample. Call this at service
    startup and discard the result. Idempotent.
    """
    global _WARMED_UP
    psutil.cpu_percent(interval=None)
    # Warm per-process cpu_percent too — each Process.cpu_percent() call
    # has the same zero-on-first-call quirk; detect_workloads re-primes
    # per process, but a global warmup keeps the first /health honest.
    for proc in psutil.process_iter(["pid"]):
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _WARMED_UP = True


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _infer_project(proc: "psutil.Process", cmdline: list[str]) -> str | None:
    """Resolve a human-readable project label for a process.

    Priority:
      1. cwd under a known project root -> the immediate subdir name
      2. any cmdline arg that's an absolute path under a known root
      3. any cmdline arg that matches a dir on disk under a known root
      4. None
    """
    roots = _project_roots()

    # 1. cwd
    try:
        cwd = proc.cwd()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        cwd = None
    if cwd:
        for root in roots:
            if cwd == root or cwd.startswith(root.rstrip("/") + "/"):
                rel = cwd[len(root):].lstrip("/")
                head = rel.split("/", 1)[0]
                if head:
                    return head

    # 2-3. cmdline scan
    for arg in cmdline:
        if not arg or not arg.startswith("/"):
            continue
        for root in roots:
            root_stripped = root.rstrip("/") + "/"
            if arg.startswith(root_stripped):
                rel = arg[len(root_stripped):]
                head = rel.split("/", 1)[0]
                if head:
                    return head

    return None


def _match(proc_name: str, cmdline_str: str, matcher: WorkloadMatcher) -> bool:
    haystack = f"{proc_name}\n{cmdline_str}".lower()
    if any(ign.lower() in haystack for ign in matcher.ignore):
        return False
    return any(pat.lower() in haystack for pat in matcher.patterns)


def _iter_process_entries() -> list[dict[str, Any]]:
    """Walk all visible processes; return one entry per tracked workload."""
    entries: list[dict[str, Any]] = []
    seen_pids: set[int] = set()

    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            info = proc.info
            pid = info["pid"]
            if pid in seen_pids:
                continue
            name = (info.get("name") or "").strip()
            cmdline = info.get("cmdline") or []
            cmdline_str = " ".join(cmdline)

            matched: WorkloadMatcher | None = None
            for matcher in MATCHERS:
                if _match(name, cmdline_str, matcher):
                    matched = matcher
                    break
            if not matched:
                continue

            cpu_pct = 0.0
            try:
                # Non-blocking read: interval=None returns the delta since the
                # previous call without sleeping. warmup() primes the counter
                # at startup, and subsequent /health polls get a real reading.
                # The previous interval=0.05 added N*50ms of synchronous sleep
                # to every /health response and tripped the monitor's timeout
                # when a worker was CPU-saturated.
                cpu_pct = float(proc.cpu_percent(interval=None))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            started_at = ""
            ct = info.get("create_time")
            if ct:
                started_at = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(ct))
                )

            project = _infer_project(proc, cmdline)

            entry: dict[str, Any] = {
                "name": matched.name,
                "pid": pid,
                "cpu_pct": round(cpu_pct, 1),
                "started_at": started_at,
                "project": project,
            }

            # Workload-specific extras
            if matched.name == "tsc":
                # Phase 6 emits error_count via supplemental updates; default 0.
                entry["error_count"] = 0

            entries.append(entry)
            seen_pids.add(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return entries


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def detect_workloads() -> list[dict[str, Any]]:
    """Return the current list of tracked workloads on this host."""
    if not _WARMED_UP:
        warmup()
    return _iter_process_entries()


def _loadavg() -> float:
    """1-minute load average. Falls back to 0.0 where unavailable."""
    # getloadavg exists on Unix; psutil.getloadavg is the portable path.
    try:
        return float(psutil.getloadavg()[0])
    except (AttributeError, OSError):
        pass
    try:
        return float(os.getloadavg()[0])
    except (AttributeError, OSError):
        return 0.0


def sample_host() -> dict[str, Any]:
    """Point-in-time host snapshot consumed by /health."""
    if not _WARMED_UP:
        warmup()

    cpu_pct = float(psutil.cpu_percent(interval=None))
    mem = psutil.virtual_memory()
    load_1m = _loadavg()
    cpu_count = psutil.cpu_count() or 1

    workloads = _iter_process_entries()
    busy_state = compute_busy_state(cpu_pct, load_1m, cpu_count, workloads)

    return {
        "cpu_pct": round(cpu_pct, 1),
        "load_1m": round(load_1m, 2),
        "mem_avail_pct": round(100.0 - mem.percent, 1),
        "cpu_count": cpu_count,
        "busy_state": busy_state,
        "workloads": workloads,
        "platform": platform.system(),
        "detector_version": 1,
    }


def compute_busy_state(
    cpu_pct: float,
    load_1m: float,
    cpu_count: int,
    workloads: list[dict[str, Any]],
) -> str:
    """Map raw host metrics to the canonical busy_state enum.

    idle       cpu < 30% AND no tracked workloads
    active     30% <= cpu <= 75%  OR  >=1 workload  OR  load > cores*0.75
    saturated  cpu > 75%  OR  load > cores
    """
    cpu_count = max(cpu_count, 1)

    if cpu_pct > _THRESH_SATURATED_CPU or load_1m > cpu_count:
        return "saturated"

    if (
        cpu_pct >= _THRESH_ACTIVE_CPU
        or workloads
        or load_1m > cpu_count * 0.75
    ):
        return "active"

    return "idle"


__all__ = [
    "MATCHERS",
    "WorkloadMatcher",
    "compute_busy_state",
    "detect_workloads",
    "sample_host",
    "warmup",
]
