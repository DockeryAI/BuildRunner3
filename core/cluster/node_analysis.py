"""
BR3 Cluster — Log Analysis (runs on Muddy)
Pattern detection, cross-file correlation, error fingerprinting.
Reads logs directly from local project directories — no SSH sync needed.

Run: uvicorn core.cluster.node_analysis:app --host 0.0.0.0 --port 8200
"""

import os
import re
import time
import json
import sqlite3
import hashlib
import threading
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import FastAPI
from pydantic import BaseModel

from core.cluster.base_service import create_app

# --- Config ---
# On Muddy, logs are local — no SSH sync needed
PROJECTS_DIR = os.environ.get("PROJECTS_DIR", os.path.expanduser("~/Projects"))
DB_PATH = os.environ.get("ANALYSIS_DB", os.path.expanduser("~/.buildrunner/analysis.db"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))

# --- App ---
app = create_app(role="log-analysis", version="0.1.0")

# --- State ---
_analyzing = False
_last_analysis_time = 0.0
_active_patterns = []
_known_fingerprints: set[str] = set()
_resolved_fingerprints: set[str] = set()

# Remove LOG_DIR — not needed when running locally
LOG_DIR = None  # kept for compatibility but unused


# --- SQLite Setup ---
def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS log_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            log_type TEXT NOT NULL,
            event_type TEXT,
            level TEXT,
            message TEXT,
            method TEXT,
            url TEXT,
            status_code INTEGER,
            duration_ms INTEGER,
            response_size INTEGER,
            payload TEXT,
            project TEXT,
            ingested_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            first_seen TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now')),
            resolved INTEGER DEFAULT 0,
            fingerprint TEXT,
            details TEXT
        );

        CREATE TABLE IF NOT EXISTS correlations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            sources TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            details TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_entries_ts ON log_entries(timestamp);
        CREATE INDEX IF NOT EXISTS idx_entries_type ON log_entries(log_type);
        CREATE INDEX IF NOT EXISTS idx_entries_level ON log_entries(level) WHERE level IN ('error', 'warn');
        CREATE INDEX IF NOT EXISTS idx_patterns_resolved ON patterns(resolved);
        CREATE INDEX IF NOT EXISTS idx_patterns_severity ON patterns(severity);

        CREATE VIRTUAL TABLE IF NOT EXISTS log_fts USING fts5(
            message, url, content='log_entries', content_rowid='id', detail='none'
        );
    """)
    conn.commit()


# --- Log Parsing ---
SUPABASE_RE = re.compile(
    r'\[(.+?)\]\s+\[(\w+)\]\s+(\w+)\s+(.+?)\s+(\d+)\s+(\d+)ms\s+(\d+)b'
)
BROWSER_RE = re.compile(
    r'\[(.+?)\]\s+\[(\w+)\]\s+(.*)'
)
WARNING_RE = re.compile(r'^\s+[⚠!]\s+(\w+)\s+[—-]\s+(.*)')


def _parse_supabase_log(filepath: str) -> list[dict]:
    entries = []
    try:
        lines = Path(filepath).read_text(errors="replace").split("\n")
    except Exception:
        return []

    current = None
    for line in lines[-500:]:  # Last 500 lines
        m = SUPABASE_RE.match(line)
        if m:
            if current:
                entries.append(current)
            status = int(m.group(5))
            size = int(m.group(7))
            level = "error" if status >= 500 else "warn" if status >= 400 or (status == 200 and size == 0) else "info"
            current = {
                "timestamp": m.group(1), "log_type": "supabase",
                "event_type": m.group(2).lower(), "method": m.group(3),
                "url": m.group(4), "status_code": status,
                "duration_ms": int(m.group(6)), "response_size": size,
                "level": level, "message": line.strip(),
            }
            continue

        w = WARNING_RE.match(line)
        if w and current:
            current["payload"] = json.dumps({"warning": w.group(1), "detail": w.group(2)})
            current["level"] = "warn"
            continue

        e = BROWSER_RE.match(line)
        if e:
            if current:
                entries.append(current)
            current = {
                "timestamp": e.group(1), "log_type": "supabase",
                "event_type": e.group(2).lower(), "level": "info",
                "message": e.group(3),
            }

    if current:
        entries.append(current)
    return entries


def _parse_browser_log(filepath: str) -> list[dict]:
    entries = []
    try:
        lines = Path(filepath).read_text(errors="replace").split("\n")
    except Exception:
        return []

    for line in lines[-500:]:
        m = BROWSER_RE.match(line)
        if m:
            level = m.group(2).lower()
            if level in ("error", "err"):
                level = "error"
            elif level in ("warn", "warning"):
                level = "warn"
            entries.append({
                "timestamp": m.group(1), "log_type": "browser",
                "event_type": "console", "level": level,
                "message": m.group(3),
            })
    return entries


def _parse_generic_log(filepath: str, log_type: str) -> list[dict]:
    entries = []
    try:
        lines = Path(filepath).read_text(errors="replace").split("\n")
    except Exception:
        return []

    for line in lines[-500:]:
        m = BROWSER_RE.match(line)
        if m:
            entries.append({
                "timestamp": m.group(1), "log_type": log_type,
                "event_type": m.group(2).lower(),
                "level": "info", "message": m.group(3),
            })
    return entries


# --- Error Fingerprinting ---
def _fingerprint(entry: dict) -> str:
    msg = entry.get("message", "")
    # Strip variable parts
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}T[\d:.]+Z?', '<TS>', msg)
    normalized = re.sub(r'\b[0-9a-f]{8,}\b', '<HEX>', normalized, flags=re.I)
    normalized = re.sub(r'\b\d{3,}\b', '<N>', normalized)
    normalized = re.sub(r'"[^"]{20,}"', '"<STR>"', normalized)

    raw = f"{entry.get('level', '')}:{entry.get('log_type', '')}:{normalized}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# --- Pattern Detection ---
def _detect_patterns(entries: list[dict]) -> list[dict]:
    patterns = []

    # Group by log_type
    by_type = defaultdict(list)
    for e in entries:
        by_type[e.get("log_type", "unknown")].append(e)

    # --- Auth refresh loop ---
    auth_events = [e for e in entries if "TOKEN_REFRESHED" in e.get("message", "") or "token" in e.get("message", "").lower()]
    if len(auth_events) >= 5:
        # Check for rapid succession (5+ in 30 seconds)
        patterns.append({
            "pattern_type": "auth_refresh_loop",
            "severity": "critical",
            "description": f"{len(auth_events)} auth token events detected — possible refresh loop",
            "count": len(auth_events),
        })

    # --- RLS denial spike ---
    supabase_entries = by_type.get("supabase", [])
    queries = [e for e in supabase_entries if e.get("event_type") == "query"]
    empty_200s = [e for e in queries if e.get("status_code") == 200 and e.get("response_size") == 0]
    if len(queries) >= 10 and len(empty_200s) / len(queries) > 0.3:
        patterns.append({
            "pattern_type": "rls_denial_spike",
            "severity": "high",
            "description": f"{len(empty_200s)}/{len(queries)} queries returning empty (RLS denial)",
            "count": len(empty_200s),
        })
    elif len(empty_200s) >= 3:
        patterns.append({
            "pattern_type": "rls_denial",
            "severity": "medium",
            "description": f"{len(empty_200s)} RLS denials (EMPTY_200)",
            "count": len(empty_200s),
        })

    # --- Server errors ---
    server_errors = [e for e in entries if e.get("status_code", 0) >= 500]
    if server_errors:
        patterns.append({
            "pattern_type": "server_error",
            "severity": "high",
            "description": f"{len(server_errors)} server errors (5xx)",
            "count": len(server_errors),
        })

    # --- Latency degradation ---
    timed_entries = [e for e in supabase_entries if e.get("duration_ms") and e.get("duration_ms") > 0]
    if len(timed_entries) >= 10:
        avg_duration = sum(e["duration_ms"] for e in timed_entries) / len(timed_entries)
        slow = [e for e in timed_entries if e["duration_ms"] > 800]
        if avg_duration > 500 or len(slow) > len(timed_entries) * 0.2:
            patterns.append({
                "pattern_type": "latency_degradation",
                "severity": "high" if avg_duration > 800 else "medium",
                "description": f"Avg latency {avg_duration:.0f}ms, {len(slow)} slow requests (>800ms)",
                "count": len(slow),
            })

    # --- Network errors ---
    net_errors = [e for e in by_type.get("device", []) if "network" in e.get("message", "").lower() or "offline" in e.get("message", "").lower()]
    if len(net_errors) >= 3:
        patterns.append({
            "pattern_type": "network_error",
            "severity": "medium",
            "description": f"{len(net_errors)} network errors in device log",
            "count": len(net_errors),
        })

    # --- New errors (never seen before) ---
    for e in entries:
        if e.get("level") in ("error", "err"):
            fp = _fingerprint(e)
            if fp not in _known_fingerprints:
                _known_fingerprints.add(fp)
                patterns.append({
                    "pattern_type": "new_error",
                    "severity": "medium",
                    "description": f"New error: {e.get('message', '')[:100]}",
                    "count": 1,
                    "fingerprint": fp,
                })
            if fp in _resolved_fingerprints:
                patterns.append({
                    "pattern_type": "regression",
                    "severity": "critical",
                    "description": f"Regression: {e.get('message', '')[:100]}",
                    "count": 1,
                    "fingerprint": fp,
                })

    # --- JS errors ---
    js_errors = [e for e in by_type.get("browser", []) if e.get("level") == "error"]
    if js_errors:
        # Group by fingerprint
        by_fp = defaultdict(list)
        for e in js_errors:
            by_fp[_fingerprint(e)].append(e)

        for fp, group in by_fp.items():
            if len(group) >= 3:
                patterns.append({
                    "pattern_type": "repeated_error",
                    "severity": "medium",
                    "description": f"{len(group)}x: {group[0].get('message', '')[:100]}",
                    "count": len(group),
                    "fingerprint": fp,
                })

    return patterns


# --- Cross-File Correlation ---
def _correlate(entries: list[dict]) -> list[dict]:
    correlations = []

    # Sort by timestamp
    timed = [e for e in entries if e.get("timestamp")]
    timed.sort(key=lambda e: e.get("timestamp", ""))

    # Build time-indexed buckets (500ms windows)
    buckets = defaultdict(list)
    for e in timed:
        try:
            ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
            bucket_key = int(ts.timestamp() * 2)  # 500ms buckets
            buckets[bucket_key].append(e)
        except (ValueError, KeyError):
            continue

    for bucket_key, bucket_entries in buckets.items():
        sources = set(e.get("log_type") for e in bucket_entries)
        if len(sources) < 2:
            continue  # Only multi-source buckets are interesting

        # Rule: Auth failure + browser redirect
        has_auth_fail = any(e.get("status_code") in (401, 403) for e in bucket_entries)
        has_redirect = any("redirect" in e.get("message", "").lower() or "login" in e.get("message", "").lower() for e in bucket_entries)
        if has_auth_fail and has_redirect:
            correlations.append({
                "rule_name": "Auth Cascade",
                "severity": "critical",
                "description": "Auth failure causing redirect — possible auth cascade",
                "sources": list(sources),
            })

        # Rule: EMPTY_200 + empty UI state
        has_empty_200 = any(e.get("status_code") == 200 and e.get("response_size") == 0 for e in bucket_entries)
        has_empty_ui = any("undefined" in e.get("message", "").lower() or "null" in e.get("message", "").lower() or "empty" in e.get("message", "").lower() for e in bucket_entries)
        if has_empty_200 and has_empty_ui:
            correlations.append({
                "rule_name": "RLS Denial Chain",
                "severity": "high",
                "description": "RLS denial causing empty UI state",
                "sources": list(sources),
            })

        # Rule: Slow query + stale/refetch
        has_slow = any(e.get("duration_ms", 0) > 1000 for e in bucket_entries)
        has_stale = any("stale" in e.get("message", "").lower() or "refetch" in e.get("message", "").lower() for e in bucket_entries)
        if has_slow and has_stale:
            correlations.append({
                "rule_name": "Slow Query Impact",
                "severity": "medium",
                "description": "Slow DB query causing React Query staleness",
                "sources": list(sources),
            })

    return correlations


# --- Log Sync (SSH tail from Muddy) ---
_sync_processes = {}


def _discover_projects() -> list[str]:
    """Discover all BR3 projects by looking for .buildrunner/ directories locally."""
    projects = []
    projects_dir = Path(PROJECTS_DIR)
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if d.is_dir() and (d / ".buildrunner").exists():
                projects.append(d.name)
    return projects if projects else ["Synapse", "workfloDock", "BuildRunner3"]


_known_projects: set[str] = set()


# --- Analysis Loop ---
def _analysis_loop():
    global _analyzing, _last_analysis_time, _active_patterns

    while True:
        time.sleep(POLL_INTERVAL)

        if _analyzing:
            continue

        _analyzing = True
        try:
            all_entries = []
            projects = _discover_projects()

            # Read logs directly from local project directories
            for project in projects:
                if project not in _known_projects:
                    _known_projects.add(project)

                project_dir = Path(PROJECTS_DIR) / project / ".buildrunner"
                if not project_dir.exists():
                    continue

                supa_log = project_dir / "supabase.log"
                if supa_log.exists():
                    entries = _parse_supabase_log(str(supa_log))
                    for e in entries:
                        e["project"] = project
                    all_entries.extend(entries)

                browser_log = project_dir / "browser.log"
                if browser_log.exists():
                    entries = _parse_browser_log(str(browser_log))
                    for e in entries:
                        e["project"] = project
                    all_entries.extend(entries)

                for logname, logtype in [("device.log", "device"), ("query.log", "query")]:
                    logpath = project_dir / logname
                    if logpath.exists():
                        entries = _parse_generic_log(str(logpath), logtype)
                        for e in entries:
                            e["project"] = project
                        all_entries.extend(entries)

            if not all_entries:
                _analyzing = False
                continue

            # Detect patterns
            patterns = _detect_patterns(all_entries)

            # Cross-file correlation
            correlations = _correlate(all_entries)

            # Store patterns — deduplicate by pattern_type + project
            conn = _get_db()
            # Clear non-fingerprinted patterns each cycle (they're recalculated)
            conn.execute("DELETE FROM patterns WHERE fingerprint IS NULL AND resolved = 0")
            for p in patterns:
                fp = p.get("fingerprint") or hashlib.md5(f"{p['pattern_type']}:{p.get('description','')}".encode()).hexdigest()[:12]
                existing = conn.execute("SELECT id FROM patterns WHERE fingerprint = ? AND resolved = 0", (fp,)).fetchone()
                if existing:
                    conn.execute("UPDATE patterns SET count = ?, last_seen = datetime('now'), description = ? WHERE id = ?",
                                 (p.get("count", 1), p["description"], existing["id"]))
                else:
                    conn.execute(
                        """INSERT INTO patterns (pattern_type, severity, description, count, fingerprint, details)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (p["pattern_type"], p["severity"], p["description"],
                         p.get("count", 1), fp, json.dumps(p))
                    )

            for c in correlations:
                conn.execute(
                    """INSERT INTO correlations (rule_name, severity, description, sources, details)
                       VALUES (?, ?, ?, ?, ?)""",
                    (c["rule_name"], c["severity"], c["description"],
                     json.dumps(c.get("sources", [])), json.dumps(c))
                )

            # Retain only last 7 days
            conn.execute("DELETE FROM patterns WHERE last_seen < datetime('now', '-7 days') AND resolved = 1")
            conn.execute("DELETE FROM correlations WHERE timestamp < datetime('now', '-7 days')")

            conn.commit()
            conn.close()

            _active_patterns = patterns
            _last_analysis_time = time.time()

            if patterns:
                print(f"Analysis: {len(patterns)} patterns, {len(correlations)} correlations")

        except Exception as e:
            print(f"Analysis error: {e}")
        finally:
            _analyzing = False


@app.on_event("startup")
async def startup():
    t = threading.Thread(target=_analysis_loop, daemon=True)
    t.start()


# --- API Endpoints ---
@app.get("/api/logs/analyze")
async def analyze(project: Optional[str] = None):
    """Get pre-analyzed log summary — designed for SessionStart hook injection."""
    conn = _get_db()

    if project:
        patterns = conn.execute(
            "SELECT * FROM patterns WHERE resolved = 0 ORDER BY severity, count DESC"
        ).fetchall()
    else:
        patterns = conn.execute(
            "SELECT * FROM patterns WHERE resolved = 0 ORDER BY severity, count DESC LIMIT 20"
        ).fetchall()

    conn.close()

    # Build token-efficient summary
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_patterns = sorted([dict(p) for p in patterns], key=lambda p: severity_order.get(p["severity"], 9))

    severity_icons = {"critical": "!!!", "high": "!!", "medium": "!", "low": ""}

    summary_lines = []
    for p in sorted_patterns[:10]:
        icon = severity_icons.get(p["severity"], "")
        summary_lines.append(f"{icon} {p['pattern_type']}: {p['description']} ({p['count']}x)")

    return {
        "summary": "\n".join(summary_lines) if summary_lines else "No active patterns",
        "patterns": sorted_patterns[:10],
        "total_patterns": len(patterns),
        "last_analysis": _last_analysis_time,
    }


@app.get("/api/logs/patterns")
async def get_patterns(resolved: bool = False):
    """Get active or resolved patterns."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM patterns WHERE resolved = ? ORDER BY severity, last_seen DESC",
        (1 if resolved else 0,)
    ).fetchall()
    conn.close()
    return {"patterns": [dict(r) for r in rows]}


@app.get("/api/logs/correlations")
async def get_correlations(limit: int = 20):
    """Get cross-file event correlations."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM correlations ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return {"correlations": [dict(r) for r in rows]}


@app.get("/api/logs/search")
async def search_logs(q: str, limit: int = 20):
    """Full-text search across all log entries."""
    conn = _get_db()
    try:
        rows = conn.execute(
            """SELECT l.* FROM log_entries l
               JOIN log_fts f ON l.id = f.rowid
               WHERE log_fts MATCH ? ORDER BY l.timestamp DESC LIMIT ?""",
            (q, limit)
        ).fetchall()
    except Exception:
        rows = conn.execute(
            "SELECT * FROM log_entries WHERE message LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{q}%", limit)
        ).fetchall()
    conn.close()
    return {"results": [dict(r) for r in rows]}


@app.post("/api/logs/resolve")
async def resolve_pattern(fingerprint: str):
    """Mark a pattern as resolved (for regression detection)."""
    _resolved_fingerprints.add(fingerprint)
    conn = _get_db()
    conn.execute("UPDATE patterns SET resolved = 1 WHERE fingerprint = ?", (fingerprint,))
    conn.commit()
    conn.close()
    return {"status": "resolved"}


@app.post("/api/migration/dryrun")
async def migration_dryrun(project: Optional[str] = None):
    """Run migrations against local Supabase sandbox. Returns pass/fail."""
    # Check if Supabase is available
    try:
        result = subprocess.run(
            ["supabase", "status"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"status": "supabase_not_running", "message": "Run 'supabase start' on Crawford first"}
    except Exception:
        return {"status": "supabase_not_available", "message": "Supabase CLI not found"}

    # Run db reset (applies all migrations from scratch)
    try:
        result = subprocess.run(
            ["supabase", "db", "reset"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return {"status": "pass", "message": "All migrations applied successfully"}
        else:
            return {
                "status": "fail",
                "message": "Migration failed",
                "error": result.stderr[-500:] if result.stderr else result.stdout[-500:],
            }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Migration timed out after 120s"}


@app.get("/api/logs/stats")
async def log_stats():
    """Log analysis statistics."""
    return {
        "analyzing": _analyzing,
        "last_analysis": _last_analysis_time,
        "active_patterns": len(_active_patterns),
        "known_fingerprints": len(_known_fingerprints),
        "resolved_fingerprints": len(_resolved_fingerprints),
        "projects_monitored": list(_known_projects),
        "mode": "local",
    }
